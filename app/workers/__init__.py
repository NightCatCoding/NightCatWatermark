"""
Workers Module - Async Thread Management
========================================
Contains QThread workers for non-blocking watermark operations.

All heavy computations run in separate threads to keep the UI responsive.

Components:
- EmbedWorker: Watermark embedding with progress tracking
- ExtractWorker: Blind watermark extraction
- PreviewWorker: Real-time preview generation with debounce
"""

from .embed_worker import EmbedWorker, EmbedConfig, VisibleConfig, BlindConfig, EmbedResult
from .extract_worker import ExtractWorker, ExtractConfig, ExtractResult, BatchExtractWorker
from .preview_worker import (
    PreviewWorker, PreviewConfig, PreviewDebouncer, PreviewManager,
    pil_image_to_qpixmap
)

__all__ = [
    # Embed
    "EmbedWorker",
    "EmbedConfig",
    "VisibleConfig",
    "BlindConfig",
    "EmbedResult",
    # Extract
    "ExtractWorker",
    "ExtractConfig",
    "ExtractResult",
    "BatchExtractWorker",
    # Preview
    "PreviewWorker",
    "PreviewConfig",
    "PreviewDebouncer",
    "PreviewManager",
    "pil_image_to_qpixmap",
]
