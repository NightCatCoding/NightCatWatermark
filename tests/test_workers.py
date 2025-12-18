"""
Test script for worker threads.

Run with: python tests/test_workers.py
"""

import gc
import sys
import tempfile
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import numpy as np

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEventLoop, QTimer

from app.workers import (
    EmbedWorker, EmbedConfig, VisibleConfig, BlindConfig, EmbedResult,
    ExtractWorker, ExtractConfig
)

# Global QApplication instance
_app = None


def get_app():
    """Get or create QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication(sys.argv)
    return _app


def safe_delete(file_path: Path, max_retries: int = 3, delay: float = 0.5):
    """Safely delete a file with retry logic."""
    if not file_path or not file_path.exists():
        return

    for attempt in range(max_retries):
        try:
            gc.collect()
            file_path.unlink()
            return
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                print(f"⚠️ Warning: Could not delete {file_path}")


def create_test_image(width: int = 1024, height: int = 768) -> Path:
    """Create a simple test image."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            arr[y, x] = [
                int(255 * x / width),
                int(255 * y / height),
                128
            ]

    img = Image.fromarray(arr, mode="RGB")
    temp_path = Path(tempfile.mktemp(suffix=".png"))
    img.save(temp_path)
    img.close()
    return temp_path


def wait_for_signal(signal, timeout_ms: int = 30000):
    """
    Wait for a Qt signal with timeout.
    
    Returns:
        The value emitted by the signal, or None if timeout.
    """
    app = get_app()
    loop = QEventLoop()
    result = [None]

    def on_signal(*args):
        result[0] = args[0] if len(args) == 1 else args
        loop.quit()

    signal.connect(on_signal)

    # Setup timeout
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(timeout_ms)

    loop.exec()
    timer.stop()

    return result[0]


def test_embed_worker_visible_only():
    """Test EmbedWorker with visible watermark only."""
    print("\n" + "=" * 50)
    print("Testing EmbedWorker - Visible Only")
    print("=" * 50)

    get_app()
    test_image = create_test_image()
    output_dir = Path(tempfile.mkdtemp())

    try:
        config = EmbedConfig(
            image_paths=[test_image],
            output_dir=output_dir,
            visible=VisibleConfig(
                enabled=True,
                text="© NightCat 2024",
                font_size=50,
                opacity=100,
                angle=-30
            ),
            blind=BlindConfig(enabled=False)
        )

        worker = EmbedWorker(config)

        # Track progress
        progress_log = []
        worker.progress.connect(lambda c, t, f: progress_log.append((c, t, f)))

        worker.start()
        results = wait_for_signal(worker.finished_all)

        assert results is not None, "Worker timed out"
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"

        result: EmbedResult = results[0]
        assert result.success, f"Embed failed: {result.error_message}"
        assert result.output_path.exists(), "Output file not created"

        print(f"✅ Visible watermark embedded successfully!")
        print(f"   Output: {result.output_path}")
        print(f"   Progress log: {progress_log}")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        gc.collect()
        safe_delete(test_image)
        # Clean output dir
        for f in output_dir.glob("*"):
            safe_delete(f)
        try:
            output_dir.rmdir()
        except:
            pass


def test_embed_worker_blind_only():
    """Test EmbedWorker with blind watermark only."""
    print("\n" + "=" * 50)
    print("Testing EmbedWorker - Blind Only")
    print("=" * 50)

    get_app()
    test_image = create_test_image()
    output_dir = Path(tempfile.mkdtemp())

    try:
        config = EmbedConfig(
            image_paths=[test_image],
            output_dir=output_dir,
            visible=VisibleConfig(enabled=False),
            blind=BlindConfig(
                enabled=True,
                text="Secret message for testing",
                password="TestPassword123"
            )
        )

        worker = EmbedWorker(config)
        worker.start()
        results = wait_for_signal(worker.finished_all)

        assert results is not None, "Worker timed out"
        assert len(results) == 1

        result: EmbedResult = results[0]
        assert result.success, f"Embed failed: {result.error_message}"
        assert result.bit_length is not None, "bit_length not set"
        assert result.bit_length > 0, "bit_length should be positive"

        print(f"✅ Blind watermark embedded successfully!")
        print(f"   Output: {result.output_path}")
        print(f"   Bit length: {result.bit_length}")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        gc.collect()
        safe_delete(test_image)
        for f in output_dir.glob("*"):
            safe_delete(f)
        try:
            output_dir.rmdir()
        except:
            pass


def test_embed_worker_combined():
    """Test EmbedWorker with both visible and blind watermarks."""
    print("\n" + "=" * 50)
    print("Testing EmbedWorker - Combined")
    print("=" * 50)

    get_app()
    test_image = create_test_image()
    output_dir = Path(tempfile.mkdtemp())

    try:
        config = EmbedConfig(
            image_paths=[test_image],
            output_dir=output_dir,
            visible=VisibleConfig(
                enabled=True,
                text="© NightCat",
                font_size=40,
                opacity=80,
                angle=-25
            ),
            blind=BlindConfig(
                enabled=True,
                text="Hidden message",
                password="CombinedTest"
            )
        )

        worker = EmbedWorker(config)
        worker.start()
        results = wait_for_signal(worker.finished_all)

        assert results is not None, "Worker timed out"
        assert len(results) == 1

        result: EmbedResult = results[0]
        assert result.success, f"Embed failed: {result.error_message}"
        assert result.bit_length is not None

        print(f"✅ Combined watermarks embedded!")
        print(f"   Output: {result.output_path}")
        print(f"   Bit length: {result.bit_length}")

        # Now test extraction
        print("\n🔍 Testing extraction...")
        extract_config = ExtractConfig(
            image_path=result.output_path,
            password="CombinedTest",
            bit_length=result.bit_length
        )

        extract_worker = ExtractWorker(extract_config)
        extract_worker.start()
        extract_result = wait_for_signal(extract_worker.result_ready)

        assert extract_result is not None, "Extract worker timed out"
        assert extract_result.success, f"Extract failed: {extract_result.error_message}"
        assert extract_result.extracted_text == "Hidden message"

        print(f"✅ Extraction successful: '{extract_result.extracted_text}'")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        gc.collect()
        safe_delete(test_image)
        for f in output_dir.glob("*"):
            safe_delete(f)
        try:
            output_dir.rmdir()
        except:
            pass


def test_embed_worker_multiple_images():
    """Test EmbedWorker with multiple images."""
    print("\n" + "=" * 50)
    print("Testing EmbedWorker - Multiple Images")
    print("=" * 50)

    get_app()
    test_images = [create_test_image() for _ in range(3)]
    output_dir = Path(tempfile.mkdtemp())

    try:
        config = EmbedConfig(
            image_paths=test_images,
            output_dir=output_dir,
            visible=VisibleConfig(
                enabled=True,
                text="Batch Test",
                font_size=35,
                opacity=90
            ),
            blind=BlindConfig(enabled=False)
        )

        worker = EmbedWorker(config)

        # Track progress
        progress_log = []
        worker.progress.connect(lambda c, t, f: progress_log.append((c, t, f)))

        worker.start()
        results = wait_for_signal(worker.finished_all)

        assert results is not None, "Worker timed out"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        success_count = sum(1 for r in results if r.success)
        assert success_count == 3, f"Only {success_count}/3 succeeded"

        print(f"✅ Batch processing successful!")
        print(f"   Processed: {len(results)} images")
        print(f"   Progress log: {progress_log}")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        gc.collect()
        for img in test_images:
            safe_delete(img)
        for f in output_dir.glob("*"):
            safe_delete(f)
        try:
            output_dir.rmdir()
        except:
            pass


def main():
    """Run all tests."""
    print("🧪 WatermarkMaster Worker Tests")
    print("=" * 50)

    results = []

    results.append(("Visible Only", test_embed_worker_visible_only()))
    results.append(("Blind Only", test_embed_worker_blind_only()))
    results.append(("Combined", test_embed_worker_combined()))
    results.append(("Multiple Images", test_embed_worker_multiple_images()))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
