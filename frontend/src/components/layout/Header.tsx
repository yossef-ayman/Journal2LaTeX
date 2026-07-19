import { useAppStore } from "@/store/useAppStore";
import { Menu, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useIsMobile } from "@/hooks/use-mobile";

export function Header() {
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const isMobile = useIsMobile();

  return (
    <header className="flex h-14 items-center gap-4 border-b bg-card px-4">
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleSidebar}
        aria-label="Toggle sidebar"
        className="shrink-0"
      >
        <Menu size={18} />
      </Button>

      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary md:hidden">
          <FileText size={16} className="text-primary-foreground" />
        </div>
        <div className="flex flex-col">
          <h1 className="text-sm font-semibold leading-tight text-foreground">
            Journal2LaTeX
          </h1>
          <p className="text-xs leading-tight text-muted-foreground">
            Academic DOCX → LaTeX Converter
          </p>
        </div>
      </div>

      <div className="flex-1" />

      {!isMobile && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Ready</span>
          <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
        </div>
      )}
    </header>
  );
}
