import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "@/config";
import { X, ExternalLink, BookOpen, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AuthorProfile {
  id?: string;
  name?: string;
  display_name?: string;
  works_count?: number;
  cited_by_count?: number;
  h_index?: number | null;
  i10_index?: number | null;
  affiliations?: string[];
  topics?: string[];
  scholar_url?: string;
  thumbnail?: string;
  source?: string;
}

interface Work {
  title: string;
  year?: number | null;
  doi?: string;
  url?: string;
  citation_count?: number;
}

interface AuthorProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  authorId?: string;
  authorName?: string;
}

export const AuthorProfileModal: React.FC<AuthorProfileModalProps> = ({
  isOpen,
  onClose,
  authorId = "",
  authorName = "",
}) => {
  const [provider, setProvider] = useState<"openalex" | "google_scholar">("openalex");
  const [profile, setProfile] = useState<AuthorProfile | null>(null);
  const [works, setWorks] = useState<Work[]>([]);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loadingProfile, setLoadingProfile] = useState<boolean>(false);
  const [loadingWorks, setLoadingWorks] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen && (authorId || authorName)) {
      setPage(1);
      fetchProfile(provider);
      fetchWorks(provider, 1);
    }
  }, [isOpen, authorId, authorName, provider]);

  if (!isOpen) return null;

  const cleanId = (authorId || authorName).replace("https://openalex.org/", "").replace("http://openalex.org/", "");

  const fetchProfile = async (prov: string) => {
    setLoadingProfile(true);
    try {
      const res = await fetch(`${API_BASE_URL}/authors/${encodeURIComponent(cleanId)}?provider=${prov}`);
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
      } else {
        setProfile(null);
      }
    } catch (err) {
      console.warn("Error fetching author profile:", err);
      setProfile(null);
    } finally {
      setLoadingProfile(false);
    }
  };

  const fetchWorks = async (prov: string, p: number) => {
    setLoadingWorks(true);
    try {
      const res = await fetch(`${API_BASE_URL}/authors/${encodeURIComponent(cleanId)}/works?page=${p}&per_page=10&provider=${prov}`);
      if (res.ok) {
        const data = await res.json();
        setWorks(data.results || []);
        const total = data.total_count || (data.results ? data.results.length : 0);
        setTotalPages(Math.ceil(total / 10) || 1);
      } else {
        setWorks([]);
      }
    } catch (err) {
      console.warn("Error fetching author works:", err);
      setWorks([]);
    } finally {
      setLoadingWorks(false);
    }
  };

  const displayName = profile?.display_name || profile?.name || authorName || authorId;
  const scholarUrl = profile?.scholar_url || `https://scholar.google.com/scholar?q=author:%22${encodeURIComponent(displayName)}%22`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl border border-gray-100 bg-white shadow-2xl overflow-hidden text-gray-900">
        
        {/* Header */}
        <div className="flex items-start justify-between border-b border-gray-100 p-6 bg-gray-50/50">
          <div className="space-y-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-xl font-bold tracking-tight text-gray-900">
                {loadingProfile ? "Loading profile..." : displayName}
              </h2>
              <a
                href={scholarUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-100 transition-colors"
              >
                <Search size={12} />
                <span>🎓 Google Scholar Profile</span>
                <ExternalLink size={10} />
              </a>
            </div>
            {profile?.affiliations && profile.affiliations.length > 0 && (
              <p className="text-xs text-gray-500">📍 {profile.affiliations.join(" • ")}</p>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Provider Selector Tabs */}
            <div className="flex items-center rounded-xl bg-gray-200/70 p-1 text-xs font-semibold">
              <button
                onClick={() => setProvider("openalex")}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  provider === "openalex" ? "bg-white text-gray-900 shadow-sm" : "text-gray-600 hover:text-gray-900"
                }`}
              >
                OpenAlex
              </button>
              <button
                onClick={() => setProvider("google_scholar")}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  provider === "google_scholar" ? "bg-white text-gray-900 shadow-sm" : "text-gray-600 hover:text-gray-900"
                }`}
              >
                🎓 Google Scholar
              </button>
            </div>

            <button
              onClick={onClose}
              className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* KPI Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 text-center">
              <div className="text-xl font-extrabold text-blue-600">
                {profile?.works_count !== undefined ? profile.works_count : "-"}
              </div>
              <div className="text-xs font-medium text-gray-500 mt-0.5">Publications</div>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 text-center">
              <div className="text-xl font-extrabold text-emerald-600">
                {profile?.cited_by_count !== undefined ? profile.cited_by_count : "-"}
              </div>
              <div className="text-xs font-medium text-gray-500 mt-0.5">Citations</div>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 text-center">
              <div className="text-xl font-extrabold text-violet-600">
                {profile?.h_index !== undefined && profile?.h_index !== null ? profile.h_index : "-"}
              </div>
              <div className="text-xs font-medium text-gray-500 mt-0.5">h-index</div>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 text-center">
              <div className="text-xl font-extrabold text-amber-600">
                {profile?.i10_index !== undefined && profile?.i10_index !== null ? profile.i10_index : "-"}
              </div>
              <div className="text-xs font-medium text-gray-500 mt-0.5">i10-index</div>
            </div>
          </div>

          {/* Research Topics */}
          {profile?.topics && profile.topics.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400">🏷️ Key Research Topics</h4>
              <div className="flex flex-wrap gap-1.5">
                {profile.topics.map((t, idx) => (
                  <span key={idx} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Publications Section */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-gray-900 border-b border-gray-100 pb-2 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <BookOpen size={16} className="text-blue-500" />
                Publications & Works ({provider === "google_scholar" ? "Google Scholar" : "OpenAlex"})
              </span>
              <span className="text-xs font-normal text-gray-400">Page {page} of {totalPages}</span>
            </h3>

            {loadingWorks ? (
              <div className="py-8 text-center text-xs text-gray-400">Loading publications...</div>
            ) : works.length === 0 ? (
              <div className="py-8 text-center text-xs text-gray-400">
                No publications returned from {provider === "google_scholar" ? "Google Scholar" : "OpenAlex"}.
              </div>
            ) : (
              <div className="space-y-2.5">
                {works.map((w, idx) => (
                  <div key={idx} className="rounded-xl border border-gray-100 bg-gray-50/40 p-4 space-y-1.5 hover:bg-gray-50 transition-colors">
                    <h4 className="text-sm font-bold text-gray-900 leading-snug">{w.title}</h4>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>📅 {w.year || "N/A"} • 📊 Citations: {w.citation_count || 0}</span>
                      {w.url && (
                        <a
                          href={w.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:underline"
                        >
                          View Article <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => {
                    const newP = page - 1;
                    setPage(newP);
                    fetchWorks(provider, newP);
                  }}
                >
                  <ChevronRight size={14} /> Previous
                </Button>
                <span className="text-xs text-gray-500 font-medium">Page {page} of {totalPages}</span>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= totalPages}
                  onClick={() => {
                    const newP = page + 1;
                    setPage(newP);
                    fetchWorks(provider, newP);
                  }}
                >
                  Next <ChevronLeft size={14} />
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthorProfileModal;
