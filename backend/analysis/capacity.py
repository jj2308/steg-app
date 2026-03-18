"""
Steganographic Capacity Estimator.

Calculates the maximum amount of data that can be hidden in a given
cover medium (image or video) before the embedding step.

This is a research-level feature useful for:
    - Informing the user whether their payload fits
    - Comparing capacity across different media formats
    - Reporting in research papers
"""

import cv2
import numpy as np
from PIL import Image


def estimate_image_capacity(image_path: str) -> dict:
    """
    Estimate the LSB embedding capacity of an image.

    Uses 1 bit per RGB channel per pixel.
    32 bits are reserved for the payload-length header.

    Returns:
        dict with max_bytes, max_kb, width, height, total_pixels
    """
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    total_pixels = w * h
    total_bits = total_pixels * 3  # R, G, B each contribute 1 bit
    header_bits = 32
    usable_bits = total_bits - header_bits
    max_bytes = usable_bits // 8

    return {
        "width": w,
        "height": h,
        "total_pixels": total_pixels,
        "usable_bits": usable_bits,
        "max_bytes": max_bytes,
        "max_kb": round(max_bytes / 1024, 2),
    }


def estimate_video_capacity(video_path: str) -> dict:
    """
    Estimate the LSB embedding capacity of a video.

    Returns carrier properties and per-frame capacity so the caller
    (or frontend) can dynamically compute frames_needed for any payload
    size:

        frames_needed = ceil(payload_bytes * 8 / bits_per_frame)

    ``max_bytes`` is the total capacity using *all* frames.

    Returns:
        dict with total_frames, fps, frame_width, frame_height,
              channels, bits_per_frame, bytes_per_frame,
              max_bytes, max_kb
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Cannot open video file. Please upload a valid video.")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise ValueError("Cannot read frames from this video file.")

    h, w, c = frame.shape
    channels = min(c, 3)
    bits_per_frame = w * h * channels
    header_bits_per_frame = 32
    bytes_per_frame = (bits_per_frame - header_bits_per_frame) // 8
    max_bytes = bytes_per_frame * total_frames

    return {
        "total_frames": total_frames,
        "fps": round(fps, 2) if fps > 0 else 25.0,
        "frame_width": w,
        "frame_height": h,
        "channels": channels,
        "bits_per_frame": bits_per_frame,
        "bytes_per_frame": bytes_per_frame,
        "max_bytes": max_bytes,
        "max_kb": round(max_bytes / 1024, 2),
    }
