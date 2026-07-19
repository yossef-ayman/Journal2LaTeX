import { cn } from "@/utils/cn";
import { ImageOff, User } from "lucide-react";

interface BiographyCardProps {
  authorName: string;
  imagePath: string | null;
  biographyText: string;
  className?: string;
}

export function BiographyCard({
  authorName,
  imagePath,
  biographyText,
  className,
}: BiographyCardProps) {
  return (
    <div
      className={cn(
        "flex gap-5 rounded-lg border bg-card p-5",
        className,
      )}
    >
      <div className="flex h-24 w-20 shrink-0 items-center justify-center overflow-hidden rounded-md bg-muted">
        {imagePath ? (
          <img
            src={imagePath}
            alt={authorName}
            className="h-full w-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
              (e.target as HTMLImageElement).nextElementSibling?.classList.remove("hidden");
            }}
          />
        ) : null}
        <div className={imagePath ? "hidden" : "flex items-center justify-center"}>
          <ImageOff size={24} className="text-muted-foreground/50" />
        </div>
      </div>
      <div className="min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          <User size={14} className="text-muted-foreground" />
          <h4 className="text-sm font-semibold text-foreground">
            {authorName}
          </h4>
        </div>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {biographyText}
        </p>
      </div>
    </div>
  );
}
