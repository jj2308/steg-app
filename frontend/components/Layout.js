import Link from "next/link";
import { Shield, Home, ArrowDownToLine, ArrowUpFromLine } from "lucide-react";

export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col bg-slate-100">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-gradient-to-r from-nav-start to-nav-end shadow-lg">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-white font-extrabold text-lg tracking-wide">
            <Shield className="w-5 h-5" />
            MultiSteg
          </Link>
          <div className="flex items-center gap-1">
            <Link href="/" className="text-white/80 hover:text-white px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors">
              <Home className="w-4 h-4" /> Home
            </Link>
            <Link href="/embed" className="text-white/80 hover:text-white px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors">
              <ArrowDownToLine className="w-4 h-4" /> Embed
            </Link>
            <Link href="/extract" className="text-white/80 hover:text-white px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors">
              <ArrowUpFromLine className="w-4 h-4" /> Extract
            </Link>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8 md:py-10">
        {children}
      </main>

      {/* Footer */}
      <footer className="text-center py-6 text-slate-400 text-sm">
        <p className="mb-1">&copy; 2026 <strong>MultiSteg</strong> — Multi-Media Steganography Research System</p>
        <p>AES-256 Encryption &middot; LSB Steganography &middot; Image &amp; Video Support</p>
      </footer>
    </div>
  );
}
