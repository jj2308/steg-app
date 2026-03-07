"""
Video Steganography Module with Password-Based Random Frame Selection.

Refactored from the original encode.py and decodetext.py.
Algorithm:
    Embed:  extract frames via OpenCV -> passphrase-seeded PRNG selects
            which frames to use -> LSB-hide chunks into those frames ->
            rebuild a playable video with FFV1 lossless codec in MKV ->
            embed total_frames and num_parts as MKV metadata tags
    Extract: read STEG_FRAMES / STEG_PARTS from MKV metadata ->
             extract frames via FFmpeg -> regenerate frame indices
             from passphrase + stored total_frames -> LSB-reveal ->
             concatenate

Output is a playable .mkv video encoded with FFV1 (lossless) and bgr24
pixel format, guaranteeing bit-perfect preservation of LSB data.
The original total_frames count and num_parts are stored as MKV metadata
so extraction only requires the passphrase — no extra values to remember.

Uses the `stegano` library for per-frame LSB operations.
Requires bundled FFmpeg (via imageio-ffmpeg) for lossless video rebuild
and frame extraction.
"""

import cv2
import hashlib
import math
import os
import shutil
from subprocess import call, run, DEVNULL, PIPE

import imageio_ffmpeg
import numpy as np
from stegano import lsb

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def count_frames(video_path: str) -> int:
    """Return the total number of frames in a video file."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return length


def get_frame_size(video_path: str) -> tuple:
    """Return (width, height) of the video frames."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise ValueError("Cannot read first frame from video.")
    h, w = frame.shape[:2]
    return w, h


def _get_fps(video_path: str) -> float:
    """Return the FPS of a video file."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return fps if fps > 0 else 25.0


def _split_string(s: str, count: int = 15) -> list:
    """Split a string into `count` roughly equal parts."""
    per_c = math.ceil(len(s) / count)
    return [s[i : i + per_c] for i in range(0, len(s), per_c)]


def _generate_frame_indices(passphrase: str, total_frames: int, count: int) -> list:
    """
    Generate a pseudo-random selection of frame indices seeded by the passphrase.

    Parameters:
        passphrase   : user passphrase (used as PRNG seed)
        total_frames : total number of frames in the video
        count        : how many frames to select

    Returns:
        Sorted list of `count` unique frame indices.
    """
    if count > total_frames:
        raise ValueError(
            f"Need {count} frames but video only has {total_frames}."
        )
    seed = int(hashlib.sha256(passphrase.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = np.random.RandomState(seed)
    selected = rng.choice(total_frames, size=count, replace=False)
    return sorted(selected.tolist())


def _extract_frames_cv(video_path: str, tmp_dir: str) -> int:
    """Extract all frames from a video file to tmp_dir as 0-indexed PNGs using OpenCV."""
    os.makedirs(tmp_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    count = 0
    while True:
        success, image = cap.read()
        if not success:
            break
        cv2.imwrite(os.path.join(tmp_dir, f"{count}.png"), image)
        count += 1
    cap.release()
    if count == 0:
        raise ValueError(f"No frames could be read from: {video_path}")
    return count


def _extract_frames_ffmpeg(video_path: str, tmp_dir: str) -> int:
    """
    Extract all frames from a video to tmp_dir as 0-indexed PNGs using FFmpeg.

    Uses bgr24 pixel format to match OpenCV's channel order so that
    stegano (PIL-based, RGB) reads the same data that was written.
    """
    os.makedirs(tmp_dir, exist_ok=True)
    ff_dir = os.path.join(tmp_dir, "_ff")
    os.makedirs(ff_dir, exist_ok=True)

    call(
        [FFMPEG, "-i", video_path, "-pix_fmt", "bgr24",
         os.path.join(ff_dir, "%d.png"), "-y"],
        stdout=DEVNULL, stderr=DEVNULL,
    )

    frame_files = sorted(
        [f for f in os.listdir(ff_dir) if f.endswith(".png")],
        key=lambda x: int(x.split(".")[0]),
    )
    count = len(frame_files)
    if count == 0:
        shutil.rmtree(ff_dir, ignore_errors=True)
        raise FileNotFoundError(f"FFmpeg failed to extract frames from: {video_path}")

    # Move to parent dir with 0-indexed names (FFmpeg outputs 1-indexed)
    first_idx = int(frame_files[0].split(".")[0])
    for f in frame_files:
        idx = int(f.split(".")[0])
        shutil.move(os.path.join(ff_dir, f),
                     os.path.join(tmp_dir, f"{idx - first_idx}.png"))
    shutil.rmtree(ff_dir, ignore_errors=True)

    return count


def _rebuild_video_ffv1(
    original_video: str, tmp_dir: str, output_path: str,
    total_frames: int, num_parts: int,
) -> str:
    """
    Rebuild a playable video from PNG frames using FFV1 lossless codec in MKV.

    Uses bgr24 pixel format to avoid any colour-space conversion, keeping
    LSB modifications bit-perfect. Audio is intentionally omitted because
    muxing audio into the MKV causes timestamp misalignment that adds a
    duplicate frame and corrupts the video stream.

    Writes STEG_FRAMES and STEG_PARTS as MKV metadata so extraction can
    recover the correct values automatically.

    Returns:
        Actual output path (always .mkv).
    """
    fps = _get_fps(original_video)

    # Ensure output has .mkv extension
    base, _ = os.path.splitext(output_path)
    output_path_mkv = base + ".mkv"

    # Rebuild video: PNGs -> FFV1 MKV (lossless, bgr24) with steg metadata
    call(
        [FFMPEG, "-framerate", str(fps), "-start_number", "0",
         "-i", os.path.join(tmp_dir, "%d.png"),
         "-c:v", "ffv1", "-pix_fmt", "bgr24",
         "-metadata", f"STEG_FRAMES={total_frames}",
         "-metadata", f"STEG_PARTS={num_parts}",
         output_path_mkv, "-y"],
        stdout=DEVNULL, stderr=DEVNULL,
    )

    if not os.path.exists(output_path_mkv):
        raise RuntimeError("FFmpeg failed to build FFV1 video.")

    return output_path_mkv


def _read_mkv_metadata(video_path: str) -> dict:
    """
    Read STEG_FRAMES and STEG_PARTS metadata tags from an MKV file.

    Uses FFmpeg's ffmetadata output format for reliable parsing.
    """
    result = run(
        [FFMPEG, "-i", video_path, "-f", "ffmetadata", "-"],
        stdout=PIPE, stderr=DEVNULL, text=True,
    )
    meta = {}
    for line in result.stdout.splitlines():
        if "=" in line and not line.startswith(";"):
            key, _, val = line.partition("=")
            meta[key.strip()] = val.strip()
    steg_frames = meta.get("STEG_FRAMES")
    steg_parts = meta.get("STEG_PARTS")
    if steg_frames is None or steg_parts is None:
        raise ValueError(
            "This video does not contain steganography metadata. "
            "Make sure you are uploading a stego video generated by this system."
        )
    return {"total_frames": int(steg_frames), "num_parts": int(steg_parts)}


def embed(
    video_path: str,
    payload_str: str,
    passphrase: str = "",
    tmp_dir: str = None,
    output_path: str = "stego_video.mkv",
) -> dict:
    """
    Embed a string payload into pseudo-randomly selected frames of a video.

    The passphrase seeds a PRNG that determines which frames receive hidden
    data. The output is a playable MKV video encoded with the FFV1 lossless
    codec, preserving LSB modifications bit-perfectly.

    Parameters:
        video_path    : path to the cover video
        payload_str   : the string to embed (typically base64-encoded encrypted data)
        passphrase    : password used to determine which frames are selected
        tmp_dir       : temporary working directory (auto-generated if None)
        output_path   : path for the output stego video

    Returns:
        dict with keys: output_path, frame_numbers, num_parts, total_frames
    """
    # Ensure .mkv extension
    base, _ = os.path.splitext(output_path)
    output_path = base + ".mkv"

    if tmp_dir is None:
        tmp_dir = os.path.join(os.path.dirname(output_path) or ".", "_tmp_embed")

    total_frames = _extract_frames_cv(video_path, tmp_dir)
    fps = _get_fps(video_path)
    split_list = _split_string(payload_str)
    n_parts = len(split_list)

    # Password-based random frame selection
    frame_numbers = _generate_frame_indices(passphrase, total_frames, n_parts)

    # Embed each chunk into its frame via LSB
    for i in range(n_parts):
        frame_path = os.path.join(tmp_dir, f"{frame_numbers[i]}.png")
        if not os.path.exists(frame_path):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise FileNotFoundError(f"Frame {frame_numbers[i]} not found at {frame_path}")
        secret_img = lsb.hide(frame_path, split_list[i])
        secret_img.save(frame_path)

    actual_output = _rebuild_video_ffv1(
        video_path, tmp_dir, output_path,
        total_frames=total_frames, num_parts=n_parts,
    )
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return {
        "output_path": actual_output,
        "frame_numbers": frame_numbers,
        "num_parts": n_parts,
        "total_frames": total_frames,
    }


def extract(
    video_path: str,
    passphrase: str,
    num_parts: int = None,
    tmp_dir: str = None,
) -> str:
    """
    Extract hidden string from a stego MKV video using password-based
    frame recovery.

    The same passphrase used during embedding is required. total_frames
    and num_parts are read automatically from MKV metadata tags written
    during embedding.

    Parameters:
        video_path : path to the stego video (.mkv)
        passphrase : password used during embedding
        num_parts  : ignored (auto-read from metadata); kept for API compat
        tmp_dir    : temporary working directory

    Returns:
        Concatenated hidden string from all data-carrying frames.
    """
    if tmp_dir is None:
        tmp_dir = os.path.join(os.path.dirname(video_path) or ".", "_tmp_extract")

    # Read the ORIGINAL total_frames and num_parts from MKV metadata
    meta = _read_mkv_metadata(video_path)
    total_frames = meta["total_frames"]
    num_parts = meta["num_parts"]

    # Extract frames from stego video via FFmpeg
    _extract_frames_ffmpeg(video_path, tmp_dir)

    # Regenerate the same frame indices from passphrase
    frame_numbers = _generate_frame_indices(passphrase, total_frames, num_parts)

    decoded = {}
    for fn in frame_numbers:
        frame_path = os.path.join(tmp_dir, f"{fn}.png")
        if not os.path.exists(frame_path):
            decoded[fn] = ""
            continue
        try:
            clear_message = lsb.reveal(frame_path)
            decoded[fn] = clear_message if clear_message else ""
        except Exception:
            decoded[fn] = ""

    shutil.rmtree(tmp_dir, ignore_errors=True)

    # Reassemble in the order of frame_numbers
    return "".join(decoded.get(fn, "") for fn in frame_numbers)
