"""
File I/O Utilities for the Multi-Media Steganography System.

Handles:
    - Saving uploaded files to a temporary uploads directory
    - Generating output file paths
    - Initialising runtime directories
    - Cleaning up temporary files
"""

import os
import uuid
import shutil

# Resolve paths relative to the project root (one level up from this file)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(_PROJECT_ROOT, "uploads")
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "output")


def init_dirs():
    """Create the uploads and output directories if they do not exist."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_upload(file_storage) -> str:
    """
    Save a Flask FileStorage object to the uploads directory.

    Parameters:
        file_storage : werkzeug.datastructures.FileStorage from request.files

    Returns:
        Absolute path to the saved file.
    """
    init_dirs()
    original_name = file_storage.filename or "upload"
    ext = os.path.splitext(original_name)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, unique_name)
    file_storage.save(path)
    return path


def output_path(filename: str) -> str:
    """
    Return an absolute path inside the output directory for the given filename.

    Parameters:
        filename : desired output filename (e.g. 'stego_output.png')

    Returns:
        Absolute path string.
    """
    init_dirs()
    return os.path.join(OUTPUT_DIR, filename)


def cleanup_uploads():
    """Remove all files in the uploads directory."""
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR)
        os.makedirs(UPLOAD_DIR, exist_ok=True)


def cleanup_output():
    """Remove all files in the output directory."""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_file_size_str(file_path: str) -> str:
    """Return a human-readable file size string."""
    if not os.path.exists(file_path):
        return "N/A"
    size = os.path.getsize(file_path)
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"
