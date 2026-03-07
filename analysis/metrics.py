"""
Image / Video Quality Metrics for Steganography Evaluation.

Computes PSNR (Peak Signal-to-Noise Ratio) and MSE (Mean Squared Error)
between an original cover medium and the resulting stego medium.

Research relevance:
    - Higher PSNR = less perceptible distortion = better steganography
    - Typical LSB steganography yields PSNR > 50 dB (imperceptible)
    - These metrics are standard in steganography research papers
"""

import cv2
import numpy as np
from math import log10, sqrt


def mse(original_path: str, stego_path: str) -> float:
    """
    Compute Mean Squared Error between two images.

    Parameters:
        original_path : path to the original cover image
        stego_path    : path to the stego image

    Returns:
        MSE value (0.0 means identical images).
    """
    orig = cv2.imread(original_path)
    steg = cv2.imread(stego_path)

    if orig is None:
        raise FileNotFoundError(f"Cannot read original image: {original_path}")
    if steg is None:
        raise FileNotFoundError(f"Cannot read stego image: {stego_path}")

    # Resize stego to match original if dimensions differ
    if orig.shape != steg.shape:
        steg = cv2.resize(steg, (orig.shape[1], orig.shape[0]))

    return float(np.mean((orig.astype(np.float64) - steg.astype(np.float64)) ** 2))


def psnr(original_path: str, stego_path: str) -> float:
    """
    Compute Peak Signal-to-Noise Ratio between two images.

    Parameters:
        original_path : path to the original cover image
        stego_path    : path to the stego image

    Returns:
        PSNR value in dB. Returns float('inf') if images are identical.
    """
    mse_val = mse(original_path, stego_path)
    if mse_val == 0:
        return float("inf")
    max_pixel = 255.0
    return 20.0 * log10(max_pixel / sqrt(mse_val))


def compute_metrics(original_path: str, stego_path: str) -> dict:
    """
    Compute all quality metrics between original and stego images.

    Returns:
        dict with mse, psnr, and a human-readable quality rating.
    """
    mse_val = mse(original_path, stego_path)
    psnr_val = psnr(original_path, stego_path)

    if psnr_val == float("inf"):
        quality = "Identical (no distortion)"
    elif psnr_val >= 50:
        quality = "Excellent (imperceptible)"
    elif psnr_val >= 40:
        quality = "Good (barely perceptible)"
    elif psnr_val >= 30:
        quality = "Acceptable (slightly noticeable)"
    else:
        quality = "Poor (noticeable distortion)"

    return {
        "mse": round(mse_val, 6),
        "psnr_db": round(psnr_val, 2) if psnr_val != float("inf") else "Inf",
        "quality": quality,
    }
