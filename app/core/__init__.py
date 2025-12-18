"""
Core Module - Pure Algorithm Logic
==================================
This module contains no UI dependencies.
All watermark processing algorithms are implemented here.
"""

from .blind import BlindWatermarkerAdapter
from .visible import VisibleWatermarker

__all__ = ["VisibleWatermarker", "BlindWatermarkerAdapter"]
