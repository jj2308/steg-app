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
import time
from subprocess import call, run, Popen, DEVNULL, PIPE

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


def _split_string(s: str, count: int) -> list:
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


def _read_exact(pipe, n):
    """Read exactly *n* bytes from a pipe, or ``None`` on EOF."""
    data = b""
    while len(data) < n:
        chunk = pipe.read(n - len(data))
        if not chunk:
            return None if not data else data
        data += chunk
    return data


def _report(callback, stage, **kwargs):
    """Fire an optional stage callback with optional progress data."""
    if callback is not None:
        callback(stage, **kwargs)


def embed(
    video_path: str,
    payload_str: str,
    passphrase: str = "",
    tmp_dir: str = None,
    output_path: str = "stego_video.mkv",
    on_stage=None,
) -> dict:
    """
    Embed a string payload into pseudo-randomly selected frames of a video.

    **Capacity-driven** — the number of frames used is the *minimum*
    required to hold the payload:

        n_parts = ceil(payload_bits / bits_per_frame)

    **Optimised pipeline** — streams the original video through FFmpeg
    pipes: decode → modify target frames with LSB → encode to FFV1.
    Only the target frames touch disk (temporary PNGs for stegano);
    all other frames are piped through memory untouched.

    Parameters:
        video_path    : path to the cover video
        payload_str   : the string to embed (base64-encoded encrypted data)
        passphrase    : password used to determine which frames are selected
        tmp_dir       : temporary working directory
        output_path   : path for the output stego video
        on_stage      : optional callback(stage_name: str) for progress

    Returns:
        dict with keys: output_path, frame_numbers, num_parts, total_frames
    """
    base, _ = os.path.splitext(output_path)
    output_path_mkv = base + ".mkv"

    if tmp_dir is None:
        tmp_dir = os.path.join(os.path.dirname(output_path_mkv) or ".", "_tmp_embed")
    os.makedirs(tmp_dir, exist_ok=True)

    # ---- Stage 1: fast metadata read ----
    _report(on_stage, "analyzing")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0
    ret, sample = cap.read()
    cap.release()
    if not ret or sample is None:
        raise ValueError("Cannot read frames from video.")
    h, w = sample.shape[:2]

    # ---- Capacity-driven frame selection ----
    bits_per_frame = w * h * 3  # 1 LSB per channel per pixel
    payload_bits = len(payload_str) * 8
    n_parts = max(1, math.ceil(payload_bits / bits_per_frame))
    if n_parts > total_frames:
        raise ValueError(
            f"Payload requires {n_parts} frames but video only has {total_frames}. "
            "Please use a larger video or a smaller payload."
        )

    split_list = _split_string(payload_str, n_parts)
    n_parts = len(split_list)  # may be ≤ requested if payload is tiny
    frame_numbers = _generate_frame_indices(passphrase, total_frames, n_parts)
    frame_payload = {frame_numbers[i]: split_list[i] for i in range(n_parts)}

    frame_size = w * h * 3  # BGR24 bytes per frame

    # ---- Stage 2: single-pass decode → modify → encode ----
    _report(on_stage, "encoding", frames_processed=0, total_frames=total_frames)

    decoder = Popen(
        [FFMPEG, "-v", "error", "-i", video_path,
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        stdout=PIPE, stderr=PIPE,
    )

    encoder = Popen(
        [FFMPEG, "-v", "error",
         "-f", "rawvideo", "-pix_fmt", "bgr24",
         "-s", f"{w}x{h}", "-r", str(fps),
         "-i", "-",
         "-c:v", "ffv1", "-level", "3", "-slices", "4",
         "-pix_fmt", "bgr24",
         "-metadata", f"STEG_FRAMES={total_frames}",
         "-metadata", f"STEG_PARTS={n_parts}",
         output_path_mkv, "-y"],
        stdin=PIPE, stdout=DEVNULL, stderr=PIPE,
    )

    try:
        embedded_count = 0
        t_start = time.monotonic()
        last_report = 0.0          # throttle reports to ~1 Hz
        for i in range(total_frames):
            raw = _read_exact(decoder.stdout, frame_size)
            if raw is None:
                break

            if i in frame_payload:
                # raw BGR bytes → numpy → PNG → stegano LSB → PNG → BGR bytes
                frame_arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3)).copy()
                tmp_png = os.path.join(tmp_dir, f"_f{i}.png")
                cv2.imwrite(tmp_png, frame_arr)
                secret_img = lsb.hide(tmp_png, frame_payload[i])
                secret_img.save(tmp_png)
                modified_arr = cv2.imread(tmp_png)
                if modified_arr is None:
                    raise RuntimeError(f"Failed to read modified frame {i} from {tmp_png}")
                encoder.stdin.write(modified_arr.tobytes())
                os.remove(tmp_png)
                embedded_count += 1
            else:
                encoder.stdin.write(raw)

            # Report frame-level progress (~1 Hz)
            now = time.monotonic()
            if now - last_report >= 1.0 or i == total_frames - 1:
                last_report = now
                elapsed = now - t_start
                stage = "embedding" if embedded_count < n_parts else "encoding"
                _report(on_stage, stage,
                        frames_processed=i + 1,
                        total_frames=total_frames,
                        elapsed=round(elapsed, 2))
    except (BrokenPipeError, OSError) as pipe_err:
        # Capture encoder stderr if the pipe breaks
        enc_err = encoder.stderr.read().decode(errors="replace").strip() if encoder.stderr else ""
        dec_err = decoder.stderr.read().decode(errors="replace").strip() if decoder.stderr else ""
        detail = enc_err or dec_err or str(pipe_err)
        raise RuntimeError(f"Video encoding failed: {detail}") from pipe_err
    finally:
        decoder.stdout.close()
        try:
            encoder.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        decoder.wait()
        encoder.wait()

    # Capture any trailing FFmpeg errors
    enc_err = encoder.stderr.read().decode(errors="replace").strip() if encoder.stderr else ""
    dec_err = decoder.stderr.read().decode(errors="replace").strip() if decoder.stderr else ""

    shutil.rmtree(tmp_dir, ignore_errors=True)

    if not os.path.exists(output_path_mkv):
        detail = enc_err or dec_err or "unknown reason"
        raise RuntimeError(f"FFmpeg failed to build the output video: {detail}")

    _report(on_stage, "done")

    return {
        "output_path": output_path_mkv,
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

    **Optimised** — instead of decoding every frame to disk, this seeks
    directly to the ~15 target frames using OpenCV.  FFV1 is intra-frame
    so seeking is essentially free.

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

    # Regenerate the same frame indices from passphrase
    frame_numbers = _generate_frame_indices(passphrase, total_frames, num_parts)

    os.makedirs(tmp_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open stego video: {video_path}")

    decoded = {}
    for fn in frame_numbers:
        if fn in decoded:
            continue  # already processed (duplicate frame index)
        cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
        ret, frame = cap.read()
        if not ret or frame is None:
            decoded[fn] = ""
            continue
        tmp_png = os.path.join(tmp_dir, f"_f{fn}.png")
        cv2.imwrite(tmp_png, frame)
        try:
            clear_message = lsb.reveal(tmp_png)
            decoded[fn] = clear_message if clear_message else ""
        except Exception:
            decoded[fn] = ""
        os.remove(tmp_png)

    cap.release()
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # Reassemble in the order of frame_numbers
    return "".join(decoded.get(fn, "") for fn in frame_numbers)
