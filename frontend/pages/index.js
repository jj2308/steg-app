import Link from "next/link";
import Head from "next/head";
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Image,
  Video,
  Lock,
  BarChart3,
  FileText,
  FileArchive,
  Layers,
  ArrowRight,
} from "lucide-react";

export default function HomePage() {
  return (
    <>
      <Head>
        <title>MultiSteg — Multi-Media Steganography System</title>
      </Head>

      {/* Hero */}
      <div className="text-center mb-10">
        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-800 tracking-tight mb-3">
          Multi-Media Steganography
        </h1>
        <p className="text-slate-500 text-lg mb-1">
          Hide encrypted data inside images and videos
        </p>
        <p className="text-slate-400">
          AES-256 encryption &middot; LSB embedding &middot; Research-grade analysis
        </p>
      </div>

      {/* Main actions */}
      <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto mb-12">
        <div className="card p-6 text-center flex flex-col">
          <ArrowDownToLine className="w-12 h-12 mx-auto mb-3 text-blue-500" />
          <h4 className="font-bold text-lg mb-2">Embed Secret Data</h4>
          <p className="text-slate-500 text-sm mb-6 flex-1">
            Encrypt and hide text or files inside an image or video using AES-256
            encryption and LSB steganography.
          </p>
          <Link href="/embed" className="btn-accent inline-block">
            <span className="flex items-center justify-center gap-2">
              <Lock className="w-4 h-4" /> Start Embedding
            </span>
          </Link>
        </div>

        <div className="card p-6 text-center flex flex-col">
          <ArrowUpFromLine className="w-12 h-12 mx-auto mb-3 text-green-500" />
          <h4 className="font-bold text-lg mb-2">Extract Hidden Data</h4>
          <p className="text-slate-500 text-sm mb-6 flex-1">
            Decode and decrypt secret data from stego media. Requires the original
            passphrase used during embedding.
          </p>
          <Link href="/extract" className="btn-outline-accent inline-block">
            <span className="flex items-center justify-center gap-2">
              <Lock className="w-4 h-4" /> Start Extraction
            </span>
          </Link>
        </div>
      </div>

      {/* System Capabilities */}
      <h5 className="text-center text-slate-400 font-bold uppercase text-sm tracking-widest mb-4">
        System Capabilities
      </h5>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        <div className="card p-4 text-center">
          <Image className="w-10 h-10 mx-auto mb-2 text-cyan-500" />
          <h6 className="font-bold text-sm mb-1">Image Steganography</h6>
          <p className="text-slate-500 text-xs">PNG &amp; JPG support via LSB embedding</p>
        </div>
        <div className="card p-4 text-center">
          <Video className="w-10 h-10 mx-auto mb-2 text-cyan-500" />
          <h6 className="font-bold text-sm mb-1">Video Steganography</h6>
          <p className="text-slate-500 text-xs">Frame-based LSB with FFmpeg rebuild</p>
        </div>
        <div className="card p-4 text-center">
          <Lock className="w-10 h-10 mx-auto mb-2 text-amber-500" />
          <h6 className="font-bold text-sm mb-1">AES-256 Encryption</h6>
          <p className="text-slate-500 text-xs">Password-protected with zlib compression</p>
        </div>
        <div className="card p-4 text-center">
          <BarChart3 className="w-10 h-10 mx-auto mb-2 text-red-500" />
          <h6 className="font-bold text-sm mb-1">Research Analysis</h6>
          <span className="inline-block bg-amber-400 text-black text-[0.6rem] font-bold px-1.5 py-0.5 rounded mb-1">
            RESEARCH
          </span>
          <p className="text-slate-500 text-xs">Capacity estimation, PSNR, integrity check</p>
        </div>
      </div>

      {/* Workflow diagram */}
      <div className="max-w-4xl mx-auto">
        <div className="card p-6">
          <h5 className="font-bold mb-4 text-center">System Workflow</h5>
          <div className="flex items-center justify-between gap-2 overflow-x-auto">
            <div className="metric-box flex-1 min-w-[80px]">
              <FileText className="w-8 h-8 mx-auto text-blue-500" />
              <div className="mt-2 font-bold text-xs">Secret Data</div>
            </div>
            <ArrowRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
            <div className="metric-box flex-1 min-w-[80px]">
              <FileArchive className="w-8 h-8 mx-auto text-amber-500" />
              <div className="mt-2 font-bold text-xs">Compress</div>
            </div>
            <ArrowRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
            <div className="metric-box flex-1 min-w-[80px]">
              <Lock className="w-8 h-8 mx-auto text-red-500" />
              <div className="mt-2 font-bold text-xs">AES-256 Encrypt</div>
            </div>
            <ArrowRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
            <div className="metric-box flex-1 min-w-[80px]">
              <Layers className="w-8 h-8 mx-auto text-green-500" />
              <div className="mt-2 font-bold text-xs">LSB Embed</div>
            </div>
            <ArrowRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
            <div className="metric-box flex-1 min-w-[80px]">
              <Image className="w-8 h-8 mx-auto text-cyan-500" />
              <div className="mt-2 font-bold text-xs">Stego Media</div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
