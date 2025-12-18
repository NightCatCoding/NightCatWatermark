"""
Embed Tab V1.0 - Three-Column Equal-Height Layout
=================================================
Implements the Input -> Process -> Output psychological model with strict height alignment.

Layout (Ratio 1:1.5:3):
┌──────────────┬─────────────────────┬────────────────────────────────────────┐
│   ZONE A     │      ZONE B         │              ZONE C                    │
│   INPUT      │      PROCESS        │              OUTPUT                    │
│              │                     │                                        │
│  ┌────────┐  │  ┌───────┬───────┐  │  ┌────────────────────────────────┐  │
│  │ Image  │  │  │ 明水印 │ 暗水印 │  │  │                                │  │
│  │ List   │  │  └───────┴───────┘  │  │      TRANSPARENCY GRID         │  │
│  │        │  │  ┌───────────────┐  │  │        PREVIEW CANVAS          │  │
│  │        │  │  │               │  │  │                                │  │
│  │        │  │  │  ScrollArea   │  │  │        (棋盤格背景)             │  │
│  │        │  │  │  Parameters   │  │  │                                │  │
│  │        │  │  │               │  │  │                                │  │
│  └────────┘  │  └───────────────┘  │  └────────────────────────────────┘  │
│              │  ┌───────────────┐  │  ┌────────────────────────────────┐  │
│              │  │ Output + CTA  │  │  │        Preview Info Bar        │  │
│              │  └───────────────┘  │  └────────────────────────────────┘  │
└──────────────┴─────────────────────┴────────────────────────────────────────┘

Design:
- Zone A: Dark "warehouse" feel, minimal, functional
- Zone B: Control center with scrollable parameters
- Zone C: Maximum reward area with transparency grid - NOW FULL HEIGHT
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import (
    QWheelEvent, QPainter, QColor, QPen, QPixmap
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSlider, QSpinBox, QPushButton,
    QFileDialog, QProgressBar, QSplitter, QFrame, QDoubleSpinBox,
    QTabWidget, QScrollArea, QSizePolicy
)

from .widgets import (
    ImageListWidget, PasswordLineEdit, ColorButton
)
from ..workers.preview_worker import PreviewManager, PreviewConfig


# ============================================================================
# CUSTOM WIDGETS
# ============================================================================

class NoWheelSlider(QSlider):
    """Slider that ignores wheel events unless explicitly focused."""

    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event: QWheelEvent):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class TransparencyGridWidget(QWidget):
    """
    Preview widget with transparency grid background.
    
    Displays a checkerboard pattern to indicate transparent areas,
    similar to Photoshop/GIMP.
    """

    # Grid colors
    GRID_LIGHT = QColor("#222639")
    GRID_DARK = QColor("#1A1E2E")
    GRID_SIZE = 12

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._pixmap: Optional[QPixmap] = None
        self._is_loading = False
        self._error_message: Optional[str] = None

        self.setObjectName("previewCanvas")
        self.setMinimumSize(400, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_preview(self, pixmap: QPixmap):
        """Set the preview image."""
        self._pixmap = pixmap
        self._is_loading = False
        self._error_message = None
        self.update()

    def set_loading(self, is_loading: bool = True):
        """Set loading state."""
        self._is_loading = is_loading
        if is_loading:
            self._pixmap = None
        self.update()

    def set_error(self, message: str):
        """Set error state."""
        self._error_message = message
        self._is_loading = False
        self._pixmap = None
        self.update()

    def clear(self):
        """Clear the preview."""
        self._pixmap = None
        self._is_loading = False
        self._error_message = None
        self.update()

    def paintEvent(self, event):
        """Custom paint with transparency grid."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()

        # === Draw rounded background with transparency grid ===
        # First, clip to rounded rect
        from PyQt6.QtGui import QPainterPath
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(rect).adjusted(1, 1, -1, -1), 10, 10)
        painter.setClipPath(clip_path)

        # Draw transparency grid
        for y in range(0, rect.height(), self.GRID_SIZE):
            for x in range(0, rect.width(), self.GRID_SIZE):
                is_light = ((x // self.GRID_SIZE) + (y // self.GRID_SIZE)) % 2 == 0
                color = self.GRID_LIGHT if is_light else self.GRID_DARK
                painter.fillRect(x, y, self.GRID_SIZE, self.GRID_SIZE, color)

        painter.setClipping(False)

        # === Draw border (rounded) ===
        pen = QPen(QColor("#3B4261"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)

        # === Draw content ===
        if self._is_loading:
            self._draw_loading(painter, rect)
        elif self._error_message:
            self._draw_error(painter, rect)
        elif self._pixmap and not self._pixmap.isNull():
            self._draw_preview(painter, rect)
        else:
            self._draw_placeholder(painter, rect)

        painter.end()

    def _draw_preview(self, painter: QPainter, rect):
        """Draw the preview image centered and scaled."""
        # Scale to fit while maintaining aspect ratio
        scaled = self._pixmap.scaled(
            rect.width() - 40,
            rect.height() - 40,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Center the image
        x = (rect.width() - scaled.width()) / 2
        y = (rect.height() - scaled.height()) / 2

        # Draw subtle shadow
        shadow_rect = QRectF(x + 4, y + 4, scaled.width(), scaled.height())
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 60))

        # Draw image
        painter.drawPixmap(int(x), int(y), scaled)

        # Draw rounded frame around image
        pen = QPen(QColor("#565F89"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRoundedRect(int(x), int(y), scaled.width(), scaled.height(), 4, 4)

    def _draw_placeholder(self, painter: QPainter, rect):
        """Draw placeholder when no image is loaded."""
        center_y = rect.height() // 2

        # Draw icon
        painter.setPen(QPen(QColor("#3B4261")))
        font = painter.font()
        font.setPointSize(48)
        painter.setFont(font)
        icon_rect = QRectF(rect.x(), center_y - 40, rect.width(), 60)
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "◇")

        # Draw text below
        font.setPointSize(13)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#565F89")))

        text_rect = QRectF(rect.x(), center_y + 30, rect.width(), 30)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                         "選擇圖片後在此預覽")

    def _draw_loading(self, painter: QPainter, rect):
        """Draw loading indicator."""
        painter.setPen(QPen(QColor("#7AA2F7")))
        font = painter.font()
        font.setPointSize(14)
        painter.setFont(font)
        painter.drawText(QRectF(rect), Qt.AlignmentFlag.AlignCenter, "⟳ 生成預覽中...")

    def _draw_error(self, painter: QPainter, rect):
        """Draw error message."""
        painter.setPen(QPen(QColor("#F7768E")))
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        painter.drawText(QRectF(rect), Qt.AlignmentFlag.AlignCenter, f"✕ {self._error_message}")


# ============================================================================
# MAIN EMBED TAB
# ============================================================================

class EmbedTab(QWidget):
    """
    Tab widget V1.0 for embedding watermarks.
    
    Three-column layout: Input (1) | Process (1.5) | Output (3)
    All columns stretch to equal height.
    """

    start_embed_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # V3.0: Reduced debounce to 50ms (safe with Proxy Pattern optimization)
        # The proxy image processing is now fast enough to handle 20 FPS updates
        self._preview_manager = PreviewManager(debounce_ms=50, parent=self)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup the three-column layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Main splitter for three columns
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        # === ZONE A: INPUT (Ratio 1) ===
        zone_a = self._create_zone_a()
        splitter.addWidget(zone_a)

        # === ZONE B: PROCESS (Ratio 1.5) ===
        zone_b = self._create_zone_b()
        splitter.addWidget(zone_b)

        # === ZONE C: OUTPUT (Ratio 3) ===
        zone_c = self._create_zone_c()
        splitter.addWidget(zone_c)

        # Set proportions (1 : 1.5 : 3 = 2 : 3 : 6)
        splitter.setSizes([200, 300, 600])
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 6)

        main_layout.addWidget(splitter)

    # ========================================================================
    # ZONE A: INPUT
    # ========================================================================

    def _create_zone_a(self) -> QFrame:
        """Create Zone A - Input panel (image list)."""
        panel = QFrame()
        panel.setObjectName("inputPanel")
        panel.setMinimumWidth(200)
        panel.setMaximumWidth(320)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 8, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("INPUT")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("panelSeparator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Image list widget
        self.image_list = ImageListWidget()
        layout.addWidget(self.image_list, 1)

        return panel

    # ========================================================================
    # ZONE B: PROCESS
    # ========================================================================

    def _create_zone_b(self) -> QFrame:
        """Create Zone B - Control/Process panel."""
        panel = QFrame()
        panel.setObjectName("controlPanel")
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(420)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("PROCESS")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("panelSeparator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # === TABBED SETTINGS ===
        self.settings_tabs = QTabWidget()
        self.settings_tabs.setObjectName("settingsTabs")
        self.settings_tabs.setDocumentMode(False)

        # Tab 1: Visible Watermark
        visible_tab = self._create_visible_tab()
        self.settings_tabs.addTab(visible_tab, "明水印")

        # Tab 2: Blind Watermark
        blind_tab = self._create_blind_tab()
        self.settings_tabs.addTab(blind_tab, "暗水印")

        layout.addWidget(self.settings_tabs, 1)

        # === OUTPUT SECTION (Fixed at bottom) ===
        output_section = self._create_output_section()
        layout.addWidget(output_section)

        return panel

    def _create_visible_tab(self) -> QWidget:
        """Create the visible watermark settings tab with scroll area."""
        # Outer container
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Scroll area for parameters
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Content widget inside scroll
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Enable toggle
        self.visible_enabled = QPushButton("◆ 啟用明水印")
        self.visible_enabled.setObjectName("toggleButton")
        self.visible_enabled.setCheckable(True)
        self.visible_enabled.setChecked(True)
        self.visible_enabled.setMinimumHeight(42)
        layout.addWidget(self.visible_enabled)

        # Text input
        layout.addWidget(self._create_field_group(
            "水印文字",
            self._create_text_input()
        ))

        # Two-column grid for sliders
        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(16)

        # Left column
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        size_widget, self.font_size_slider, self.font_size_spin = self._create_slider(
            "字體大小", 8, 200, 40, " px"
        )
        left_col.addWidget(size_widget)

        opacity_widget, self.opacity_slider, self.opacity_spin = self._create_slider(
            "不透明度", 0, 255, 80, ""
        )
        left_col.addWidget(opacity_widget)

        h_space_widget, self.spacing_h_slider, self.spacing_h_spin = self._create_float_slider(
            "水平間距", 1, 10.0, 1.5, "x"
        )
        left_col.addWidget(h_space_widget)

        grid_layout.addLayout(left_col)

        # Right column
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        angle_widget, self.angle_slider, self.angle_spin = self._create_slider(
            "旋轉角度", -90, 90, 30, "°"
        )
        right_col.addWidget(angle_widget)

        # Color button
        color_widget = QWidget()
        color_layout = QVBoxLayout(color_widget)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(6)
        color_label = QLabel("顏色")
        color_label.setObjectName("fieldLabel")
        color_layout.addWidget(color_label)
        self.color_button = ColorButton((128, 128, 128))
        self.color_button.setFixedHeight(40)
        color_layout.addWidget(self.color_button)
        right_col.addWidget(color_widget)

        v_space_widget, self.spacing_v_slider, self.spacing_v_spin = self._create_float_slider(
            "垂直間距", 1, 10.0, 1.2, "x"
        )
        right_col.addWidget(v_space_widget)

        grid_layout.addLayout(right_col)
        layout.addWidget(grid_widget)

        layout.addStretch()

        scroll.setWidget(content)
        container_layout.addWidget(scroll)

        return container

    def _create_blind_tab(self) -> QWidget:
        """Create the blind watermark settings tab."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Enable toggle
        self.blind_enabled = QPushButton("◆ 啟用暗水印")
        self.blind_enabled.setObjectName("toggleButton")
        self.blind_enabled.setCheckable(True)
        self.blind_enabled.setChecked(False)
        self.blind_enabled.setMinimumHeight(42)
        layout.addWidget(self.blind_enabled)

        # Password
        self.blind_password = PasswordLineEdit("加密密碼（必填）")
        layout.addWidget(self._create_field_group("加密密碼", self.blind_password))

        # Hidden text
        self.blind_text = QLineEdit()
        self.blind_text.setPlaceholderText("要隱藏的文字信息")
        layout.addWidget(self._create_field_group("隱藏信息", self.blind_text))

        # Info box
        info_box = QFrame()
        info_box.setObjectName("infoBox")
        info_layout = QVBoxLayout(info_box)
        info_layout.setContentsMargins(14, 14, 14, 14)
        info_layout.setSpacing(10)

        info_title = QLabel("◇ 關於暗水印")
        info_title.setObjectName("infoBoxTitle")
        info_layout.addWidget(info_title)

        info_text = QLabel(
            "• 嵌入圖片頻域，肉眼完全不可見\n"
            "• 提取需要相同的密碼\n"
            "• 輸出必須為 PNG 格式（無損）"
        )
        info_text.setObjectName("infoBoxText")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        layout.addWidget(info_box)
        layout.addStretch()

        scroll.setWidget(content)
        container_layout.addWidget(scroll)

        return container

    def _create_output_section(self) -> QFrame:
        """Create the output directory and action button section."""
        section = QFrame()
        section.setObjectName("outputSection")

        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(12)

        # Output directory row
        output_row = QHBoxLayout()
        output_row.setSpacing(8)

        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("輸出目錄...")
        self.output_path.setText(str(Path.home() / "Pictures" / "Watermarked"))
        output_row.addWidget(self.output_path, 1)

        self.browse_btn = QPushButton("📁")
        self.browse_btn.setObjectName("iconButton")
        self.browse_btn.setFixedSize(40, 40)
        self.browse_btn.setToolTip("選擇輸出目錄")
        self.browse_btn.clicked.connect(self._browse_output)
        output_row.addWidget(self.browse_btn)

        layout.addLayout(output_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusText")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # CTA Button
        self.start_btn = QPushButton("▶ 開始製作")
        self.start_btn.setObjectName("ctaButton")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.start_btn)

        # Cancel button (hidden by default)
        self.cancel_btn = QPushButton("✕ 取消")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setMinimumHeight(48)
        layout.addWidget(self.cancel_btn)

        return section

    # ========================================================================
    # ZONE C: OUTPUT / PREVIEW
    # ========================================================================

    def _create_zone_c(self) -> QFrame:
        """Create Zone C - Preview/Output panel (V1.0: fills full height)."""
        panel = QFrame()
        panel.setObjectName("previewPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 16, 16, 16)
        layout.setSpacing(12)

        # Header row (simplified - no mascot here anymore)
        header = QLabel("OUTPUT")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("panelSeparator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # === PREVIEW CANVAS (Main attraction - fills remaining space) ===
        self.preview_canvas = TransparencyGridWidget()
        layout.addWidget(self.preview_canvas, 1)  # stretch factor 1 to fill

        # Preview status bar
        self.preview_info = QLabel("◇ 平鋪預覽 — 調整參數即時更新")
        self.preview_info.setObjectName("previewInfoBar")
        self.preview_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_info)

        return panel

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _create_text_input(self) -> QLineEdit:
        """Create the watermark text input."""
        self.visible_text = QLineEdit()
        self.visible_text.setPlaceholderText("水印文字，如：© NightCat 2024")
        self.visible_text.setText("© NightCat")
        return self.visible_text

    def _create_field_group(self, label: str, widget: QWidget) -> QWidget:
        """Create a labeled field group."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setObjectName("fieldLabel")
        layout.addWidget(lbl)
        layout.addWidget(widget)

        return container

    def _create_slider(self, label: str, min_val: int, max_val: int,
                       default: int, suffix: str) -> tuple:
        """Create a slider with spin box."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setObjectName("fieldLabel")
        layout.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(10)

        slider = NoWheelSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        row.addWidget(slider, 1)

        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSuffix(suffix)
        spin.setFixedWidth(80)
        row.addWidget(spin)

        layout.addLayout(row)

        # Sync slider and spin
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)

        return widget, slider, spin

    def _create_float_slider(self, label: str, min_val: float, max_val: float,
                             default: float, suffix: str) -> tuple:
        """Create a float slider with double spin box."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setObjectName("fieldLabel")
        layout.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(10)

        slider = NoWheelSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(min_val * 10), int(max_val * 10))
        slider.setValue(int(default * 10))
        row.addWidget(slider, 1)

        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(0.1)
        spin.setDecimals(1)
        spin.setSuffix(suffix)
        spin.setFixedWidth(80)
        row.addWidget(spin)

        layout.addLayout(row)

        slider.valueChanged.connect(lambda v: spin.setValue(v / 10.0))
        spin.valueChanged.connect(lambda v: slider.setValue(int(v * 10)))

        return widget, slider, spin

    # ========================================================================
    # SIGNAL CONNECTIONS (V3.0: Optimized for Proxy Pattern)
    # ========================================================================

    def _connect_signals(self):
        """
        Connect all signals for reactive preview updates.
        
        SIGNAL STRATEGY:
        ----------------
        We connect to SpinBox.valueChanged (not Slider.valueChanged) because:
        1. Slider and Spin are already cross-connected (slider→spin, spin→slider)
        2. This prevents duplicate signal emissions
        3. SpinBox valueChanged fires on FINAL values, reducing noise
        
        DEBOUNCE CHAIN:
        User drags slider → slider.valueChanged → spin.setValue
        → spin.valueChanged → _request_preview → PreviewManager.request_preview
        → PreviewDebouncer (50ms) → PreviewWorker.start
        
        This ensures smooth UX even during rapid slider adjustments.
        """
        # Image list changes → clear cache and re-preview
        self.image_list.images_changed.connect(self._on_images_changed)

        # Image selection changes → update preview to show selected image
        self.image_list.selection_changed.connect(self._on_selection_changed)

        # Preview manager signals → UI updates
        self._preview_manager.preview_updated.connect(self._on_preview_updated)
        self._preview_manager.preview_error.connect(self._on_preview_error)
        self._preview_manager.preview_started.connect(self._on_preview_started)

        # === Visible watermark settings → preview ===
        # All changes funnel through _request_preview → debouncer
        self.visible_enabled.toggled.connect(self._request_preview)
        self.visible_text.textChanged.connect(self._request_preview)

        # Connect to SPIN valueChanged (not slider) to avoid double-triggering
        # The slider↔spin sync handles the other direction
        self.font_size_spin.valueChanged.connect(self._request_preview)
        self.opacity_spin.valueChanged.connect(self._request_preview)
        self.angle_spin.valueChanged.connect(self._request_preview)
        self.spacing_h_spin.valueChanged.connect(self._request_preview)
        self.spacing_v_spin.valueChanged.connect(self._request_preview)

        # Color picker
        self.color_button.color_changed.connect(self._request_preview)

    def _on_images_changed(self, images):
        """Handle image list change (add/remove images)."""
        self._preview_manager.clear_cache()
        if images:
            self._request_preview()
        else:
            self.preview_canvas.clear()

    def _on_selection_changed(self, selected_paths):
        """
        Handle image selection change in the list.
        
        When user clicks on an image in the list, update the preview
        to show that specific image with current watermark settings.
        """
        if selected_paths:
            # Trigger preview update for the newly selected image
            self._request_preview()

    def _request_preview(self, *args):
        """
        Request a new preview generation via the Proxy Pattern.
        
        IMPORTANT: The config contains ORIGINAL user parameters.
        The PreviewWorker will automatically scale them for the proxy image.
        This ensures WYSIWYG: preview looks identical to final output.
        """
        # Get selected image, or fall back to first image
        selected_image = self.image_list.get_selected_image()
        if not selected_image:
            return

        config = PreviewConfig(
            image_path=selected_image,
            visible_enabled=self.visible_enabled.isChecked(),
            visible_text=self.visible_text.text(),
            font_size=self.font_size_spin.value(),  # Original size (will be scaled)
            opacity=self.opacity_spin.value(),
            angle=self.angle_spin.value(),
            color=self.color_button.get_color(),
            spacing_h_ratio=self.spacing_h_spin.value(),  # Ratios don't need scaling
            spacing_v_ratio=self.spacing_v_spin.value(),
            max_preview_size=800  # Proxy size limit for fast preview
        )

        self._preview_manager.request_preview(config)

    def _on_preview_started(self):
        """Handle preview generation started."""
        self.preview_canvas.set_loading(True)
        self.preview_info.setText("⟳ 生成預覽中...")
        self.preview_info.setProperty("status", "loading")
        self.preview_info.style().unpolish(self.preview_info)
        self.preview_info.style().polish(self.preview_info)

    def _on_preview_updated(self, pixmap):
        """Handle preview updated."""
        self.preview_canvas.set_preview(pixmap)
        self.preview_info.setText("◆ 預覽已更新")
        self.preview_info.setProperty("status", "success")
        self.preview_info.style().unpolish(self.preview_info)
        self.preview_info.style().polish(self.preview_info)

    def _on_preview_error(self, error):
        """Handle preview error."""
        self.preview_canvas.set_error(error)
        self.preview_info.setText(f"✕ {error}")
        self.preview_info.setProperty("status", "error")
        self.preview_info.style().unpolish(self.preview_info)
        self.preview_info.style().polish(self.preview_info)

    def _browse_output(self):
        """Open directory browser."""
        directory = QFileDialog.getExistingDirectory(
            self, "選擇輸出目錄", self.output_path.text()
        )
        if directory:
            self.output_path.setText(directory)

    def _on_start_clicked(self):
        """Handle start button click."""
        config = self.get_config()
        self.start_embed_requested.emit(config)

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def get_config(self) -> dict:
        """Get current configuration."""
        return {
            "image_paths": self.image_list.get_images(),
            "output_dir": Path(self.output_path.text()),
            "visible": {
                "enabled": self.visible_enabled.isChecked(),
                "text": self.visible_text.text(),
                "font_size": self.font_size_spin.value(),
                "opacity": self.opacity_spin.value(),
                "angle": self.angle_spin.value(),
                "color": self.color_button.get_color(),
                "spacing_h_ratio": self.spacing_h_spin.value(),
                "spacing_v_ratio": self.spacing_v_spin.value(),
            },
            "blind": {
                "enabled": self.blind_enabled.isChecked(),
                "text": self.blind_text.text(),
                "password": self.blind_password.text(),
            }
        }

    # Compatibility aliases
    @property
    def visible_group(self):
        return self.visible_enabled

    @property
    def blind_group(self):
        return self.blind_enabled

    @property
    def preview_widget(self):
        """Compatibility alias for preview canvas."""
        return self.preview_canvas

    def set_progress(self, current: int, total: int, filename: str = ""):
        """Update progress bar."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        if filename:
            self.status_label.setText(f"處理中: {filename}")

    def set_status(self, message: str):
        """Set status message."""
        self.status_label.setText(message)

    def set_processing(self, is_processing: bool):
        """Set processing state."""
        self.start_btn.setEnabled(not is_processing)
        self.start_btn.setVisible(not is_processing)
        self.cancel_btn.setVisible(is_processing)
        self.progress_bar.setVisible(is_processing)

        self.image_list.setEnabled(not is_processing)
        self.output_path.setEnabled(not is_processing)
        self.browse_btn.setEnabled(not is_processing)

    def set_complete(self, success: bool = True, message: str = ""):
        """Set completion state."""
        if success:
            self.status_label.setText(message or "✓ 完成！")
            self.status_label.setStyleSheet("color: #9ECE6A;")
        else:
            self.status_label.setText(message or "✕ 失敗")
            self.status_label.setStyleSheet("color: #F7768E;")

    def reset_progress(self):
        """Reset progress indicators."""
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        self.status_label.setStyleSheet("")

    def set_output_directory(self, path: str):
        """Set output directory."""
        self.output_path.setText(path)

    def get_output_directory(self) -> str:
        """Get output directory."""
        return self.output_path.text()
