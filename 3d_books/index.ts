/**
 * 3D Book Showcase Module
 * 
 * Reusable 3D physical book showcase component system completely self-contained inside `3d_books`.
 */

export { BookViewer } from './components/BookViewer';
export { Book3D } from './components/Book3D';
export { BookControls } from './components/BookControls';
export { BookFallback } from './components/BookFallback';
export { DemoShowcase } from './components/DemoShowcase';

export { sliceCoverSpread } from './utils/coverMapping';
export { calculateBookThickness, DEFAULT_THICKNESS_CONFIG } from './utils/thickness';

export type { BookData, CoverLayout, ThicknessConfig, ViewerControls } from './types/book';
export { DEMO_BOOKS } from './data/demoBooks';

