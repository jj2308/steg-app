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

## Project Structure

```
project-root/
├── backend/
│   ├── main_app.py              # Flask REST API (no templates)
│   ├── requirements.txt         # Python dependencies
│   ├── Procfile                 # Gunicorn config for Render
│   ├── steganography/
│   │   ├── image_steg.py        # LSB image steganography with random embedding
│   │   └── video_steg.py        # FFV1 video steganography with metadata tags
│   ├── encryption/
│   │   └── aes_crypto.py        # AES-256-CBC encryption/decryption
│   ├── analysis/
│   │   ├── capacity.py          # Capacity estimation for images and videos
│   │   ├── integrity.py         # SHA-256 file hashing
│   │   └── metrics.py           # PSNR and MSE quality metrics
│   └── utils/
│       ├── file_handler.py      # File I/O and directory management
│       └── payload.py           # Payload packaging (preserves original filename)
├── frontend/
│   ├── pages/
│   │   ├── _app.js              # Next.js app wrapper
│   │   ├── index.js             # Home page
│   │   ├── embed.js             # Embed page
│   │   └── extract.js           # Extract page
│   ├── components/
│   │   ├── Layout.js            # Shared navbar + footer
│   │   ├── EmbedResult.js       # Embed result display
│   │   └── ExtractResult.js     # Extract result display
│   ├── lib/
│   │   └── api.js               # API helper (fetch + XHR with progress)
│   ├── styles/
│   │   └── globals.css          # Tailwind CSS globals
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── .env.example
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/embed` | Embed secret data into cover media |
| POST | `/api/extract` | Extract hidden data from stego media |
| GET | `/api/download/<filename>` | Download output file |
| POST | `/api/capacity` | Estimate cover media capacity |

## Installation & Running

### Backend

```bash
cd backend
pip install -r requirements.txt
python main_app.py
```

The API will be available at **http://localhost:5000**.

> **Note:** FFmpeg is bundled via `imageio-ffmpeg` — no system-level FFmpeg installation required.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at **http://localhost:3000**.

Create a `.env.local` file (or copy from `.env.example`):

```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## Deployment

### Backend (Render)

1. Push the `backend/` directory to a GitHub repo
2. Create a **New Web Service** on Render and connect your repo
3. **Root Directory:** `backend`
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `gunicorn main_app:app`
6. Add env var: `SECRET_KEY` = any random string

### Frontend (Vercel)

1. Push the `frontend/` directory to a GitHub repo (or the same repo)
2. Import the project on Vercel
3. **Root Directory:** `frontend`
4. **Framework Preset:** Next.js
5. Add env var: `NEXT_PUBLIC_API_URL` = your deployed backend URL (e.g. `https://your-api.onrender.com`)

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
