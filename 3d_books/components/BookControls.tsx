import React from 'react';
import type { ViewerControls } from '../types/book';

interface BookControlsProps {
  controls: ViewerControls;
}

export const BookControls: React.FC<BookControlsProps> = ({ controls }) => {
  return (
    <div className="book-controls-bar" aria-label="3D Book Controls">
      <button
        className="book-control-btn"
        onClick={controls.zoomIn}
        title="Zoom In"
        aria-label="Zoom In"
        type="button"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
          <line x1="11" y1="8" x2="11" y2="14" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
      </button>

      <button
        className="book-control-btn"
        onClick={controls.zoomOut}
        title="Zoom Out"
        aria-label="Zoom Out"
        type="button"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
      </button>

      <button
        className="book-control-btn"
        onClick={controls.resetCamera}
        title="Reset Camera"
        aria-label="Reset Camera"
        type="button"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
          <path d="M3 3v5h5" />
        </svg>
      </button>

      <button
        className={`book-control-btn ${controls.isAutoRotating ? 'active' : ''}`}
        onClick={controls.toggleAutoRotate}
        title={controls.isAutoRotating ? 'Pause Auto-Rotate' : 'Start Auto-Rotate'}
        aria-label="Toggle Auto-Rotate"
        type="button"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21.5 2v6h-6" />
          <path d="M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
        </svg>
      </button>
    </div>
  );
};
