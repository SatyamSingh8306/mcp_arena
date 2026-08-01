"""Audio processing MCP server: info, conversion, editing, effects, analysis."""
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer

try:
    from pydub import AudioSegment as _AudioSegment
except ImportError:
    _AudioSegment = None

try:
    import librosa as _librosa
except ImportError:
    _librosa = None

try:
    import numpy as _np
except ImportError:
    _np = None


def _ensure_pydub():
    if _AudioSegment is None:
        raise ImportError("pydub is required. pip install pydub")
    return _AudioSegment


def _ensure_librosa():
    if _librosa is None:
        raise ImportError("librosa is required. pip install librosa")
    return _librosa


def _ensure_numpy():
    if _np is None:
        raise ImportError("numpy is required. pip install numpy")
    return _np


class AudioMCPServer(BaseMCPServer):
    """Audio processing MCP server (pydub + librosa)."""
    _REQUIRED_EXTRAS = {"librosa": "audio", "numpy": "audio", "pydub": "audio"}

    def __init__(
        self,
        default_output_dir: Optional[str] = None,
        default_format: str = "mp3",
        default_bitrate: str = "192k",
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.default_output_dir = default_output_dir or os.path.join(os.getcwd(), "audio_output")
        self.default_format = default_format
        self.default_bitrate = default_bitrate
        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)

        super().__init__(
            name="Audio Processing MCP Server",
            description="MCP server for audio processing (pydub + librosa)",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _register_tools(self) -> None:
        """Register all audio processing tools."""
        self._register_info_tools()
        self._register_conversion_tools()
        self._register_editing_tools()
        self._register_effects_tools()
        self._register_analysis_tools()

    def _register_info_tools(self):
        """Register audio information tools."""

        @self.mcp_server.tool()
        def get_audio_info(audio_path: str) -> Dict[str, Any]:
            """Get detailed information about an audio file."""
            try:
                audio = _ensure_pydub().from_file(audio_path)
                return {
                    "success": True,
                    "info": {
                        "path": audio_path,
                        "filename": os.path.basename(audio_path),
                        "duration_seconds": len(audio) / 1000.0,
                        "channels": audio.channels,
                        "sample_rate": audio.frame_rate,
                        "sample_width": audio.sample_width,
                        "frame_count": audio.frame_count(),
                        "format": os.path.splitext(audio_path)[1][1:],
                        "size_bytes": os.path.getsize(audio_path),
                    },
                }
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def analyze_audio(audio_path: str) -> Dict[str, Any]:
            """Analyze audio characteristics using librosa."""
            try:
                librosa = _ensure_librosa()
                y, sr = librosa.load(audio_path, sr=None)
                duration = len(y) / sr
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
                spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr).mean()
                rms = librosa.feature.rms(y=y).mean()

                return {
                    "success": True,
                    "duration_seconds": round(duration, 2),
                    "sample_rate": sr,
                    "tempo_bpm": round(float(tempo), 1),
                    "spectral_centroid_hz": round(float(spectral_centroid), 1),
                    "spectral_rolloff_hz": round(float(spectral_rolloff), 1),
                    "rms_energy": round(float(rms), 4),
                }
            except Exception as exc:
                return {"error": str(exc)}

    def _register_conversion_tools(self):
        """Register audio conversion tools."""

        @self.mcp_server.tool()
        def convert_audio(
            input_path: str,
            output_format: str = "mp3",
            output_path: Optional[str] = None,
            bitrate: str = "192k",
            sample_rate: Optional[int] = None
        ) -> Dict[str, Any]:
            """Convert audio to a different format."""
            try:
                AudioSegment = _ensure_pydub()
                audio = AudioSegment.from_file(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}.{output_format}"
                    )

                if sample_rate:
                    audio = audio.set_frame_rate(sample_rate)

                audio.export(output_path, format=output_format, bitrate=bitrate)

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "output_format": output_format,
                    "output_size": os.path.getsize(output_path)
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def batch_convert(
            input_paths: List[str],
            output_format: str = "mp3",
            bitrate: str = "192k"
        ) -> Dict[str, Any]:
            """Convert multiple audio files."""
            results = []
            for path in input_paths:
                result = convert_audio(path, output_format, None, bitrate)
                results.append(result)
            return {
                "success": True,
                "total": len(input_paths),
                "converted": len([r for r in results if r.get("success")]),
                "results": results
            }

    def _register_editing_tools(self):
        """Register audio editing tools."""

        @self.mcp_server.tool()
        def trim_audio(
            input_path: str,
            start_time: float,
            end_time: float,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Trim audio to specified time range."""
            try:
                AudioSegment = _ensure_pydub()
                audio = AudioSegment.from_file(input_path)

                start_ms = int(start_time * 1000)
                end_ms = int(end_time * 1000)

                trimmed = audio[start_ms:end_ms]

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_trimmed.{self.default_format}"
                    )

                trimmed.export(output_path, format=self.default_format)

                return {
                    "success": True,
                    "output_path": output_path,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": end_time - start_time
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def concatenate_audio(
            audio_paths: List[str],
            output_path: Optional[str] = None,
            crossfade: int = 0
        ) -> Dict[str, Any]:
            """Concatenate multiple audio files."""
            try:
                AudioSegment = _ensure_pydub()

                segments = [AudioSegment.from_file(path) for path in audio_paths]

                if crossfade > 0:
                    combined = segments[0]
                    for seg in segments[1:]:
                        combined = combined.append(seg, crossfade=crossfade)
                else:
                    combined = sum(segments)

                if output_path is None:
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"concatenated.{self.default_format}"
                    )

                combined.export(output_path, format=self.default_format)

                return {
                    "success": True,
                    "output_path": output_path,
                    "files_concatenated": len(audio_paths),
                    "total_duration": len(combined) / 1000.0
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def split_audio(
            input_path: str,
            segment_duration: float,
            output_dir: Optional[str] = None
        ) -> Dict[str, Any]:
            """Split audio into segments."""
            try:
                AudioSegment = _ensure_pydub()
                audio = AudioSegment.from_file(input_path)

                if output_dir is None:
                    output_dir = self.default_output_dir

                segment_ms = int(segment_duration * 1000)
                output_files = []

                for i, start in enumerate(range(0, len(audio), segment_ms)):
                    segment = audio[start:start + segment_ms]
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        output_dir,
                        f"{base_name}_segment_{i+1}.{self.default_format}"
                    )
                    segment.export(output_path, format=self.default_format)
                    output_files.append(output_path)

                return {
                    "success": True,
                    "output_files": output_files,
                    "segment_count": len(output_files)
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def change_volume(
            input_path: str,
            volume_change: float,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Change audio volume (dB)."""
            try:
                AudioSegment = _ensure_pydub()
                audio = AudioSegment.from_file(input_path)

                adjusted = audio + volume_change

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_volume.{self.default_format}"
                    )

                adjusted.export(output_path, format=self.default_format)

                return {
                    "success": True,
                    "output_path": output_path,
                    "volume_change_db": volume_change
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def normalize_audio(
            input_path: str,
            target_dBFS: float = -20.0,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Normalize audio to target dBFS."""
            try:
                AudioSegment = _ensure_pydub()
                audio = AudioSegment.from_file(input_path)

                change_in_dBFS = target_dBFS - audio.dBFS
                normalized = audio.apply_gain(change_in_dBFS)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_normalized.{self.default_format}"
                    )

                normalized.export(output_path, format=self.default_format)

                return {
                    "success": True,
                    "output_path": output_path,
                    "target_dBFS": target_dBFS
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_effects_tools(self):
        """Register audio effects tools."""

        @self.mcp_server.tool()
        def add_fade(
            input_path: str,
            fade_in: float = 0.0,
            fade_out: float = 0.0,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add fade in/out effects to audio."""
            try:
                AudioSegment = _ensure_pydub()
                audio = AudioSegment.from_file(input_path)

                if fade_in > 0:
                    audio = audio.fade_in(int(fade_in * 1000))
                if fade_out > 0:
                    audio = audio.fade_out(int(fade_out * 1000))

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_fade.{self.default_format}"
                    )

                audio.export(output_path, format=self.default_format)

                return {
                    "success": True,
                    "output_path": output_path,
                    "fade_in_seconds": fade_in,
                    "fade_out_seconds": fade_out
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def change_speed(
            input_path: str,
            speed_factor: float,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Change audio playback speed."""
            try:
                AudioSegment = _ensure_pydub()
                audio = AudioSegment.from_file(input_path)

                # Change speed by adjusting frame rate
                new_frame_rate = int(audio.frame_rate * speed_factor)
                audio._spawn = audio._spawn._spawn
                sped_up = audio._spawn(audio.raw_data, overrides={
                    "frame_rate": new_frame_rate
                }).set_frame_rate(audio.frame_rate)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_speed.{self.default_format}"
                    )

                sped_up.export(output_path, format=self.default_format)

                return {
                    "success": True,
                    "output_path": output_path,
                    "speed_factor": speed_factor,
                    "new_duration": len(sped_up) / 1000.0
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_echo(
            input_path: str,
            delay: float = 0.5,
            decay: float = 0.5,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add echo effect to audio."""
            try:
                AudioSegment = _ensure_pydub()
                audio = AudioSegment.from_file(input_path)

                # Create delayed copy
                delay_ms = int(delay * 1000)
                echo = audio - 10  # Reduce volume
                echo = echo.overlay(audio, position=delay_ms)

                # Mix original and echo
                result = audio.overlay(echo)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_echo.{self.default_format}"
                    )

                result.export(output_path, format=self.default_format)

                return {
                    "success": True,
                    "output_path": output_path,
                    "delay_seconds": delay,
                    "decay": decay
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def reverse_audio(
            input_path: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Reverse audio playback."""
            try:
                AudioSegment = _ensure_pydub()
                audio = AudioSegment.from_file(input_path)

                reversed_audio = audio.reverse()

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_reversed.{self.default_format}"
                    )

                reversed_audio.export(output_path, format=self.default_format)

                return {
                    "success": True,
                    "output_path": output_path
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_analysis_tools(self):
        """Register audio analysis tools."""

        @self.mcp_server.tool()
        def detect_beats(
            audio_path: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Detect beats in audio."""
            try:
                librosa = _ensure_librosa()
                y, sr = librosa.load(audio_path, sr=None)

                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                beat_times = librosa.frames_to_time(beats, sr=sr)

                return {
                    "success": True,
                    "tempo_bpm": float(tempo),
                    "beat_count": len(beats),
                    "beat_times": [round(float(t), 3) for t in beat_times.tolist()]
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def extract_mfcc(
            audio_path: str,
            n_mfcc: int = 13
        ) -> Dict[str, Any]:
            """Extract MFCC features from audio."""
            try:
                librosa = _ensure_librosa()
                y, sr = librosa.load(audio_path, sr=None)

                mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)

                return {
                    "success": True,
                    "n_mfcc": n_mfcc,
                    "mfcc_shape": list(mfccs.shape),
                    "mfcc_mean": [round(float(x), 4) for x in mfccs.mean(axis=1).tolist()]
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def get_spectrogram(audio_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
            """Generate spectrogram data for audio."""
            try:
                librosa = _ensure_librosa()
                np = _ensure_numpy()
                y, sr = librosa.load(audio_path, sr=None)
                D = librosa.stft(y)
                S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)
                return {
                    "success": True,
                    "sample_rate": sr,
                    "spectrogram_shape": list(S_db.shape),
                    "frequency_bins": S_db.shape[0],
                    "time_frames": S_db.shape[1],
                }
            except Exception as exc:
                return {"error": str(exc)}

