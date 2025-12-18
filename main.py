"""
NightCat Watermark - Main Entry Point
=====================================
A desktop application for visible and blind watermark processing.

Usage:
    python main.py

Architecture:
    - Model: app/core/ (pure algorithms)
    - View: app/ui/ (PyQt6 interface)
    - Controller: This file (signal/slot connections)
    
Features:
    - Visible text watermarks with customizable spacing
    - Blind (invisible) watermarks for copyright protection
    - Real-time preview with debounce
    - Persistent mascot status indicator
"""

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QApplication, QMessageBox

from app.ui import MainWindow
from app.workers import (
    EmbedWorker, EmbedConfig, VisibleConfig, BlindConfig, EmbedResult,
    ExtractWorker, ExtractConfig, ExtractResult
)


class WatermarkController:
    """
    Controller class that connects UI signals to worker threads.
    
    Responsibilities:
    - Validate user input before processing
    - Create and manage worker threads
    - Update UI based on worker progress/results
    - Handle errors and display appropriate messages
    """

    def __init__(self, main_window: MainWindow):
        """
        Initialize the controller.
        
        Args:
            main_window: The main application window.
        """
        self.window = main_window
        self.embed_tab = main_window.embed_tab
        self.extract_tab = main_window.extract_tab

        # Worker references (to prevent garbage collection)
        self._embed_worker: Optional[EmbedWorker] = None
        self._extract_worker: Optional[ExtractWorker] = None

        # Store results for reference
        self._last_embed_results: list[EmbedResult] = []

        self._connect_signals()

    def _connect_signals(self):
        """Connect UI signals to controller slots."""
        # Embed tab signals
        self.embed_tab.start_embed_requested.connect(self._on_embed_requested)
        self.embed_tab.cancel_btn.clicked.connect(self._on_embed_cancel)

        # Extract tab signals
        self.extract_tab.start_extract_requested.connect(self._on_extract_requested)

    # ===== Embed Operations =====

    def _on_embed_requested(self, config_dict: dict):
        """
        Handle embed request from UI.
        
        Args:
            config_dict: Configuration dictionary from EmbedTab.
        """
        # Validate input
        error = self._validate_embed_config(config_dict)
        if error:
            self.window.show_error("配置錯誤", error)
            return

        # Create config objects
        try:
            config = self._create_embed_config(config_dict)
        except Exception as e:
            self.window.show_error("配置錯誤", str(e))
            return

        # Create and start worker
        self._embed_worker = EmbedWorker(config)

        # Connect worker signals
        self._embed_worker.progress.connect(self._on_embed_progress)
        self._embed_worker.image_completed.connect(self._on_embed_image_completed)
        self._embed_worker.finished_all.connect(self._on_embed_finished)
        self._embed_worker.error.connect(self._on_embed_error)

        # Update UI state
        self.embed_tab.set_processing(True)
        self.embed_tab.set_status("正在處理...")
        self.window.show_message("開始處理圖片...")

        # Start worker
        self._embed_worker.start()

    def _validate_embed_config(self, config: dict) -> Optional[str]:
        """
        Validate embed configuration.
        
        Args:
            config: Configuration dictionary.
            
        Returns:
            Error message if validation fails, None otherwise.
        """
        # Check images
        if not config.get("image_paths"):
            return "請先添加要處理的圖片"

        # Check output directory
        output_dir = config.get("output_dir")
        if not output_dir:
            return "請指定輸出目錄"

        # Check at least one watermark type is enabled
        visible_enabled = config.get("visible", {}).get("enabled", False)
        blind_enabled = config.get("blind", {}).get("enabled", False)

        if not visible_enabled and not blind_enabled:
            return "請至少啟用一種水印類型（明水印或暗水印）"

        # Validate visible watermark
        if visible_enabled:
            text = config.get("visible", {}).get("text", "").strip()
            if not text:
                return "請輸入明水印文字內容"

        # Validate blind watermark
        if blind_enabled:
            password = config.get("blind", {}).get("password", "")
            text = config.get("blind", {}).get("text", "").strip()

            if not password:
                return "請輸入暗水印加密密碼"
            if not text:
                return "請輸入暗水印隱藏信息"

        return None

    def _create_embed_config(self, config_dict: dict) -> EmbedConfig:
        """
        Create EmbedConfig from dictionary.
        
        Args:
            config_dict: Configuration dictionary.
            
        Returns:
            EmbedConfig object.
        """
        visible_dict = config_dict.get("visible", {})
        blind_dict = config_dict.get("blind", {})

        visible_config = VisibleConfig(
            enabled=visible_dict.get("enabled", False),
            text=visible_dict.get("text", ""),
            font_size=visible_dict.get("font_size", 40),
            opacity=visible_dict.get("opacity", 80),
            angle=float(visible_dict.get("angle", -30)),
            color=visible_dict.get("color", (128, 128, 128)),
            spacing_h_ratio=float(visible_dict.get("spacing_h_ratio", 2.5)),
            spacing_v_ratio=float(visible_dict.get("spacing_v_ratio", 2.0))
        )

        blind_config = BlindConfig(
            enabled=blind_dict.get("enabled", False),
            text=blind_dict.get("text", ""),
            password=blind_dict.get("password", "")
        )

        return EmbedConfig(
            image_paths=config_dict.get("image_paths", []),
            output_dir=Path(config_dict.get("output_dir", ".")),
            visible=visible_config,
            blind=blind_config,
            output_format="png"
        )

    def _on_embed_progress(self, current: int, total: int, filename: str):
        """Handle embed progress update."""
        self.embed_tab.set_progress(current, total, filename)
        self.window.show_message(f"處理中: {filename} ({current}/{total})")

    def _on_embed_image_completed(self, result: EmbedResult):
        """Handle single image completion."""
        if result.success:
            status = f"✅ {result.source_path.name} 處理完成"
        else:
            status = f"❌ {result.source_path.name} 失敗: {result.error_message}"
        self.embed_tab.set_status(status)

    def _on_embed_finished(self, results: list):
        """Handle embed completion."""
        self._last_embed_results = results

        # Update UI state
        self.embed_tab.set_processing(False)
        self.embed_tab.reset_progress()

        # Count results
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        # Show completion message
        if fail_count == 0:
            self.window.show_message(f"全部完成！成功處理 {success_count} 張圖片", 5000)
            self.embed_tab.set_status(f"✅ 完成！成功處理 {success_count} 張圖片")
            self.embed_tab.set_complete(True, f"成功處理 {success_count} 張圖片！")

            # Show success dialog with details
            self._show_embed_success_dialog(results)
        else:
            self.window.show_message(
                f"處理完成：成功 {success_count} 張，失敗 {fail_count} 張", 5000
            )
            self.embed_tab.set_status(
                f"⚠️ 完成：成功 {success_count} 張，失敗 {fail_count} 張"
            )
            self.embed_tab.set_complete(False, f"成功 {success_count}，失敗 {fail_count}")

            # Show partial success dialog
            self._show_embed_partial_dialog(results)

        # Cleanup worker
        if self._embed_worker:
            self._embed_worker.deleteLater()
            self._embed_worker = None

    def _on_embed_error(self, error_message: str):
        """Handle embed error."""
        self.window.show_error("處理錯誤", error_message)
        self.embed_tab.set_status(f"❌ 錯誤: {error_message}")
        self.embed_tab.set_complete(False, error_message)

    def _on_embed_cancel(self):
        """Handle embed cancellation."""
        if self._embed_worker and self._embed_worker.isRunning():
            self._embed_worker.cancel()
            self.embed_tab.set_status("正在取消...")
            self.window.show_message("正在取消操作...")

    def _show_embed_success_dialog(self, results: list):
        """Show success dialog with results."""
        # Build message
        blind_enabled = any(r.bit_length is not None for r in results)

        message = f"成功處理 {len(results)} 張圖片！\n\n"
        message += f"輸出目錄：\n{results[0].output_path.parent}\n"

        if blind_enabled:
            message += "\n" + "=" * 40 + "\n"
            message += "⚠️ 重要：請保存以下暗水印提取信息！\n"
            message += "=" * 40 + "\n\n"

            for r in results:
                if r.bit_length:
                    message += f"📄 {r.source_path.name}\n"
                    message += f"   → {r.output_path.name}\n"
                    message += f"   bit_length = {r.bit_length}\n\n"

        QMessageBox.information(self.window, "處理完成", message)

    def _show_embed_partial_dialog(self, results: list):
        """Show dialog for partial success."""
        success = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        message = f"處理完成\n\n"
        message += f"✅ 成功：{len(success)} 張\n"
        message += f"❌ 失敗：{len(failed)} 張\n\n"

        if failed:
            message += "失敗詳情：\n"
            for r in failed[:5]:  # Show max 5 failures
                message += f"  • {r.source_path.name}: {r.error_message}\n"
            if len(failed) > 5:
                message += f"  ... 還有 {len(failed) - 5} 個錯誤\n"

        # Show bit_length info for successful blind watermarks
        blind_success = [r for r in success if r.bit_length is not None]
        if blind_success:
            message += "\n暗水印 bit_length 值：\n"
            for r in blind_success[:5]:
                message += f"  • {r.output_path.name}: {r.bit_length}\n"

        QMessageBox.warning(self.window, "處理完成（部分失敗）", message)

    # ===== Extract Operations =====

    def _on_extract_requested(self, config_dict: dict):
        """
        Handle extract request from UI.
        
        Args:
            config_dict: Configuration dictionary from ExtractTab.
        """
        # Validate input
        error = self._validate_extract_config(config_dict)
        if error:
            self.window.show_error("配置錯誤", error)
            return

        # Create config
        config = ExtractConfig(
            image_path=config_dict["image_path"],
            password=config_dict["password"],
            bit_length=config_dict["bit_length"]
        )

        # Create and start worker
        self._extract_worker = ExtractWorker(config)

        # Connect worker signals
        self._extract_worker.started_extraction.connect(self._on_extract_started)
        self._extract_worker.result_ready.connect(self._on_extract_result)
        self._extract_worker.error.connect(self._on_extract_error)

        # Update UI state
        self.extract_tab.set_processing(True)
        self.window.show_message("正在提取暗水印...")

        # Start worker
        self._extract_worker.start()

    def _validate_extract_config(self, config: dict) -> Optional[str]:
        """
        Validate extract configuration.
        
        Args:
            config: Configuration dictionary.
            
        Returns:
            Error message if validation fails, None otherwise.
        """
        if not config.get("image_path"):
            return "請先選擇要解析的圖片"

        if not config.get("password"):
            return "請輸入加密密碼"

        bit_length = config.get("bit_length", 0)
        if bit_length <= 0:
            return "請輸入有效的 bit_length 值"

        return None

    def _on_extract_started(self, filename: str):
        """Handle extraction start."""
        self.window.show_message(f"正在提取: {filename}")

    def _on_extract_result(self, result: ExtractResult):
        """Handle extraction result."""
        # Update UI state
        self.extract_tab.set_processing(False)

        if result.success:
            self.extract_tab.set_result(result.extracted_text, success=True)
            self.window.show_message("提取成功！", 5000)
        else:
            self.extract_tab.set_result(result.error_message, success=False)
            self.window.show_message("提取失敗", 3000)

        # Cleanup worker
        if self._extract_worker:
            self._extract_worker.deleteLater()
            self._extract_worker = None

    def _on_extract_error(self, error_message: str):
        """Handle extraction error."""
        self.extract_tab.set_processing(False)
        self.extract_tab.set_result(error_message, success=False)
        self.window.show_message("提取失敗", 3000)


def main():
    """Application entry point."""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("NightCat Watermark")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("NightCat")

    # Set application-wide font
    from PyQt6.QtGui import QFont
    font = QFont()
    font.setFamily("Microsoft YaHei")
    font.setPointSize(10)
    app.setFont(font)

    # Create main window
    window = MainWindow()

    # Create controller (connects signals)
    controller = WatermarkController(window)

    # Show window
    window.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
