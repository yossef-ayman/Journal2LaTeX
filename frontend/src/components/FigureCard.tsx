import { cn } from "@/utils/cn";
import { ImageIcon } from "lucide-react";

interface FigureCardProps {
  caption: string;
  filename: string;
  sourceLocation: string | null;
  assetPath?: string;
  className?: string;
}

export function FigureCard({
  caption,
  filename,
  sourceLocation,
  assetPath,
  className,
}: FigureCardProps) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border bg-card",
        className,
      )}
    >
      <div className="flex h-40 items-center justify-center bg-muted">
        {assetPath ? (
          <img
            src={assetPath}
            alt={caption || filename}
            className="h-full w-full object-contain p-2"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
              (e.target as HTMLImageElement).nextElementSibling?.classList.remove("hidden");
            }}
          />
        ) : null}
        <div
          className={assetPath ? "hidden" : "flex flex-col items-center gap-2 text-muted-foreground/50"}
        >
          <ImageIcon size={32} />
          <span className="text-xs">{filename}</span>
        </div>
      </div>
      <div className="space-y-1 p-3">
        <p className="line-clamp-2 text-xs font-medium text-foreground">
          {caption || "No caption"}
        </p>
        <p className="truncate text-[10px] text-muted-foreground">
          {filename}
        </p>
        {sourceLocation && (
          <p className="truncate text-[10px] text-muted-foreground">
            {sourceLocation}
          </p>
        )}
      </div>
    </div>
  );
}
