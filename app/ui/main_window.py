"""
Main Window V5.1 - Clean Professional Design
=============================================
遵循 Windows 用戶心智模型，使用 QSS 確保樣式一致性。
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSettings, QPoint, QRect, QRectF
from PyQt6.QtGui import (
    QCloseEvent, QMouseEvent, QPainter, QColor, QPainterPath,
    QPixmap, QRegion, QPen
)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QMessageBox, QApplication, QLabel, QPushButton, QStackedWidget
)

from .tab_embed import EmbedTab
from .tab_extract import ExtractTab
from .widgets import get_mascot_path


class MascotAvatarWidget(QWidget):
    """標題欄吉祥物頭像 - 32x32 圓形"""

    def __init__(self, size: int = 32, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = size
        self._pixmap: Optional[QPixmap] = None
        self.setFixedSize(size, size)
        self._load_mascot()

    def _load_mascot(self):
        mascot_path = get_mascot_path()
        if mascot_path.exists():
            self._pixmap = QPixmap(str(mascot_path))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = QRectF(0, 0, self._size, self._size)
        path = QPainterPath()
        path.addEllipse(rect)

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(self._size, self._size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                         Qt.TransformationMode.SmoothTransformation)
            x_off = (scaled.width() - self._size) // 2
            y_off = (scaled.height() - self._size) // 2
            cropped = scaled.copy(x_off, y_off, self._size, self._size)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, cropped)
            painter.setClipping(False)
        else:
            painter.fillPath(path, QColor("#24283B"))
            painter.setPen(QColor("#7AA2F7"))
            font = painter.font()
            font.setPointSize(14)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🐱")

        # 藍色光暈邊框
        pen = QPen(QColor("#7AA2F7"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
        painter.end()


class CustomTitleBar(QWidget):
    """
    標題欄 V5.1 - 簡潔專業
    
    ┌────────────────────────────────────────────────────────────────┐
    │  🐱 NIGHTCAT  │  [製作水印] [解析水印]  │   [─]  [□]  [×]  │
    └────────────────────────────────────────────────────────────────┘
    """

    def __init__(self, parent: Optional['RoundedMainWindow'] = None):
        super().__init__(parent)
        self._parent = parent
        self._drag_position: Optional[QPoint] = None
        self._is_dragging = False

        self.setObjectName("customTitleBar")
        self.setFixedHeight(52)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(0)

        # ===== 左側：品牌 =====
        self.mascot = MascotAvatarWidget(size=32)
        layout.addWidget(self.mascot)

        layout.addSpacing(10)

        brand = QLabel("NIGHTCAT")
        brand.setStyleSheet("""
            color: #C0CAF5;
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        layout.addWidget(brand)

        layout.addSpacing(32)

        # ===== 中央：分段控制 =====
        layout.addStretch(1)

        # 分段控制容器
        seg_container = QWidget()
        seg_container.setObjectName("segmentedControl")
        seg_layout = QHBoxLayout(seg_container)
        seg_layout.setContentsMargins(4, 4, 4, 4)
        seg_layout.setSpacing(2)
        
        self.btn_embed = QPushButton("製作水印")
        self.btn_embed.setObjectName("segmentButton")
        self.btn_embed.setCheckable(True)
        self.btn_embed.setChecked(True)
        self.btn_embed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_embed.setFixedSize(100, 32)
        seg_layout.addWidget(self.btn_embed)
        
        self.btn_extract = QPushButton("解析水印")
        self.btn_extract.setObjectName("segmentButton")
        self.btn_extract.setCheckable(True)
        self.btn_extract.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_extract.setFixedSize(100, 32)
        seg_layout.addWidget(self.btn_extract)

        layout.addWidget(seg_container)

        layout.addStretch(1)

        # ===== 右側：窗口控制 =====
        # 最小化
        self.btn_minimize = QPushButton("─")
        self.btn_minimize.setObjectName("windowButton")
        self.btn_minimize.setFixedSize(46, 52)
        self.btn_minimize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minimize.setToolTip("最小化")
        layout.addWidget(self.btn_minimize)

        # 最大化
        self.btn_maximize = QPushButton("□")
        self.btn_maximize.setObjectName("windowButton")
        self.btn_maximize.setFixedSize(46, 52)
        self.btn_maximize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_maximize.setToolTip("最大化")
        layout.addWidget(self.btn_maximize)

        # 關閉
        self.btn_close = QPushButton("×")
        self.btn_close.setObjectName("windowButtonClose")
        self.btn_close.setFixedSize(46, 52)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("關閉")
        layout.addWidget(self.btn_close)

    def update_maximize_button(self, is_maximized: bool):
        self.btn_maximize.setText("❐" if is_maximized else "□")
        self.btn_maximize.setToolTip("還原" if is_maximized else "最大化")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            widget = self.childAt(event.position().toPoint())
            is_draggable = not isinstance(widget, QPushButton)
            if widget:
                p = widget.parent()
                while p and p != self:
                    if p.objectName() == "segmentedControl":
                        is_draggable = False
                        break
                    p = p.parent()
                    
            if is_draggable:
                self._is_dragging = True
                self._drag_position = event.globalPosition().toPoint() - self._parent.frameGeometry().topLeft()
                event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging and self._drag_position:
            if self._parent.isMaximized():
                self._parent.showNormal()
                self._drag_position = QPoint(self._parent.width() // 2, 26)
            self._parent.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_dragging = False
        self._drag_position = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            widget = self.childAt(event.position().toPoint())
            if not isinstance(widget, QPushButton):
                if self._parent.isMaximized():
                    self._parent.showNormal()
                else:
                    self._parent.showMaximized()
        super().mouseDoubleClickEvent(event)


class RoundedMainWindow(QMainWindow):
    """
    Frameless main window with rounded corners.

    Uses QPainterPath mask for true rounded corners on Windows.
    """

    BORDER_RADIUS = 16
    RESIZE_MARGIN = 8

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Remove standard window frame
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Window
        )

        # Enable translucent background for proper rounded corners
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Resize tracking
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        self._is_maximized_custom = False

        self.setMouseTracking(True)

    def _apply_rounded_mask(self):
        """Apply rounded corner mask to the window."""
        if self.isMaximized():
            # No rounded corners when maximized
            self.clearMask()
        else:
            path = QPainterPath()
            path.addRoundedRect(
                QRectF(self.rect()),
                self.BORDER_RADIUS,
                self.BORDER_RADIUS
            )
            region = QRegion(path.toFillPolygon().toPolygon())
            self.setMask(region)

    def resizeEvent(self, event):
        """Handle resize to update mask."""
        super().resizeEvent(event)
        self._apply_rounded_mask()

    def showMaximized(self):
        """Override to handle custom maximized state."""
        self._is_maximized_custom = True
        super().showMaximized()
        self._apply_rounded_mask()

    def showNormal(self):
        """Override to handle custom normal state."""
        self._is_maximized_custom = False
        super().showNormal()
        self._apply_rounded_mask()

    def _get_resize_edge(self, pos: QPoint) -> Optional[str]:
        """Determine which edge/corner is being hovered for resize."""
        if self.isMaximized():
            return None

        rect = self.rect()
        m = self.RESIZE_MARGIN

        edges = []
        if pos.x() <= m:
            edges.append("left")
        elif pos.x() >= rect.width() - m:
            edges.append("right")
        if pos.y() <= m:
            edges.append("top")
        elif pos.y() >= rect.height() - m:
            edges.append("bottom")

        if not edges:
            return None
        return "_".join(edges)

    def _update_cursor(self, edge: Optional[str]):
        """Update cursor based on resize edge."""
        cursor_map = {
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
            "top_left": Qt.CursorShape.SizeFDiagCursor,
            "bottom_right": Qt.CursorShape.SizeFDiagCursor,
            "top_right": Qt.CursorShape.SizeBDiagCursor,
            "bottom_left": Qt.CursorShape.SizeBDiagCursor,
        }
        if edge in cursor_map:
            self.setCursor(cursor_map[edge])
        else:
            self.unsetCursor()

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for resizing."""
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.position().toPoint())
            if edge:
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geo = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for resize cursor and resizing."""
        if self._resize_edge and self._resize_start_pos and self._resize_start_geo:
            # Perform resize
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            geo = QRect(self._resize_start_geo)
            min_w, min_h = self.minimumWidth(), self.minimumHeight()

            if "left" in self._resize_edge:
                new_left = geo.left() + delta.x()
                new_width = geo.width() - delta.x()
                if new_width >= min_w:
                    geo.setLeft(new_left)
            if "right" in self._resize_edge:
                geo.setWidth(max(min_w, geo.width() + delta.x()))
            if "top" in self._resize_edge:
                new_top = geo.top() + delta.y()
                new_height = geo.height() - delta.y()
                if new_height >= min_h:
                    geo.setTop(new_top)
            if "bottom" in self._resize_edge:
                geo.setHeight(max(min_h, geo.height() + delta.y()))

            self.setGeometry(geo)
            self._resize_start_pos = event.globalPosition().toPoint()
            self._resize_start_geo = geo
            event.accept()
            return
        else:
            # Update cursor based on position
            edge = self._get_resize_edge(event.position().toPoint())
            self._update_cursor(edge)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        self.unsetCursor()
        super().mouseReleaseEvent(event)


class MainWindow(RoundedMainWindow):
    """
    Features:
    - Rounded corners (16px)
    - Mascot in title bar
    - Anime-style window controls
    - Soft, approachable aesthetics
    """

    APP_NAME = "NightCat Watermark"
    APP_VERSION = "2.0.0"

    # QSettings keys
    SETTINGS_ORG = "NightCat"
    SETTINGS_APP = "WatermarkTool"
    KEY_OUTPUT_DIR = "output_directory"
    KEY_WINDOW_GEOMETRY = "window_geometry"
    KEY_LAST_TAB = "last_tab"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._settings = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)

        self._setup_window()
        self._setup_ui()
        self._setup_statusbar()
        self._load_stylesheet()
        self._connect_signals()
        self._restore_settings()

    def _setup_window(self):
        """Setup window properties."""
        self.setWindowTitle(self.APP_NAME)
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)

        # Center on screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)

    def _setup_ui(self):
        """Setup the main UI with rounded container."""
        # Central container - this will be painted with rounded corners
        central = QWidget()
        central.setObjectName("centralContainer")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === CUSTOM TITLE BAR ===
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        # === CONTENT AREA (Stacked Widget) ===
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")

        # Create tabs
        self.embed_tab = EmbedTab()
        self.extract_tab = ExtractTab()

        self.content_stack.addWidget(self.embed_tab)
        self.content_stack.addWidget(self.extract_tab)

        main_layout.addWidget(self.content_stack, 1)

    def _setup_statusbar(self):
        """Setup minimal status bar."""
        self.statusbar = QStatusBar()
        self.statusbar.setObjectName("mainStatusBar")
        self.setStatusBar(self.statusbar)

        # Status label
        self.status_label = QLabel("系統就緒")
        self.status_label.setObjectName("statusLabel")
        self.statusbar.addWidget(self.status_label)

        # Right side info
        right_label = QLabel("◇ NIGHTCAT TERMINAL v1.0.0")
        right_label.setObjectName("statusRightLabel")
        self.statusbar.addPermanentWidget(right_label)

    def _load_stylesheet(self):
        """Load the application stylesheet."""
        style_path = Path(__file__).parent / "styles.qss"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _connect_signals(self):
        """Connect all signals."""
        # Title bar buttons
        self.title_bar.btn_minimize.clicked.connect(self.showMinimized)
        self.title_bar.btn_maximize.clicked.connect(self._toggle_maximize)
        self.title_bar.btn_close.clicked.connect(self.close)

        # Segmented control
        self.title_bar.btn_embed.clicked.connect(lambda: self._switch_tab(0))
        self.title_bar.btn_extract.clicked.connect(lambda: self._switch_tab(1))

    def _toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

        self.title_bar.update_maximize_button(self.isMaximized())

    def _switch_tab(self, index: int):
        """Switch to the specified tab."""
        self.content_stack.setCurrentIndex(index)

        # Update segmented control state
        self.title_bar.btn_embed.setChecked(index == 0)
        self.title_bar.btn_extract.setChecked(index == 1)

    def _restore_settings(self):
        """Restore user settings."""
        # Output directory
        last_dir = self._settings.value(self.KEY_OUTPUT_DIR, "")
        if last_dir and Path(last_dir).exists():
            self.embed_tab.set_output_directory(last_dir)
        else:
            default = str(Path.home() / "Pictures" / "Watermarked")
            self.embed_tab.set_output_directory(default)

        # Last tab
        last_tab = self._settings.value(self.KEY_LAST_TAB, 0, type=int)
        if 0 <= last_tab < self.content_stack.count():
            self._switch_tab(last_tab)

    def _save_settings(self):
        """Save user settings."""
        self._settings.setValue(self.KEY_OUTPUT_DIR, self.embed_tab.get_output_directory())
        self._settings.setValue(self.KEY_WINDOW_GEOMETRY, self.saveGeometry())
        self._settings.setValue(self.KEY_LAST_TAB, self.content_stack.currentIndex())
        self._settings.sync()

    def paintEvent(self, event):
        """Paint the rounded window background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())

        # Draw rounded background
        path = QPainterPath()
        path.addRoundedRect(rect, self.BORDER_RADIUS, self.BORDER_RADIUS)

        # Main background
        painter.fillPath(path, QColor("#1A1B26"))

        # Border
        pen = QPen(QColor("#3B4261"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), self.BORDER_RADIUS, self.BORDER_RADIUS)

        painter.end()

    # === Public API ===

    def show_message(self, message: str, timeout: int = 3000):
        """Show a message in the status bar."""
        self.status_label.setText(message)
        if timeout > 0:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(timeout, lambda: self.status_label.setText("系統就緒"))

    def show_error(self, title: str, message: str):
        """Show an error dialog."""
        QMessageBox.critical(self, title, message)

    def show_warning(self, title: str, message: str):
        """Show a warning dialog."""
        QMessageBox.warning(self, title, message)

    def show_info(self, title: str, message: str):
        """Show an info dialog."""
        QMessageBox.information(self, title, message)

    def closeEvent(self, event: QCloseEvent):
        """Handle window close."""
        self._save_settings()
        event.accept()
