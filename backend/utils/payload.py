"""
Payload Packaging Utilities for the Multi-Media Steganography System.

Provides functions to serialize and deserialize file payloads with
metadata (original filename) so that extracted files can be restored
with their correct name and extension.

Binary format:
    [8 bytes]  magic header  b"STEGFILE"
    [2 bytes]  filename length (big-endian uint16)
    [N bytes]  filename (UTF-8 encoded)
    [rest]     file data

Plain text payloads (no file upload) skip this wrapper entirely,
so the unpacker can distinguish them by checking for the magic header.
"""

import struct

MAGIC = b"STEGFILE"


def pack_payload(filename: str, data: bytes) -> bytes:
    """
    Wrap file data with its original filename into a binary payload.

    Parameters:
        filename : original filename (e.g. 'secret.pdf')
        data     : raw file bytes

    Returns:
        Serialized bytes: MAGIC + filename_len + filename + data
    """
    fname_bytes = filename.encode("utf-8")
    if len(fname_bytes) > 65535:
        raise ValueError("Filename is too long (max 65535 bytes UTF-8).")
    header = MAGIC + struct.pack(">H", len(fname_bytes)) + fname_bytes
    return header + data


def unpack_payload(payload: bytes) -> tuple:
    """
    Attempt to unpack a payload that may contain filename metadata.

    Returns:
        (filename, data) if the payload has the STEGFILE header.
        (None, payload)  if the payload is plain (no header).
    """
    if not payload.startswith(MAGIC):
        return None, payload

    offset = len(MAGIC)
    if len(payload) < offset + 2:
        return None, payload

    fname_len = struct.unpack(">H", payload[offset : offset + 2])[0]
    offset += 2

    if len(payload) < offset + fname_len:
        return None, payload

    filename = payload[offset : offset + fname_len].decode("utf-8")
    offset += fname_len

    data = payload[offset:]
    return filename, data
