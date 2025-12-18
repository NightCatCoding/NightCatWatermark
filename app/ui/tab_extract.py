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
    QLabel, QSpinBox, QPushButton,
    QTextEdit, QFrame, QSplitter, QApplication
)

from .widgets import DragDropLabel, PasswordLineEdit, MascotStatus, get_mascot_path


class MascotDisplay(QWidget):
    """Simple mascot display with status."""

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
        self._setup_ui()
        self._load_mascot()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        self.mascot_label = QLabel()
        self.mascot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mascot_label.setFixedSize(100, 100)
        layout.addWidget(self.mascot_label)

        self.status_label = QLabel("等待中")
        self.status_label.setStyleSheet("color: #00D4FF; font-size: 14px; font-weight: 600;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

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

        size = 100
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

        # Border
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
        self.status_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 600;")
        self._update_display()


class TerminalOutput(QTextEdit):
    """Terminal-style output."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(180)
        self._reset_style()
        self._show_welcome()

    def _reset_style(self):
        self.setStyleSheet("""
            QTextEdit {
                background-color: #0D1117;
                color: #00D4FF;
                border: 1px solid #21262D;
                border-radius: 10px;
                padding: 16px;
                font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
                font-size: 13px;
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

[{self._ts()}] 請檢查密碼或 bit_length""")

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
        panel = QFrame()
        panel.setObjectName("controlPanel")
        panel.setMinimumWidth(350)
        panel.setMaximumWidth(450)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 12, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel("🔍 解析暗水印")
        header.setStyleSheet("font-size: 16px; font-weight: 600; color: #F0F2F5;")
        layout.addWidget(header)

        # Drop zone
        self.drop_label = DragDropLabel(text="拖放圖片到這裡", show_mascot=False)
        self.drop_label.setMinimumHeight(140)
        layout.addWidget(self.drop_label)

        # File info
        self.file_info = QLabel("")
        self.file_info.setStyleSheet("""
            color: #00D4FF;
            background-color: rgba(0, 212, 255, 0.1);
            border-radius: 6px;
            padding: 10px;
            font-size: 12px;
        """)
        self.file_info.setVisible(False)
        layout.addWidget(self.file_info)

        # Settings
        settings_frame = QFrame()
        settings_frame.setStyleSheet("""
            QFrame {
                background-color: #1E2025;
                border: 1px solid #2E323B;
                border-radius: 10px;
            }
        """)
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        settings_layout.setSpacing(14)

        # Password
        pwd_label = QLabel("加密密碼")
        pwd_label.setStyleSheet("color: #B0B8C4; font-size: 12px;")
        settings_layout.addWidget(pwd_label)
        self.password_input = PasswordLineEdit("輸入嵌入時的密碼")
        settings_layout.addWidget(self.password_input)

        # Bit length
        bit_row = QHBoxLayout()
        bit_label = QLabel("Bit Length")
        bit_label.setStyleSheet("color: #B0B8C4; font-size: 12px;")
        bit_row.addWidget(bit_label)
        bit_row.addStretch()
        self.bit_length_spin = QSpinBox()
        self.bit_length_spin.setRange(1, 100000)
        self.bit_length_spin.setValue(200)
        self.bit_length_spin.setFixedWidth(100)
        bit_row.addWidget(self.bit_length_spin)
        settings_layout.addLayout(bit_row)

        layout.addWidget(settings_frame)

        # Extract button
        self.extract_btn = QPushButton("🔓 開始提取")
        self.extract_btn.setObjectName("ctaButton")
        self.extract_btn.setMinimumHeight(48)
        self.extract_btn.setEnabled(False)
        self.extract_btn.clicked.connect(self._on_extract_clicked)
        layout.addWidget(self.extract_btn)

        # Clear button
        self.clear_btn = QPushButton("✕ 清除")
        self.clear_btn.setObjectName("dangerButton")
        self.clear_btn.setVisible(False)
        self.clear_btn.clicked.connect(self._clear_image)
        layout.addWidget(self.clear_btn)

        layout.addStretch()

        return panel

    def _create_right_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background-color: #1A1D23;")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 20, 20, 20)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mascot
        self.mascot = MascotDisplay()
        layout.addWidget(self.mascot, alignment=Qt.AlignmentFlag.AlignCenter)

        # Terminal
        self.result_text = TerminalOutput()
        layout.addWidget(self.result_text, 1)

        # Copy button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.copy_btn = QPushButton("📋 複製結果")
        self.copy_btn.setObjectName("secondaryButton")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_result)
        btn_row.addWidget(self.copy_btn)
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
            "bit_length": self.bit_length_spin.value()
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
        self.bit_length_spin.setEnabled(not is_processing)

    def get_config(self):
        return {
            "image_path": self._current_image,
            "password": self.password_input.text(),
            "bit_length": self.bit_length_spin.value()
        }
