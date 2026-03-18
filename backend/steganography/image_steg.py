"""
LSB Image Steganography Module with Password-Based Random Embedding.

Instead of embedding bits sequentially (easy to detect), this module uses
the passphrase as a seed for a PRNG to generate a pseudo-random permutation
of pixel-channel indices. Bits are scattered across the image at positions
determined solely by the passphrase.

Security benefits:
    - Without the passphrase, an attacker cannot determine WHERE data is hidden
    - Resistant to sequential-LSB steganalysis attacks
    - Same passphrase deterministically reproduces the same index permutation

A 32-bit header (payload length) is embedded first, followed by the payload,
both at pseudo-random positions derived from the passphrase.

Supports:
    - PNG (lossless, ideal)
    - JPG input (converted to PNG on output to preserve LSB data)

Operations:
    - embed(cover_path, payload, passphrase) -> PIL Image
    - extract(stego_path, passphrase) -> bytes
    - get_capacity(image_path) -> int (max embeddable bytes)
"""

import hashlib
import struct

import numpy as np
from PIL import Image


HEADER_BITS = 32  # 4 bytes (uint32) to store payload length


def _generate_permutation(passphrase: str, total_indices: int, count: int) -> list:
    """
    Generate a pseudo-random permutation of pixel-channel indices
    seeded by the passphrase.

    Parameters:
        passphrase    : user passphrase (used as PRNG seed)
        total_indices : total number of available pixel-channel slots
        count         : how many indices to select

    Returns:
        List of `count` unique indices in pseudo-random order.
    """
    seed = int(hashlib.sha256(passphrase.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = np.random.RandomState(seed)
    permutation = rng.permutation(total_indices)
    return permutation[:count].tolist()


def get_capacity(image_path: str) -> int:
    """
    Calculate the maximum number of bytes that can be embedded in the image.

    Each pixel has 3 channels (RGB), each channel contributes 1 LSB bit.
    Total usable bits = W * H * 3 - HEADER_BITS (32 bits for length header).
    """
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    total_bits = w * h * 3
    return (total_bits - HEADER_BITS) // 8


def _bytes_to_bits(data: bytes) -> list:
    """Convert a bytes object to a list of individual bits (MSB first per byte)."""
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _bits_to_bytes(bits: list) -> bytes:
    """Convert a list of bits back to a bytes object."""
    out = bytearray()
    for i in range(0, len(bits), 8):
        val = 0
        for bit in bits[i : i + 8]:
            val = (val << 1) | bit
        out.append(val)
    return bytes(out)


def embed(cover_path: str, payload: bytes, passphrase: str = "") -> Image.Image:
    """
    Embed a payload into the cover image using password-based random LSB embedding.

    The passphrase seeds a PRNG that generates a pseudo-random permutation of
    pixel-channel indices. Header and payload bits are scattered across the
    image at those positions, making the embedding undetectable without the
    passphrase.

    Parameters:
        cover_path : path to the cover image (PNG or JPG)
        payload    : encrypted bytes to hide
        passphrase : password used to determine embedding positions

    Returns:
        PIL Image with the payload embedded (must be saved as PNG)

    Raises:
        ValueError if payload exceeds image capacity.
    """
    img = Image.open(cover_path).convert("RGB")
    pixels = np.array(img, dtype=np.uint8)
    flat = pixels.flatten()
    total_indices = len(flat)

    max_bytes = (total_indices - HEADER_BITS) // 8
    if len(payload) > max_bytes:
        raise ValueError(
            f"Payload too large: {len(payload):,} bytes exceeds "
            f"capacity of {max_bytes:,} bytes for this image."
        )

    # Build bit stream: 32-bit big-endian length header + payload bits
    header = struct.pack(">I", len(payload))
    all_bits = _bytes_to_bits(header) + _bytes_to_bits(payload)
    num_bits = len(all_bits)

    # Generate pseudo-random positions from passphrase
    positions = _generate_permutation(passphrase, total_indices, num_bits)

    # Scatter bits at random positions
    for bit_idx, pos in enumerate(positions):
        flat[pos] = (flat[pos] & 0xFE) | all_bits[bit_idx]

    stego_pixels = flat.reshape(pixels.shape)
    return Image.fromarray(stego_pixels)


def extract(stego_path: str, passphrase: str = "") -> bytes:
    """
    Extract the hidden payload from a stego image using password-based
    random position recovery.

    The same passphrase that was used during embedding must be provided
    to regenerate the pseudo-random index permutation and locate the
    scattered bits.

    Parameters:
        stego_path : path to the stego image (PNG)
        passphrase : password used during embedding

    Returns:
        The extracted bytes (still encrypted; caller must decrypt).

    Raises:
        ValueError if no valid data found (wrong passphrase or tampered image).
    """
    img = Image.open(stego_path).convert("RGB")
    flat = np.array(img, dtype=np.uint8).flatten()
    total_indices = len(flat)

    # First, recover the 32-bit header to learn payload length
    header_positions = _generate_permutation(passphrase, total_indices, HEADER_BITS)
    header_bits = [int(flat[pos] & 1) for pos in header_positions]
    length = struct.unpack(">I", _bits_to_bytes(header_bits))[0]

    if length <= 0 or length > (total_indices - HEADER_BITS) // 8:
        raise ValueError(
            "No valid hidden data found. Check that the passphrase is correct "
            "and the image has not been modified."
        )

    # Now recover header + payload bits
    total_bits = HEADER_BITS + (length * 8)
    all_positions = _generate_permutation(passphrase, total_indices, total_bits)

    # Skip header positions, read payload positions
    payload_positions = all_positions[HEADER_BITS:]
    payload_bits = [int(flat[pos] & 1) for pos in payload_positions]

    return _bits_to_bytes(payload_bits)
