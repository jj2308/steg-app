"""
MultiSteg — Multi-Media Steganography Research System

Flask web application providing a modern UI for:
    - Image steganography (LSB-based, PNG/JPG)
    - Video steganography (frame-based LSB via stegano + FFmpeg)
    - AES-256 encryption with optional zlib compression
    - Research features: capacity estimation, integrity hashing, PSNR metrics
"""

import math
import os
import json
import traceback

from flask import (
    Flask,
    render_template,
    request,
    send_file,
    flash,
    redirect,
    url_for,
    jsonify,
)

from steganography import image_steg, video_steg
from encryption.aes_crypto import encrypt, decrypt
from analysis.capacity import estimate_image_capacity, estimate_video_capacity
from analysis.integrity import compute_hash
from analysis.metrics import compute_metrics
from utils.file_handler import save_upload, output_path, get_file_size_str, init_dirs
from utils.payload import pack_payload, unpack_payload


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB upload limit

# Ensure runtime directories exist (also needed when running under Gunicorn)
init_dirs()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    """Landing page — choose embed or extract."""
    return render_template("new_index.html")


@app.route("/embed", methods=["GET", "POST"])
def embed():
    """Embed secret data into a cover medium."""
    if request.method == "GET":
        return render_template("new_embed.html")

    try:
        media_type = request.form.get("media_type", "image")
        passphrase = request.form.get("passphrase", "")
        cover_file = request.files.get("cover_file")
        secret_file = request.files.get("secret_file")
        secret_text = request.form.get("secret_text", "")

        # --- Validation ---
        if not cover_file or not cover_file.filename:
            flash("Please upload a cover file.", "danger")
            return redirect(url_for("embed"))

        if not passphrase:
            flash("Please enter a passphrase for encryption.", "danger")
            return redirect(url_for("embed"))

        if (not secret_file or not secret_file.filename) and not secret_text.strip():
            flash("Please provide secret text or upload a secret file.", "danger")
            return redirect(url_for("embed"))

        # --- Save cover ---
        cover_path = save_upload(cover_file)

        # --- Prepare secret payload ---
        if secret_file and secret_file.filename:
            file_bytes = secret_file.read()
            secret_name = secret_file.filename
            raw_secret = pack_payload(secret_name, file_bytes)
        else:
            raw_secret = secret_text.strip().encode("utf-8")
            secret_name = "text input"

        # --- Encrypt (compress + AES-256) ---
        encrypted = encrypt(raw_secret, passphrase, compress=True)
        original_size = len(raw_secret)
        encrypted_size = len(encrypted)
        compression_pct = round((1 - encrypted_size / max(original_size, 1)) * 100, 1)

        # --- Capacity check + embed ---
        capacity_info = {}
        metrics_info = {}
        file_hash = ""
        output_filename = ""

        if media_type == "image":
            cap = estimate_image_capacity(cover_path)
            capacity_info = cap

            # encrypted is bytes (base64); for image steg we embed raw encrypted bytes
            if encrypted_size > cap["max_bytes"]:
                needed_px = math.ceil(encrypted_size * 8 / 3)
                side = math.ceil(math.sqrt(needed_px))
                flash(
                    f"Payload is already compressed (zlib) + encrypted: "
                    f"{original_size:,} bytes → {encrypted_size:,} bytes "
                    f"({'saved ' + str(abs(compression_pct)) + '%' if compression_pct > 0 else 'expanded ' + str(abs(compression_pct)) + '% due to encryption overhead'}). "
                    f"Image capacity is {cap['max_bytes']:,} bytes. "
                    f"Use a cover image of at least {side}×{side} pixels.",
                    "danger",
                )
                return redirect(url_for("embed"))

            stego_img = image_steg.embed(cover_path, encrypted, passphrase)
            output_filename = "stego_output.png"
            out_path = output_path(output_filename)
            stego_img.save(out_path, "PNG")

            # Compute quality metrics
            try:
                metrics_info = compute_metrics(cover_path, out_path)
            except Exception:
                metrics_info = {"note": "Metrics unavailable for this pair."}

        else:
            # Video steganography
            cap = estimate_video_capacity(cover_path)
            capacity_info = cap
            payload_str = encrypted.decode("ascii")  # base64 is ASCII-safe
            output_filename = "stego_output.mkv"
            out_path = output_path(output_filename)

            result = video_steg.embed(
                cover_path, payload_str, passphrase=passphrase, output_path=out_path
            )
            out_path = result["output_path"]
            output_filename = os.path.basename(out_path)
            capacity_info["frame_numbers"] = result["frame_numbers"]
            capacity_info["num_parts"] = result["num_parts"]

        file_hash = compute_hash(out_path)
        file_size = get_file_size_str(out_path)

        return render_template(
            "new_result.html",
            mode="embed",
            media_type=media_type,
            download_filename=output_filename,
            file_hash=file_hash,
            file_size=file_size,
            capacity=capacity_info,
            metrics=metrics_info,
            secret_name=secret_name,
            secret_size=len(raw_secret),
            encrypted_size=len(encrypted),
        )

    except Exception as e:
        traceback.print_exc()
        flash(f"Error during embedding: {str(e)}", "danger")
        return redirect(url_for("embed"))


@app.route("/extract", methods=["GET", "POST"])
def extract():
    """Extract and decrypt hidden data from stego media."""
    if request.method == "GET":
        return render_template("new_extract.html")

    try:
        media_type = request.form.get("media_type", "image")
        passphrase = request.form.get("passphrase", "")
        stego_file = request.files.get("stego_file")

        # --- Validation ---
        if not stego_file or not stego_file.filename:
            flash("Please upload a stego file.", "danger")
            return redirect(url_for("extract"))

        if not passphrase:
            flash("Please enter the passphrase used during embedding.", "danger")
            return redirect(url_for("extract"))

        stego_path = save_upload(stego_file)

        # --- Extract ---
        if media_type == "image":
            encrypted = image_steg.extract(stego_path, passphrase)
        else:
            # total_frames and num_parts are auto-read from MKV metadata
            payload_str = video_steg.extract(stego_path, passphrase)
            encrypted = payload_str.encode("ascii")

        # --- Decrypt ---
        decrypted = decrypt(encrypted, passphrase)

        # Unpack payload: recover original filename if present
        original_name, file_data = unpack_payload(decrypted)

        is_text = False
        message = ""
        download_filename = None

        if original_name is not None:
            # File payload — restore with original filename
            is_text = False
            download_filename = original_name
            out = output_path(download_filename)
            with open(out, "wb") as f:
                f.write(file_data)
        else:
            # Plain text payload (no file header)
            try:
                message = file_data.decode("utf-8")
                is_text = True
            except (UnicodeDecodeError, ValueError):
                is_text = False
                download_filename = "extracted_file.bin"
                out = output_path(download_filename)
                with open(out, "wb") as f:
                    f.write(file_data)

        return render_template(
            "new_result.html",
            mode="extract",
            media_type=media_type,
            is_text=is_text,
            message=message,
            download_filename=download_filename,
            decrypted_size=len(file_data),
        )

    except ValueError as e:
        flash(f"Decryption failed — wrong passphrase or corrupted data: {e}", "danger")
        return redirect(url_for("extract"))
    except Exception as e:
        traceback.print_exc()
        flash(f"Error during extraction: {str(e)}", "danger")
        return redirect(url_for("extract"))


@app.route("/download/<filename>")
def download(filename):
    """Download an output file."""
    file_path = output_path(filename)
    if not os.path.exists(file_path):
        flash("File not found.", "danger")
        return redirect(url_for("index"))
    return send_file(file_path, as_attachment=True)


@app.route("/api/capacity", methods=["POST"])
def api_capacity():
    """AJAX endpoint — estimate capacity for an uploaded file."""
    cover_file = request.files.get("cover_file")
    media_type = request.form.get("media_type", "image")

    if not cover_file or not cover_file.filename:
        return jsonify({"error": "No file provided"}), 400

    path = save_upload(cover_file)
    try:
        if media_type == "image":
            info = estimate_image_capacity(path)
        else:
            info = estimate_video_capacity(path)
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n  MultiSteg — Multi-Media Steganography Research System")
    print("  Running at http://127.0.0.1:5000\n")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
