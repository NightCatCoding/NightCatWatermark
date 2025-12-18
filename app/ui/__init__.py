"""
UI Module - User Interface Components
=====================================
Contains all PyQt6 UI components for the WatermarkMaster application.

Architecture:
- widgets.py: Reusable UI components
- tab_embed.py: Watermark embedding interface
- tab_extract.py: Watermark extraction interface  
- main_window.py: Main application window
- styles.qss: Dark theme stylesheet
"""

from .main_window import MainWindow
from .tab_embed import EmbedTab
from .tab_extract import ExtractTab
from .widgets import DragDropLabel, ImageListWidget, PasswordLineEdit

__all__ = [
    "DragDropLabel",
    "ImageListWidget",
    "PasswordLineEdit",
    "EmbedTab",
    "ExtractTab",
    "MainWindow",
]
