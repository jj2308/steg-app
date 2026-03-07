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

    The stegano library embeds data into individual PNG frames, so each
    frame has its own capacity. This reports per-frame and total capacity.

    Returns:
        dict with total_frames, frame_width, frame_height,
              bytes_per_frame, max_total_bytes, max_total_kb
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": f"Cannot open video: {video_path}"}

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        return {"error": "Cannot read first frame from video."}

    h, w, c = frame.shape
    bits_per_frame = w * h * min(c, 3)
    bytes_per_frame = bits_per_frame // 8

    return {
        "total_frames": total_frames,
        "frame_width": w,
        "frame_height": h,
        "channels": min(c, 3),
        "bits_per_frame": bits_per_frame,
        "bytes_per_frame": bytes_per_frame,
        "max_total_bytes": bytes_per_frame * total_frames,
        "max_total_kb": round(bytes_per_frame * total_frames / 1024, 2),
    }
