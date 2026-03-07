"""
AES-256-CBC Encryption Module for Multi-Media Steganography System.

Workflow:
    Encrypt: raw bytes -> (optional zlib compress) -> AES-256-CBC encrypt -> base64 encode
    Decrypt: base64 decode -> AES-256-CBC decrypt -> (optional zlib decompress) -> raw bytes

Passphrase is hashed with SHA-256 to derive a 32-byte key.
A random 16-byte IV is prepended to the ciphertext.
"""

import base64
import hashlib
import os
import zlib

from Crypto.Cipher import AES


BLOCK_SIZE = AES.block_size  # 16 bytes


def _derive_key(passphrase: str) -> bytes:
    """Derive a 256-bit key from a passphrase using SHA-256."""
    return hashlib.sha256(passphrase.encode("utf-8")).digest()


def encrypt(data: bytes, passphrase: str, compress: bool = True) -> bytes:
    """
    Encrypt arbitrary bytes with AES-256-CBC.

    Parameters:
        data        : raw bytes to encrypt
        passphrase  : user-supplied password
        compress    : if True, zlib-compress before encrypting (multi-layer)

    Returns:
        base64-encoded bytes of (IV + ciphertext)
    """
    if compress:
        data = b"ZLIB" + zlib.compress(data, level=9)

    key = _derive_key(passphrase)
    iv = os.urandom(BLOCK_SIZE)

    # PKCS7 padding
    pad_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    data += bytes([pad_len]) * pad_len

    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(data)

    return base64.b64encode(iv + ciphertext)


def decrypt(token: bytes, passphrase: str) -> bytes:
    """
    Decrypt base64-encoded AES-256-CBC ciphertext.

    Parameters:
        token       : base64-encoded bytes (IV + ciphertext)
        passphrase  : user-supplied password

    Returns:
        original raw bytes
    """
    key = _derive_key(passphrase)
    raw = base64.b64decode(token)

    iv = raw[:BLOCK_SIZE]
    ciphertext = raw[BLOCK_SIZE:]

    cipher = AES.new(key, AES.MODE_CBC, iv)
    data = cipher.decrypt(ciphertext)

    # Remove PKCS7 padding
    pad_len = data[-1]
    if pad_len < 1 or pad_len > BLOCK_SIZE:
        raise ValueError("Invalid padding encountered during decryption.")
    if data[-pad_len:] != bytes([pad_len]) * pad_len:
        raise ValueError("Incorrect passphrase or corrupted data.")
    data = data[:-pad_len]

    # Decompress if marker present
    if data[:4] == b"ZLIB":
        data = zlib.decompress(data[4:])

    return data
