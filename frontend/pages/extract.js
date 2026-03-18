import { useState } from "react";
import Head from "next/head";
import Link from "next/link";
import { Image, Video, Upload, Key, Unlock, Eye, EyeOff, Info } from "lucide-react";
import { extractData } from "../lib/api";
import ExtractResult from "../components/ExtractResult";

export default function ExtractPage() {
  const [mediaType, setMediaType] = useState("image");
  const [stegoFile, setStegoFile] = useState(null);
  const [passphrase, setPassphrase] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);
    setProgress(0);

    if (!stegoFile) { setError("Please upload a stego file."); return; }
    if (!passphrase || passphrase.length < 4) { setError("Passphrase must be at least 4 characters."); return; }

    const formData = new FormData();
    formData.append("media_type", mediaType);
    formData.append("stego_file", stegoFile);
    formData.append("passphrase", passphrase);

    setLoading(true);
    try {
      const data = await extractData(formData, setProgress);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <>
        <Head><title>Extraction Result — MultiSteg</title></Head>
        <ExtractResult data={result} />
        <div className="text-center mt-6 flex items-center justify-center gap-3">
          <Link href="/" className="px-4 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-100 text-sm font-medium">Home</Link>
          <Link href="/embed" className="px-4 py-2 border border-blue-400 rounded-lg text-blue-600 hover:bg-blue-50 text-sm font-medium">Embed</Link>
          <button onClick={() => setResult(null)} className="px-4 py-2 border border-green-400 rounded-lg text-green-600 hover:bg-green-50 text-sm font-medium">Extract More</button>
        </div>
      </>
    );
  }

  return (
    <>
      <Head><title>Extract — MultiSteg</title></Head>

      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-extrabold text-slate-800 flex items-center justify-center gap-2">
            <Unlock className="w-6 h-6 text-green-500" /> Extract Hidden Data
          </h2>
          <p className="text-slate-500">Decode and decrypt secret data from stego media</p>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Step 1: Media type */}
          <div className="form-section mb-5">
            <h5 className="font-bold mb-3 flex items-center gap-2 text-slate-700">
              <span className="bg-green-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">1</span>
              Choose Media Type
            </h5>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setMediaType("image")}
                className={`py-4 rounded-xl border-2 font-semibold flex flex-col items-center gap-1 transition-colors ${
                  mediaType === "image" ? "border-green-500 bg-green-50 text-green-700" : "border-slate-200 text-slate-500 hover:border-slate-300"
                }`}
              >
                <Image className="w-8 h-8" />
                Image
              </button>
              <button
                type="button"
                onClick={() => setMediaType("video")}
                className={`py-4 rounded-xl border-2 font-semibold flex flex-col items-center gap-1 transition-colors ${
                  mediaType === "video" ? "border-green-500 bg-green-50 text-green-700" : "border-slate-200 text-slate-500 hover:border-slate-300"
                }`}
              >
                <Video className="w-8 h-8" />
                Video
              </button>
            </div>
          </div>

          {/* Step 2: Stego file */}
          <div className="form-section mb-5">
            <h5 className="font-bold mb-3 flex items-center gap-2 text-slate-700">
              <span className="bg-green-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">2</span>
              Upload Stego Media
            </h5>
            <label className="file-upload-area block">
              <Upload className="w-8 h-8 mx-auto text-slate-400 mb-1" />
              {stegoFile ? (
                <p className="text-sm">
                  <strong>{stegoFile.name}</strong>{" "}
                  ({(stegoFile.size / (1024 * 1024)).toFixed(2)} MB)
                </p>
              ) : (
                <>
                  <p className="text-slate-500 text-sm mb-1">Click to upload the stego file containing hidden data</p>
                  <p className="text-slate-400 text-xs">PNG for images &middot; MKV for videos</p>
                </>
              )}
              <input
                type="file"
                className="hidden"
                accept={
                  mediaType === "image"
                    ? "image/png,image/jpeg"
                    : "video/x-matroska,.mkv"
                }
                onChange={(e) => setStegoFile(e.target.files[0] || null)}
              />
            </label>
          </div>

          {/* Video info note */}
          {mediaType === "video" && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-5 text-sm text-blue-800 flex items-start gap-2">
              <Info className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>
                Upload the <strong>.mkv</strong> stego video generated during embedding.
                All extraction metadata is embedded in the video file — you only need the passphrase.
              </span>
            </div>
          )}

          {/* Step 3: Passphrase */}
          <div className="form-section mb-5">
            <h5 className="font-bold mb-3 flex items-center gap-2 text-slate-700">
              <span className="bg-green-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">3</span>
              Decryption Passphrase
            </h5>
            <div className="flex">
              <span className="flex items-center px-3 bg-slate-100 border border-r-0 border-slate-300 rounded-l-lg">
                <Key className="w-4 h-4 text-slate-500" />
              </span>
              <input
                type={showPass ? "text" : "password"}
                className="flex-1 border border-slate-300 py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                placeholder="Enter the passphrase used during embedding"
                value={passphrase}
                onChange={(e) => setPassphrase(e.target.value)}
                minLength={4}
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
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-5 text-sm">
              {error}
            </div>
          )}

          {/* Progress bar */}
          {loading && progress > 0 && (
            <div className="mb-5">
              <div className="bg-slate-200 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-accent h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-slate-400 mt-1 text-center">Uploading... {progress}%</p>
            </div>
          )}

          {/* Submit */}
          <div className="text-center">
            <button
              type="submit"
              disabled={loading}
              className="btn-accent text-lg px-8 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Processing...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Unlock className="w-4 h-4" /> Extract &amp; Decrypt
                </span>
              )}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
