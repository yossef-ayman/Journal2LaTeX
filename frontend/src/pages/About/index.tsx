import { PageContainer } from "@/components/PageContainer";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, FileText, FileDown, Zap, Package, Layers, Settings, Code, Globe } from "lucide-react";

export default function AboutPage() {
  return (
    <PageContainer>
      {/* Hero */}
      <header className="rounded-2xl bg-gradient-to-br from-emerald-50/60 to-white p-8 shadow-sm border border-emerald-100">
        <div className="md:flex md:items-center md:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 flex items-center justify-center rounded-lg bg-gradient-to-br from-emerald-600 to-emerald-800 text-white shadow">
                <FileText size={20} />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Journal2LaTeX</h1>
                <p className="text-sm text-gray-600 mt-1">A professional pipeline for converting academic manuscripts from DOCX into publication-ready LaTeX and PDF.</p>
              </div>
            </div>
          </div>

          <div className="mt-4 md:mt-0 md:flex md:items-center gap-3">
            <Button size="sm" className="h-9 bg-emerald-600 text-white hover:bg-emerald-700" onClick={() => window.location.assign('/upload')}>
              <ArrowRight size={14} />
              Start a Conversion
            </Button>
            <Button variant="outline" size="sm" className="h-9" onClick={() => window.location.assign('/history')}>
              View History
            </Button>
          </div>
        </div>
      </header>

      {/* How it works */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-gray-900">How it works</h2>
        <p className="text-sm text-gray-600 max-w-2xl">Journal2LaTeX streamlines the conversion and publication workflow. Upload your manuscript, select a target template, and let the pipeline produce a clean LaTeX source and compiled PDF optimized for journals.</p>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { title: 'Upload', desc: 'Add your DOCX manuscript. The interface validates and previews the file.', icon: FileText },
            { title: 'Analyze', desc: 'The system extracts structure, figures, tables and references.' , icon: Zap },
            { title: 'Render LaTeX', desc: 'High-fidelity LaTeX source is generated respecting journal requirements.', icon: Code },
            { title: 'Compile & Download', desc: 'PDF is compiled and delivered with build logs and artifacts.', icon: FileDown },
          ].map((s) => (
            <Card key={s.title} className="transform transition-all hover:-translate-y-1 hover:shadow-md">
              <CardContent className="flex flex-col gap-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                    <s.icon size={16} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">{s.title}</h3>
                    <p className="text-xs text-gray-500">{s.desc}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-gray-900">Features</h2>
        <p className="text-sm text-gray-600 max-w-2xl">A focused set of capabilities designed for researchers, editors, and publishers.</p>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card className="overflow-hidden">
            <CardContent className="flex gap-4 items-start">
              <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                <FileText size={16} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">DOCX → LaTeX conversion</h3>
                <p className="text-xs text-gray-500">Robust structural conversion that preserves headings, tables, captions and references with minimal manual edits.</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex gap-4 items-start">
              <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                <FileDown size={16} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">PDF compilation</h3>
                <p className="text-xs text-gray-500">Automated LaTeX compilation with build logs and artifact management so outputs are reproducible and auditable.</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex gap-4 items-start">
              <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                <Layers size={16} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Journal template support</h3>
                <p className="text-xs text-gray-500">Target journals are supported through configurable templates to ensure format compliance.</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex gap-4 items-start">
              <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                <Package size={16} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">ZIP template management</h3>
                <p className="text-xs text-gray-500">Upload custom LaTeX ZIP packages. Versioned templates make it easy to maintain journal styles.</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex gap-4 items-start">
              <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                <Settings size={16} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Automatic formatting</h3>
                <p className="text-xs text-gray-500">Consistent typographic and structural formatting across documents, removing manual tedious fixes.</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex gap-4 items-start">
              <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                <Zap size={16} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Visual Fidelity Engine (Experimental)</h3>
                <p className="text-xs text-gray-500">A layout-aware validation engine that compares the original document and rendered PDF. Marked experimental while under refinement.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Technology stack */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-gray-900">Technology Stack</h2>
        <p className="text-sm text-gray-600">Built with a modern, fast stack focused on reliability and developer productivity.</p>
        <div className="flex flex-wrap gap-3 mt-2">
          {['React', 'TypeScript', 'Vite', 'FastAPI', 'Python', 'Pandoc', 'LaTeX'].map((t) => (
            <div key={t} className="rounded-lg border border-gray-100 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm">
              <div className="flex items-center gap-2">
                <Globe size={14} className="text-emerald-600" />
                <span>{t}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Statistics */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-gray-900">At a glance</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <Card>
            <CardContent>
              <p className="text-3xl font-bold text-emerald-700">12,432</p>
              <p className="text-sm text-gray-500">Documents converted</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-3xl font-bold text-emerald-700">48</p>
              <p className="text-sm text-gray-500">Templates supported</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-3xl font-bold text-emerald-700">7</p>
              <p className="text-sm text-gray-500">Pipeline stages</p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* FAQ */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-gray-900">Frequently asked questions</h2>
        <div className="space-y-2">
          <details className="group rounded-lg border border-gray-100 p-4">
            <summary className="flex items-center justify-between cursor-pointer text-sm font-semibold">
              How long does conversion typically take?
              <span className="text-xs text-gray-400">Approx. 15–60s</span>
            </summary>
            <div className="mt-2 text-sm text-gray-600">
              Typical conversions complete within a minute for standard manuscripts. Complex documents with many figures or large embedded media may take longer.
            </div>
          </details>

          <details className="group rounded-lg border border-gray-100 p-4">
            <summary className="flex items-center justify-between cursor-pointer text-sm font-semibold">
              Can I use custom LaTeX templates?
              <span className="text-xs text-gray-400">Yes</span>
            </summary>
            <div className="mt-2 text-sm text-gray-600">
              Upload your ZIP package containing the LaTeX template. The system supports multiple template versions and lets you select a target when converting.
            </div>
          </details>

          <details className="group rounded-lg border border-gray-100 p-4">
            <summary className="flex items-center justify-between cursor-pointer text-sm font-semibold">
              What happens if compilation fails?
              <span className="text-xs text-gray-400">Logs provided</span>
            </summary>
            <div className="mt-2 text-sm text-gray-600">
              Build logs and the generated LaTeX source are available to diagnose failures. Use the logs to adjust the template or the source and retry compilation.
            </div>
          </details>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-6 border-t border-gray-100 pt-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Journal2LaTeX</h3>
            <p className="text-xs text-gray-500">A professional conversion pipeline for academic publishing.</p>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span>© {new Date().getFullYear()} Journal2LaTeX</span>
            <a className="text-emerald-600 hover:underline" href="/settings">Settings</a>
            <a className="text-emerald-600 hover:underline" href="/history">History</a>
          </div>
        </div>
      </footer>
    </PageContainer>
  );
}
