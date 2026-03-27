# Secure Steganography System For Data Transmission

Hide encrypted data inside images and videos using LSB steganography and AES-256 encryption. The project is split into a **Flask REST API backend** and a **Next.js (React) frontend** for independent deployment.

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

## Usage

### Embedding

1. Open the frontend and click **Start Embedding**
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

- **Backend:** Flask, Gunicorn, flask-cors
- **Frontend:** Next.js (React), Tailwind CSS, Lucide Icons
- **Steganography:** stegano (LSB), OpenCV, Pillow
- **Video Processing:** FFmpeg (via imageio-ffmpeg), FFV1 lossless codec
- **Encryption:** PyCryptodome (AES-256-CBC)
