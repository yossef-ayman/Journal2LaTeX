import { diffWords, type DiffHunk } from "@/utils/diff";

function DiffText({ hunks }: { hunks: DiffHunk[] }) {
  return (
    <>
      {hunks.map((hunk, i) => {
        if (hunk.kind === "delete") {
          return (
            <del
              key={i}
              className="rounded bg-red-50 px-0.5 text-red-600 decoration-red-400/70"
            >
              {hunk.text}
            </del>
          );
        }
        if (hunk.kind === "insert") {
          return (
            <ins
              key={i}
              className="rounded bg-emerald-50 px-0.5 text-emerald-700 no-underline"
            >
              {hunk.text}
            </ins>
          );
        }
        return <span key={i}>{hunk.text}</span>;
      })}
    </>
  );
}

interface WordDiffProps {
  original: string;
  suggested: string;
}

/** Inline word-level diff between the original and the suggested text. */
export function WordDiff({ original, suggested }: WordDiffProps) {
  const hunks = diffWords(original, suggested);
  return (
    <div className="space-y-2">
      <div className="rounded-lg bg-red-50/50 border border-red-100 px-3 py-2">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-red-500 mb-1">
          Original
        </p>
        <p className="text-sm leading-relaxed text-gray-700 break-words whitespace-pre-wrap">
          <DiffText
            hunks={hunks.filter((h) => h.kind !== "insert")}
          />
        </p>
      </div>
      <div className="rounded-lg bg-emerald-50/50 border border-emerald-100 px-3 py-2">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 mb-1">
          Suggested
        </p>
        <p className="text-sm leading-relaxed text-gray-800 break-words whitespace-pre-wrap">
          <DiffText hunks={hunks.filter((h) => h.kind !== "delete")} />
        </p>
      </div>
    </div>
  );
}
