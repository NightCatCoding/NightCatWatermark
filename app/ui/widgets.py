"""
Reusable UI Widgets
===================
Custom widgets used across the application.
Modern Cyberpunk theme with NightCat mascot integration.

Key Components:
- MascotStatusWidget: Persistent mascot display with status
- DragDropLabel: Drag-and-drop file zone
- ImageListWidget: Image list with thumbnails
- PreviewWidget: Real-time watermark preview display
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF
from PyQt6.QtGui import (
    QDragEnterEvent, QDropEvent, QPixmap, QIcon, QColor,
    QPainter, QPainterPath, QBrush, QPen, QFont, QLinearGradient
)
from PyQt6.QtWidgets import (
    QLabel, QListWidget, QListWidgetItem, QLineEdit,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QAbstractItemView, QSizePolicy, QGraphicsDropShadowEffect
)


def get_mascot_path() -> Path:
    """Get the path to the mascot image."""
    # Try multiple possible locations
    possible_paths = [
        Path(__file__).parent / "assets" / "dark_watermarked_blind-200.png"
    ]
    for path in possible_paths:
        if path.exists():
            return path
    return possible_paths[0]  # Return default path even if not exists


class MascotStatus(Enum):
    """Status states for the mascot widget."""
    IDLE = "idle"
    THINKING = "thinking"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class MascotStatusWidget(QWidget):
    """
    Persistent mascot widget that displays throughout the application.
    
    Shows the NightCat mascot with status text that changes based on
    application state (idle, processing, complete, etc.).
    
    This widget should be placed in a fixed location and never hidden.
    """

    # Status messages for different states
    STATUS_MESSAGES = {
        MascotStatus.IDLE: "準備好了，隨時開始！",
        MascotStatus.THINKING: "讓我想想看...",
        MascotStatus.PROCESSING: "正在努力處理中...",
        MascotStatus.COMPLETE: "搞定啦！✨",
        MascotStatus.ERROR: "哎呀，出了點問題...",
    }

    STATUS_ICONS = {
        MascotStatus.IDLE: "😺",
        MascotStatus.THINKING: "🤔",
        MascotStatus.PROCESSING: "⚙️",
        MascotStatus.COMPLETE: "🎉",
        MascotStatus.ERROR: "😿",
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._status = MascotStatus.IDLE
        self._mascot_pixmap: Optional[QPixmap] = None
        self._mascot_size = 80

        self._setup_ui()
        self._load_mascot()

    def _setup_ui(self):
        """Setup the widget UI."""
        self.setObjectName("mascotWidget")
        self.setMinimumSize(120, 140)
        self.setMaximumHeight(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mascot image label
        self.mascot_label = QLabel()
        self.mascot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mascot_label.setFixedSize(self._mascot_size, self._mascot_size)
        layout.addWidget(self.mascot_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status text label
        self.status_label = QLabel(self.STATUS_MESSAGES[MascotStatus.IDLE])
        self.status_label.setObjectName("mascotStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("""
            QLabel#mascotStatus {
                color: #B0B8C4;
                font-size: 11px;
                font-weight: 500;
                padding: 4px;
            }
        """)
        layout.addWidget(self.status_label)

        # Add glow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 180, 216, 40))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    def _load_mascot(self):
        """Load and display the mascot image."""
        mascot_path = get_mascot_path()
        if mascot_path.exists():
            self._mascot_pixmap = QPixmap(str(mascot_path))
            self._update_mascot_display()
        else:
            # Fallback to emoji if image not found
            self.mascot_label.setText("🐱")
            self.mascot_label.setStyleSheet("""
                QLabel {
                    font-size: 48px;
                    background-color: #2A2D35;
                    border-radius: 40px;
                }
            """)

    def _update_mascot_display(self):
        """Update the mascot display with circular crop."""
        if self._mascot_pixmap is None or self._mascot_pixmap.isNull():
            return

        # Scale mascot
        scaled = self._mascot_pixmap.scaled(
            self._mascot_size, self._mascot_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

        # Center crop to square
        if scaled.width() > self._mascot_size:
            x_offset = (scaled.width() - self._mascot_size) // 2
            scaled = scaled.copy(x_offset, 0, self._mascot_size, self._mascot_size)
        if scaled.height() > self._mascot_size:
            y_offset = (scaled.height() - self._mascot_size) // 2
            scaled = scaled.copy(0, y_offset, self._mascot_size, self._mascot_size)

        # Create circular mask
        circular = QPixmap(self._mascot_size, self._mascot_size)
        circular.fill(Qt.GlobalColor.transparent)

        painter = QPainter(circular)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw circular clip path
        path = QPainterPath()
        path.addEllipse(0, 0, self._mascot_size, self._mascot_size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)

        # Draw border based on status
        border_color = self._get_status_color()
        pen = QPen(QColor(border_color))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setClipping(False)
        painter.drawEllipse(1, 1, self._mascot_size - 2, self._mascot_size - 2)

        painter.end()

        self.mascot_label.setPixmap(circular)

    def _get_status_color(self) -> str:
        """Get the border color for current status."""
        colors = {
            MascotStatus.IDLE: "#00B4D8",
            MascotStatus.THINKING: "#F59E0B",
            MascotStatus.PROCESSING: "#8B5CF6",
            MascotStatus.COMPLETE: "#10B981",
            MascotStatus.ERROR: "#EF4444",
        }
        return colors.get(self._status, "#00B4D8")

    def set_status(self, status: MascotStatus, custom_message: Optional[str] = None):
        """
        Set the mascot status.
        
        Args:
            status: The new status.
            custom_message: Optional custom message to display.
        """
        self._status = status

        # Update status text
        message = custom_message or self.STATUS_MESSAGES.get(status, "")
        icon = self.STATUS_ICONS.get(status, "")
        self.status_label.setText(f"{icon} {message}")

        # Update border color
        self._update_mascot_display()

    def get_status(self) -> MascotStatus:
        """Get the current status."""
        return self._status

    def paintEvent(self, event):
        """Custom paint for background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # Draw rounded background
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 12, 12)

        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, QColor("#2A2D35"))
        gradient.setColorAt(1, QColor("#252830"))
        painter.fillPath(path, gradient)

        # Draw subtle border
        pen = QPen(QColor("#353842"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)

        painter.end()


class PreviewWidget(QWidget):
    """
    Widget for displaying real-time watermark preview.
    
    Shows a scaled preview of the watermarked image with loading
    and error states.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._pixmap: Optional[QPixmap] = None
        self._is_loading = False
        self._error_message: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the widget UI."""
        self.setObjectName("previewWidget")
        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.preview_label.setObjectName("previewLabel")
        layout.addWidget(self.preview_label)

        # Set initial state
        self._show_placeholder()

    def _show_placeholder(self):
        """Show placeholder when no image is loaded."""
        self.preview_label.setText("📷 選擇圖片後將在此顯示預覽")
        self.preview_label.setStyleSheet("""
            QLabel#previewLabel {
                color: #6B7280;
                font-size: 14px;
                background-color: #1E2025;
                border: 2px dashed #353842;
                border-radius: 12px;
            }
        """)

    def set_preview(self, pixmap: QPixmap):
        """
        Set the preview image.
        
        Args:
            pixmap: QPixmap to display.
        """
        self._pixmap = pixmap
        self._is_loading = False
        self._error_message = None
        self._update_display()

    def set_loading(self, is_loading: bool = True):
        """
        Set loading state.
        
        Args:
            is_loading: Whether preview is loading.
        """
        self._is_loading = is_loading
        if is_loading:
            self.preview_label.setText("⏳ 正在生成預覽...")
            self.preview_label.setStyleSheet("""
                QLabel#previewLabel {
                    color: #00B4D8;
                    font-size: 14px;
                    background-color: #1E2025;
                    border: 2px solid #00B4D8;
                    border-radius: 12px;
                }
            """)

    def set_error(self, message: str):
        """
        Set error state.
        
        Args:
            message: Error message to display.
        """
        self._error_message = message
        self._is_loading = False
        self.preview_label.setText(f"❌ {message}")
        self.preview_label.setStyleSheet("""
            QLabel#previewLabel {
                color: #EF4444;
                font-size: 13px;
                background-color: #1E2025;
                border: 2px solid #DC2626;
                border-radius: 12px;
                padding: 20px;
            }
        """)

    def clear(self):
        """Clear the preview."""
        self._pixmap = None
        self._is_loading = False
        self._error_message = None
        self._show_placeholder()

    def _update_display(self):
        """Update the display with current pixmap."""
        if self._pixmap is None or self._pixmap.isNull():
            self._show_placeholder()
            return

        # Scale pixmap to fit widget while maintaining aspect ratio
        scaled = self._pixmap.scaled(
            self.preview_label.size() - QSize(20, 20),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.preview_label.setPixmap(scaled)
        self.preview_label.setStyleSheet("""
            QLabel#previewLabel {
                background-color: #1E2025;
                border: 2px solid #353842;
                border-radius: 12px;
                padding: 10px;
            }
        """)

    def resizeEvent(self, event):
        """Handle resize to update preview scaling."""
        super().resizeEvent(event)
        if self._pixmap and not self._is_loading and not self._error_message:
            self._update_display()


class DragDropLabel(QLabel):
    """
    A label that accepts drag-and-drop files.
    
    Displays a drop zone with visual feedback when files are dragged over.
    Compact design without mascot (mascot is now in separate widget).
    
    Signals:
        files_dropped(list[Path]): Emitted when files are dropped.
    """

    files_dropped = pyqtSignal(list)  # List[Path]

    # Supported image formats
    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff"}

    # Color scheme
    ACCENT_COLOR = "#00B4D8"
    BG_COLOR = "#2A2D35"
    BORDER_COLOR = "#4B5563"
    TEXT_COLOR = "#B0B8C4"

    def __init__(
            self,
            text: str = "把圖片拖過來給我吧～",
            show_mascot: bool = False,  # Default to False now
            parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._hint_text = text
        self._show_mascot = show_mascot
        self._is_dragging = False
        self._mascot_pixmap: Optional[QPixmap] = None

        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setObjectName("dragDropLabel")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Load mascot image if needed
        if self._show_mascot:
            self._load_mascot()

        # Add subtle glow effect
        self._setup_effects()

    def _load_mascot(self):
        """Load the mascot image."""
        mascot_path = get_mascot_path()
        if mascot_path.exists():
            self._mascot_pixmap = QPixmap(str(mascot_path))
        else:
            self._mascot_pixmap = None

    def _setup_effects(self):
        """Setup visual effects."""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 180, 216, 20))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        """Custom paint for the drop zone - V4.1 Fixed Layout."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()
        margin = 4

        # Draw background with rounded corners
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect).adjusted(margin, margin, -margin, -margin), 10, 10)

        # Background gradient
        gradient = QLinearGradient(0, 0, 0, rect.height())
        if self._is_dragging:
            gradient.setColorAt(0, QColor("#1E3A4A"))
            gradient.setColorAt(1, QColor("#152535"))
        else:
            gradient.setColorAt(0, QColor("#2A2D35"))
            gradient.setColorAt(1, QColor("#252830"))

        painter.fillPath(path, QBrush(gradient))

        # Draw dashed border
        pen = QPen()
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(2)
        pen.setDashPattern([6, 4])

        if self._is_dragging:
            pen.setColor(QColor(self.ACCENT_COLOR))
        else:
            pen.setColor(QColor(self.BORDER_COLOR))

        painter.setPen(pen)
        painter.drawRoundedRect(QRectF(rect).adjusted(margin + 1, margin + 1, -margin - 1, -margin - 1), 9, 9)

        # Calculate content area
        content_rect = rect.adjusted(margin + 8, margin + 8, -margin - 8, -margin - 8)
        content_height = content_rect.height()
        content_width = content_rect.width()

        # Total content height: icon(24) + gap(8) + text(16) + gap(4) + subtext(14) = ~66
        total_content_height = 66
        start_y = content_rect.top() + (content_height - total_content_height) // 2

        # Draw upload arrow icon
        icon_color = QColor(self.ACCENT_COLOR if self._is_dragging else "#6B7280")
        painter.setPen(QPen(icon_color, 2))

        center_x = content_rect.center().x()
        arrow_top = start_y
        arrow_size = 24

        # Arrow pointing up
        painter.drawLine(center_x, arrow_top + 4, center_x, arrow_top + arrow_size - 4)
        painter.drawLine(center_x, arrow_top + 4, center_x - 7, arrow_top + 12)
        painter.drawLine(center_x, arrow_top + 4, center_x + 7, arrow_top + 12)

        # Draw main hint text
        text_y = arrow_top + arrow_size + 8
        
        font = QFont()
        font.setFamily("Microsoft YaHei UI")
        font.setPointSize(11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)

        if self._is_dragging:
            painter.setPen(QColor(self.ACCENT_COLOR))
            hint = "鬆開滑鼠放下圖片 ✨"
        else:
            painter.setPen(QColor(self.TEXT_COLOR))
            hint = self._hint_text

        text_rect = QRectF(content_rect.left(), text_y, content_width, 20)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, hint)

        # Draw secondary hint
        sub_y = text_y + 20
        font.setPointSize(9)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor("#6B7280"))

        sub_hint = "PNG, JPG, WEBP 等格式"
        sub_rect = QRectF(content_rect.left(), sub_y, content_width, 16)
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, sub_hint)

        painter.end()

    def mousePressEvent(self, event):
        """Handle mouse click to open file dialog."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_file_dialog()
        super().mousePressEvent(event)

    def _open_file_dialog(self):
        """Open file dialog to select images."""
        formats = " ".join(f"*{fmt}" for fmt in self.SUPPORTED_FORMATS)
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "選擇圖片",
            "",
            f"圖片檔案 ({formats});;所有檔案 (*.*)"
        )

        if files:
            paths = [Path(f) for f in files]
            self.files_dropped.emit(paths)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = Path(url.toLocalFile())
                    if path.suffix.lower() in self.SUPPORTED_FORMATS:
                        event.acceptProposedAction()
                        self._is_dragging = True
                        self.update()
                        return
        event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        self._is_dragging = False
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        self._is_dragging = False
        self.update()

        paths: List[Path] = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.suffix.lower() in self.SUPPORTED_FORMATS:
                    paths.append(path)

        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()

    def set_hint_text(self, text: str):
        """Update the hint text."""
        self._hint_text = text
        self.update()


class ImageListWidget(QWidget):
    """
    A widget displaying a list of images with thumbnails.
    V3.0: Fixed button alignment and consistent sizing.
    
    Supports drag-and-drop, selection, and removal of images.
    Compact design for side panel layout.
    
    Signals:
        images_changed(list[Path]): Emitted when the image list changes.
        selection_changed(list[Path]): Emitted when selection changes.
    """

    images_changed = pyqtSignal(list)  # List[Path]
    selection_changed = pyqtSignal(list)  # List[Path]

    THUMBNAIL_SIZE = 48

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._image_paths: List[Path] = []
        self._setup_ui()

    def _setup_ui(self):
        """Setup the widget UI - V4.0: Unified element sizes."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Drag drop area (compact)
        self.drop_label = DragDropLabel(
            text="點擊或拖放添加圖片",
            show_mascot=False
        )
        self.drop_label.setMinimumHeight(70)
        self.drop_label.setMaximumHeight(90)
        self.drop_label.files_dropped.connect(self.add_images)
        layout.addWidget(self.drop_label)

        # Image list
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("imageList")
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setIconSize(QSize(self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE))
        self.list_widget.setSpacing(3)
        self.list_widget.setAlternatingRowColors(False)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget, 1)

        # Button row - V4.0: Consistent button sizing and alignment
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.setContentsMargins(0, 6, 0, 0)

        self.btn_add = QPushButton("➕")
        self.btn_add.setObjectName("iconButton")
        self.btn_add.setFixedSize(34, 34)  # V4.0: Unified size
        self.btn_add.setToolTip("添加圖片")
        self.btn_add.clicked.connect(self._on_add_clicked)
        btn_layout.addWidget(self.btn_add, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_remove = QPushButton("➖")
        self.btn_remove.setObjectName("iconButton")
        self.btn_remove.setFixedSize(34, 34)  # V4.0: Unified size
        self.btn_remove.setToolTip("移除選中")
        self.btn_remove.clicked.connect(self._on_remove_clicked)
        btn_layout.addWidget(self.btn_remove, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_clear = QPushButton("🗑️")
        self.btn_clear.setObjectName("iconButton")
        self.btn_clear.setFixedSize(34, 34)  # V4.0: Unified size
        self.btn_clear.setToolTip("清空列表")
        self.btn_clear.clicked.connect(self.clear_images)
        btn_layout.addWidget(self.btn_clear, 0, Qt.AlignmentFlag.AlignVCenter)

        btn_layout.addStretch(1)

        # Image count label - V4.0: Proper centering and sizing
        self.count_label = QLabel("0 張")
        self.count_label.setObjectName("countLabel")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setFixedSize(52, 24)
        btn_layout.addWidget(self.count_label, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(btn_layout)

    def _create_thumbnail(self, image_path: Path) -> QIcon:
        """Create a thumbnail icon for an image."""
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            # Create placeholder
            pixmap = QPixmap(self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE)
            pixmap.fill(QColor("#353842"))
        else:
            pixmap = pixmap.scaled(
                self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        return QIcon(pixmap)

    def add_images(self, paths: List[Path]):
        """Add images to the list."""
        for path in paths:
            if path not in self._image_paths:
                self._image_paths.append(path)

                item = QListWidgetItem()
                item.setText(path.name)
                item.setToolTip(str(path))
                item.setIcon(self._create_thumbnail(path))
                item.setData(Qt.ItemDataRole.UserRole, path)
                item.setSizeHint(QSize(-1, self.THUMBNAIL_SIZE + 8))

                self.list_widget.addItem(item)

        self._update_ui_state()
        self.images_changed.emit(self._image_paths.copy())

    def remove_selected(self):
        """Remove selected images from the list."""
        selected_items = self.list_widget.selectedItems()
        for item in selected_items:
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in self._image_paths:
                self._image_paths.remove(path)
            self.list_widget.takeItem(self.list_widget.row(item))

        self._update_ui_state()
        self.images_changed.emit(self._image_paths.copy())

    def clear_images(self):
        """Clear all images from the list."""
        self._image_paths.clear()
        self.list_widget.clear()
        self._update_ui_state()
        self.images_changed.emit(self._image_paths.copy())

    def get_images(self) -> List[Path]:
        """Get the list of image paths."""
        return self._image_paths.copy()

    def get_first_image(self) -> Optional[Path]:
        """Get the first image in the list, if any."""
        return self._image_paths[0] if self._image_paths else None

    def get_selected_image(self) -> Optional[Path]:
        """
        Get the currently selected image.
        
        Returns the first selected image if multiple are selected,
        or the first image in the list if nothing is selected.
        """
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            # Return the first selected item
            return selected_items[0].data(Qt.ItemDataRole.UserRole)
        # Fallback to first image if nothing selected
        return self.get_first_image()

    def get_selected_images(self) -> List[Path]:
        """Get all currently selected images."""
        selected_paths = []
        for item in self.list_widget.selectedItems():
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                selected_paths.append(path)
        return selected_paths

    def _update_ui_state(self):
        """Update UI based on current state."""
        count = len(self._image_paths)
        self.count_label.setText(f"{count} 張")

    def _on_add_clicked(self):
        """Handle add button click."""
        self.drop_label._open_file_dialog()

    def _on_remove_clicked(self):
        """Handle remove button click."""
        self.remove_selected()

    def _on_selection_changed(self):
        """Handle selection change."""
        selected_paths = []
        for item in self.list_widget.selectedItems():
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                selected_paths.append(path)
        self.selection_changed.emit(selected_paths)


class PasswordLineEdit(QWidget):
    """
    A password input field with visibility toggle.
    V4.0: Fixed button alignment and sizing with unified heights.
    
    Signals:
        textChanged(str): Emitted when text changes.
    """

    textChanged = pyqtSignal(str)

    def __init__(
            self,
            placeholder: str = "輸入密碼",
            parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_edit.setFixedHeight(34)  # V4.0: Unified height
        self.line_edit.textChanged.connect(self.textChanged.emit)
        layout.addWidget(self.line_edit, 1)

        self.toggle_btn = QPushButton("👁")
        self.toggle_btn.setObjectName("iconButton")
        self.toggle_btn.setFixedSize(34, 34)  # V4.0: Match input height
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self._toggle_visibility)
        self.toggle_btn.setToolTip("顯示/隱藏密碼")
        layout.addWidget(self.toggle_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def _toggle_visibility(self, checked: bool):
        """Toggle password visibility."""
        if checked:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("🔒")
        else:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("👁")

    def text(self) -> str:
        """Get the current text."""
        return self.line_edit.text()

    def setText(self, text: str):
        """Set the text."""
        self.line_edit.setText(text)

    def clear(self):
        """Clear the text."""
        self.line_edit.clear()

    def setEnabled(self, enabled: bool):
        """Enable or disable the widget."""
        super().setEnabled(enabled)
        self.line_edit.setEnabled(enabled)
        self.toggle_btn.setEnabled(enabled)


class ColorButton(QPushButton):
    """
    A button that shows and allows selecting a color.
    
    Signals:
        color_changed(tuple): Emitted when color changes (r, g, b).
    """

    color_changed = pyqtSignal(tuple)

    def __init__(
            self,
            initial_color: tuple = (128, 128, 128),
            parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._color = initial_color
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._open_color_dialog)
        self._update_style()

    def _update_style(self):
        """Update button style to show current color."""
        r, g, b = self._color
        # Calculate contrasting border color
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        border_color = "#353842" if luminance > 0.5 else "#6B7280"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                border: 2px solid {border_color};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                border-color: #00B4D8;
            }}
        """)

    def _open_color_dialog(self):
        """Open color picker dialog."""
        from PyQt6.QtWidgets import QColorDialog

        r, g, b = self._color
        initial = QColor(r, g, b)

        color = QColorDialog.getColor(initial, self, "選擇水印顏色")
        if color.isValid():
            self._color = (color.red(), color.green(), color.blue())
            self._update_style()
            self.color_changed.emit(self._color)

    def get_color(self) -> tuple:
        """Get current color as (r, g, b) tuple."""
        return self._color

    def set_color(self, color: tuple):
        """Set the color."""
        self._color = color
        self._update_style()
