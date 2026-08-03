export interface Anchor {
  part: string;
  start: number;
  end: number;
}

export interface BaseNode {
  id: string;
  confidence: number;
  evidence: string[];
  anchor: Anchor | null;
}

export interface TextNode extends BaseNode {
  text: string;
}

export interface AuthorNode extends BaseNode {
  name: string;
  markers: string[];
  email: string | null;
  is_corresponding: boolean;
  affiliation_ids: string[];
}

export interface AffiliationNode extends BaseNode {
  text: string;
  marker: string;
}

export interface SectionBlock {
  id: string;
  kind: string;
  item: TextNode | null;
}

export interface SectionNode extends BaseNode {
  title: string;
  level: number;
  number: string | null;
  kind: string;
  content: SectionBlock[];
  children: SectionNode[];
}

export interface MetadataModel {
  title: TextNode | null;
  subtitle: TextNode | null;
  authors: AuthorNode[];
  affiliations: AffiliationNode[];
  emails: string[];
  keywords: string[];
  abstract: SectionNode | null;
  doi: string | null;
  received: string | null;
  accepted: string | null;
  published: string | null;
}

export interface ReferenceNode extends TextNode {
  marker: string | null;
  ordered: boolean;
}

export interface TableNode extends BaseNode {
  caption: TextNode | null;
  rows: number;
  columns: number;
  header_rows: number;
  cells: string[][];
}

export interface FigureNode extends BaseNode {
  caption: TextNode | null;
  relationship_ids: string[];
  width_emu: number | null;
  height_emu: number | null;
  inline: boolean;
}

export interface EquationNode extends TextNode {
  number: string | null;
  display: boolean;
}

export interface AnalyzeResult {
  source: string;
  metadata: MetadataModel;
  sections: SectionNode[];
  references: ReferenceNode[];
  tables: TableNode[];
  figures: FigureNode[];
  equations: EquationNode[];
  headers: TextNode[];
  footers: TextNode[];
  observations: Record<string, unknown>;
  warnings: string[];
}

export interface PluginDescription {
  name: string;
  title: string;
  description: string;
  enabled_by_default: boolean;
}

export type SuggestionStatus = "pending" | "accepted" | "rejected";

export interface Suggestion {
  id: string;
  node_id: string;
  kind: string;
  reason: string;
  source: string;
  confidence: number;
  status: SuggestionStatus;
  original: string;
  suggested: string;
  user_text: string | null;
  replacement: string;
}

export interface Note {
  plugin: string;
  message: string;
  node_id: string | null;
  severity: "info" | "warning";
}

export interface PluginRun {
  name: string;
  title: string;
  suggestions: number;
  notes: number;
  error: string | null;
}

export interface SuggestResult {
  suggestions: Suggestion[];
  notes: Note[];
  plugins: PluginRun[];
  counts: {
    suggestions: number;
    notes: number;
    failed_plugins: number;
  };
  source: string;
}

export interface SuggestionCounts {
  total: number;
  accepted: number;
  pending: number;
  rejected: number;
}

export interface DiffHunk {
  kind: "equal" | "delete" | "insert";
  text: string;
}

export interface EditDiff {
  hunks: DiffHunk[];
  words_removed: number;
  words_added: number;
  characters_changed: number;
}

export interface AppliedEdit {
  suggestion_id: string;
  node_id: string;
  part: string;
  span: [number, number];
  original: string;
  replacement: string;
  diff: EditDiff;
}

export interface RefusedEdit {
  suggestion_id: string;
  node_id: string;
  reason: string;
}

export interface PartImpact {
  name: string;
  original_bytes: number;
  new_bytes: number;
  delta: number;
  changed: boolean;
}

export interface PreviewResult {
  applied: AppliedEdit[];
  refused: RefusedEdit[];
  changed_parts: string[];
  counts: {
    applied: number;
    refused: number;
    parts_touched: number;
  };
  impact: PartImpact[];
  package: {
    parts_total: number;
    parts_untouched: number;
    parts_rewritten: number;
  };
  suggestions: SuggestionCounts;
}

export interface EngineStatus {
  available: boolean;
  phase: number;
  capabilities: Record<string, boolean>;
}
