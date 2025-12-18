"""
Extract Worker - Async Watermark Extraction
==========================================
QThread worker for extracting blind watermarks from images.

Workflow:
1. Load the watermarked image
2. Extract blind watermark using provided password and bit_length
3. Emit result signal with extracted text
"""

import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.blind import BlindWatermarkerAdapter


@dataclass
class ExtractConfig:
    """Configuration for blind watermark extraction."""
    image_path: Path
    password: str
    bit_length: int  # Required - from embed result


@dataclass
class ExtractResult:
    """Result of extraction operation."""
    source_path: Path
    extracted_text: str = ""
    success: bool = False
    error_message: str = ""


class ExtractWorker(QThread):
    """
    Worker thread for extracting blind watermarks from images.
    
    Signals:
        started_extraction(str): Emitted when extraction starts (filename)
        result_ready(ExtractResult): Emitted with extraction result
        error(str): Emitted on errors
    """

    # Signals
    started_extraction = pyqtSignal(str)  # filename
    result_ready = pyqtSignal(object)  # ExtractResult
    error = pyqtSignal(str)  # Error message

    def __init__(self, config: ExtractConfig, parent=None):
        """
        Initialize the extract worker.
        
        Args:
            config: ExtractConfig with extraction settings.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.config = config
        self._blind_wm: Optional[BlindWatermarkerAdapter] = None

    def run(self):
        """
        Main worker execution.
        
        Extracts the blind watermark and emits the result.
        """
        result = ExtractResult(source_path=self.config.image_path)

        try:
            # Validate config
            if not self.config.image_path.exists():
                raise FileNotFoundError(
                    f"Image not found: {self.config.image_path}"
                )

            if not self.config.password:
                raise ValueError("Password cannot be empty")

            if self.config.bit_length <= 0:
                raise ValueError("Invalid bit_length value")

            # Emit started signal
            self.started_extraction.emit(self.config.image_path.name)

            # Initialize extractor
            self._blind_wm = BlindWatermarkerAdapter()

            # Perform extraction
            extracted_text = self._blind_wm.extract(
                image_path=self.config.image_path,
                password=self.config.password,
                bit_length=self.config.bit_length
            )

            result.extracted_text = extracted_text
            result.success = True

        except ValueError as e:
            result.success = False
            result.error_message = str(e)
            self.error.emit(str(e))

        except FileNotFoundError as e:
            result.success = False
            result.error_message = str(e)
            self.error.emit(str(e))

        except Exception as e:
            result.success = False
            result.error_message = f"Extraction failed: {str(e)}"
            self.error.emit(result.error_message)
            traceback.print_exc()

        finally:
            # Cleanup
            if self._blind_wm is not None:
                self._blind_wm.cleanup()
                self._blind_wm = None

        # Emit result
        self.result_ready.emit(result)


class BatchExtractWorker(QThread):
    """
    Worker thread for extracting blind watermarks from multiple images.
    
    Useful when processing a batch of images with the same password/bit_length.
    
    Signals:
        progress(int, int, str): (current, total, filename)
        image_completed(ExtractResult): Emitted for each image
        finished_all(list[ExtractResult]): Emitted when all done
        error(str): Emitted on critical errors
    """

    # Signals
    progress = pyqtSignal(int, int, str)  # current, total, filename
    image_completed = pyqtSignal(object)  # ExtractResult
    finished_all = pyqtSignal(list)  # List[ExtractResult]
    error = pyqtSignal(str)  # Error message

    def __init__(
            self,
            image_paths: list[Path],
            password: str,
            bit_length: int,
            parent=None
    ):
        """
        Initialize the batch extract worker.
        
        Args:
            image_paths: List of image paths to process.
            password: Password for all images.
            bit_length: Bit length for all images.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self.image_paths = image_paths
        self.password = password
        self.bit_length = bit_length
        self._is_cancelled = False
        self._blind_wm: Optional[BlindWatermarkerAdapter] = None

    def cancel(self):
        """Request cancellation of the worker."""
        self._is_cancelled = True

    def run(self):
        """
        Main worker execution.
        
        Processes all images and emits progress/result signals.
        """
        results: list[ExtractResult] = []
        total = len(self.image_paths)

        if total == 0:
            self.error.emit("No images to process")
            self.finished_all.emit(results)
            return

        try:
            # Validate
            if not self.password:
                self.error.emit("Password cannot be empty")
                self.finished_all.emit(results)
                return

            if self.bit_length <= 0:
                self.error.emit("Invalid bit_length value")
                self.finished_all.emit(results)
                return

            # Initialize extractor
            self._blind_wm = BlindWatermarkerAdapter()

            for idx, image_path in enumerate(self.image_paths):
                if self._is_cancelled:
                    break

                # Emit progress
                self.progress.emit(idx + 1, total, image_path.name)

                # Process
                result = ExtractResult(source_path=image_path)

                try:
                    if not image_path.exists():
                        raise FileNotFoundError(f"Image not found: {image_path}")

                    extracted_text = self._blind_wm.extract(
                        image_path=image_path,
                        password=self.password,
                        bit_length=self.bit_length
                    )

                    result.extracted_text = extracted_text
                    result.success = True

                except Exception as e:
                    result.success = False
                    result.error_message = str(e)

                results.append(result)
                self.image_completed.emit(result)

        except Exception as e:
            self.error.emit(f"Critical error: {str(e)}")
            traceback.print_exc()

        finally:
            if self._blind_wm is not None:
                self._blind_wm.cleanup()
                self._blind_wm = None

        self.finished_all.emit(results)
