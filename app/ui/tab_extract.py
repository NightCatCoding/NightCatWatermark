"""
Extract Tab - Clean Dashboard Layout
====================================
Simplified extraction interface with focus on results.

Layout:
┌─────────────────────┬───────────────────────────────┐
│   Drop Zone         │                               │
│   + File Info       │     Result Dashboard          │
├─────────────────────┤     (Mascot + Terminal)       │
│   Settings          │                               │
│   + Extract Button  │                               │
└─────────────────────┴───────────────────────────────┘
"""

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton,
    QTextEdit, QFrame, QSplitter, QApplication
)

from .widgets import DragDropLabel, PasswordLineEdit, MascotStatus, get_mascot_path


class MascotDisplay(QWidget):
    """Simple mascot display with status - V4.0: Fixed centering and sizing."""

    STATUS_DATA = {
        MascotStatus.IDLE: ("😺", "等待中", "#00D4FF"),
        MascotStatus.PROCESSING: ("⚙️", "解析中...", "#8B5CF6"),
        MascotStatus.COMPLETE: ("🎉", "找到了！", "#10B981"),
        MascotStatus.ERROR: ("😿", "失敗", "#EF4444"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = MascotStatus.IDLE
        self._mascot_pixmap = None
        self.setFixedSize(120, 130)  # V4.0: Fixed widget size
        self._setup_ui()
        self._load_mascot()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)

        # Mascot label - V4.0: Proper centering
        self.mascot_label = QLabel()
        self.mascot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mascot_label.setFixedSize(90, 90)
        layout.addWidget(self.mascot_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Status label - V4.0: Proper centering and sizing
        self.status_label = QLabel("等待中")
        self.status_label.setStyleSheet("color: #00D4FF; font-size: 12px; font-weight: 600;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFixedHeight(22)
        self.status_label.setMinimumWidth(90)
        layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignCenter)

    def _load_mascot(self):
        path = get_mascot_path()
        if path.exists():
            self._mascot_pixmap = QPixmap(str(path))
            self._update_display()
        else:
            self.mascot_label.setText("🐱")
            self.mascot_label.setStyleSheet("font-size: 48px;")

    def _update_display(self):
        if not self._mascot_pixmap:
            return

        size = 90  # V4.0: Adjusted size
        scaled = self._mascot_pixmap.scaled(size, size,
                                            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                            Qt.TransformationMode.SmoothTransformation)

        circular = QPixmap(size, size)
        circular.fill(Qt.GlobalColor.transparent)

        painter = QPainter(circular)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)

        # Border - V4.0: Consistent sizing
        _, _, color = self.STATUS_DATA.get(self._status, self.STATUS_DATA[MascotStatus.IDLE])
        from PyQt6.QtGui import QPen
        painter.setClipping(False)
        painter.setPen(QPen(QColor(color), 3))
        painter.drawEllipse(2, 2, size - 4, size - 4)
        painter.end()

        self.mascot_label.setPixmap(circular)

    def set_status(self, status: MascotStatus, text: str = ""):
        self._status = status
        icon, default_text, color = self.STATUS_DATA.get(status, self.STATUS_DATA[MascotStatus.IDLE])
        self.status_label.setText(text or default_text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
        self._update_display()


class TerminalOutput(QTextEdit):
    """Terminal-style output."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(150)
        self._reset_style()
        self._show_welcome()

    def _reset_style(self):
        self.setStyleSheet("""
            QTextEdit {
                background-color: #0D1117;
                color: #00D4FF;
                border: 1px solid #21262D;
                border-radius: 8px;
                padding: 12px;
                font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
                font-size: 11px;
                line-height: 1.4;
            }
        """)

    def _show_welcome(self):
        self.setPlainText("""╭────────────────────────────────╮
│   NightCat Watermark Extractor │
╰────────────────────────────────╯

等待提取指令...""")

    def show_processing(self, filename: str):
        self._reset_style()
        self.setPlainText(f"""[{self._ts()}] 開始解析: {filename}
[{self._ts()}] 讀取頻域數據...
[{self._ts()}] 嘗試解密...""")

    def show_result(self, text: str, success: bool):
        if success:
            self.setStyleSheet(self.styleSheet().replace("#00D4FF", "#10B981").replace("#21262D", "#10B981"))
            self.setPlainText(f"""╭────────────────────────────────╮
│       ✓ 提取成功               │
╰────────────────────────────────╯

隱藏信息:
┌────────────────────────────────┐
  {text}
└────────────────────────────────┘

[{self._ts()}] 完成""")
        else:
            self.setStyleSheet(self.styleSheet().replace("#00D4FF", "#EF4444").replace("#21262D", "#DC2626"))
            self.setPlainText(f"""╭────────────────────────────────╮
│       ✗ 提取失敗               │
╰────────────────────────────────╯

錯誤: {text}

[{self._ts()}] 請檢查密碼是否正確""")

    def reset(self):
        self._reset_style()
        self._show_welcome()

    def _ts(self):
        return datetime.now().strftime("%H:%M:%S")


class ExtractTab(QWidget):
    """Tab for extracting blind watermarks."""

    start_extract_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_image = None
        self._extracted_text = ""
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel
        left = self._create_left_panel()
        splitter.addWidget(left)

        # Right panel
        right = self._create_right_panel()
        splitter.addWidget(right)

        splitter.setSizes([400, 600])
        main_layout.addWidget(splitter)

    def _create_left_panel(self):
        """Create left panel - V4.0: Fixed alignment, spacing, and unified sizes."""
        panel = QFrame()
        panel.setObjectName("controlPanel")
        panel.setMinimumWidth(300)
        panel.setMaximumWidth(380)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 14, 16)
        layout.setSpacing(12)

        # Header - V4.0: Proper sizing
        header = QLabel("🔍 解析暗水印")
        header.setStyleSheet("font-size: 14px; font-weight: 600; color: #F0F2F5;")
        header.setFixedHeight(26)
        header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(header)

        # Drop zone
        self.drop_label = DragDropLabel(text="拖放圖片到這裡", show_mascot=False)
        self.drop_label.setMinimumHeight(110)
        self.drop_label.setMaximumHeight(150)
        layout.addWidget(self.drop_label)

        # File info - V4.0: Consistent styling with unified height
        self.file_info = QLabel("")
        self.file_info.setStyleSheet("""
            color: #00D4FF;
            background-color: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 11px;
        """)
        self.file_info.setVisible(False)
        self.file_info.setFixedHeight(34)  # V4.0: Unified height
        self.file_info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.file_info)

        # Settings frame
        settings_frame = QFrame()
        settings_frame.setStyleSheet("""
            QFrame {
                background-color: #1E2025;
                border: 1px solid #2E323B;
                border-radius: 10px;
            }
        """)
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(14, 14, 14, 14)
        settings_layout.setSpacing(12)

        # Password - V4.0: Proper label alignment
        pwd_label = QLabel("加密密碼")
        pwd_label.setStyleSheet("color: #B0B8C4; font-size: 11px; font-weight: 500;")
        pwd_label.setFixedHeight(18)
        pwd_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        settings_layout.addWidget(pwd_label)
        self.password_input = PasswordLineEdit("輸入嵌入時的密碼")
        settings_layout.addWidget(self.password_input)

        # Info note (replaces old bit_length field)
        info_note = QLabel("✦ 自動檢測")
        info_note.setStyleSheet(
            "color: #10B981; font-size: 10px; padding: 6px 0 0 0;"
        )
        info_note.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        settings_layout.addWidget(info_note)

        layout.addWidget(settings_frame)

        # Extract button - V4.0: Consistent sizing
        self.extract_btn = QPushButton("🔓 開始提取")
        self.extract_btn.setObjectName("ctaButton")
        self.extract_btn.setFixedHeight(44)  # V4.0: Unified CTA height
        self.extract_btn.setEnabled(False)
        self.extract_btn.clicked.connect(self._on_extract_clicked)
        layout.addWidget(self.extract_btn)

        # Clear button - V4.0: Consistent sizing
        self.clear_btn = QPushButton("✕ 清除")
        self.clear_btn.setObjectName("dangerButton")
        self.clear_btn.setVisible(False)
        self.clear_btn.setFixedHeight(40)
        self.clear_btn.clicked.connect(self._clear_image)
        layout.addWidget(self.clear_btn)

        layout.addStretch(1)

        return panel

    def _create_right_panel(self):
        """Create right panel - V4.0: Fixed alignment and centering."""
        panel = QFrame()
        panel.setStyleSheet("background-color: #1A1D23;")
        panel.setMinimumWidth(340)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 18, 18, 18)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Mascot - V4.0: Proper centering with container
        mascot_container = QWidget()
        mascot_container.setFixedHeight(140)
        mascot_layout = QHBoxLayout(mascot_container)
        mascot_layout.setContentsMargins(0, 0, 0, 0)
        mascot_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.mascot = MascotDisplay()
        mascot_layout.addWidget(self.mascot, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(mascot_container, 0, Qt.AlignmentFlag.AlignCenter)

        # Terminal
        self.result_text = TerminalOutput()
        self.result_text.setMinimumHeight(180)
        layout.addWidget(self.result_text, 1)

        # Copy button row - V4.0: Better alignment with unified height
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_row.addStretch(1)
        self.copy_btn = QPushButton("📋 複製結果")
        self.copy_btn.setObjectName("secondaryButton")
        self.copy_btn.setEnabled(False)
        self.copy_btn.setFixedHeight(38)  # V4.0: Unified button height
        self.copy_btn.setFixedWidth(120)
        self.copy_btn.clicked.connect(self._copy_result)
        btn_row.addWidget(self.copy_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(btn_row)

        return panel

    def _connect_signals(self):
        self.drop_label.files_dropped.connect(self._on_files_dropped)
        self.password_input.textChanged.connect(self._update_button)

    def _on_files_dropped(self, paths):
        if paths:
            self._set_image(paths[0])

    def _set_image(self, path: Path):
        self._current_image = path
        size_kb = path.stat().st_size / 1024
        self.file_info.setText(f"📄 {path.name}  ({size_kb:.1f} KB)")
        self.file_info.setVisible(True)
        self.clear_btn.setVisible(True)
        self.drop_label.setMaximumHeight(100)
        self.result_text.reset()
        self.copy_btn.setEnabled(False)
        self._update_button()

    def _clear_image(self):
        self._current_image = None
        self.file_info.setVisible(False)
        self.clear_btn.setVisible(False)
        self.drop_label.setMaximumHeight(16777215)
        self.result_text.reset()
        self.copy_btn.setEnabled(False)
        self.mascot.set_status(MascotStatus.IDLE)
        self._update_button()

    def _update_button(self):
        has_image = self._current_image is not None
        has_pwd = bool(self.password_input.text().strip())
        self.extract_btn.setEnabled(has_image and has_pwd)

    def _on_extract_clicked(self):
        if not self._current_image:
            return
        self.mascot.set_status(MascotStatus.PROCESSING)
        self.result_text.show_processing(self._current_image.name)
        config = {
            "image_path": self._current_image,
            "password": self.password_input.text(),
            "bit_length": 0  # Ignored by TrustMark — kept for API compat
        }
        self.start_extract_requested.emit(config)

    def _copy_result(self):
        if self._extracted_text:
            QApplication.clipboard().setText(self._extracted_text)

    def set_result(self, text: str, success: bool = True):
        self._extracted_text = text if success else ""
        self.result_text.show_result(text, success)
        self.copy_btn.setEnabled(success)
        if success:
            self.mascot.set_status(MascotStatus.COMPLETE, f"找到: {text[:20]}...")
        else:
            self.mascot.set_status(MascotStatus.ERROR)

    def set_processing(self, is_processing: bool):
        self.extract_btn.setEnabled(not is_processing)
        self.extract_btn.setText("⏳ 提取中..." if is_processing else "🔓 開始提取")
        self.password_input.setEnabled(not is_processing)

    def get_config(self):
        return {
            "image_path": self._current_image,
            "password": self.password_input.text(),
            "bit_length": 0  # Ignored by TrustMark
        }
