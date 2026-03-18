import { Download, ShieldCheck, Film, BarChart3 } from "lucide-react";
import { getDownloadUrl } from "../lib/api";

export default function EmbedResult({ data }) {
  const {
    media_type,
    download_filename,
    file_hash,
    file_size,
    capacity,
    metrics,
    secret_name,
    secret_size,
    encrypted_size,
  } = data;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Success header */}
      <div className="text-center mb-6">
        <div className="text-6xl mb-3 text-green-500">&#10003;</div>
        <h2 className="text-2xl font-extrabold text-slate-800">Embedding Complete</h2>
        <p className="text-slate-500">
          Your secret data has been encrypted and hidden inside the {media_type}
        </p>
      </div>

      {/* Download card */}
      <div className="bg-gradient-to-r from-violet-100 to-indigo-100 rounded-2xl p-6 mb-6 text-center">
        <h5 className="font-bold mb-3 flex items-center justify-center gap-2">
          <Download className="w-5 h-5" /> Download Stego {media_type === "image" ? "Image" : "Video"}
        </h5>
        <a
          href={getDownloadUrl(download_filename)}
          className="btn-accent inline-block mb-3"
        >
          Download {download_filename}
        </a>
        <p className="text-slate-500 text-sm">File size: {file_size}</p>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="metric-box">
          <div className="metric-value">
            {media_type === "image"
              ? `${capacity?.width || "?"}×${capacity?.height || "?"}`
              : capacity?.total_frames || "?"}
          </div>
          <div className="metric-label">
            {media_type === "image" ? "Resolution" : "Total Frames"}
          </div>
        </div>
        <div className="metric-box">
          <div className="metric-value">{secret_size ?? "?"}</div>
          <div className="metric-label">Secret Bytes</div>
        </div>
        <div className="metric-box">
          <div className="metric-value">{encrypted_size ?? "?"}</div>
          <div className="metric-label">Encrypted Bytes</div>
        </div>
        <div className="metric-box">
          <div className="metric-value">
            {media_type === "image"
              ? `${capacity?.max_kb || "?"} KB`
              : `${capacity?.max_total_kb || "?"} KB`}
          </div>
          <div className="metric-label">Max Capacity</div>
        </div>
      </div>

      {/* PSNR Metrics (image only) */}
      {metrics?.psnr_db && (
        <div className="card p-6 mb-6">
          <h5 className="font-bold mb-3 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-accent" /> Quality Metrics
            <span className="bg-amber-400 text-black text-[0.65rem] font-bold px-2 py-0.5 rounded">
              RESEARCH
            </span>
          </h5>
          <div className="grid grid-cols-3 gap-3">
            <div className="metric-box">
              <div className="metric-value">{metrics.psnr_db} dB</div>
              <div className="metric-label">PSNR</div>
            </div>
            <div className="metric-box">
              <div className="metric-value">{metrics.mse}</div>
              <div className="metric-label">MSE</div>
            </div>
            <div className="metric-box">
              <div className="metric-value text-base">{metrics.quality}</div>
              <div className="metric-label">Quality Rating</div>
            </div>
          </div>
        </div>
      )}

      {/* Integrity hash */}
      <div className="card p-6 mb-6">
        <h5 className="font-bold mb-3 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-amber-500" /> Integrity Verification
          <span className="bg-amber-400 text-black text-[0.65rem] font-bold px-2 py-0.5 rounded">
            RESEARCH
          </span>
        </h5>
        <p className="text-sm text-slate-500 mb-2">
          SHA-256 hash of the stego file. Save this to verify the file has not been tampered with.
        </p>
        <div className="bg-slate-100 rounded-lg p-3">
          <code className="text-sm break-all select-all">{file_hash}</code>
        </div>
      </div>

      {/* Video details */}
      {media_type === "video" && capacity?.num_parts && (
        <div className="card p-6 mb-6">
          <h5 className="font-bold mb-3 flex items-center gap-2">
            <Film className="w-5 h-5 text-accent" /> Video Steganography Details
          </h5>
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 text-sm text-green-800">
            <strong>Extraction is simple:</strong> Upload this stego video and enter your passphrase.
            All metadata is embedded in the MKV file automatically.
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="metric-box">
              <div className="metric-value">FFV1</div>
              <div className="metric-label">Lossless Codec</div>
            </div>
            <div className="metric-box">
              <div className="metric-value">{capacity.num_parts}</div>
              <div className="metric-label">Chunks Embedded</div>
            </div>
            <div className="metric-box">
              <div className="metric-value">{capacity.frame_numbers?.length || "?"}</div>
              <div className="metric-label">Frames Used</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
