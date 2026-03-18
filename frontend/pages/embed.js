import { useState, useEffect, useCallback, useRef } from "react";
import Head from "next/head";
import Link from "next/link";
import { Image, Video, Upload, FileUp, Key, Lock, Eye, EyeOff, ShieldCheck, HardDrive, AlertTriangle } from "lucide-react";
import { embedData, checkCapacity, generateJobId, checkEmbedProgress } from "../lib/api";
import EmbedResult from "../components/EmbedResult";

export default function EmbedPage() {
  const [mediaType, setMediaType] = useState("image");
  const [coverFile, setCoverFile] = useState(null);
  const [capacity, setCapacity] = useState(null);      // { max_bytes, ... }
  const [capLoading, setCapLoading] = useState(false);
  const [capError, setCapError] = useState("");
  const [secretMode, setSecretMode] = useState("text");
  const [secretText, setSecretText] = useState("");
  const [secretFile, setSecretFile] = useState(null);
  const [passphrase, setPassphrase] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState("");        // current processing stage
  const [frameProgress, setFrameProgress] = useState(null); // {frames_processed, total_frames, elapsed}
  const [error, setError] = useState("");
  const pollRef = useRef(null);

  const fmtTime = (secs) => {
    if (!secs || secs < 0) return "--:--";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  const STAGE_LABELS = {
    uploading:  "Uploading file...",
    analyzing:  "Analyzing video...",
    embedding:  "Embedding data into frames...",
    encoding:   "Encoding output video...",
    finalizing: "Finalizing...",
    done:       "Complete",
    processing: "Processing...",
    queued:     "Waiting to process...",
  };

  // --- Capacity fetch on cover file change ---
  const handleCoverFile = useCallback(async (file) => {
    setCoverFile(file);
    setCapacity(null);
    setCapError("");
    setError("");
    if (!file) return;
    setCapLoading(true);
    try {
      const data = await checkCapacity(file, mediaType);
      setCapacity(data);
    } catch (err) {
      setCapError(err.message);
    } finally {
      setCapLoading(false);
    }
  }, [mediaType]);

  // Re-fetch capacity if media type changes while a file is selected
  useEffect(() => {
    if (coverFile) handleCoverFile(coverFile);
  }, [mediaType]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Secret data size (estimated) ---
  const secretSize = secretMode === "file"
    ? (secretFile ? secretFile.size : 0)
    : new Blob([secretText]).size;

  // Encryption adds ~1.45x overhead (zlib + AES padding + base64)
  const estimatedEncryptedSize = secretSize > 0 ? Math.ceil(secretSize * 1.45) + 64 : 0;
  const maxBytes = capacity?.max_bytes ?? null;
  const overCapacity = maxBytes !== null && estimatedEncryptedSize > 0 && estimatedEncryptedSize > maxBytes;

  // --- Dynamic frame calculation (video only) ---
  const bitsPerFrame = capacity?.bits_per_frame ?? 0;
  const totalFrames = capacity?.total_frames ?? 0;
  const framesNeeded = (bitsPerFrame > 0 && estimatedEncryptedSize > 0)
    ? Math.min(Math.max(1, Math.ceil((estimatedEncryptedSize * 8) / bitsPerFrame)), totalFrames)
    : 0;

  const fmtSize = (bytes) => {
    if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + " MB";
    if (bytes >= 1024) return (bytes / 1024).toFixed(1) + " KB";
    return bytes + " B";
  };

  const handlePassphraseChange = (value) => {
    setPassphrase(value);
    // Always clear error when the user edits the passphrase field — avoids
    // stale "Password too weak" messages lingering after the password becomes valid.
    setError("");
  };
  const [result, setResult] = useState(null);

  // --- Password strength logic ---
  const getPassChecks = (pw) => ({
    length: pw.length >= 8,
    upper: /[A-Z]/.test(pw),
    lower: /[a-z]/.test(pw),
    number: /[0-9]/.test(pw),
    special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?`~]/.test(pw),
  });

  const passChecks = getPassChecks(passphrase);
  const passScore = Object.values(passChecks).filter(Boolean).length; // 0-5
  const passValid = passScore === 5;

  const strengthLabel =
    passphrase.length === 0 ? null
    : passScore <= 2 ? "Weak"
    : passScore <= 4 ? "Medium"
    : "Strong";

  const strengthColor =
    passScore <= 2 ? "bg-red-500"
    : passScore <= 4 ? "bg-amber-500"
    : "bg-green-500";

  const strengthTextColor =
    passScore <= 2 ? "text-red-600"
    : passScore <= 4 ? "text-amber-600"
    : "text-green-600";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);
    setProgress(0);

    if (!coverFile) { setError("Please upload a cover file."); return; }
    if (!passValid) {
      setError("Password too weak. Please use at least 8 characters including uppercase, lowercase, number, and special character.");
      return;
    }
    if (secretMode === "text" && !secretText.trim()) { setError("Please enter secret text."); return; }
    if (secretMode === "file" && !secretFile) { setError("Please upload a secret file."); return; }
    if (overCapacity) {
      setError("The selected carrier file is too small to hold this data. Please upload a larger file.");
      return;
    }

    const formData = new FormData();
    formData.append("media_type", mediaType);
    formData.append("cover_file", coverFile);
    formData.append("passphrase", passphrase);
    if (secretMode === "text") {
      formData.append("secret_text", secretText);
    } else {
      formData.append("secret_file", secretFile);
    }

    setLoading(true);
    setStage("uploading");

    // For video embeds, generate a job ID and poll progress
    const jobId = mediaType === "video" ? generateJobId() : "";
    if (jobId) formData.append("job_id", jobId);

    // Start polling backend for stage + frame progress (video only)
    if (jobId) {
      pollRef.current = setInterval(async () => {
        try {
          const info = await checkEmbedProgress(jobId);
          if (info.stage && info.stage !== "queued") {
            setStage(info.stage);
          }
          if (info.frames_processed != null) {
            setFrameProgress({
              frames_processed: info.frames_processed,
              total_frames: info.total_frames,
              elapsed: info.elapsed,
            });
          }
        } catch {}
      }, 1000);
    }

    try {
      const data = await embedData(formData, (pct) => {
        setProgress(pct);
        if (pct >= 100 && !jobId) setStage("processing");
        if (pct >= 100 && jobId && stage === "uploading") setStage("analyzing");
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      setLoading(false);
      setStage("");
      setFrameProgress(null);
    }
  };

  if (result) {
    return (
      <>
        <Head><title>Embedding Result — MultiSteg</title></Head>
        <EmbedResult data={result} />
        <div className="text-center mt-6 flex items-center justify-center gap-3">
          <Link href="/" className="px-4 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-100 text-sm font-medium">Home</Link>
          <button onClick={() => setResult(null)} className="px-4 py-2 border border-blue-400 rounded-lg text-blue-600 hover:bg-blue-50 text-sm font-medium">Embed More</button>
          <Link href="/extract" className="px-4 py-2 border border-green-400 rounded-lg text-green-600 hover:bg-green-50 text-sm font-medium">Extract</Link>
        </div>
      </>
    );
  }

  return (
    <>
      <Head><title>Embed — MultiSteg</title></Head>

      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-extrabold text-slate-800 flex items-center justify-center gap-2">
            <Lock className="w-6 h-6 text-blue-500" /> Embed Secret Data
          </h2>
          <p className="text-slate-500">Encrypt and hide your data inside an image or video</p>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Step 1: Media type */}
          <div className="form-section mb-5">
            <h5 className="font-bold mb-3 flex items-center gap-2 text-slate-700">
              <span className="bg-blue-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">1</span>
              Choose Media Type
            </h5>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setMediaType("image")}
                className={`py-4 rounded-xl border-2 font-semibold flex flex-col items-center gap-1 transition-colors ${
                  mediaType === "image" ? "border-blue-500 bg-blue-50 text-blue-700" : "border-slate-200 text-slate-500 hover:border-slate-300"
                }`}
              >
                <Image className="w-8 h-8" />
                Image Steganography
              </button>
              <button
                type="button"
                onClick={() => setMediaType("video")}
                className={`py-4 rounded-xl border-2 font-semibold flex flex-col items-center gap-1 transition-colors ${
                  mediaType === "video" ? "border-blue-500 bg-blue-50 text-blue-700" : "border-slate-200 text-slate-500 hover:border-slate-300"
                }`}
              >
                <Video className="w-8 h-8" />
                Video Steganography
              </button>
            </div>
          </div>

          {/* Step 2: Cover file */}
          <div className="form-section mb-5">
            <h5 className="font-bold mb-3 flex items-center gap-2 text-slate-700">
              <span className="bg-blue-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">2</span>
              Upload Cover Media
            </h5>
            <label className="file-upload-area block">
              <Upload className="w-8 h-8 mx-auto text-slate-400 mb-1" />
              {coverFile ? (
                <p className="text-sm">
                  <strong>{coverFile.name}</strong>{" "}
                  ({(coverFile.size / (1024 * 1024)).toFixed(2)} MB)
                </p>
              ) : (
                <>
                  <p className="text-slate-500 text-sm mb-1">Click to upload cover image or video</p>
                  <p className="text-slate-400 text-xs">
                    Supported: PNG, JPG for images &middot; MP4, MOV for videos
                  </p>
                </>
              )}
              <input
                type="file"
                className="hidden"
                accept={
                  mediaType === "image"
                    ? "image/png,image/jpeg"
                    : "video/mp4,video/quicktime,video/x-msvideo"
                }
                onChange={(e) => handleCoverFile(e.target.files[0] || null)}
              />
            </label>

            {/* Capacity indicator */}
            {capLoading && (
              <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                <span className="w-3.5 h-3.5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                Estimating capacity...
              </div>
            )}
            {capError && (
              <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-xs text-amber-700">
                {capError} You can still attempt embedding.
              </div>
            )}
            {capacity && !capLoading && (
              <div className="mt-3 bg-slate-50 border border-slate-200 rounded-lg p-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
                  <HardDrive className="w-4 h-4 text-blue-500" /> Carrier Capacity
                </div>
                <div className="grid grid-cols-3 gap-3 text-center text-xs">
                  <div>
                    <div className="font-bold text-slate-800 text-sm">{fmtSize(maxBytes)}</div>
                    <div className="text-slate-500">Max capacity</div>
                  </div>
                  {estimatedEncryptedSize > 0 && (
                    <div>
                      <div className={`font-bold text-sm ${overCapacity ? "text-red-600" : "text-slate-800"}`}>
                        {fmtSize(estimatedEncryptedSize)}
                      </div>
                      <div className="text-slate-500">Est. encrypted size</div>
                    </div>
                  )}
                  {estimatedEncryptedSize > 0 && maxBytes !== null && (
                    <div>
                      <div className={`font-bold text-sm ${overCapacity ? "text-red-600" : "text-green-600"}`}>
                        {overCapacity ? "- " + fmtSize(estimatedEncryptedSize - maxBytes) : fmtSize(maxBytes - estimatedEncryptedSize)}
                      </div>
                      <div className="text-slate-500">{overCapacity ? "Over limit" : "Remaining"}</div>
                    </div>
                  )}
                </div>
                {/* Capacity bar */}
                {estimatedEncryptedSize > 0 && maxBytes > 0 && (
                  <div className="mt-2">
                    <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          overCapacity ? "bg-red-500" : "bg-green-500"
                        }`}
                        style={{ width: `${Math.min((estimatedEncryptedSize / maxBytes) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
                {overCapacity && (
                  <div className="mt-2 flex items-center gap-1.5 text-xs text-red-600 font-medium">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    The selected carrier file is too small to hold this data. Please upload a larger file.
                  </div>
                )}
                {/* Video-specific metadata */}
                {capacity.total_frames != null && (
                  <div className="mt-2 pt-2 border-t border-slate-200">
                    <div className="grid grid-cols-2 gap-3 text-center text-xs text-slate-500">
                      <div>{capacity.frame_width}&times;{capacity.frame_height} px</div>
                      <div>{capacity.total_frames} frames{capacity.fps ? ` @ ${capacity.fps} fps` : ""}</div>
                    </div>
                    {framesNeeded > 0 && (
                      <div className="mt-2 grid grid-cols-3 gap-3 text-center text-xs">
                        <div>
                          <div className="font-bold text-slate-700">{totalFrames}</div>
                          <div className="text-slate-500">Available</div>
                        </div>
                        <div>
                          <div className="font-bold text-blue-600">{framesNeeded}</div>
                          <div className="text-slate-500">Required</div>
                        </div>
                        <div>
                          <div className="font-bold text-green-600">{framesNeeded}</div>
                          <div className="text-slate-500">Will be used</div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Step 3: Secret data */}
          <div className="form-section mb-5">
            <h5 className="font-bold mb-3 flex items-center gap-2 text-slate-700">
              <span className="bg-blue-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">3</span>
              Secret Data
            </h5>
            <div className="flex border-b border-slate-200 mb-4">
              <button
                type="button"
                onClick={() => setSecretMode("text")}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  secretMode === "text" ? "border-accent text-accent" : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                Text
              </button>
              <button
                type="button"
                onClick={() => setSecretMode("file")}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  secretMode === "file" ? "border-accent text-accent" : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                File
              </button>
            </div>
            {secretMode === "text" ? (
              <textarea
                className="w-full border border-slate-300 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                rows={4}
                placeholder="Type or paste your secret message here..."
                value={secretText}
                onChange={(e) => setSecretText(e.target.value)}
              />
            ) : (
              <label className="file-upload-area block">
                <FileUp className="w-7 h-7 mx-auto text-slate-400 mb-1" />
                {secretFile ? (
                  <p className="text-sm">
                    <strong>{secretFile.name}</strong>{" "}
                    ({(secretFile.size / (1024 * 1024)).toFixed(2)} MB)
                  </p>
                ) : (
                  <p className="text-slate-500 text-sm">Click to upload a secret file</p>
                )}
                <input
                  type="file"
                  className="hidden"
                  onChange={(e) => setSecretFile(e.target.files[0] || null)}
                />
              </label>
            )}
          </div>

          {/* Step 4: Passphrase */}
          <div className="form-section mb-5">
            <h5 className="font-bold mb-3 flex items-center gap-2 text-slate-700">
              <span className="bg-blue-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">4</span>
              Encryption Passphrase
            </h5>
            <div className="flex">
              <span className="flex items-center px-3 bg-slate-100 border border-r-0 border-slate-300 rounded-l-lg">
                <Key className="w-4 h-4 text-slate-500" />
              </span>
              <input
                type={showPass ? "text" : "password"}
                className="flex-1 border border-slate-300 py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                placeholder="Enter a strong passphrase"
                value={passphrase}
                onChange={(e) => handlePassphraseChange(e.target.value)}
                minLength={8}
                required
              />
              <button
                type="button"
                onClick={() => setShowPass(!showPass)}
                className="flex items-center px-3 bg-slate-100 border border-l-0 border-slate-300 rounded-r-lg"
              >
                {showPass ? <EyeOff className="w-4 h-4 text-slate-500" /> : <Eye className="w-4 h-4 text-slate-500" />}
              </button>
            </div>

            {/* Live strength indicator */}
            {passphrase.length > 0 && (
              <div className="mt-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" /> Password Strength
                  </span>
                  <span className={`text-xs font-bold ${strengthTextColor}`}>{strengthLabel}</span>
                </div>
                <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${strengthColor}`}
                    style={{ width: `${(passScore / 5) * 100}%` }}
                  />
                </div>
                <ul className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <li className={passChecks.length ? "text-green-600" : "text-slate-400"}>
                    {passChecks.length ? "\u2713" : "\u2717"} At least 8 characters
                  </li>
                  <li className={passChecks.upper ? "text-green-600" : "text-slate-400"}>
                    {passChecks.upper ? "\u2713" : "\u2717"} Uppercase letter
                  </li>
                  <li className={passChecks.lower ? "text-green-600" : "text-slate-400"}>
                    {passChecks.lower ? "\u2713" : "\u2717"} Lowercase letter
                  </li>
                  <li className={passChecks.number ? "text-green-600" : "text-slate-400"}>
                    {passChecks.number ? "\u2713" : "\u2717"} Number
                  </li>
                  <li className={passChecks.special ? "text-green-600" : "text-slate-400"}>
                    {passChecks.special ? "\u2713" : "\u2717"} Special character (!@#$...)
                  </li>
                </ul>
              </div>
            )}

            <p className="text-xs text-slate-400 mt-2">
              AES-256-CBC encryption with zlib compression. Remember this passphrase for extraction.
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-5 text-sm">
              {error}
            </div>
          )}

          {/* Progress / stage indicator */}
          {loading && (
            <div className="mb-5">
              {progress > 0 && progress < 100 && (
                <div className="mb-2">
                  <div className="bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-accent h-2 rounded-full transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-400 mt-1 text-center">Uploading... {progress}%</p>
                </div>
              )}
              {(progress >= 100 || stage !== "uploading") && stage && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                  {/* Frame-level progress bar */}
                  {frameProgress && frameProgress.total_frames > 0 ? (() => {
                    const fp = frameProgress;
                    const pct = Math.min((fp.frames_processed / fp.total_frames) * 100, 100);
                    const encFps = fp.elapsed > 0 ? (fp.frames_processed / fp.elapsed) : 0;
                    const remaining = fp.total_frames - fp.frames_processed;
                    const eta = encFps > 0 ? remaining / encFps : 0;
                    return (
                      <>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                            {STAGE_LABELS[stage] || "Processing..."}
                          </span>
                          <span className="text-sm font-bold text-accent">{pct.toFixed(1)}%</span>
                        </div>
                        <div className="bg-slate-200 rounded-full h-2.5 overflow-hidden mb-3">
                          <div
                            className="bg-accent h-2.5 rounded-full transition-all duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                          <div className="text-slate-500">Progress</div>
                          <div className="text-right font-medium text-slate-700">{fp.frames_processed.toLocaleString()} / {fp.total_frames.toLocaleString()} frames</div>
                          <div className="text-slate-500">Encoding speed</div>
                          <div className="text-right font-medium text-slate-700">{encFps > 0 ? encFps.toFixed(1) : "--"} fps</div>
                          <div className="text-slate-500">Elapsed time</div>
                          <div className="text-right font-medium text-slate-700">{fmtTime(fp.elapsed)}</div>
                          <div className="text-slate-500">Estimated remaining time</div>
                          <div className="text-right font-medium text-blue-600">~{fmtTime(eta)}</div>
                        </div>
                      </>
                    );
                  })() : (
                    <div className="flex items-center justify-center gap-2 text-sm text-slate-600 font-medium">
                      <span className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                      {STAGE_LABELS[stage] || "Processing..."}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Submit */}
          <div className="text-center">
            <button
              type="submit"
              disabled={loading || overCapacity}
              className="btn-accent text-lg px-8 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {stage === "uploading" ? "Uploading..." : STAGE_LABELS[stage] || "Processing..."}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Lock className="w-4 h-4" /> Encrypt &amp; Embed
                </span>
              )}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
