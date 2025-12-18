"""
Embed Worker - Async Watermark Embedding
========================================
QThread worker for embedding visible and/or blind watermarks.

Workflow:
1. For each image in the queue:
   a. Apply visible watermark (if enabled)
   b. Apply blind watermark (if enabled)
   c. Save to output directory with proper naming
2. Emit progress signals during processing
3. Emit finished signal with results

Naming Convention:
- Visible only: filename_watermarked.png
- Blind only: filename_blind-{bit_length}.png
- Both: filename_watermarked_blind-{bit_length}.png
"""

import tempfile
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Tuple

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.blind import BlindWatermarkerAdapter
from app.core.visible import VisibleWatermarker


@dataclass
class VisibleConfig:
    """Configuration for visible watermark."""
    enabled: bool = False
    text: str = ""
    font_size: int = 40
    opacity: int = 80  # 0-255
    angle: float = -30.0
    color: Tuple[int, int, int] = (128, 128, 128)
    spacing_h_ratio: float = 2.5
    spacing_v_ratio: float = 2.0


@dataclass
class BlindConfig:
    """Configuration for blind watermark."""
    enabled: bool = False
    text: str = ""
    password: str = ""


@dataclass
class EmbedConfig:
    """Complete configuration for embedding watermarks."""
    image_paths: List[Path] = field(default_factory=list)
    output_dir: Path = field(default_factory=lambda: Path.cwd() / "output")
    visible: VisibleConfig = field(default_factory=VisibleConfig)
    blind: BlindConfig = field(default_factory=BlindConfig)

    # Output format: "png" recommended for blind watermark preservation
    output_format: str = "png"


@dataclass
class EmbedResult:
    """Result of embedding operation for a single image."""
    source_path: Path
    output_path: Optional[Path] = None
    bit_length: Optional[int] = None  # For blind watermark extraction
    success: bool = False
    error_message: str = ""


class EmbedWorker(QThread):
    """
    Worker thread for embedding watermarks into images.
    
    Signals:
        progress(int, int, str): (current, total, current_file_name)
        image_completed(EmbedResult): Emitted when each image is processed
        finished_all(list[EmbedResult]): Emitted when all images are done
        error(str): Emitted on critical errors
    """

    # Signals
    progress = pyqtSignal(int, int, str)  # current, total, filename
    image_completed = pyqtSignal(object)  # EmbedResult
    finished_all = pyqtSignal(list)  # List[EmbedResult]
    error = pyqtSignal(str)  # Error message

    def __init__(self, config: EmbedConfig, parent=None):
        """
        Initialize the embed worker.
        
        Args:
            config: EmbedConfig with all watermark settings.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.config = config
        self._is_cancelled = False

        # Initialize processors
        self._visible_wm: Optional[VisibleWatermarker] = None
        self._blind_wm: Optional[BlindWatermarkerAdapter] = None

    def cancel(self):
        """Request cancellation of the worker."""
        self._is_cancelled = True

    def _setup_processors(self):
        """Initialize watermark processors based on config."""
        if self.config.visible.enabled:
            self._visible_wm = VisibleWatermarker()

        if self.config.blind.enabled:
            self._blind_wm = BlindWatermarkerAdapter()

    def _cleanup_processors(self):
        """Clean up processor resources."""
        if self._visible_wm is not None:
            self._visible_wm._cached_fonts.clear()
            self._visible_wm = None

        if self._blind_wm is not None:
            self._blind_wm.cleanup()
            self._blind_wm = None

    def _generate_output_filename(
            self,
            source_path: Path,
            bit_length: Optional[int] = None
    ) -> str:
        """
        Generate the output filename based on watermark types.
        
        Naming Convention:
        - Visible only: filename_watermarked.png
        - Blind only: filename_blind-{bit_length}.png
        - Both: filename_watermarked_blind-{bit_length}.png
        
        Args:
            source_path: Original source file path.
            bit_length: Bit length for blind watermark (if applicable).
            
        Returns:
            Output filename string.
        """
        base_name = source_path.stem
        suffix = f".{self.config.output_format}"

        visible_enabled = self.config.visible.enabled
        blind_enabled = self.config.blind.enabled

        if visible_enabled and blind_enabled and bit_length is not None:
            # Both watermarks
            return f"{base_name}_watermarked_blind-{bit_length}{suffix}"
        elif blind_enabled and bit_length is not None:
            # Blind watermark only - include bit_length in filename
            return f"{base_name}_blind-{bit_length}{suffix}"
        elif visible_enabled:
            # Visible watermark only
            return f"{base_name}_watermarked{suffix}"
        else:
            # Fallback (shouldn't happen)
            return f"{base_name}_output{suffix}"

    def _process_single_image(self, image_path: Path) -> EmbedResult:
        """
        Process a single image with configured watermarks.
        
        Args:
            image_path: Path to the source image.
            
        Returns:
            EmbedResult with processing outcome.
        """
        result = EmbedResult(source_path=image_path)
        temp_file: Optional[Path] = None
        bit_length: Optional[int] = None

        try:
            # Ensure output directory exists
            self.config.output_dir.mkdir(parents=True, exist_ok=True)

            # Track current working image path
            current_image = image_path

            # Step 1: Apply visible watermark (if enabled)
            if self.config.visible.enabled and self._visible_wm is not None:
                vis_cfg = self.config.visible

                # If blind watermark is also enabled, save to temp file first
                if self.config.blind.enabled:
                    temp_file = Path(tempfile.mktemp(suffix=".png"))
                    vis_output = temp_file
                else:
                    # Generate output filename (visible only)
                    output_name = self._generate_output_filename(image_path, None)
                    vis_output = self.config.output_dir / output_name

                visible_result = self._visible_wm.process(
                    image_path=current_image,
                    text=vis_cfg.text,
                    size=vis_cfg.font_size,
                    opacity=vis_cfg.opacity,
                    angle=vis_cfg.angle,
                    color=vis_cfg.color,
                    output_path=vis_output,
                    spacing_h_ratio=vis_cfg.spacing_h_ratio,
                    spacing_v_ratio=vis_cfg.spacing_v_ratio
                )
                visible_result.close()
                current_image = vis_output

                # If no blind watermark, set the final output path
                if not self.config.blind.enabled:
                    result.output_path = vis_output

            # Step 2: Apply blind watermark (if enabled)
            if self.config.blind.enabled and self._blind_wm is not None:
                blind_cfg = self.config.blind

                # First, embed to get the bit_length
                temp_blind_output = Path(tempfile.mktemp(suffix=".png"))

                try:
                    _, bit_length = self._blind_wm.embed(
                        image_path=current_image,
                        password=blind_cfg.password,
                        text=blind_cfg.text,
                        output_path=temp_blind_output
                    )

                    result.bit_length = bit_length

                    # Now generate the final filename with bit_length
                    final_output_name = self._generate_output_filename(
                        image_path, bit_length
                    )
                    final_output = self.config.output_dir / final_output_name

                    # Move/rename the temp file to final location
                    import shutil
                    shutil.move(str(temp_blind_output), str(final_output))

                    result.output_path = final_output

                finally:
                    # Cleanup temp blind output if it still exists
                    if temp_blind_output.exists():
                        try:
                            temp_blind_output.unlink()
                        except OSError:
                            pass

            result.success = True

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            traceback.print_exc()

        finally:
            # Clean up temp file from visible watermark step
            if temp_file is not None and temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

        return result

    def run(self):
        """
        Main worker execution.
        
        Processes all images in the config and emits progress signals.
        """
        results: List[EmbedResult] = []
        total = len(self.config.image_paths)

        if total == 0:
            self.error.emit("No images to process")
            self.finished_all.emit(results)
            return

        try:
            # Validate config
            if self.config.visible.enabled and not self.config.visible.text.strip():
                self.error.emit("Visible watermark text cannot be empty")
                self.finished_all.emit(results)
                return

            if self.config.blind.enabled:
                if not self.config.blind.password:
                    self.error.emit("Blind watermark password cannot be empty")
                    self.finished_all.emit(results)
                    return
                if not self.config.blind.text.strip():
                    self.error.emit("Blind watermark text cannot be empty")
                    self.finished_all.emit(results)
                    return

            # Setup processors
            self._setup_processors()

            # Process each image
            for idx, image_path in enumerate(self.config.image_paths):
                if self._is_cancelled:
                    break

                # Emit progress
                self.progress.emit(idx + 1, total, image_path.name)

                # Process image
                result = self._process_single_image(image_path)
                results.append(result)

                # Emit individual result
                self.image_completed.emit(result)

        except Exception as e:
            self.error.emit(f"Critical error: {str(e)}")
            traceback.print_exc()

        finally:
            self._cleanup_processors()

        # Emit final results
        self.finished_all.emit(results)
