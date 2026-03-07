# Secure Steganography System For Data Transmission

A Flask-based web application for hiding encrypted data inside images and videos using LSB steganography and AES-256 encryption.

## Features

- **Image Steganography** — LSB embedding with password-based random pixel scattering (PNG & JPG support)
- **Video Steganography** — Frame-based LSB embedding with FFV1 lossless codec in MKV container
- **AES-256 Encryption** — All payloads are compressed (zlib) and encrypted before embedding
- **Password-Based Embedding** — Passphrase seeds a PRNG to determine embedding positions, making hidden data undetectable without the password
- **Original File Restoration** — Embedded files are extracted with their original filename and extension
- **Research Analysis** — Capacity estimation, PSNR/MSE metrics, SHA-256 integrity verification

## How It Works

```
Secret File → Compress (zlib) → AES-256 Encrypt → LSB Embed → Stego Media
Stego Media → LSB Extract → AES-256 Decrypt → Decompress → Original File
```

### Image Pipeline
Payload bits are scattered across pseudo-random pixel positions determined by the passphrase. A 32-bit header stores payload length. Output is a lossless PNG.

### Video Pipeline
Frames are extracted via OpenCV, then the passphrase seeds a PRNG to select which frames carry hidden data. Each selected frame gets a chunk of the payload via LSB embedding. Frames are reassembled into a playable MKV video using the FFV1 lossless codec with `bgr24` pixel format for bit-perfect preservation. Frame count and chunk count are stored as MKV metadata tags, so extraction only requires the passphrase.

## Project Structure

```
MultiSteg/
├── main_app.py              # Flask application entry point
├── requirements.txt         # Python dependencies
├── Procfile                 # Gunicorn config for cloud deployment
├── steganography/
│   ├── image_steg.py        # LSB image steganography with random embedding
│   └── video_steg.py        # FFV1 video steganography with metadata tags
├── encryption/
│   └── aes_crypto.py        # AES-256-CBC encryption/decryption
├── analysis/
│   ├── capacity.py          # Capacity estimation for images and videos
│   ├── integrity.py         # SHA-256 file hashing
│   └── metrics.py           # PSNR and MSE quality metrics
├── utils/
│   ├── file_handler.py      # File I/O and directory management
│   └── payload.py           # Payload packaging (preserves original filename)
├── templates/               # Flask HTML templates
│   ├── base.html
│   ├── new_index.html
│   ├── new_embed.html
│   ├── new_extract.html
│   └── new_result.html
└── static/assets/           # Favicon
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/jj2308/steg-app.git
cd steg-app
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** FFmpeg is bundled via `imageio-ffmpeg` — no system-level FFmpeg installation required.

### 3. Run the application

```bash
python main_app.py
```

The app will be available at **http://localhost:5000**.

## Usage

### Embedding

1. Open the web UI and click **Start Embedding**
2. Select media type (Image or Video)
3. Upload a cover file (PNG/JPG for images, MP4/AVI for video)
4. Upload a secret file or enter secret text
5. Enter a passphrase
6. Download the stego output (`.png` for images, `.mkv` for videos)

### Extraction

1. Click **Start Extraction**
2. Upload the stego file
3. Enter the same passphrase used during embedding
4. The original file is restored with its correct filename and extension

## Security

- **AES-256-CBC** encryption with SHA-256 key derivation
- **zlib compression** applied before encryption
- **Password-based random embedding** — without the passphrase, an attacker cannot determine where data is hidden
- Resistant to sequential-LSB steganalysis attacks

## Tech Stack

- **Backend:** Flask, Gunicorn
- **Steganography:** stegano (LSB), OpenCV, Pillow
- **Video Processing:** FFmpeg (via imageio-ffmpeg), FFV1 lossless codec
- **Encryption:** PyCryptodome (AES-256-CBC)
- **Frontend:** Bootstrap 5, Bootstrap Icons
