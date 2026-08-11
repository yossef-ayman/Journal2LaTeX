import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { BookData, ViewerControls } from '../types/book';
import type { ProcessedCoverRegions } from '../utils/coverMapping';
import { sliceCoverSpread } from '../utils/coverMapping';
import { Book3D } from './Book3D';
import { BookControls } from './BookControls';
import { BookFallback } from './BookFallback';
import '../styles/book3d.css';

interface BookViewerProps {
  book: BookData;
  heightPx?: number;
  autoRotateDefault?: boolean;
}

export const BookViewer: React.FC<BookViewerProps> = ({
  book,
  heightPx = 290,
  autoRotateDefault = false,
}) => {
  const [processedRegions, setProcessedRegions] = useState<ProcessedCoverRegions | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Camera / Rotation State
  const [rotation, setRotation] = useState<{ x: number; y: number }>({ x: -12, y: -30 });
  const [zoom, setZoom] = useState<number>(1);
  const [isAutoRotating, setIsAutoRotating] = useState<boolean>(autoRotateDefault);

  // Interaction Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef<boolean>(false);
  const lastMouseRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const pinchDistRef = useRef<number | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // 1. Process & Slice Cover Artwork
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    sliceCoverSpread(book.coverImage, book.coverLayout)
      .then((regions) => {
        if (isMounted) {
          setProcessedRegions(regions);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to process book cover spread image.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [book.coverImage, book.coverLayout]);

  // 2. Auto Rotation Loop
  useEffect(() => {
    if (!isAutoRotating) return;

    const animate = () => {
      setRotation((prev) => ({
        x: prev.x,
        y: (prev.y + 0.4) % 360,
      }));
      animFrameRef.current = requestAnimationFrame(animate);
    };

    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [isAutoRotating]);

  // 3. Pointer & Mouse Drag Interaction Handlers
  const handlePointerDown = (e: React.PointerEvent) => {
    isDraggingRef.current = true;
    lastMouseRef.current = { x: e.clientX, y: e.clientY };
    if (isAutoRotating) setIsAutoRotating(false);
  };

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isDraggingRef.current) return;

      const deltaX = e.clientX - lastMouseRef.current.x;
      const deltaY = e.clientY - lastMouseRef.current.y;

      lastMouseRef.current = { x: e.clientX, y: e.clientY };

      setRotation((prev) => ({
        x: Math.max(-75, Math.min(75, prev.x - deltaY * 0.45)), // Clamp Pitch
        y: prev.y + deltaX * 0.5,
      }));
    },
    []
  );

  const handlePointerUp = () => {
    isDraggingRef.current = false;
  };

  // 4. Wheel Zoom Interaction Handler
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const zoomDelta = e.deltaY > 0 ? -0.08 : 0.08;
    setZoom((prev) => Math.max(0.5, Math.min(1.8, prev + zoomDelta)));
  }, []);

  // 5. Touch Pinch Zoom Interaction Handlers
  const handleTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const dist = Math.hypot(touch2.clientX - touch1.clientX, touch2.clientY - touch1.clientY);

      if (pinchDistRef.current !== null) {
        const delta = (dist - pinchDistRef.current) * 0.005;
        setZoom((prev) => Math.max(0.5, Math.min(1.8, prev + delta)));
      }
      pinchDistRef.current = dist;
    }
  };

  const handleTouchEnd = () => {
    pinchDistRef.current = null;
  };

  // 6. Camera Controls Callbacks
  const controls: ViewerControls = {
    zoomIn: () => setZoom((prev) => Math.min(1.8, prev + 0.15)),
    zoomOut: () => setZoom((prev) => Math.max(0.5, prev - 0.15)),
    resetCamera: () => {
      setRotation({ x: -12, y: -30 });
      setZoom(1);
    },
    toggleAutoRotate: () => setIsAutoRotating((prev) => !prev),
    isAutoRotating,
    zoomLevel: zoom,
  };

  if (error) {
    return <BookFallback message={`Error loading "${book.title}"`} error={error} />;
  }

  return (
    <div
      ref={containerRef}
      className="book-viewer-container"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
      onWheel={handleWheel}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {loading ? (
        <div className="book-status-overlay">
          <div className="book-spinner" />
          <div style={{ fontSize: '14px', fontWeight: 500 }}>Generating 3D Book Model...</div>
        </div>
      ) : (
        processedRegions && (
          <div className="book-stage">
            <Book3D
              processedRegions={processedRegions}
              pages={book.pages}
              rotation={rotation}
              zoom={zoom}
              heightPx={heightPx}
              isRtl={book.isRtl ?? true}
            />
          </div>
        )
      )}

      <BookControls controls={controls} />
    </div>
  );
};
