"""
Test script for core watermark functionality.

Run with: python -m pytest tests/test_core.py -v
Or simply: python tests/test_core.py
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

from app.core.visible import VisibleWatermarker
from app.core.blind import BlindWatermarkerAdapter


def safe_delete(file_path: Path, max_retries: int = 3, delay: float = 0.5):
    """
    Safely delete a file with retry logic for Windows file locking issues.
    """
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


def create_test_image(width: int = 800, height: int = 600) -> Path:
    """Create a simple test image with gradient."""
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


def test_visible_watermark():
    """Test visible watermark functionality."""
    print("\n" + "=" * 50)
    print("Testing Visible Watermark")
    print("=" * 50)

    test_image = create_test_image()
    output_path = test_image.parent / "test_visible_output.png"
    result = None
    wm = None

    try:
        wm = VisibleWatermarker()

        result = wm.process(
            image_path=test_image,
            text="NightCat © 2024",
            size=50,
            opacity=100,
            angle=-30,
            output_path=output_path
        )

        result_size = result.size

        print(f"✅ Visible watermark applied successfully!")
        print(f"   Input: {test_image}")
        print(f"   Output: {output_path}")
        print(f"   Result size: {result_size}")

        assert output_path.exists(), "Output file not created"

        with Image.open(output_path) as output_img:
            assert output_img.size == result_size, "Size mismatch"

        print("✅ All visible watermark tests passed!")
        return True

    except Exception as e:
        print(f"❌ Visible watermark test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if result is not None:
            result.close()
        if wm is not None:
            wm._cached_fonts.clear()
        gc.collect()
        safe_delete(test_image)
        safe_delete(output_path)


def test_blind_watermark():
    """Test blind watermark functionality."""
    print("\n" + "=" * 50)
    print("Testing Blind Watermark")
    print("=" * 50)

    # Use larger image for sufficient capacity
    test_image = create_test_image(1024, 768)
    output_path = None
    adapter = None

    try:
        adapter = BlindWatermarkerAdapter()

        # Check image capacity
        max_text_len = adapter.get_max_text_length(test_image)
        print(f"   Image capacity: {max_text_len} bytes")

        password = "MySecretKey123"
        original_text = "Hello, this is a secret message! 你好世界"

        print(f"   Original text: {original_text}")
        print(f"   Text length: {len(original_text.encode('utf-8'))} bytes")
        print(f"   Password: {password}")

        # Embed watermark
        print("\n📝 Embedding watermark...")
        output_path, bit_length = adapter.embed(
            image_path=test_image,
            password=password,
            text=original_text
        )

        print(f"✅ Watermark embedded!")
        print(f"   Output: {output_path}")
        print(f"   Bit length: {bit_length}")

        # Extract watermark (must provide bit_length)
        print("\n🔍 Extracting watermark...")
        extracted_text = adapter.extract(
            image_path=output_path,
            password=password,
            bit_length=bit_length
        )

        print(f"✅ Watermark extracted!")
        print(f"   Extracted text: {extracted_text}")

        assert extracted_text == original_text, \
            f"Text mismatch: expected '{original_text}', got '{extracted_text}'"

        print("\n✅ All blind watermark tests passed!")
        return True

    except Exception as e:
        print(f"❌ Blind watermark test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if adapter is not None:
            adapter.cleanup()
        gc.collect()
        safe_delete(test_image)
        if output_path:
            safe_delete(output_path)


def test_wrong_password():
    """Test that wrong password fails gracefully."""
    print("\n" + "=" * 50)
    print("Testing Wrong Password Detection")
    print("=" * 50)

    test_image = create_test_image(1024, 768)
    output_path = None
    adapter = None

    try:
        adapter = BlindWatermarkerAdapter()

        # Embed with one password
        output_path, bit_length = adapter.embed(
            image_path=test_image,
            password="CorrectPassword",
            text="Secret data"
        )
        print("✅ Watermark embedded with 'CorrectPassword'")

        # Try to extract with wrong password
        print("🔍 Attempting extraction with wrong password...")
        try:
            adapter.extract(
                image_path=output_path,
                password="WrongPassword",
                bit_length=bit_length
            )
            print("❌ Should have raised an error!")
            return False
        except ValueError as e:
            print(f"✅ Correctly detected wrong password: {e}")
            return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if adapter is not None:
            adapter.cleanup()
        gc.collect()
        safe_delete(test_image)
        if output_path:
            safe_delete(output_path)


def test_combined_watermarks():
    """Test combining visible and blind watermarks."""
    print("\n" + "=" * 50)
    print("Testing Combined Watermarks")
    print("=" * 50)

    test_image = create_test_image(1024, 768)
    output_visible = test_image.parent / "combined_step1.png"
    output_final = None
    visible_result = None
    visible_wm = None
    blind_wm = None

    try:
        # Step 1: Apply visible watermark
        visible_wm = VisibleWatermarker()
        visible_result = visible_wm.process(
            image_path=test_image,
            text="© NightCat",
            size=40,
            opacity=80,
            angle=-25,
            output_path=output_visible
        )
        visible_result.close()
        visible_result = None
        print("✅ Step 1: Visible watermark applied")

        # Step 2: Apply blind watermark
        blind_wm = BlindWatermarkerAdapter()
        password = "Combined123"
        secret_text = "Licensed to User123"

        output_final, bit_length = blind_wm.embed(
            image_path=output_visible,
            password=password,
            text=secret_text
        )
        print("✅ Step 2: Blind watermark embedded")

        # Step 3: Verify extraction
        extracted = blind_wm.extract(output_final, password, bit_length)
        assert extracted == secret_text
        print(f"✅ Step 3: Blind watermark verified: {extracted}")

        print("\n✅ Combined watermark test passed!")
        return True

    except Exception as e:
        print(f"❌ Combined watermark test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if visible_result is not None:
            visible_result.close()
        if visible_wm is not None:
            visible_wm._cached_fonts.clear()
        if blind_wm is not None:
            blind_wm.cleanup()
        gc.collect()
        safe_delete(test_image)
        safe_delete(output_visible)
        if output_final:
            safe_delete(output_final)


def main():
    """Run all tests."""
    print("🧪 WatermarkMaster Core Module Tests")
    print("=" * 50)

    results = []

    results.append(("Visible Watermark", test_visible_watermark()))
    results.append(("Blind Watermark", test_blind_watermark()))
    results.append(("Wrong Password", test_wrong_password()))
    results.append(("Combined Watermarks", test_combined_watermarks()))

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
