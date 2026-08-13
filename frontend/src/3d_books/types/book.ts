/**
 * 3D Book Showcase - Data Types
 */

export interface CoverLayout {
  /** Percentage ratio of back cover width relative to total image width (default: 0.425) */
  backRatio?: number;
  /** Percentage ratio of spine width relative to total image width (default: 0.15) */
  spineRatio?: number;
  /** Percentage ratio of front cover width relative to total image width (default: 0.425) */
  frontRatio?: number;
}

export interface BookData {
  id: string;
  title: string;
  author?: string;
  coverImage: string;
  pages: number;
  description?: string;
  coverLayout?: CoverLayout;
  /** Right-to-Left book orientation for Arabic/Hebrew books (Spine on the right side) */
  isRtl?: boolean;
  /** Optional attached PDF manuscript file or URL */
  pdfUrl?: string;
}

export interface ThicknessConfig {
  /** Minimum physical thickness in pixels (default: 10) */
  minThickness: number;
  /** Maximum physical thickness in pixels (default: 80) */
  maxThickness: number;
  /** Thickness in pixels per page (default: 0.12) */
  thicknessPerPage: number;
}

export interface ViewerControls {
  zoomIn: () => void;
  zoomOut: () => void;
  resetCamera: () => void;
  toggleAutoRotate: () => void;
  isAutoRotating: boolean;
  zoomLevel: number;
  openBook?: () => void;
}
