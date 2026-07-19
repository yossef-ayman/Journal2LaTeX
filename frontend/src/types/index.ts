export type JobStatus =
  | "CREATED"
  | "VALIDATING"
  | "ANALYZING_DOCUMENT"
  | "EXTRACTING_ASSETS"
  | "LOADING_TEMPLATE"
  | "RENDERING_LATEX"
  | "COMPILING"
  | "COMPLETED"
  | "FAILED";

export interface JobMetadata {
  job_id: string;
  status: JobStatus;
  progress: number;
  current_step: string;
  created_at: string;
  updated_at: string;
  paper_name: string;
  template_id?: string;
  template_name: string;
  template_version?: string;
  template_type?: string;
  output_pdf: string;
  output_tex: string;
  compile_success: boolean;
  errors: string[];
  warnings: string[];
}

export interface JobSummary {
  job_id: string;
  paper_name: string;
  status: JobStatus;
  progress: number;
  created_at: string;
  updated_at: string;
  template_name?: string;
}

export interface TemplateMetadata {
  template_id: string;
  name?: string;
  version: string;
  journal_title?: string;
  display_name?: string;
  journal_name?: string;
  upload_date?: string;
  description?: string;
  template_type?: "built_in" | "uploaded";
  engine?: string;
  publisher?: string;
  doi_prefix?: string;
  class_file: string;
  entry_file?: string;
  supported_features: {
    author_biographies: boolean;
    double_column: boolean;
    custom_headers: boolean;
  };
}

export interface FidelityReport {
  content_match_score: number;
  asset_match_score: number;
  layout_match_score: number;
  overall_fidelity_score: number;
  critical_missing_content: number;
  assets_validation: {
    total_original_assets: number;
    total_rendered_assets: number;
    matched_assets: number;
    missing_assets: string[];
    unexpected_assets: string[];
  };
  missing_assets: string[];
  missing_sections: string[];
  missing_figures: string[];
  missing_tables: string[];
  layout_warnings: string[];
  pdf_validations: {
    text_overflow_warnings: number;
    empty_pages_detected: boolean;
    latex_log_warnings: string[];
  };
}

export interface AssetReport {
  assets: Array<{
    asset_index: number;
    path: string;
    type: string;
    original_relationship_id: string;
    surrounding_paragraphs: string[];
    nearby_captions: string[];
    caption?: string;
    author?: string;
  }>;
  mappings?: Record<string, unknown>;
}

export interface DocumentStructure {
  title: string;
  authors: Array<{
    name: string;
    affiliation: string | null;
    email: string | null;
    photo_path: string | null;
  }>;
  abstract: string;
  keywords: string[];
  sections: Array<{
    title: string;
    level: number;
    blocks: Array<{
      type: string;
      content: Record<string, unknown>;
      block_index: number;
      original_order: number;
      source_location: string | null;
    }>;
  }>;
  references: string[];
  author_biographies: Array<{
    author_name: string;
    image_path: string | null;
    biography_text: string;
  }>;
}

export interface ConversionRequest {
  job_id: string;
  template_id?: string;
  template_name?: string;
}

export interface CompileRequest {
  job_id: string;
  template_id?: string;
  template_name?: string;
}
