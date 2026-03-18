const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

// ---------------------------------------------------------------------------
// Friendly error mapping (frontend safety net)
// ---------------------------------------------------------------------------

const FRIENDLY_MAP = [
  [/too large/i, "The uploaded file is too large. Please use a smaller file."],
  [/not enough space/i, "The selected file does not have enough space to hide the data. Please use a larger file."],
  [/not supported/i, null],          // already friendly — pass through
  [/passphrase is incorrect/i, null],
  [/password too weak/i, null],
  [/corrupt/i, "The file appears to be corrupted or incomplete. Please upload a valid file."],
  [/truncated/i, "The file appears to be corrupted or incomplete. Please upload a valid file."],
  [/codec|ffmpeg|identify image/i, "The file could not be processed. Please upload a valid media file."],
  [/ECONNREFUSED|ERR_CONNECTION|Failed to fetch/i,
   "Cannot connect to the server. Please make sure the backend is running and try again."],
  [/timeout|timed out/i, "The request timed out. The file may be too large or the server is busy. Please try again."],
  [/Network error/i, "Cannot connect to the server. Please check your internet connection and try again."],
];

function friendlyMessage(raw, fallback) {
  if (!raw) return fallback;
  for (const [pattern, replacement] of FRIENDLY_MAP) {
    if (pattern.test(raw)) {
      return replacement || raw; // null means the message is already friendly
    }
  }
  // If the message looks technical (has stack-trace artifacts, Python class names, etc.), hide it
  if (/Traceback|File "|\.py|Error:|Exception/i.test(raw)) {
    return fallback;
  }
  return raw;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

function apiRequest(url, formData, onProgress, fallbackMsg) {
  const xhr = new XMLHttpRequest();

  return new Promise((resolve, reject) => {
    xhr.open("POST", url);
    xhr.timeout = 5 * 60 * 1000; // 5 minutes

    if (onProgress) {
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      });
    }

    xhr.onload = () => {
      try {
        const data = JSON.parse(xhr.responseText);
        if (xhr.status >= 400) {
          reject(new Error(friendlyMessage(data.error, fallbackMsg)));
        } else {
          resolve(data);
        }
      } catch {
        if (xhr.status === 413) {
          reject(new Error("The uploaded file is too large. Maximum size is 200 MB."));
        } else {
          reject(new Error(fallbackMsg));
        }
      }
    };

    xhr.ontimeout = () =>
      reject(new Error("The request timed out. The file may be too large or the server is busy. Please try again."));

    xhr.onerror = () =>
      reject(new Error("Cannot connect to the server. Please make sure the backend is running and try again."));

    xhr.send(formData);
  });
}

export function embedData(formData, onProgress) {
  return apiRequest(
    `${API}/api/embed`,
    formData,
    onProgress,
    "Something went wrong while hiding the data. Please try again or use a different file."
  );
}

export function extractData(formData, onProgress) {
  return apiRequest(
    `${API}/api/extract`,
    formData,
    onProgress,
    "Something went wrong during extraction. Please check your file and passphrase and try again."
  );
}

export async function checkCapacity(file, mediaType) {
  const formData = new FormData();
  formData.append("cover_file", file);
  formData.append("media_type", mediaType);
  return apiRequest(
    `${API}/api/capacity`,
    formData,
    null,
    "Could not estimate capacity for this file."
  );
}

export function generateJobId() {
  return crypto.randomUUID ? crypto.randomUUID()
    : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
      });
}

export async function checkEmbedProgress(jobId) {
  try {
    const res = await fetch(`${API}/api/embed/progress/${encodeURIComponent(jobId)}`);
    return await res.json();
  } catch {
    return { stage: "processing" };
  }
}

export function getDownloadUrl(filename) {
  return `${API}/api/download/${encodeURIComponent(filename)}`;
}

export async function checkHealth() {
  try {
    const res = await fetch(`${API}/api/health`);
    const data = await res.json();
    return data.status === "ok";
  } catch {
    return false;
  }
}
