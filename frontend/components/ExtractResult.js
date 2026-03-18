import { Download, FileText, Unlock } from "lucide-react";
import { getDownloadUrl } from "../lib/api";

export default function ExtractResult({ data }) {
  const { is_text, media_type, message, download_filename, decrypted_size } = data;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Success header */}
      <div className="text-center mb-6">
        <Unlock className="w-16 h-16 mx-auto mb-3 text-green-500" />
        <h2 className="text-2xl font-extrabold text-slate-800">Extraction Complete</h2>
        <p className="text-slate-500">Secret data has been successfully decoded and decrypted</p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-6 max-w-md mx-auto">
        <div className="metric-box">
          <div className="metric-value">{decrypted_size ?? "?"}</div>
          <div className="metric-label">Decrypted Bytes</div>
        </div>
        <div className="metric-box">
          <div className="metric-value capitalize">{media_type}</div>
          <div className="metric-label">Source Type</div>
        </div>
      </div>

      {is_text ? (
        /* Text result */
        <div className="card p-6 mb-6">
          <h5 className="font-bold mb-3 flex items-center gap-2">
            <FileText className="w-5 h-5 text-accent" /> Extracted Message
          </h5>
          <div className="bg-slate-100 rounded-lg p-4 max-h-96 overflow-y-auto">
            <pre className="whitespace-pre-wrap break-words text-sm">{message}</pre>
          </div>
        </div>
      ) : (
        /* File result */
        <div className="card p-6 mb-6 text-center">
          <h5 className="font-bold mb-3 flex items-center justify-center gap-2">
            <Download className="w-5 h-5 text-accent" /> Extracted File
          </h5>
          <p className="text-slate-500 mb-4">
            {download_filename && download_filename !== "extracted_file.bin" ? (
              <>
                Original file <strong>{download_filename}</strong> has been restored successfully.
              </>
            ) : (
              "The extracted data has been saved as a binary file."
            )}
          </p>
          <a
            href={getDownloadUrl(download_filename)}
            className="btn-accent inline-block"
          >
            Download {download_filename}
          </a>
        </div>
      )}
    </div>
  );
}
