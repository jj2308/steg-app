"""
Media Integrity Verification Module.

Computes SHA-256 hashes of media files so the user can verify that a
stego file has not been tampered with after embedding.

Research relevance:
    - Tamper detection for steganographic media
    - Chain-of-custody verification
    - Can be extended to per-frame hashing for video
"""

import hashlib


def compute_hash(file_path: str) -> str:
    """
    Compute the SHA-256 hash of a file.

    Parameters:
        file_path : path to the file

    Returns:
        Hex-encoded SHA-256 digest string.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify(file_path: str, expected_hash: str) -> bool:
    """
    Verify a file against an expected SHA-256 hash.

    Parameters:
        file_path     : path to the file to check
        expected_hash : hex-encoded SHA-256 digest to compare against

    Returns:
        True if the file matches, False otherwise.
    """
    return compute_hash(file_path) == expected_hash.strip().lower()
