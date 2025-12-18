"""
Visible Watermark Processor V1.0
================================
Handles visible text watermark embedding using PIL/Pillow.

Technical Notes:
- Rotation is handled by creating an expanded canvas to prevent text clipping
- The watermark is tiled across the entire image
- RGBA mode is used for proper opacity blending
- Supports customizable horizontal and vertical spacing ratios
"""

import math
from pathlib import Path
from typing import Union, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


class VisibleWatermarker:
    """
    A class to add visible text watermarks to images.
    
    The watermark text is rotated and tiled across the image with
    configurable size, opacity, angle, and spacing.
    """

    # Default spacing between watermark tiles (as ratio of text size)
    DEFAULT_HORIZONTAL_SPACING_RATIO = 1.5
    DEFAULT_VERTICAL_SPACING_RATIO = 1.2

    def __init__(self, font_path: Optional[str] = None):
        """
        Initialize the VisibleWatermarker.
        
        Args:
            font_path: Optional path to a custom TTF font file.
                      If None, uses system default font.
        """
        self._font_path = font_path
        self._cached_fonts: dict[int, ImageFont.FreeTypeFont] = {}

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """
        Get or create a cached font object for the given size.
        
        Args:
            size: Font size in pixels.
            
        Returns:
            ImageFont object for drawing text.
        """
        if size not in self._cached_fonts:
            if self._font_path and Path(self._font_path).exists():
                self._cached_fonts[size] = ImageFont.truetype(self._font_path, size)
            else:
                # Try to use a nice default font
                try:
                    # Windows
                    self._cached_fonts[size] = ImageFont.truetype("msyh.ttc", size)
                except OSError:
                    try:
                        # macOS
                        self._cached_fonts[size] = ImageFont.truetype(
                            "/System/Library/Fonts/PingFang.ttc", size
                        )
                    except OSError:
                        try:
                            # Linux
                            self._cached_fonts[size] = ImageFont.truetype(
                                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
                            )
                        except OSError:
                            # Fallback to default
                            self._cached_fonts[size] = ImageFont.load_default()

        return self._cached_fonts[size]

    def _create_watermark_tile(
            self,
            text: str,
            font_size: int,
            opacity: int,
            angle: float,
            color: Tuple[int, int, int] = (128, 128, 128)
    ) -> Tuple[Image.Image, Tuple[int, int]]:
        """
        Create a single rotated watermark tile.
        
        This method handles the rotation properly by:
        1. Creating a large enough canvas for the text
        2. Drawing the text at center
        3. Rotating with expand=True to prevent clipping
        
        Args:
            text: Watermark text content.
            font_size: Size of the font in pixels.
            opacity: Opacity value (0-255), where 255 is fully opaque.
            angle: Rotation angle in degrees (counter-clockwise).
            color: RGB tuple for text color.
            
        Returns:
            Tuple of (RGBA Image containing the rotated watermark tile, (text_width, text_height))
        """
        font = self._get_font(font_size)

        # Calculate text bounding box
        temp_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calculate the diagonal of the text rectangle
        diagonal = int(math.sqrt(text_width ** 2 + text_height ** 2))
        # Add small margin (10% of diagonal)
        padding = int(diagonal * 0.1)
        canvas_size = diagonal + padding

        # Create transparent canvas
        tile = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(tile)

        # Calculate center position for text
        x = (canvas_size - text_width) // 2
        y = (canvas_size - text_height) // 2

        # Draw text with specified color and opacity
        text_color = (*color, opacity)
        draw.text((x, y), text, font=font, fill=text_color)

        # Rotate the tile (expand=True prevents clipping)
        if angle != 0:
            tile = tile.rotate(angle, expand=True, resample=Image.BICUBIC)

        return tile, (text_width, text_height)

    def _tile_watermark(
            self,
            base_image: Image.Image,
            tile: Image.Image,
            text_dims: Tuple[int, int],
            spacing_h_ratio: float,
            spacing_v_ratio: float,
            font_size: int
    ) -> Image.Image:
        """
        Tile the watermark across the entire image.
        
        Args:
            base_image: The original image to watermark.
            tile: The watermark tile to repeat.
            text_dims: (text_width, text_height) from tile creation.
            spacing_h_ratio: Horizontal spacing ratio.
            spacing_v_ratio: Vertical spacing ratio.
            font_size: Font size used for the watermark.
            
        Returns:
            New image with watermark applied.
        """
        # Ensure base image is RGBA
        if base_image.mode != "RGBA":
            base_image = base_image.convert("RGBA")

        # Create a transparent overlay for the watermarks
        watermark_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))

        tile_w, tile_h = tile.size
        img_w, img_h = base_image.size
        text_w, text_h = text_dims

        # Formula: actual_step = tile_size + font_size * (ratio - 1.0)
        step_h = tile_w + int(font_size * max(0, spacing_h_ratio - 1.0))
        step_v = tile_h + int(font_size * max(0, spacing_v_ratio - 1.0))

        # Calculate starting offset to center the tiling pattern
        start_x = -tile_w // 2
        start_y = -tile_h // 2

        # Tile across the image
        y = start_y
        row = 0
        while y < img_h + tile_h:
            x = start_x
            # Offset every other row for a more natural pattern
            if row % 2 == 1:
                x += step_h // 2

            while x < img_w + tile_w:
                # Paste the tile onto the watermark layer
                watermark_layer.paste(tile, (int(x), int(y)), tile)
                x += step_h

            y += step_v
            row += 1

        # Composite the watermark layer onto the base image
        result = Image.alpha_composite(base_image, watermark_layer)

        return result

    def process(
            self,
            image_path: Union[str, Path],
            text: str,
            size: int = 40,
            opacity: int = 80,
            angle: float = -30,
            color: Tuple[int, int, int] = (128, 128, 128),
            output_path: Optional[Union[str, Path]] = None,
            spacing_h_ratio: Optional[float] = None,
            spacing_v_ratio: Optional[float] = None
    ) -> Image.Image:
        """
        Apply visible watermark to an image.
        
        Args:
            image_path: Path to the source image file.
            text: Watermark text content.
            size: Font size in pixels (default: 40).
            opacity: Opacity 0-255, where 255 is fully opaque (default: 80).
            angle: Rotation angle in degrees, counter-clockwise (default: -30).
            color: RGB tuple for text color (default: gray).
            output_path: Optional path to save the result. If None, not saved.
            spacing_h_ratio: Horizontal spacing ratio (default: 1.5).
                            1.0 = tight arrangement, 2.0 = one character gap.
            spacing_v_ratio: Vertical spacing ratio (default: 1.2).
                            1.0 = tight arrangement, 2.0 = one character gap.
            
        Returns:
            PIL Image object with watermark applied.
            
        Raises:
            FileNotFoundError: If the source image doesn't exist.
            ValueError: If parameters are out of valid range.
        """
        # Validate inputs
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if not text or not text.strip():
            raise ValueError("Watermark text cannot be empty")

        if not 1 <= size <= 500:
            raise ValueError("Font size must be between 1 and 500")

        if not 0 <= opacity <= 255:
            raise ValueError("Opacity must be between 0 and 255")

        # Use default spacing ratios if not provided
        if spacing_h_ratio is None:
            spacing_h_ratio = self.DEFAULT_HORIZONTAL_SPACING_RATIO
        if spacing_v_ratio is None:
            spacing_v_ratio = self.DEFAULT_VERTICAL_SPACING_RATIO

        spacing_h_ratio = max(0.5, min(10.0, spacing_h_ratio))
        spacing_v_ratio = max(0.5, min(10.0, spacing_v_ratio))

        # Load the image
        base_image = Image.open(image_path)

        # Handle EXIF orientation
        try:
            from PIL import ExifTags
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = base_image._getexif()
            if exif is not None:
                orientation_value = exif.get(orientation)
                if orientation_value == 3:
                    base_image = base_image.rotate(180, expand=True)
                elif orientation_value == 6:
                    base_image = base_image.rotate(270, expand=True)
                elif orientation_value == 8:
                    base_image = base_image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            pass

        tile, text_dims = self._create_watermark_tile(
            text=text.strip(),
            font_size=size,
            opacity=opacity,
            angle=angle,
            color=color
        )

        result = self._tile_watermark(
            base_image=base_image,
            tile=tile,
            text_dims=text_dims,
            spacing_h_ratio=spacing_h_ratio,
            spacing_v_ratio=spacing_v_ratio,
            font_size=size
        )

        # Save if output path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Determine format from extension
            suffix = output_path.suffix.lower()
            if suffix in [".jpg", ".jpeg"]:
                # Convert RGBA to RGB for JPEG
                rgb_result = Image.new("RGB", result.size, (255, 255, 255))
                rgb_result.paste(result, mask=result.split()[3])
                rgb_result.save(output_path, quality=95)
            else:
                result.save(output_path)

        return result

    def process_image_object(
            self,
            image: Image.Image,
            text: str,
            size: int = 40,
            opacity: int = 80,
            angle: float = -30,
            color: Tuple[int, int, int] = (128, 128, 128),
            spacing_h_ratio: Optional[float] = None,
            spacing_v_ratio: Optional[float] = None
    ) -> Image.Image:
        """
        Apply visible watermark to an existing PIL Image object.
        
        This method is useful for chaining with other processing steps
        or for preview generation.
        
        Args:
            image: PIL Image object to watermark.
            text: Watermark text content.
            size: Font size in pixels.
            opacity: Opacity 0-255.
            angle: Rotation angle in degrees.
            color: RGB tuple for text color.
            spacing_h_ratio: Horizontal spacing ratio (default: 1.5).
                            1.0 = tight, 2.0 = one character gap.
            spacing_v_ratio: Vertical spacing ratio (default: 1.2).
                            1.0 = tight, 2.0 = one character gap.
            
        Returns:
            New PIL Image object with watermark applied.
        """
        if not text or not text.strip():
            raise ValueError("Watermark text cannot be empty")

        # Use default spacing ratios if not provided
        if spacing_h_ratio is None:
            spacing_h_ratio = self.DEFAULT_HORIZONTAL_SPACING_RATIO
        if spacing_v_ratio is None:
            spacing_v_ratio = self.DEFAULT_VERTICAL_SPACING_RATIO

        # Validate spacing ratios
        spacing_h_ratio = max(0.5, min(10.0, spacing_h_ratio))
        spacing_v_ratio = max(0.5, min(10.0, spacing_v_ratio))

        # Create watermark tile
        tile, text_dims = self._create_watermark_tile(
            text=text.strip(),
            font_size=size,
            opacity=opacity,
            angle=angle,
            color=color
        )

        # Apply tiled watermark
        return self._tile_watermark(
            base_image=image,
            tile=tile,
            text_dims=text_dims,
            spacing_h_ratio=spacing_h_ratio,
            spacing_v_ratio=spacing_v_ratio,
            font_size=size
        )


# Convenience function for simple usage
def add_visible_watermark(
        image_path: Union[str, Path],
        output_path: Union[str, Path],
        text: str,
        size: int = 40,
        opacity: int = 80,
        angle: float = -30,
        spacing_h_ratio: float = 1.5,
        spacing_v_ratio: float = 1.2
) -> None:
    """
    Convenience function to add a visible watermark to an image.
    
    Args:
        image_path: Source image path.
        output_path: Destination path for watermarked image.
        text: Watermark text.
        size: Font size.
        opacity: Text opacity (0-255).
        angle: Rotation angle in degrees.
        spacing_h_ratio: Horizontal spacing ratio (1.0 = tight).
        spacing_v_ratio: Vertical spacing ratio (1.0 = tight).
    """
    watermarker = VisibleWatermarker()
    watermarker.process(
        image_path=image_path,
        text=text,
        size=size,
        opacity=opacity,
        angle=angle,
        output_path=output_path,
        spacing_h_ratio=spacing_h_ratio,
        spacing_v_ratio=spacing_v_ratio
    )
