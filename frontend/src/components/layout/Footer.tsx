export function Footer() {
  return (
    <footer className="flex items-center justify-between border-t border-gray-100 bg-white px-6 py-3 shrink-0">
      <p className="text-xs text-gray-400 font-medium">
        © {new Date().getFullYear()} Journal2LaTeX
      </p>
      <p className="text-xs text-gray-400 hidden sm:block">
        Academic DOCX → LaTeX Conversion Engine
      </p>
    </footer>
  );
}
