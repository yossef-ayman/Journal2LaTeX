# Document Visual Fidelity Engine Architecture (Phase 1 & Phase 2 Complete)

The **Visual Fidelity Engine** is an independent, document-agnostic backend module located in `backend/app/fidelity/`. Its purpose is to evaluate both page-level and region-level visual/structural layout similarity between arbitrary source documents (DOCX, PDF, or Images) and target generated LaTeX PDFs.

---

## 1. Package Architecture

```
backend/app/fidelity/
├── __init__.py           # Package exports (FidelityEngine, schemas, configuration models)
├── exceptions.py         # Exception hierarchy (FidelityError, RenderingError, ConfigurationError...)
├── schemas.py            # Pydantic schemas (RenderingConfig, FidelityConfig, NormalizedPage...)
├── engine.py             # Main facade orchestrator (FidelityEngine with Dependency Injection)
├── image_converter.py    # Preprocessing, DPI normalization, and alignment (ImageConverter)
├── page_matcher.py       # Page pairing and alignment strategy (PageMatcher)
├── visual_diff.py        # Heatmap, difference map, and bounding box generator (VisualDiffEngine)
├── report_generator.py   # FidelityReport aggregation & visual issue compiler
├── renderers/            # Modular DocumentRenderer implementations
│   ├── __init__.py
│   ├── base.py           # DocumentRenderer interface
│   ├── pdf.py            # PDFRenderer (PyMuPDF / fitz)
│   ├── docx.py           # DocxRenderer (MS Word COM / LibreOffice reference PDF)
│   └── image.py          # ImageRenderer (raw image files/folders)
└── metrics/              # Extensible SimilarityMetric plugins
    ├── __init__.py
    ├── base.py           # SimilarityMetric interface (compute & compute_region)
    ├── registry.py       # MetricRegistry (loader, sequence ordering, fault tolerance)
    ├── ssim.py           # SSIMMetric plugin stub
    ├── pixel_diff.py     # PixelDifferenceMetric plugin stub
    ├── layout.py         # LayoutMetric plugin stub
    ├── ocr.py            # OCRMetric plugin stub (On-Demand)
    └── feature.py        # FeatureMatchingMetric plugin stub
```

---

## 2. Component Dependency Graph

```
                   ┌─────────────────┐
                   │ FidelityEngine  │
                   └────────┬────────┘
                            │ (Constructor Injection)
       ┌────────────────────┼────────────────────┬────────────────────┐
       ▼                    ▼                    ▼                    ▼
┌──────────────┐    ┌────────────────┐   ┌───────────────┐   ┌─────────────────┐
│  Renderers   │    │ ImageConverter │   │  PageMatcher  │   │ MetricRegistry  │
└──────┬───────┘    └────────────────┘   └───────────────┘   └────────┬────────┘
       │                                                              │
       ├─► PDFRenderer                                                ├─► SSIMMetric
       ├─► DocxRenderer                                               ├─► PixelDiffMetric
       └─► ImageRenderer                                              ├─► LayoutMetric
                                                                      ├─► OCRMetric
                                                                      └─► CustomPlugins...
```

---

## 3. Pipeline Execution Flow

1. **Configuration Validation**: User passes `FidelityConfig`. Model validators reject invalid settings (DPI <= 0, invalid hex colors, out-of-bounds thresholds) raising `ConfigurationError`.
2. **Document Rendering**: `FidelityEngine` selects appropriate `DocumentRenderer` for source and target files, generating `List[NormalizedPage]`.
3. **Page Alignment**: `PageMatcher.match_pages()` maps source pages to target pages (`List[PageMatch]`).
4. **Canvas Normalization**: `ImageConverter.normalize_pair()` pads or scales smaller page images to matching canvas dimensions (`width x height`) using `RenderingConfig.alignment_mode`.
5. **Metric Execution**: `MetricRegistry` runs active, enabled plugins in `order` priority sequence, capturing `execution_time_ms` and trapping plugin errors gracefully without breaking execution.
6. **Visual Artifact Generation**: `VisualDiffEngine` constructs difference maps, heatmaps, and bounding boxes.
7. **Report Compilation**: `FidelityReportGenerator` compiles metrics, per-region breakdowns, and semantic visual issues into `FidelityReport`.

---

## 4. Canonical DOCX Source Representation

> [!IMPORTANT]
> For DOCX manuscript inputs, rendering is performed through an intermediate reference PDF generated via **Microsoft Word COM automation** (on Windows) or **LibreOffice Headless** (other platforms).
> This reference PDF serves as the **canonical visual representation** of the Word document, which is rasterized via `PDFRenderer` into `NormalizedPage` objects.

---

## 5. Developer Extension Guide

### How to Add a Custom Similarity Metric Plugin

1. Subclass `SimilarityMetric` in `backend/app/fidelity/metrics/`:

```python
from app.fidelity.metrics import SimilarityMetric
from app.fidelity.schemas import NormalizedPage, MetricScore, FidelityConfig

class LPIPSMetric(SimilarityMetric):
    @property
    def name(self) -> str:
        return "lpips"

    @property
    def order(self) -> int:
        return 40  # Sequence priority (lower numbers execute earlier)

    def is_enabled(self, config: FidelityConfig) -> bool:
        return config.enabled_metrics is None or self.name in config.enabled_metrics

    def compute(self, source_page: NormalizedPage, target_page: NormalizedPage) -> MetricScore:
        # Calculate perceptual similarity score (0.0 to 1.0)
        score = 0.95
        return MetricScore(metric_name=self.name, score=score, details={})
```

2. Register the metric into `FidelityEngine`:

```python
from app.fidelity import FidelityEngine
from my_metrics import LPIPSMetric

engine = FidelityEngine()
engine.register_metric(LPIPSMetric())
```

---

### How to Add a New Document Renderer

1. Subclass `DocumentRenderer` in `backend/app/fidelity/renderers/`:

```python
from typing import List
from app.fidelity.renderers import DocumentRenderer
from app.fidelity.schemas import NormalizedPage, SourceType

class HTMLRenderer(DocumentRenderer):
    @property
    def supported_source_type(self) -> SourceType:
        return SourceType.HTML

    def render(self, document_path: str, output_dir: str, dpi: int = 150) -> List[NormalizedPage]:
        # Render HTML pages to images...
        return []
```

2. Inject into `FidelityEngine`:

```python
engine = FidelityEngine(renderers=[HTMLRenderer(), PDFRenderer(), DocxRenderer()])
```
