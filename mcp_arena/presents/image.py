"""
Image Processing MCP Server
A comprehensive image processing server using Pillow and OpenCV for image
manipulation, effects, format conversion, and computer vision operations.
"""
import io
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from mcp_arena.mcp.server import BaseMCPServer

try:
    from PIL import Image as _PIL_Image
    from PIL import ImageFilter as _PIL_Filter
    from PIL import ImageEnhance as _PIL_Enhance
    from PIL import ImageDraw as _PIL_Draw
    from PIL import ImageFont as _PIL_Font
    from PIL import ImageOps as _PIL_Ops
except ImportError:
    _PIL_Image = _PIL_Filter = _PIL_Enhance = _PIL_Draw = _PIL_Font = _PIL_Ops = None

try:
    import cv2 as _cv2
    import numpy as _np
except ImportError:
    _cv2 = _np = None


def _ensure_pil():
    if _PIL_Image is None:
        raise ImportError("Pillow is required. pip install Pillow")
    return _PIL_Image


def _ensure_cv2():
    if _cv2 is None:
        raise ImportError("opencv-python is required. pip install opencv-python")
    return _cv2, _np


class ImageMCPServer(BaseMCPServer):
    """Image processing MCP server (Pillow + OpenCV)."""
    _REQUIRED_EXTRAS = {"PIL": "image", "cv2": "image"}

    def __init__(
        self,
        default_output_dir: Optional[str] = None,
        default_format: str = "png",
        default_quality: int = 95,
        temp_dir: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.default_output_dir = default_output_dir or os.path.join(os.getcwd(), "image_output")
        self.default_format = default_format
        self.default_quality = default_quality
        self.temp_dir = temp_dir or os.path.join(os.getcwd(), "image_temp")

        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

        super().__init__(
            name="Image Processing MCP Server",
            description="MCP server for image processing (Pillow + OpenCV)",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _register_tools(self) -> None:
        """Register all image processing tools."""
        self._register_info_tools()
        self._register_conversion_tools()
        self._register_basic_tools()
        self._register_effects_tools()
        self._register_drawing_tools()
        self._register_cv_tools()

    def _register_info_tools(self):
        """Register image information tools."""

        @self.mcp_server.tool()
        def get_image_info(image_path: str) -> Dict[str, Any]:
            """Get detailed information about an image file.

            Args:
                image_path: Path to the image file
            """
            try:
                Image = _ensure_pil()
                img = _ensure_pil().open(image_path)

                info = {
                    "path": image_path,
                    "filename": os.path.basename(image_path),
                    "width": img.width,
                    "height": img.height,
                    "format": img.format or "Unknown",
                    "mode": img.mode,
                    "size_bytes": os.path.getsize(image_path),
                    "aspect_ratio": round(img.width / img.height, 2) if img.height > 0 else 0,
                    "has_transparency": img.mode in ("RGBA", "LA", "P"),
                    "dpi": img.info.get("dpi"),
                }

                img.close()
                return {"success": True, "info": info}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def analyze_colors(image_path: str, num_colors: int = 5) -> Dict[str, Any]:
            """Analyze colors in an image.

            Args:
                image_path: Path to the image file
                num_colors: Number of dominant colors to extract
            """
            try:
                cv2, np = _ensure_cv2()

                img = cv2.imread(image_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                pixels = img.reshape(-1, 3)

                # Average color
                avg_color = tuple(map(int, np.mean(pixels, axis=0)))

                # Dominant colors using k-means
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
                _, labels, centers = cv2.kmeans(
                    np.float32(pixels), num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
                )

                dominant_colors = [tuple(map(int, center)) for center in centers]

                # Brightness and contrast
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                brightness = round(np.mean(gray) / 255 * 100, 1)
                contrast = round(np.std(gray) / 255 * 100, 1)

                return {
                    "success": True,
                    "dominant_colors": dominant_colors,
                    "average_color": avg_color,
                    "brightness_percent": brightness,
                    "contrast_percent": contrast
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_conversion_tools(self):
        """Register image conversion tools."""

        @self.mcp_server.tool()
        def convert_image(
            input_path: str,
            output_format: str = "png",
            output_path: Optional[str] = None,
            quality: int = 95
        ) -> Dict[str, Any]:
            """Convert image to a different format.

            Args:
                input_path: Path to input image
                output_format: Output format (jpeg, png, webp, gif, bmp, tiff, ico)
                output_path: Output file path
                quality: Image quality (1-100)
            """
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}.{output_format}"
                    )

                # Handle format-specific conversions
                if output_format.lower() in ['jpeg', 'jpg']:
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')

                save_kwargs = {"quality": quality}
                if output_format.lower() == 'png':
                    save_kwargs = {"optimize": True}

                img.save(output_path, format=output_format.upper(), **save_kwargs)
                img.close()

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
            output_format: str = "png",
            quality: int = 95
        ) -> Dict[str, Any]:
            """Convert multiple images to a different format.

            Args:
                input_paths: List of input image paths
                output_format: Output format
                quality: Image quality
            """
            try:
                results = []
                for input_path in input_paths:
                    result = convert_image(input_path, output_format, None, quality)
                    results.append(result)

                successful = [r for r in results if r.get("success")]
                failed = [r for r in results if r.get("error")]

                return {
                    "success": True,
                    "total": len(input_paths),
                    "converted": len(successful),
                    "failed": len(failed),
                    "results": results
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_basic_tools(self):
        """Register basic image manipulation tools."""

        @self.mcp_server.tool()
        def resize_image(
            input_path: str,
            width: Optional[int] = None,
            height: Optional[int] = None,
            scale: Optional[float] = None,
            maintain_aspect: bool = True,
            method: str = "lanczos",
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Resize an image.

            Args:
                input_path: Path to input image
                width: Target width
                height: Target height
                scale: Scale factor (overrides width/height)
                maintain_aspect: Maintain aspect ratio
                method: Resize method (nearest, bilinear, bicubic, lanczos)
                output_path: Output file path
            """
            try:
                Image = _ensure_pil()

                resample_methods = {
                    "nearest": _PIL_Image.Resampling.NEAREST,
                    "bilinear": _PIL_Image.Resampling.BILINEAR,
                    "bicubic": _PIL_Image.Resampling.BICUBIC,
                    "lanczos": _PIL_Image.Resampling.LANCZOS
                }
                resample = resample_methods.get(method, _PIL_Image.Resampling.LANCZOS)

                img = Image.open(input_path)
                original_size = img.size

                if scale:
                    new_size = (int(img.width * scale), int(img.height * scale))
                elif width and height:
                    new_size = (width, height)
                elif width:
                    if maintain_aspect:
                        ratio = width / img.width
                        new_size = (width, int(img.height * ratio))
                    else:
                        new_size = (width, img.height)
                elif height:
                    if maintain_aspect:
                        ratio = height / img.height
                        new_size = (int(img.width * ratio), height)
                    else:
                        new_size = (img.width, height)
                else:
                    return {"error": "Must specify width, height, or scale"}

                resized = img.resize(new_size, resample)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_resized.{self.default_format}"
                    )

                resized.save(output_path, quality=self.default_quality)
                img.close()
                resized.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "original_size": f"{original_size[0]}x{original_size[1]}",
                    "new_size": f"{new_size[0]}x{new_size[1]}"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def crop_image(
            input_path: str,
            left: int,
            top: int,
            right: int,
            bottom: int,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Crop an image.

            Args:
                input_path: Path to input image
                left, top, right, bottom: Crop coordinates
                output_path: Output file path
            """
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)

                cropped = img.crop((left, top, right, bottom))

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_cropped.{self.default_format}"
                    )

                cropped.save(output_path, quality=self.default_quality)
                img.close()
                cropped.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "original_size": f"{img.width}x{img.height}",
                    "cropped_size": f"{right-left}x{bottom-top}"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def rotate_image(
            input_path: str,
            angle: float,
            expand: bool = False,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Rotate an image.

            Args:
                input_path: Path to input image
                angle: Rotation angle in degrees
                expand: Expand canvas to fit rotated image
                output_path: Output file path
            """
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)

                rotated = img.rotate(angle, expand=expand)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_rotated.{self.default_format}"
                    )

                rotated.save(output_path, quality=self.default_quality)
                img.close()
                rotated.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "angle": angle,
                    "new_size": f"{rotated.width}x{rotated.height}"
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def flip_image(
            input_path: str,
            direction: str = "horizontal",
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Flip an image.

            Args:
                input_path: Path to input image
                direction: Flip direction (horizontal, vertical)
                output_path: Output file path
            """
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)

                if direction == "horizontal":
                    flipped = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                else:
                    flipped = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_flipped.{self.default_format}"
                    )

                flipped.save(output_path, quality=self.default_quality)
                img.close()
                flipped.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "direction": direction
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def compress_image(
            input_path: str,
            target_size_kb: Optional[int] = None,
            quality: int = 85,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Compress an image.

            Args:
                input_path: Path to input image
                target_size_kb: Target file size in KB (optional)
                quality: Initial quality to try
                output_path: Output file path
            """
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)
                original_size = os.path.getsize(input_path)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_compressed.jpg"
                    )

                if target_size_kb:
                    # Binary search for optimal quality
                    low, high = 1, 100
                    while low < high:
                        mid = (low + high) // 2
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=mid)
                        size = buffer.tell() / 1024

                        if size > target_size_kb:
                            high = mid
                        else:
                            low = mid + 1

                    quality = max(1, low - 1)

                img.save(output_path, format='JPEG', quality=quality)
                compressed_size = os.path.getsize(output_path)
                img.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "original_size_kb": round(original_size / 1024, 2),
                    "compressed_size_kb": round(compressed_size / 1024, 2),
                    "compression_ratio": round(original_size / compressed_size, 2),
                    "quality_used": quality
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def create_thumbnail(
            input_path: str,
            size: int = 128,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Create a thumbnail of an image.

            Args:
                input_path: Path to input image
                size: Maximum dimension size
                output_path: Output file path
            """
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)

                # Calculate thumbnail size maintaining aspect ratio
                img.thumbnail((size, size), _PIL_Image.Resampling.LANCZOS)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_thumb.{self.default_format}"
                    )

                img.save(output_path, quality=self.default_quality)
                img.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "thumbnail_size": f"{img.width}x{img.height}"
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_effects_tools(self):
        """Register image effects tools."""

        @self.mcp_server.tool()
        def apply_filter(
            input_path: str,
            filter_type: str,
            intensity: float = 1.0,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Apply a filter to an image.

            Args:
                input_path: Path to input image
                filter_type: Filter type (blur, sharpen, edge_enhance, emboss, contour, smooth, detail)
                intensity: Filter intensity (0.0-2.0)
                output_path: Output file path
            """
            try:
                Image = _ensure_pil()

                filters = {
                    "blur": _PIL_Filter.BLUR,
                    "sharpen": _PIL_Filter.SHARPEN,
                    "edge_enhance": _PIL_Filter.EDGE_ENHANCE,
                    "emboss": _PIL_Filter.EMBOSS,
                    "contour": _PIL_Filter.CONTOUR,
                    "smooth": _PIL_Filter.SMOOTH,
                    "detail": _PIL_Filter.DETAIL
                }

                if filter_type not in filters:
                    return {"error": f"Unknown filter: {filter_type}"}

                img = Image.open(input_path)

                # Apply filter
                filtered = img.filter(filters[filter_type])

                # Apply additional passes for intensity > 1
                for _ in range(int(intensity) - 1):
                    filtered = filtered.filter(filters[filter_type])

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_{filter_type}.{self.default_format}"
                    )

                filtered.save(output_path, quality=self.default_quality)
                img.close()
                filtered.close()

                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "filter": filter_type
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def adjust_colors(
            input_path: str,
            brightness: float = 1.0,
            contrast: float = 1.0,
            saturation: float = 1.0,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Adjust image colors.

            Args:
                input_path: Path to input image
                brightness: Brightness factor (0.0-2.0, 1.0 = normal)
                contrast: Contrast factor (0.0-2.0, 1.0 = normal)
                saturation: Saturation factor (0.0-2.0, 1.0 = normal)
                output_path: Output file path
            """
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)

                # Apply brightness
                if brightness != 1.0:
                    enhancer = _PIL_Enhance.Brightness(img)
                    img = enhancer.enhance(brightness)

                # Apply contrast
                if contrast != 1.0:
                    enhancer = _PIL_Enhance.Contrast(img)
                    img = enhancer.enhance(contrast)

                # Apply saturation
                if saturation != 1.0:
                    enhancer = _PIL_Enhance.Color(img)
                    img = enhancer.enhance(saturation)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_adjusted.{self.default_format}"
                    )

                img.save(output_path, quality=self.default_quality)
                img.close()

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
        def grayscale(
            input_path: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Convert image to grayscale."""
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)
                gray = img.convert('L')

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_gray.{self.default_format}"
                    )

                gray.save(output_path, quality=self.default_quality)
                img.close()
                gray.close()

                return {"success": True, "output_path": output_path}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def invert_colors(
            input_path: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Invert image colors."""
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)

                if img.mode == 'RGBA':
                    r, g, b, a = img.split()
                    rgb = Image.merge('RGB', (r, g, b))
                    inverted = _PIL_Ops.invert(rgb)
                    r2, g2, b2 = inverted.split()
                    inverted = Image.merge('RGBA', (r2, g2, b2, a))
                else:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    inverted = _PIL_Ops.invert(img)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_inverted.{self.default_format}"
                    )

                inverted.save(output_path, quality=self.default_quality)
                img.close()
                inverted.close()

                return {"success": True, "output_path": output_path}
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_vignette(
            input_path: str,
            intensity: float = 0.5,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add vignette effect to image.

            Args:
                input_path: Path to input image
                intensity: Vignette intensity (0.0-1.0)
                output_path: Output file path
            """
            try:
                cv2, np = _ensure_cv2()

                img = cv2.imread(input_path)
                h, w = img.shape[:2]

                # Create vignette mask
                Y, X = np.ogrid[:h, :w]
                center_y, center_x = h / 2, w / 2
                dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
                max_dist = np.sqrt(center_x**2 + center_y**2)
                vignette = 1 - (dist / max_dist) * intensity
                vignette = np.clip(vignette, 0, 1)
                vignette = (vignette * 255).astype(np.uint8)

                # Apply vignette
                img = img.astype(np.float64)
                for i in range(3):
                    img[:, :, i] = img[:, :, i] * vignette / 255

                img = img.astype(np.uint8)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_vignette.jpg"
                    )

                cv2.imwrite(output_path, img)

                return {
                    "success": True,
                    "output_path": output_path,
                    "intensity": intensity
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_drawing_tools(self):
        """Register image drawing tools."""

        @self.mcp_server.tool()
        def add_text(
            input_path: str,
            text: str,
            position: Tuple[int, int] = (10, 10),
            font_size: int = 24,
            color: Tuple[int, int, int] = (255, 255, 255),
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add text to an image.

            Args:
                input_path: Path to input image
                text: Text to add
                position: Text position (x, y)
                font_size: Font size in pixels
                color: Text color (R, G, B)
                output_path: Output file path
            """
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)

                if img.mode != 'RGBA':
                    img = img.convert('RGBA')

                draw = _PIL_Draw.Draw(img)

                try:
                    font = _PIL_Font.truetype("arial.ttf", font_size)
                except Exception:
                    font = _PIL_Font.load_default()

                draw.text(position, text, fill=color, font=font)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_text.{self.default_format}"
                    )

                img.save(output_path, quality=self.default_quality)
                img.close()

                return {
                    "success": True,
                    "output_path": output_path,
                    "text": text
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def add_watermark(
            input_path: str,
            watermark_path: str,
            position: str = "bottom_right",
            opacity: float = 0.5,
            scale: float = 0.2,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Add watermark image to another image.

            Args:
                input_path: Path to input image
                watermark_path: Path to watermark image
                position: Position (top_left, top_right, bottom_left, bottom_right, center)
                opacity: Watermark opacity (0.0-1.0)
                scale: Watermark scale factor
                output_path: Output file path
            """
            try:
                Image = _ensure_pil()
                img = Image.open(input_path)
                watermark = Image.open(watermark_path)

                # Resize watermark
                wm_size = (int(img.width * scale), int(img.height * scale))
                watermark = watermark.resize(wm_size, _PIL_Image.Resampling.LANCZOS)

                # Apply opacity
                if watermark.mode != 'RGBA':
                    watermark = watermark.convert('RGBA')

                # Scale the alpha channel by the requested opacity.
                r, g, b, alpha = watermark.split()
                alpha = alpha.point(lambda px: int(px * opacity))
                watermark = watermark.merge((r, g, b, alpha))

                # Calculate position
                positions = {
                    "top_left": (0, 0),
                    "top_right": (img.width - watermark.width, 0),
                    "bottom_left": (0, img.height - watermark.height),
                    "bottom_right": (img.width - watermark.width, img.height - watermark.height),
                    "center": ((img.width - watermark.width) // 2, (img.height - watermark.height) // 2)
                }

                pos = positions.get(position, positions["bottom_right"])

                # Composite
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')

                img.paste(watermark, pos, watermark)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_watermarked.{self.default_format}"
                    )

                # Convert back to RGB for saving
                img = img.convert('RGB')
                img.save(output_path, quality=self.default_quality)
                img.close()
                watermark.close()

                return {
                    "success": True,
                    "output_path": output_path,
                    "position": position
                }
            except Exception as e:
                return {"error": str(e)}

    def _register_cv_tools(self):
        """Register computer vision tools."""

        @self.mcp_server.tool()
        def detect_faces(
            input_path: str,
            output_path: Optional[str] = None,
            draw_boxes: bool = True
        ) -> Dict[str, Any]:
            """Detect faces in an image.

            Args:
                input_path: Path to input image
                output_path: Output file path
                draw_boxes: Draw bounding boxes around faces
            """
            try:
                cv2, np = _ensure_cv2()

                img = cv2.imread(input_path)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                # Load Haar cascade
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)

                face_data = []
                for (x, y, w, h) in faces:
                    face_data.append({
                        "x": int(x),
                        "y": int(y),
                        "width": int(w),
                        "height": int(h)
                    })
                    if draw_boxes:
                        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_faces.jpg"
                    )

                if draw_boxes:
                    cv2.imwrite(output_path, img)

                return {
                    "success": True,
                    "faces_detected": len(faces),
                    "faces": face_data,
                    "output_path": output_path if draw_boxes else None
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def detect_objects(
            input_path: str,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Detect objects in an image using edge detection.

            Args:
                input_path: Path to input image
                output_path: Output file path
            """
            try:
                cv2, np = _ensure_cv2()

                img = cv2.imread(input_path)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                # Apply edge detection
                edges = cv2.Canny(gray, 100, 200)

                # Find contours
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                objects = []
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w > 50 and h > 50:  # Filter small objects
                        objects.append({
                            "x": int(x),
                            "y": int(y),
                            "width": int(w),
                            "height": int(h),
                            "area": int(cv2.contourArea(contour))
                        })
                        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_objects.jpg"
                    )

                cv2.imwrite(output_path, img)

                return {
                    "success": True,
                    "objects_detected": len(objects),
                    "objects": objects,
                    "output_path": output_path
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def remove_background(
            input_path: str,
            output_path: Optional[str] = None,
            threshold: int = 240
        ) -> Dict[str, Any]:
            """Remove background from image (simple threshold-based).

            Args:
                input_path: Path to input image
                output_path: Output file path
                threshold: Background color threshold (0-255)
            """
            try:
                cv2, np = _ensure_cv2()

                img = cv2.imread(input_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

                # Convert to grayscale for threshold
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

                # Create mask
                _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
                mask = cv2.bitwise_not(mask)

                # Apply mask
                img[:, :, 3] = mask

                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(input_path))[0]
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"{base_name}_nobg.png"
                    )

                cv2.imwrite(output_path, img)

                return {
                    "success": True,
                    "output_path": output_path
                }
            except Exception as e:
                return {"error": str(e)}

