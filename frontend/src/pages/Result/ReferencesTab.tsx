import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";
import { Bookmark, Search, ExternalLink, User } from "lucide-react";
import AuthorProfileModal from "@/components/AuthorProfileModal";

interface ReferenceObj {
  id?: number | string;
  text?: string;
  original_text?: string;
  title?: string;
  authors?: (string | { name?: string; display_name?: string; author_id?: string })[];
  doi?: string;
  confidence?: number;
  citation_count?: number;
  match_status?: string;
}

interface ReferencesTabProps {
  doc: {
    references?: (string | ReferenceObj)[];
    enriched_references?: ReferenceObj[];
  };
}

export function ReferencesTab({ doc }: ReferencesTabProps) {
  const [selectedAuthorId, setSelectedAuthorId] = useState("");
  const [selectedAuthorName, setSelectedAuthorName] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);

  const rawRefs = doc.enriched_references || doc.references || [];

  if (!rawRefs || rawRefs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>References</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={<Bookmark size={48} strokeWidth={1} />}
            title="No references found"
            description="No references were detected in the document."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>References & Enriched Citations ({rawRefs.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            {rawRefs.map((item, i) => {
              const refObj: ReferenceObj = typeof item === "string" ? { text: item } : item;
              const text = refObj.original_text || refObj.text || "";
              const cleanSearch = text.replace(/^(?:\[\d+\]|\(\d+\)|\d+\.)\s*/, "").trim();
              const googleUrl = `https://www.google.com/search?q=${encodeURIComponent(cleanSearch)}`;
              const scholarUrl = `https://scholar.google.com/scholar?q=${encodeURIComponent(cleanSearch)}`;

              return (
                <div key={i} className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 space-y-2 hover:bg-gray-50 transition-colors">
                  <div className="text-sm font-medium text-gray-800 leading-relaxed">
                    <span className="font-bold text-gray-900 me-2">[{refObj.id || i + 1}]</span>
                    {text}
                  </div>

                  {/* Metadata Badges */}
                  <div className="flex items-center gap-2 flex-wrap text-xs">
                    {refObj.match_status === "matched" && (
                      <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-700 border border-emerald-200">
                        ✓ Matched ({Math.round((refObj.confidence || 0) * 100)}%)
                      </span>
                    )}
                    {refObj.citation_count !== undefined && refObj.citation_count > 0 && (
                      <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 font-semibold text-blue-700 border border-blue-200">
                        📊 {refObj.citation_count} Citations
                      </span>
                    )}
                  </div>

                  {/* Clickable Authors */}
                  {Array.isArray(refObj.authors) && refObj.authors.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap pt-1">
                      {refObj.authors.map((a, idx) => {
                        const aName = typeof a === "object" ? (a.name || a.display_name || "") : String(a);
                        const aId = typeof a === "object" ? (a.author_id || "") : aName;
                        return (
                          <button
                            key={idx}
                            onClick={() => {
                              setSelectedAuthorId(aId);
                              setSelectedAuthorName(aName);
                              setIsModalOpen(true);
                            }}
                            className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-white px-2.5 py-0.5 text-xs text-gray-700 hover:border-blue-300 hover:text-blue-600 transition-colors cursor-pointer"
                          >
                            <User size={10} /> {aName}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* External Links */}
                  <div className="flex items-center gap-2 pt-2 border-t border-gray-200/60 text-xs">
                    {refObj.doi && (
                      <a
                        href={`https://doi.org/${refObj.doi}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-blue-600 hover:underline font-semibold"
                      >
                        🔗 DOI <ExternalLink size={10} />
                      </a>
                    )}
                    <a
                      href={googleUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-gray-600 hover:text-gray-900 font-medium"
                    >
                      <Search size={12} /> Google Search
                    </a>
                    <a
                      href={scholarUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-blue-600 hover:underline font-semibold"
                    >
                      🎓 Google Scholar <ExternalLink size={10} />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <AuthorProfileModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        authorId={selectedAuthorId}
        authorName={selectedAuthorName}
      />
    </>
  );
}
