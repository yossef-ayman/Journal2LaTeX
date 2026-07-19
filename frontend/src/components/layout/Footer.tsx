export function Footer() {
  return (
    <footer className="flex items-center justify-between border-t bg-card px-6 py-3">
      <p className="text-xs text-muted-foreground">
        &copy; {new Date().getFullYear()} Journal2LaTeX
      </p>
      <p className="text-xs text-muted-foreground">
        Academic DOCX to LaTeX Conversion System
      </p>
    </footer>
  );
}
