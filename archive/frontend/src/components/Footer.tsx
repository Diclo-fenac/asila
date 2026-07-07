export function Footer() {
  return (
    <footer className="w-full py-4 border-t border-aasila-border/30 bg-aasila-bg-main flex flex-col md:flex-row justify-between items-center px-8 z-10">
      <div className="font-mono text-[10px] tracking-widest text-aasila-muted uppercase">
        © 2026 AASILA SECURE SYSTEMS. CLASSIFIED CONTENT.
      </div>
      <div className="flex gap-6 mt-4 md:mt-0">
        <a className="font-mono text-[10px] tracking-widest text-aasila-muted hover:text-aasila-text transition-opacity opacity-80 hover:opacity-100 uppercase" href="#">Privacy Policy</a>
        <a className="font-mono text-[10px] tracking-widest text-aasila-muted hover:text-aasila-text transition-opacity opacity-80 hover:opacity-100 uppercase" href="#">Terms of Service</a>
        <a className="font-mono text-[10px] tracking-widest text-aasila-muted hover:text-aasila-text transition-opacity opacity-80 hover:opacity-100 uppercase" href="#">Security Disclosure</a>
      </div>
    </footer>
  )
}
