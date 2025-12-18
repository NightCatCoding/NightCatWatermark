"""
Blind Watermark Processor (Adapter)
===================================
Wraps the blind_watermark library for invisible watermark embedding/extraction.

Technical Notes:
- Uses frequency domain (DCT) watermarking for robustness
- Password/seed affects the embedding pattern - MUST match for extraction
- PNG format is REQUIRED to preserve watermark (JPEG compression destroys it)
- Data format: [MAGIC][LENGTH][DATA] for validation
"""

import hashlib
import tempfile
from pathlib import Path
from typing import Union, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from blind_watermark import WaterMark


class BlindWatermarkerAdapter:
    """
    Adapter class for the blind_watermark library.
    
    This class provides a clean interface for embedding and extracting
    invisible watermarks from images.
    
    Data format (in bits):
    - MAGIC: 32 bits (4 bytes) - "NCAT" for validation
    - LENGTH: 32 bits (4 bytes) - data length in bytes
    - DATA: variable - UTF-8 encoded text
    
    Important: 
    - Always use PNG format for output to preserve watermark integrity
    - The password used for embedding MUST be used for extraction
    """

    # Magic number for validation: "NCAT" in ASCII
    MAGIC_BYTES = b"NCAT"
    MAGIC_SIZE = 32  # bits (4 bytes)

    # Header format: 4 bytes magic + 4 bytes length
    LENGTH_SIZE = 32  # bits (4 bytes)
    HEADER_SIZE = MAGIC_SIZE + LENGTH_SIZE  # 64 bits total

    # Maximum supported text length in bytes
    MAX_TEXT_BYTES = 500

    def __init__(self):
        """Initialize the BlindWatermarkerAdapter."""
        self._temp_files: list[Path] = []

    def _password_to_seed(self, password: str) -> int:
        """
        Convert a password string to an integer seed.
        
        Uses SHA-256 to generate a consistent seed from any password.
        
        Args:
            password: The password string.
            
        Returns:
            Integer seed for the watermark algorithm.
        """
        hash_bytes = hashlib.sha256(password.encode("utf-8")).digest()
        seed = int.from_bytes(hash_bytes[:8], byteorder="big")
        return seed % (2 ** 31 - 1)

    def _get_image_capacity(self, image_path: Path) -> int:
        """
        Calculate the maximum number of bits that can be embedded in an image.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Maximum embeddable bits.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")

        height, width = img.shape[:2]
        # Capacity formula: width * height / 64
        capacity = (width * height) // 64
        return capacity

    def _text_to_bits(self, text: str) -> np.ndarray:
        """
        Convert text string to bit array for embedding.
        
        Format: [4-byte magic "NCAT"][4-byte length][UTF-8 data]
        
        Args:
            text: Text to convert.
            
        Returns:
            Numpy array of bits (0s and 1s).
        """
        data_bytes = text.encode("utf-8")
        data_length = len(data_bytes)

        # Build: MAGIC + LENGTH + DATA
        length_bytes = data_length.to_bytes(4, byteorder="big")
        full_data = self.MAGIC_BYTES + length_bytes + data_bytes

        # Convert to bits
        bits = []
        for byte in full_data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)

        return np.array(bits, dtype=np.uint8)

    def _bits_to_text(self, bits: np.ndarray) -> str:
        """
        Convert bit array back to text string.
        
        Args:
            bits: Numpy array of bits.
            
        Returns:
            Decoded text string.
            
        Raises:
            ValueError: If the data is corrupted or invalid.
        """
        if len(bits) < self.HEADER_SIZE:
            raise ValueError("Insufficient data: missing header")

        # Extract and verify magic (first 32 bits)
        magic_bits = bits[:self.MAGIC_SIZE]
        magic_bytes = bytes([
            int("".join(map(str, magic_bits[i:i + 8])), 2)
            for i in range(0, self.MAGIC_SIZE, 8)
        ])

        if magic_bytes != self.MAGIC_BYTES:
            raise ValueError(
                "Invalid watermark data. "
                "The password may be incorrect or the image may not contain a watermark."
            )

        # Extract length (next 32 bits)
        length_bits = bits[self.MAGIC_SIZE:self.HEADER_SIZE]
        length_bytes = bytes([
            int("".join(map(str, length_bits[i:i + 8])), 2)
            for i in range(0, self.LENGTH_SIZE, 8)
        ])
        data_length = int.from_bytes(length_bytes, byteorder="big")

        # Sanity check
        if data_length <= 0 or data_length > self.MAX_TEXT_BYTES:
            raise ValueError(
                f"Invalid data length: {data_length}. "
                "The password may be incorrect or data is corrupted."
            )

        expected_total_bits = self.HEADER_SIZE + (data_length * 8)

        if len(bits) < expected_total_bits:
            raise ValueError(
                f"Data truncated: expected {expected_total_bits} bits, got {len(bits)}"
            )

        # Extract data bits
        data_bits = bits[self.HEADER_SIZE:expected_total_bits]

        # Convert to bytes
        data_bytes = bytes([
            int("".join(map(str, data_bits[i:i + 8])), 2)
            for i in range(0, len(data_bits), 8)
        ])

        try:
            return data_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode text: {e}")

    def _ensure_png_format(self, image_path: Path) -> Path:
        """
        Ensure the image is in PNG format for processing.
        
        Args:
            image_path: Path to the input image.
            
        Returns:
            Path to the PNG image (may be temporary).
        """
        if image_path.suffix.lower() == ".png":
            return image_path

        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")

        temp_path = Path(tempfile.mktemp(suffix=".png"))
        img.save(temp_path, "PNG")
        img.close()
        self._temp_files.append(temp_path)

        return temp_path

    def get_max_text_length(self, image_path: Union[str, Path]) -> int:
        """
        Get the maximum text length (in bytes) that can be embedded in an image.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Maximum text length in bytes.
        """
        image_path = Path(image_path)
        png_path = self._ensure_png_format(image_path)
        capacity_bits = self._get_image_capacity(png_path)

        # Subtract header size and convert to bytes
        available_bits = capacity_bits - self.HEADER_SIZE
        max_from_image = max(0, available_bits // 8)

        # Also cap at MAX_TEXT_BYTES
        return min(max_from_image, self.MAX_TEXT_BYTES)

    def embed(
            self,
            image_path: Union[str, Path],
            password: str,
            text: str,
            output_path: Optional[Union[str, Path]] = None
    ) -> Tuple[Path, int]:
        """
        Embed invisible watermark text into an image.
        
        Args:
            image_path: Path to the source image.
            password: Password/key for watermark encryption.
            text: Text to embed as watermark.
            output_path: Path for output image. If None, auto-generated.
            
        Returns:
            Tuple of (output_path, bit_length) where bit_length is needed
            for extraction.
            
        Raises:
            FileNotFoundError: If source image doesn't exist.
            ValueError: If password or text is empty, or text too long.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if not password:
            raise ValueError("Password cannot be empty")

        if not text:
            raise ValueError("Watermark text cannot be empty")

        text_bytes = text.encode("utf-8")
        if len(text_bytes) > self.MAX_TEXT_BYTES:
            raise ValueError(
                f"Text too long: {len(text_bytes)} bytes (max: {self.MAX_TEXT_BYTES})"
            )

        # Ensure PNG format
        png_path = self._ensure_png_format(image_path)

        # Check image capacity
        max_text_len = self.get_max_text_length(png_path)
        if len(text_bytes) > max_text_len:
            raise ValueError(
                f"Text too long for this image: {len(text_bytes)} bytes "
                f"(image capacity: {max_text_len} bytes). "
                "Use a larger image or shorter text."
            )

        seed = self._password_to_seed(password)
        bits = self._text_to_bits(text)
        bit_length = len(bits)

        if output_path is None:
            output_path = image_path.parent / f"{image_path.stem}_blind.png"
        else:
            output_path = Path(output_path)
            if output_path.suffix.lower() != ".png":
                output_path = output_path.with_suffix(".png")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        wm = WaterMark(password_img=seed, password_wm=seed)
        wm.read_img(str(png_path))
        wm.read_wm(bits, mode="bit")
        wm.embed(str(output_path))

        return output_path, bit_length

    def embed_to_image(
            self,
            image: Image.Image,
            password: str,
            text: str
    ) -> Tuple[Image.Image, int]:
        """
        Embed invisible watermark into a PIL Image object.
        
        Args:
            image: PIL Image object.
            password: Password/key for watermark encryption.
            text: Text to embed.
            
        Returns:
            Tuple of (watermarked_image, bit_length).
        """
        temp_input = Path(tempfile.mktemp(suffix=".png"))
        temp_output = Path(tempfile.mktemp(suffix=".png"))

        try:
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.save(temp_input, "PNG")

            self.embed(temp_input, password, text, temp_output)

            result = Image.open(temp_output).copy()
            bits = self._text_to_bits(text)

            return result, len(bits)

        finally:
            if temp_input.exists():
                temp_input.unlink()
            if temp_output.exists():
                temp_output.unlink()

    def extract(
            self,
            image_path: Union[str, Path],
            password: str,
            bit_length: Optional[int] = None
    ) -> str:
        """
        Extract invisible watermark from an image.
        
        Args:
            image_path: Path to the watermarked image.
            password: Password used during embedding.
            bit_length: Length of embedded data in bits. If None, uses
                       the bit_length that was returned from embed().
                       
        Returns:
            Extracted watermark text.
            
        Raises:
            FileNotFoundError: If image doesn't exist.
            ValueError: If extraction fails or data is corrupted.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if not password:
            raise ValueError("Password cannot be empty")

        if bit_length is None:
            raise ValueError(
                "bit_length is required for extraction. "
                "Use the bit_length returned from embed()."
            )

        seed = self._password_to_seed(password)
        png_path = self._ensure_png_format(image_path)

        # Verify bit_length doesn't exceed capacity
        capacity = self._get_image_capacity(png_path)
        if bit_length > capacity:
            raise ValueError(
                f"bit_length ({bit_length}) exceeds image capacity ({capacity})"
            )

        wm = WaterMark(password_img=seed, password_wm=seed)
        extracted_bits = wm.extract(str(png_path), wm_shape=bit_length, mode="bit")

        bits = np.array(extracted_bits).round().astype(np.uint8)

        return self._bits_to_text(bits)

    def cleanup(self):
        """Clean up any temporary files created during processing."""
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except OSError:
                pass
        self._temp_files.clear()

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Convenience functions
def embed_blind_watermark(
        image_path: Union[str, Path],
        output_path: Union[str, Path],
        password: str,
        text: str
) -> int:
    """
    Convenience function to embed a blind watermark.
    
    Returns:
        Bit length needed for extraction.
    """
    adapter = BlindWatermarkerAdapter()
    try:
        _, bit_length = adapter.embed(image_path, password, text, output_path)
        return bit_length
    finally:
        adapter.cleanup()


def extract_blind_watermark(
        image_path: Union[str, Path],
        password: str,
        bit_length: int
) -> str:
    """
    Convenience function to extract a blind watermark.
    
    Args:
        bit_length: Required - the bit_length from embed().
    """
    adapter = BlindWatermarkerAdapter()
    try:
        return adapter.extract(image_path, password, bit_length)
    finally:
        adapter.cleanup()
