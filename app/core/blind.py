"""
Blind Watermark Processor — TrustMark Engine
=============================================
Robust invisible watermarking using Adobe TrustMark (ICCV 2025).

Key improvements over the old blind_watermark approach:
- Survives JPEG compression (any quality)
- Survives resize, crop (up to ~20%), rotation
- Survives color filters, brightness/contrast changes
- Survives screenshots and social-media recompression
- No bit_length needed for extraction — auto-detected
- Works with PNG, JPEG, WebP — any PIL-supported format

Capacity with password: 6 ASCII chars (base64url encoded, fits BCH_5).
Capacity without password: 8 ASCII7 chars (raw, BCH_5 default).
"""

import base64
import hashlib
from pathlib import Path
from typing import Union, Optional, Tuple

from PIL import Image

# Lazy-load TrustMark to avoid slow torch import at startup
_tm_instance = None


def _get_trustmark():
    """Lazy-initialize the TrustMark encoder/decoder (singleton)."""
    global _tm_instance
    if _tm_instance is None:
        from trustmark import TrustMark
        _tm_instance = TrustMark(
            verbose=False,
            model_type='Q',  # PSNR 43-45 dB, best robustness/quality balance
            loadRemover=False,  # We only need encode + decode
            loadBBoxDetector=False,  # Skip unused detector model
        )
    return _tm_instance


# ─── Constants ───────────────────────────────────────────────────────────

# TrustMark BCH_5 mode capacity: 8 ASCII7 characters.
# With base64url encryption: 6 input bytes → 8 base64 chars (exactly fits).
# Without encryption: 8 raw ASCII7 chars.
TRUSTMARK_MAX_PAYLOAD_CHARS = 8  # BCH_5 hard limit
MAX_TEXT_CHARS_RAW = 8  # Without password
MAX_TEXT_CHARS_ENCRYPTED = 6  # With password (base64url overhead)

# Magic prefix to distinguish encrypted vs raw payloads.
# Encrypted payloads start with "!" (1 char overhead).
ENCRYPTED_PREFIX = "!"


# ─── Crypto helpers ──────────────────────────────────────────────────────

def _derive_key(password: str, length: int = 32) -> bytes:
    """Derive a fixed-length key from a password using SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).digest()[:length]


def _xor_crypt(data: bytes, key: bytes) -> bytes:
    """XOR-encrypt/decrypt data with a repeating key."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _encrypt_text(text: str, password: str) -> str:
    """
    Encrypt text with password → base64url encoded string.

    Flow: UTF-8 bytes → XOR with SHA-256(password) → base64url (no padding).

    Capacity: 6 input bytes → 8 base64url chars → fits BCH_5 (8 char limit).
    """
    raw = text.encode("utf-8")
    key = _derive_key(password)
    encrypted = _xor_crypt(raw, key)
    return base64.urlsafe_b64encode(encrypted).rstrip(b'=').decode('ascii')


def _decrypt_text(b64_str: str, password: str) -> str:
    """
    Decrypt a base64url-encoded, XOR-encrypted string back to plaintext.

    Raises ValueError if decryption produces invalid UTF-8.
    """
    # Restore base64 padding
    try:
        padding = 4 - len(b64_str) % 4
        if padding != 4:
            b64_str_padded = b64_str + '=' * padding
        else:
            b64_str_padded = b64_str
        encrypted = base64.urlsafe_b64decode(b64_str_padded)
    except Exception:
        raise ValueError(
            "提取的數據不是有效的水印格式。\n"
            "密碼可能不正確，或圖片不含暗水印。"
        )

    key = _derive_key(password)
    raw = _xor_crypt(encrypted, key)

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("解密失敗 — 密碼可能不正確。")


def _compute_encrypted_length(text: str) -> int:
    """Calculate how many base64url chars the encrypted text will produce."""
    n_bytes = len(text.encode("utf-8"))
    # base64url without padding: ceil(n_bytes * 4 / 3)
    return -(-n_bytes * 4 // 3)  # ceil division


# ─── Public API ──────────────────────────────────────────────────────────

class BlindWatermarkerAdapter:
    """
    Adapter for TrustMark-based robust invisible watermarking.

    Usage:
        adapter = BlindWatermarkerAdapter()

        # Embed (with password encryption)
        output_path, _ = adapter.embed(image_path, "mypassword", "NC2025", output_path)

        # Extract — no bit_length needed!
        text = adapter.extract(image_path, "mypassword")

    Capacity:
        With password: 6 ASCII chars (e.g. "NC2025", "User42")
        Without password: 8 ASCII7 chars
    """

    MAX_TEXT_CHARS = MAX_TEXT_CHARS_ENCRYPTED  # Default assumes password is used

    def __init__(self):
        pass

    @staticmethod
    def get_max_text_length(image_path: Union[str, Path] = None) -> int:
        """
        Get max text length in characters (assumes password encryption).

        TrustMark capacity is fixed regardless of image size.
        Image must be >= 150px on shortest side.
        """
        return MAX_TEXT_CHARS_ENCRYPTED

    @staticmethod
    def get_max_text_length_raw() -> int:
        """Get max text length without password encryption."""
        return MAX_TEXT_CHARS_RAW

    def embed(
            self,
            image_path: Union[str, Path],
            password: str,
            text: str,
            output_path: Optional[Union[str, Path]] = None,
    ) -> Tuple[Path, int]:
        """
        Embed invisible watermark into an image.

        Args:
            image_path: Source image (any PIL-supported format).
            password: Password for encryption. If empty, text is embedded raw.
            text: Text to embed (max 6 chars with password, 8 without).
            output_path: Output path. Defaults to {stem}_blind.png.

        Returns:
            Tuple of (output_path, 0).
            Second element is always 0 (bit_length no longer needed).
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"圖片不存在: {image_path}")

        if not text:
            raise ValueError("水印文字不能為空")

        # Encrypt if password is provided
        if password:
            payload = _encrypt_text(text, password)
            max_input = MAX_TEXT_CHARS_ENCRYPTED
        else:
            payload = text
            max_input = MAX_TEXT_CHARS_RAW

        # Validate payload fits TrustMark capacity
        if len(payload) > TRUSTMARK_MAX_PAYLOAD_CHARS:
            raise ValueError(
                f"文字太長：編碼後 {len(payload)} 字符"
                f"（上限 {TRUSTMARK_MAX_PAYLOAD_CHARS}）。\n"
                f"請將文字縮短到 {max_input} 個 ASCII 字符以內。"
            )

        # Load image
        cover = Image.open(image_path).convert("RGB")

        # Validate minimum size
        min_side = min(cover.size)
        if min_side < 150:
            raise ValueError(
                f"圖片太小：最短邊 {min_side}px（最低要求 150px）。"
            )

        # Determine output path
        if output_path is None:
            output_path = image_path.parent / f"{image_path.stem}_blind.png"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Embed watermark
        tm = _get_trustmark()
        watermarked = tm.encode(cover, payload)

        # Save with appropriate format
        suffix = output_path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            watermarked.save(str(output_path), "JPEG", quality=95)
        elif suffix == ".webp":
            watermarked.save(str(output_path), "WEBP", quality=95)
        else:
            watermarked.save(str(output_path), "PNG")

        cover.close()
        return output_path, 0

    def embed_to_image(
            self,
            image: Image.Image,
            password: str,
            text: str,
    ) -> Tuple[Image.Image, int]:
        """Embed invisible watermark into a PIL Image object."""
        if image.mode != "RGB":
            image = image.convert("RGB")

        if not text:
            raise ValueError("水印文字不能為空")

        if password:
            payload = _encrypt_text(text, password)
        else:
            payload = text

        if len(payload) > TRUSTMARK_MAX_PAYLOAD_CHARS:
            max_input = MAX_TEXT_CHARS_ENCRYPTED if password else MAX_TEXT_CHARS_RAW
            raise ValueError(
                f"文字太長：編碼後 {len(payload)} 字符"
                f"（上限 {TRUSTMARK_MAX_PAYLOAD_CHARS}）。\n"
                f"請將文字縮短到 {max_input} 個 ASCII 字符以內。"
            )

        tm = _get_trustmark()
        watermarked = tm.encode(image, payload)
        return watermarked, 0

    def extract(
            self,
            image_path: Union[str, Path],
            password: str,
            bit_length: Optional[int] = None,  # IGNORED — kept for API compat
    ) -> str:
        """
        Extract invisible watermark from an image.

        No bit_length needed! TrustMark auto-detects.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"圖片不存在: {image_path}")

        stego = Image.open(image_path).convert("RGB")

        tm = _get_trustmark()
        wm_secret, wm_present, wm_schema = tm.decode(stego)
        stego.close()

        if not wm_present:
            raise ValueError(
                "未檢測到暗水印。\n"
                "可能原因：\n"
                "• 圖片不含 TrustMark 水印\n"
                "• 圖片遭受了嚴重破壞（如極低質量 JPEG 或大幅裁剪）"
            )

        if password:
            return _decrypt_text(wm_secret, password)
        else:
            return wm_secret

    def cleanup(self):
        """No-op. Kept for API compatibility."""
        pass

    def __del__(self):
        pass


# ─── Convenience functions ───────────────────────────────────────────────

def embed_blind_watermark(
        image_path: Union[str, Path],
        output_path: Union[str, Path],
        password: str,
        text: str,
) -> int:
    """Convenience function. Returns 0 (bit_length no longer needed)."""
    adapter = BlindWatermarkerAdapter()
    _, bit_length = adapter.embed(image_path, password, text, output_path)
    return bit_length


def extract_blind_watermark(
        image_path: Union[str, Path],
        password: str,
        bit_length: int = 0,
) -> str:
    """Convenience function. bit_length is ignored."""
    adapter = BlindWatermarkerAdapter()
    return adapter.extract(image_path, password)
