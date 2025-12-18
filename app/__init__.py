"""
NightCat Watermark Application Package
======================================
A desktop tool for visible and blind watermark processing.

Modules:
    - core: Pure algorithm logic (no UI dependencies)
    - workers: QThread workers for async processing
    - ui: PyQt6 user interface components

Usage:
    from app.core import VisibleWatermarker, BlindWatermarkerAdapter
    from app.workers import EmbedWorker, ExtractWorker
    from app.ui import MainWindow
"""

__version__ = "1.0.0"
__author__ = "NightCat"
__app_name__ = "NightCat Watermark"

# Core exports
from .core import VisibleWatermarker, BlindWatermarkerAdapter
# UI exports
from .ui import (
    MainWindow,
    EmbedTab,
    ExtractTab,
    DragDropLabel,
    ImageListWidget,
    PasswordLineEdit
)
# Worker exports
from .workers import (
    EmbedWorker, EmbedConfig, VisibleConfig, BlindConfig, EmbedResult,
    ExtractWorker, ExtractConfig, ExtractResult, BatchExtractWorker
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__app_name__",

    # Core
    "VisibleWatermarker",
    "BlindWatermarkerAdapter",

    # Workers
    "EmbedWorker",
    "EmbedConfig",
    "VisibleConfig",
    "BlindConfig",
    "EmbedResult",
    "ExtractWorker",
    "ExtractConfig",
    "ExtractResult",
    "BatchExtractWorker",

    # UI
    "MainWindow",
    "EmbedTab",
    "ExtractTab",
    "DragDropLabel",
    "ImageListWidget",
    "PasswordLineEdit",
]
