"""Video editing MCP server (MoviePy + FFmpeg)."""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from mcp_arena.mcp.server import BaseMCPServer

try:
    from moviepy.editor import (
        ImageClip as _ImageClip,
        VideoFileClip as _VideoFileClip,
        AudioFileClip as _AudioFileClip,
        CompositeVideoClip as _CompositeVideoClip,
        concatenate_videoclips as _concatenate_videoclips,
        ColorClip as _ColorClip,
        TextClip as _TextClip,
    )
except ImportError:
    _ImageClip = _VideoFileClip = _AudioFileClip = None
    _CompositeVideoClip = _concatenate_videoclips = _ColorClip = _TextClip = None

try:
    from moviepy.video.fx import all as _vfx
except ImportError:
    _vfx = None

try:
    import numpy as _np
except ImportError:
    _np = None


# ponytail: these dict lookups replace the deleted `Resolution`/`TransitionType`
# enums; avoids re-creating strings each call.
_RESOLUTIONS = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k": (3840, 2160),
}


def _ensure_moviepy():
    if _VideoFileClip is None:
        raise ImportError("moviepy is required. pip install moviepy")
    if _np is None:
        raise ImportError("numpy is required. pip install numpy")
    return _VideoFileClip



class VideoMCPServer(BaseMCPServer):
    """Video Editing MCP Server for advanced video manipulation."""

    def __init__(
        self,
        default_output_dir: Optional[str] = None,
        default_format: str = "mp4",
        default_fps: int = 30,
        default_codec: str = "libx264",
        default_audio_codec: str = "aac",
        ffmpeg_path: Optional[str] = None,
        temp_dir: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Video Editing MCP Server.

        Args:
            default_output_dir: Default directory for output files
            default_format: Default output video format
            default_fps: Default frames per second
            default_codec: Default video codec
            default_audio_codec: Default audio codec
            ffmpeg_path: Path to FFmpeg executable
            temp_dir: Temporary directory for processing
            host: Host to run MCP server on
            port: Port to run MCP server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.default_output_dir = default_output_dir or os.path.join(os.getcwd(), "video_output")
        self.default_format = default_format
        self.default_fps = default_fps
        self.default_codec = default_codec
        self.default_audio_codec = default_audio_codec
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"
        self.temp_dir = temp_dir or os.path.join(os.getcwd(), "video_temp")
        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        self._active_clips: Dict[str, Any] = {}

        super().__init__(
            name="Video Editing MCP Server",
            description="MCP server for video editing (MoviePy + FFmpeg)",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _get_resolution(self, preset: str) -> Tuple[int, int]:
        return _RESOLUTIONS.get(preset, _RESOLUTIONS["1080p"])

    def _run_ffmpeg(self, args: List[str]) -> Dict[str, Any]:
        """Run FFmpeg command."""
        try:
            cmd = [self.ffmpeg_path] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "FFmpeg command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "FFmpeg not found. Please install FFmpeg."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _register_tools(self) -> None:
        """Register all video editing tools."""
        self._register_info_tools()
        self._register_conversion_tools()
        self._register_basic_editing_tools()
        self._register_effects_tools()
        self._register_audio_tools()
        self._register_text_tools()
        self._register_advanced_tools()
        self._register_gif_tools()

    def _register_info_tools(self):
        """Register video information tools."""

        @self.mcp_server.tool()
        def get_video_info(video_path: str) -> Dict[str, Any]:
            """Get detailed information about a video file.

            Args:
                video_path: Path to the video file
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(video_path)

                info = {
                    "path": video_path,
                    "filename": os.path.basename(video_path),
                    "duration": clip.duration,
                    "fps": clip.fps,
                    "width": clip.w,
                    "height": clip.h,
                    "resolution": f"{clip.w}x{clip.h}",
                    "aspect_ratio": clip.w / clip.h if clip.h > 0 else 0,
                    "has_audio": clip.audio is not None,
                    "audio_fps": clip.audio.fps if clip.audio else None,
                    "audio_channels": clip.audio.nchannels if clip.audio else None,
                    "size_bytes": os.path.getsize(video_path),
                    "format": os.path.splitext(video_path)[1][1:],
                    "bitrate": None,
                }

                clip.close()
                return {"success": True, "info": info}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def get_ffmpeg_info() -> Dict[str, Any]:
            """Get FFmpeg version and capabilities."""
            try:
                result = subprocess.run(
                    [self.ffmpeg_path, "-version"],
                    capture_output=True,
                    text=True
                )

                return {
                    "success": True,
                    "ffmpeg_available": result.returncode == 0,
                    "version": result.stdout.split('\n')[0] if result.returncode == 0 else None,
                    "output_dir": self.default_output_dir
                }
            except Exception as e:
                return {
                    "success": False,
                    "ffmpeg_available": False,
                    "error": str(e)
                }

    def _register_conversion_tools(self):
        """Register video conversion tools."""

        @self.mcp_server.tool()
        def convert_video(
            input_path: str,
            output_format: str = "mp4",
            output_path: Optional[str] = None,
            codec: Optional[str] = None,
            audio_codec: Optional[str] = None,
            fps: Optional[int] = None,
            bitrate: Optional[str] = None
        ) -> Dict[str, Any]:
            """Convert video to a different format.

            Args:
                input_path: Path to input video file
                output_format: Output format (mp4, avi, mov, webm, mkv)
                output_path: Output file path (optional)
                codec: Video codec (libx264, libx265, vp9, etc.)
                audio_codec: Audio codec (aac, mp3, opus, etc.)
                fps: Frames per second
                bitrate: Video bitrate (e.g., '5M' for 5 Mbps)
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_converted.{output_format}"
                    )

                # Build write options
                write_kwargs = {
                    "fps": fps or self.default_fps,
                    "codec": codec or self.default_codec,
                    "audio_codec": audio_codec or self.default_audio_codec
                }

                if bitrate:
                    write_kwargs["bitrate"] = bitrate

                clip.write_videofile(output_path, **write_kwargs)
                clip.close()

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
        def compress_video(
            input_path: str,
            output_path: Optional[str] = None,
            target_size_mb: Optional[float] = None,
            quality: str = "medium"
        ) -> Dict[str, Any]:
            """Compress video file size.

            Args:
                input_path: Path to input video
                output_path: Output file path
                target_size_mb: Target file size in MB
                quality: Quality preset (low, medium, high)
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_compressed.mp4"
                    )

                original_size_mb = os.path.getsize(input_path) / (1024 * 1024)

                # Calculate bitrate based on target size
                if target_size_mb:
                    duration = clip.duration
                    target_bitrate = (target_size_mb * 8 * 1024) / duration  # kbps
                    bitrate = f"{int(target_bitrate)}k"
                else:
                    quality_bitrates = {
                        "low": "1M",
                        "medium": "2.5M",
                        "high": "5M"
                    }
                    bitrate = quality_bitrates.get(quality, "2.5M")

                clip.write_videofile(
                    output_path,
                    bitrate=bitrate,
                    codec=self.default_codec,
                    audio_bitrate="128k"
                )
                clip.close()

                new_size_mb = os.path.getsize(output_path) / (1024 * 1024)

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "original_size_mb": round(original_size_mb, 2),
                    "compressed_size_mb": round(new_size_mb, 2),
                    "compression_ratio": round(original_size_mb / new_size_mb, 2) if new_size_mb > 0 else 0
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def change_resolution(
            input_path: str,
            resolution: str = "1080p",
            output_path: Optional[str] = None,
            maintain_aspect_ratio: bool = True
        ) -> Dict[str, Any]:
            """Change video resolution.

            Args:
                input_path: Path to input video
                resolution: Target resolution (480p, 720p, 1080p, 1440p, 4k)
                output_path: Output file path
                maintain_aspect_ratio: Maintain aspect ratio
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_{resolution}.mp4"
                    )

                target_width, target_height = self._get_resolution(resolution)

                if maintain_aspect_ratio:
                    current_ratio = clip.w / clip.h
                    target_ratio = target_width / target_height

                    if current_ratio > target_ratio:
                        new_width = target_width
                        new_height = int(target_width / current_ratio)
                    else:
                        new_height = target_height
                        new_width = int(target_height * current_ratio)
                else:
                    new_width = target_width
                    new_height = target_height

                resized_clip = clip.resize(newsize=(new_width, new_height))
                resized_clip.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                resized_clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "original_resolution": f"{clip.w}x{clip.h}",
                    "new_resolution": f"{new_width}x{new_height}"
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_basic_editing_tools(self):
        """Register basic video editing tools."""

        @self.mcp_server.tool()
        def trim_video(
            input_path: str,
            start_time: float,
            end_time: float,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Trim a video to specified time range.

            Args:
                input_path: Path to input video
                start_time: Start time in seconds
                end_time: End time in seconds
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if end_time > clip.duration:
                    return {"error": f"End time {end_time} exceeds video duration {clip.duration}"}

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_trimmed.mp4"
                    )

                trimmed = clip.subclip(start_time, end_time)
                trimmed.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                trimmed.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": end_time - start_time
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def concatenate_videos(
            video_paths: List[str],
            output_path: Optional[str] = None,
            method: str = "compose"
        ) -> Dict[str, Any]:
            """Concatenate multiple videos into one.

            Args:
                video_paths: List of video file paths
                output_path: Output file path
                method: Concatenation method (compose, concat)
            """
            try:
                _ensure_moviepy()
                clips = [_VideoFileClip(path) for path in video_paths]

                if output_path is None:
                    output_path = os.path.join(
                        self.default_output_dir,
                        "concatenated_video.mp4"
                    )

                # Get the target resolution from the first clip
                target_size = (clips[0].w, clips[0].h)
                target_fps = clips[0].fps

                # Resize all clips to match the first one
                resized_clips = []
                for clip in clips:
                    if (clip.w, clip.h) != target_size:
                        resized = clip.resize(newsize=target_size)
                        resized_clips.append(resized)
                    else:
                        resized_clips.append(clip)

                # Concatenate
                final_clip = _concatenate_videoclips(resized_clips, method=method)
                final_clip.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=target_fps
                )

                # Cleanup
                for clip in clips + resized_clips:
                    clip.close()
                final_clip.close()

                return {
                    "success": True,
                    "output_path": output_path,
                    "input_count": len(video_paths),
                    "total_duration": final_clip.duration,
                    "resolution": f"{target_size[0]}x{target_size[1]}"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def split_video(
            input_path: str,
            segments: List[Dict[str, float]],
            output_prefix: Optional[str] = None
        ) -> Dict[str, Any]:
            """Split video into multiple segments.

            Args:
                input_path: Path to input video
                segments: List of segment definitions with 'start' and 'end' times
                output_prefix: Prefix for output files
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_prefix is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_prefix = os.path.join(self.default_output_dir, f"{base_name}_segment")

                output_files = []

                for i, segment in enumerate(segments):
                    start = segment.get("start", 0)
                    end = segment.get("end", clip.duration)

                    segment_clip = clip.subclip(start, end)
                    output_path = f"{output_prefix}_{i+1}.mp4"
                    segment_clip.write_videofile(
                        output_path,
                        codec=self.default_codec,
                        fps=self.default_fps
                    )
                    segment_clip.close()
                    output_files.append(output_path)

                clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_files": output_files,
                    "segments_count": len(output_files)
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def crop_video(
            input_path: str,
            x1: int,
            y1: int,
            x2: int,
            y2: int,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Crop video to specified region.

            Args:
                input_path: Path to input video
                x1, y1: Top-left corner coordinates
                x2, y2: Bottom-right corner coordinates
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_cropped.mp4"
                    )

                cropped = clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
                cropped.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                cropped.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "original_size": f"{clip.w}x{clip.h}",
                    "cropped_size": f"{x2-x1}x{y2-y1}"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def rotate_video(
            input_path: str,
            angle: float,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Rotate video by specified angle.

            Args:
                input_path: Path to input video
                angle: Rotation angle in degrees
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_rotated.mp4"
                    )

                rotated = clip.rotate(angle)
                rotated.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                rotated.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "rotation_angle": angle
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def set_video_speed(
            input_path: str,
            speed_factor: float,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Change video playback speed.

            Args:
                input_path: Path to input video
                speed_factor: Speed multiplier (0.5 = half speed, 2.0 = double speed)
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_speed.mp4"
                    )

                # Apply speed change
                new_clip = clip.speedx(speed_factor)
                new_clip.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                new_clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "original_duration": clip.duration,
                    "new_duration": new_clip.duration,
                    "speed_factor": speed_factor
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def reverse_video(
            input_path: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Reverse video playback.

            Args:
                input_path: Path to input video
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_reversed.mp4"
                    )

                reversed_clip = clip.time_mirror()
                reversed_clip.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                reversed_clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "duration": clip.duration
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_effects_tools(self):
        """Register video effects tools."""

        @self.mcp_server.tool()
        def add_fade_effect(
            input_path: str,
            fade_type: str = "both",
            duration: float = 1.0,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add fade in/out effect to video.

            Args:
                input_path: Path to input video
                fade_type: Type of fade (in, out, both)
                duration: Fade duration in seconds
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_fade.mp4"
                    )

                if fade_type in ["in", "both"]:
                    clip = clip.fadein(duration)
                if fade_type in ["out", "both"]:
                    clip = clip.fadeout(duration)

                clip.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "fade_type": fade_type,
                    "fade_duration": duration
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_color_effect(
            input_path: str,
            brightness: float = 1.0,
            contrast: float = 1.0,
            saturation: float = 1.0,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Adjust video color properties.

            Args:
                input_path: Path to input video
                brightness: Brightness multiplier (1.0 = normal)
                contrast: Contrast multiplier (1.0 = normal)
                saturation: Saturation multiplier (1.0 = normal)
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                from moviepy.video.fx import all as _vfx

                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_color.mp4"
                    )

                # Apply effects
                if brightness != 1.0:
                    clip = clip.fx(vfx.brightness, brightness)
                if contrast != 1.0:
                    clip = clip.fx(vfx.contrast, contrast)
                if saturation != 1.0:
                    clip = clip.fx(vfx.saturation, saturation)

                clip.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "brightness": brightness,
                    "contrast": contrast,
                    "saturation": saturation
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_blur_effect(
            input_path: str,
            blur_strength: int = 5,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add blur effect to video.

            Args:
                input_path: Path to input video
                blur_strength: Blur strength (1-20)
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                from moviepy.video.fx import all as _vfx

                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_blurred.mp4"
                    )

                blurred = clip.fx(vfx.blur, blur_strength)
                blurred.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                blurred.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "blur_strength": blur_strength
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_black_white_effect(
            input_path: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Convert video to black and white.

            Args:
                input_path: Path to input video
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                from moviepy.video.fx import all as _vfx

                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_bw.mp4"
                    )

                bw_clip = clip.fx(vfx.blackwhite)
                bw_clip.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                bw_clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_vignette_effect(
            input_path: str,
            intensity: float = 0.5,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add vignette effect to video.

            Args:
                input_path: Path to input video
                intensity: Vignette intensity (0.0-1.0)
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                import numpy as np

                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_vignette.mp4"
                    )

                def apply_vignette(get_frame, t):
                    frame = get_frame(t)
                    h, w = frame.shape[:2]
                    Y, X = np.ogrid[:h, :w]
                    center_y, center_x = h / 2, w / 2
                    dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
                    max_dist = np.sqrt(center_x**2 + center_y**2)
                    vignette = 1 - (dist / max_dist) * intensity
                    vignette = np.clip(vignette, 0, 1)
                    frame = frame * vignette[:, :, np.newaxis]
                    return frame.astype(np.uint8)

                vignette_clip = clip.fl(apply_vignette)
                vignette_clip.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                vignette_clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "intensity": intensity
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_zoom_effect(
            input_path: str,
            start_scale: float = 1.0,
            end_scale: float = 1.5,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add zoom in/out effect to video.

            Args:
                input_path: Path to input video
                start_scale: Starting scale (1.0 = 100%)
                end_scale: Ending scale
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                import numpy as np

                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_zoom.mp4"
                    )

                def zoom_effect(get_frame, t):
                    frame = get_frame(t)
                    progress = t / clip.duration
                    scale = start_scale + (end_scale - start_scale) * progress
                    h, w = frame.shape[:2]
                    new_h, new_w = int(h * scale), int(w * scale)

                    # Resize frame
                    from PIL import Image
                    img = Image.fromarray(frame)
                    img = img.resize((new_w, new_h), Image.LANCZOS)

                    # Crop center
                    left = (new_w - w) // 2
                    top = (new_h - h) // 2
                    img = img.crop((left, top, left + w, top + h))

                    return np.array(img)

                zoomed_clip = clip.fl(zoom_effect)
                zoomed_clip.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                zoomed_clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "start_scale": start_scale,
                    "end_scale": end_scale
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_audio_tools(self):
        """Register audio-related tools."""

        @self.mcp_server.tool()
        def extract_audio(
            input_path: str,
            output_format: str = "mp3",
            output_path: Optional[str] = None,
            audio_bitrate: str = "192k"
        ) -> Dict[str, Any]:
            """Extract audio from video.

            Args:
                input_path: Path to input video
                output_format: Audio format (mp3, wav, aac, ogg)
                output_path: Output file path
                audio_bitrate: Audio bitrate
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if clip.audio is None:
                    return {"error": "Video has no audio track"}

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}.{output_format}"
                    )

                clip.audio.write_audiofile(output_path, bitrate=audio_bitrate)
                clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "audio_format": output_format,
                    "audio_duration": clip.duration
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def replace_audio(
            video_path: str,
            audio_path: str,
            output_path: Optional[str] = None,
            volume: float = 1.0
        ) -> Dict[str, Any]:
            """Replace video audio with a new audio file.

            Args:
                video_path: Path to video file
                audio_path: Path to new audio file
                output_path: Output file path
                volume: Audio volume multiplier
            """
            try:
                _ensure_moviepy()
                video = _VideoFileClip(video_path)
                audio = _AudioFileClip(audio_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(video_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_new_audio.mp4"
                    )

                # Adjust audio to video duration
                if audio.duration > video.duration:
                    audio = audio.subclip(0, video.duration)
                elif audio.duration < video.duration:
                    # Loop or pad with silence
                    audio = audio.set_duration(video.duration)

                audio = audio.volumex(volume)
                final = video.set_audio(audio)
                final.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                video.close()
                audio.close()
                final.close()

                return {
                    "success": True,
                    "video_path": video_path,
                    "audio_path": audio_path,
                    "output_path": output_path
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_background_music(
            video_path: str,
            music_path: str,
            output_path: Optional[str] = None,
            music_volume: float = 0.3,
            original_volume: float = 1.0,
            fade_out: float = 2.0
        ) -> Dict[str, Any]:
            """Add background music to video.

            Args:
                video_path: Path to video file
                music_path: Path to music file
                output_path: Output file path
                music_volume: Background music volume (0.0-1.0)
                original_volume: Original audio volume
                fade_out: Music fade out duration
            """
            try:
                _ensure_moviepy()
                video = _VideoFileClip(video_path)
                music = _AudioFileClip(music_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(video_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_with_music.mp4"
                    )

                # Process original audio
                if video.audio:
                    original_audio = video.audio.volumex(original_volume)
                else:
                    original_audio = None

                # Process music
                if music.duration > video.duration:
                    music = music.subclip(0, video.duration - fade_out)
                    music = music.audio_fadeout(fade_out)
                else:
                    music = music.set_duration(video.duration)

                music = music.volumex(music_volume)

                # Combine audio
                if original_audio:
                    from moviepy.audio import CompositeAudioClip
                    final_audio = CompositeAudioClip([original_audio, music])
                else:
                    final_audio = music

                final = video.set_audio(final_audio)
                final.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                video.close()
                music.close()
                final.close()

                return {
                    "success": True,
                    "output_path": output_path,
                    "music_volume": music_volume
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def mute_video(
            input_path: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Remove audio from video.

            Args:
                input_path: Path to input video
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_muted.mp4"
                    )

                muted = clip.without_audio()
                muted.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                muted.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def adjust_audio_volume(
            input_path: str,
            volume: float,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Adjust audio volume in video.

            Args:
                input_path: Path to input video
                volume: Volume multiplier (0.5 = half, 2.0 = double)
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if clip.audio is None:
                    return {"error": "Video has no audio track"}

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_volume.mp4"
                    )

                adjusted_audio = clip.audio.volumex(volume)
                final = clip.set_audio(adjusted_audio)
                final.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                final.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "volume": volume
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_text_tools(self):
        """Register text and subtitle tools."""

        @self.mcp_server.tool()
        def add_text_watermark(
            input_path: str,
            text: str,
            position: str = "bottom_right",
            font_size: int = 24,
            color: str = "white",
            opacity: float = 0.7,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add text watermark to video.

            Args:
                input_path: Path to input video
                text: Watermark text
                position: Position (top_left, top_right, bottom_left, bottom_right, center)
                font_size: Font size in pixels
                color: Text color
                opacity: Text opacity (0.0-1.0)
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_watermarked.mp4"
                    )

                # Calculate position
                positions = {
                    "top_left": (10, 10),
                    "top_right": (clip.w - 10 - font_size * len(text) // 2, 10),
                    "bottom_left": (10, clip.h - 10 - font_size),
                    "bottom_right": (clip.w - 10 - font_size * len(text) // 2, clip.h - 10 - font_size),
                    "center": (clip.w // 2 - font_size * len(text) // 4, clip.h // 2)
                }

                pos = positions.get(position, positions["bottom_right"])

                # Create text clip
                txt_clip = _TextClip(
                    text,
                    fontsize=font_size,
                    color=color,
                    font="Arial"
                ).set_position(pos).set_duration(clip.duration).set_opacity(opacity)

                # Composite
                final = _CompositeVideoClip([clip, txt_clip])
                final.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                txt_clip.close()
                final.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "text": text,
                    "position": position
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_title_card(
            input_path: str,
            title: str,
            subtitle: Optional[str] = None,
            duration: float = 3.0,
            background_color: str = "black",
            title_color: str = "white",
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add title card at the beginning of video.

            Args:
                input_path: Path to input video
                title: Title text
                subtitle: Subtitle text (optional)
                duration: Title card duration in seconds
                background_color: Background color
                title_color: Text color
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_titled.mp4"
                    )

                # Create background
                bg = _ColorClip(
                    size=(clip.w, clip.h),
                    color=background_color,
                    duration=duration
                )

                # Create title text
                title_clip = _TextClip(
                    title,
                    fontsize=60,
                    color=title_color,
                    font="Arial-Bold"
                ).set_position("center").set_duration(duration)

                clips_to_composite = [bg, title_clip]

                # Add subtitle if provided
                if subtitle:
                    sub_clip = _TextClip(
                        subtitle,
                        fontsize=30,
                        color=title_color,
                        font="Arial"
                    ).set_position(("center", clip.h // 2 + 50)).set_duration(duration)
                    clips_to_composite.append(sub_clip)

                # Create title composite
                title_composite = _CompositeVideoClip(clips_to_composite)

                # Concatenate with video
                final = _concatenate_videoclips([title_composite, clip])
                final.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                bg.close()
                title_clip.close()
                final.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "title": title,
                    "title_duration": duration
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_subtitles(
            input_path: str,
            subtitles: List[Dict[str, Any]],
            font_size: int = 24,
            color: str = "white",
            bg_color: Optional[str] = "black",
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add subtitles to video.

            Args:
                input_path: Path to input video
                subtitles: List of subtitle dicts with 'start', 'end', 'text'
                font_size: Font size
                color: Text color
                bg_color: Background color (optional)
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_subtitled.mp4"
                    )

                subtitle_clips = []

                for sub in subtitles:
                    start = sub.get("start", 0)
                    end = sub.get("end", clip.duration)
                    text = sub.get("text", "")

                    txt = _TextClip(
                        text,
                        fontsize=font_size,
                        color=color,
                        bg_color=bg_color,
                        font="Arial"
                    ).set_position(("center", clip.h - 50 - font_size)).set_start(start).set_end(end)

                    subtitle_clips.append(txt)

                # Composite video with subtitles
                final = _CompositeVideoClip([clip] + subtitle_clips)
                final.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                for txt in subtitle_clips:
                    txt.close()
                final.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "subtitles_count": len(subtitles)
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_advanced_tools(self):
        """Register advanced video editing tools."""

        @self.mcp_server.tool()
        def create_video_from_images(
            image_paths: List[str],
            duration_per_image: float = 3.0,
            output_path: Optional[str] = None,
            resolution: str = "1080p",
            transition: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create video from a sequence of images.

            Args:
                image_paths: List of image file paths
                duration_per_image: Duration for each image in seconds
                output_path: Output file path
                resolution: Output resolution
                transition: Transition type (fadein, crossfade)
            """
            try:
                _ensure_moviepy()
                from PIL import Image
                import numpy as np

                if output_path is None:
                    output_path = os.path.join(
                        self.default_output_dir,
                        "slideshow.mp4"
                    )

                target_width, target_height = self._get_resolution(resolution)

                clips = []
                for img_path in image_paths:
                    # Load and resize image
                    img = Image.open(img_path)
                    img = img.resize((target_width, target_height), Image.LANCZOS)
                    img_array = np.array(img)

                    # Create clip
                    clip = _ImageClip(img_array, duration=duration_per_image)

                    if transition == "fadein":
                        clip = clip.fadein(0.5).fadeout(0.5)

                    clips.append(clip)

                # Concatenate
                if transition == "crossfade" and len(clips) > 1:
                    # Add crossfade between clips
                    final_clips = []
                    for i, clip in enumerate(clips):
                        if i > 0:
                            clip = clip.crossfadein(0.5)
                        if i < len(clips) - 1:
                            clip = clip.crossfadeout(0.5)
                        final_clips.append(clip)
                    final = _concatenate_videoclips(final_clips, method="compose")
                else:
                    final = _concatenate_videoclips(clips)

                final.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                for clip in clips:
                    clip.close()
                final.close()

                return {
                    "success": True,
                    "output_path": output_path,
                    "images_count": len(image_paths),
                    "total_duration": len(image_paths) * duration_per_image,
                    "resolution": resolution
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_picture_in_picture(
            main_video: str,
            overlay_video: str,
            position: str = "bottom_right",
            scale: float = 0.25,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add picture-in-picture overlay.

            Args:
                main_video: Path to main video
                overlay_video: Path to overlay video
                position: Position of overlay
                scale: Scale of overlay (0.1-0.5)
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                main = _VideoFileClip(main_video)
                overlay = _VideoFileClip(overlay_video)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(main_video))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_pip.mp4"
                    )

                # Resize overlay
                overlay = overlay.resize(scale)

                # Calculate position
                positions = {
                    "top_left": (10, 10),
                    "top_right": (main.w - overlay.w - 10, 10),
                    "bottom_left": (10, main.h - overlay.h - 10),
                    "bottom_right": (main.w - overlay.w - 10, main.h - overlay.h - 10),
                    "center": ((main.w - overlay.w) // 2, (main.h - overlay.h) // 2)
                }

                pos = positions.get(position, positions["bottom_right"])
                overlay = overlay.set_position(pos)

                # Adjust duration
                if overlay.duration > main.duration:
                    overlay = overlay.subclip(0, main.duration)

                # Composite
                final = _CompositeVideoClip([main, overlay])
                final.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                main.close()
                overlay.close()
                final.close()

                return {
                    "success": True,
                    "output_path": output_path,
                    "position": position,
                    "scale": scale
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_logo_overlay(
            input_path: str,
            logo_path: str,
            position: str = "top_right",
            scale: float = 0.1,
            opacity: float = 1.0,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add logo watermark to video.

            Args:
                input_path: Path to input video
                logo_path: Path to logo image
                position: Logo position
                scale: Logo scale (0.05-0.3)
                opacity: Logo opacity
                output_path: Output file path
            """
            try:
                _ensure_moviepy()
                import numpy as np
                from PIL import Image

                clip = _VideoFileClip(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_logo.mp4"
                    )

                # Load and process logo
                logo_img = Image.open(logo_path)

                # Convert to RGBA if needed
                if logo_img.mode != 'RGBA':
                    logo_img = logo_img.convert('RGBA')

                # Resize
                new_width = int(clip.w * scale)
                new_height = int(logo_img.height * (new_width / logo_img.width))
                logo_img = logo_img.resize((new_width, new_height), Image.LANCZOS)

                # Apply opacity
                if opacity < 1.0:
                    logo_array = np.array(logo_img)
                    logo_array[:, :, 3] = logo_array[:, :, 3] * opacity
                    logo_img = Image.fromarray(logo_array)

                logo_array = np.array(logo_img)
                logo_clip = _ImageClip(logo_array, duration=clip.duration)

                # Calculate position
                positions = {
                    "top_left": (10, 10),
                    "top_right": (clip.w - new_width - 10, 10),
                    "bottom_left": (10, clip.h - new_height - 10),
                    "bottom_right": (clip.w - new_width - 10, clip.h - new_height - 10)
                }

                pos = positions.get(position, positions["top_right"])
                logo_clip = logo_clip.set_position(pos)

                # Composite
                final = _CompositeVideoClip([clip, logo_clip])
                final.write_videofile(
                    output_path,
                    codec=self.default_codec,
                    fps=self.default_fps
                )

                clip.close()
                logo_clip.close()
                final.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "position": position
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_gif_tools(self):
        """Register GIF creation tools."""

        @self.mcp_server.tool()
        def create_gif(
            input_path: str,
            start_time: float = 0,
            end_time: Optional[float] = None,
            output_path: Optional[str] = None,
            fps: int = 15,
            scale: float = 1.0
        ) -> Dict[str, Any]:
            """Create GIF from video.

            Args:
                input_path: Path to input video
                start_time: Start time in seconds
                end_time: End time in seconds (optional)
                output_path: Output file path
                fps: GIF frames per second
                scale: Scale factor
            """
            try:
                _ensure_moviepy()
                clip = _VideoFileClip(input_path)

                if end_time is None:
                    end_time = min(start_time + 10, clip.duration)  # Default 10 seconds

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}.gif"
                    )

                # Create subclip
                gif_clip = clip.subclip(start_time, end_time)

                if scale != 1.0:
                    gif_clip = gif_clip.resize(scale)

                gif_clip.write_gif(output_path, fps=fps)

                clip.close()
                gif_clip.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "gif_duration": end_time - start_time,
                    "gif_fps": fps
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def optimize_gif(
            input_path: str,
            output_path: Optional[str] = None,
            colors: int = 256,
            lossy: int = 20
        ) -> Dict[str, Any]:
            """Optimize GIF file size.

            Args:
                input_path: Path to input GIF
                output_path: Output file path
                colors: Number of colors (lower = smaller)
                lossy: Lossy compression level (0-200)
            """
            try:
                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_optimized.gif"
                    )

                # Use gifsicle for optimization if available
                try:
                    result = subprocess.run(
                        ["gifsicle", "-O3", f"--colors={colors}", f"--lossy={lossy}",
                         "-o", output_path, input_path],
                        capture_output=True
                    )

                    if result.returncode == 0:
                        original_size = os.path.getsize(input_path)
                        optimized_size = os.path.getsize(output_path)
                        return {
                            "success": True,
                            "input_path": input_path,
                            "output_path": output_path,
                            "original_size_kb": round(original_size / 1024, 2),
                            "optimized_size_kb": round(optimized_size / 1024, 2),
                            "reduction": round((1 - optimized_size / original_size) * 100, 1)
                        }
                except FileNotFoundError:
                    pass

                # Fallback: just copy
                import shutil
                shutil.copy(input_path, output_path)
                return {
                    "success": True,
                    "message": "Gifsicle not installed. GIF copied without optimization.",
                    "output_path": output_path
                }
            except Exception as e:
                return {"error": str(e)}
