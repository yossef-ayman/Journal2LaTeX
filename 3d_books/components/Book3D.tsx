import React, { useMemo } from 'react';
import type { ProcessedCoverRegions } from '../utils/coverMapping';
import { calculateBookThickness } from '../utils/thickness';

interface Book3DProps {
  processedRegions: ProcessedCoverRegions;
  pages: number;
  rotation: { x: number; y: number };
  zoom: number;
  heightPx?: number;
  isRtl?: boolean;
}

export const Book3D: React.FC<Book3DProps> = ({
  processedRegions,
  pages,
  rotation,
  zoom,
  heightPx = 360,
  isRtl = true, // Default to Arabic Right-To-Left (Spine on the Right side)
}) => {
  // 1. Calculate physical book dimensions based on page count & front cover ratio
  const bookHeight = heightPx;
  const bookWidth = Math.round(heightPx * (processedRegions.aspectRatio || 0.68));
  const bookThickness = useMemo(() => calculateBookThickness(pages), [pages]);

  // Half dimensions for CSS origin translation
  const halfW = bookWidth / 2;
  const halfH = bookHeight / 2;
  const halfT = bookThickness / 2;

  const { frontUrl, spineUrl, backUrl, paperTextureUrl } = processedRegions;

  // Every face is centered on the box's own center point BEFORE any
  // rotate/translateZ is applied. That way each face's default
  // transform-origin (its own center, 50% 50%) sits exactly on the box's
  // true hinge point, so rotating it swings it onto the correct surface
  // instead of flying off to a corner. Faces that share the box's full
  // width/height (front/back) don't strictly need this, but it's applied
  // uniformly for consistency and to survive future size tweaks.
  const centered = (w: number, h: number): React.CSSProperties => ({
    width: `${w}px`,
    height: `${h}px`,
    left: '50%',
    top: '50%',
    marginLeft: `-${w / 2}px`,
    marginTop: `-${h / 2}px`,
  });

  return (
    <div
      className="book-3d-box"
      style={{
        width: `${bookWidth}px`,
        height: `${bookHeight}px`,
        transform: `scale(${zoom}) rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
      }}
    >
      {/* Dynamic Floor Drop Shadow */}
      <div
        className="book-shadow"
        style={{
          width: `${bookWidth * 1.1}px`,
          height: `${bookThickness * 2.5 + 140}px`,
          marginLeft: `-${(bookWidth * 1.1) / 2}px`,
          transform: `translate3d(0, ${halfH + 15}px, 0) rotateX(90deg) scale(${1 + bookThickness / 120})`,
          opacity: Math.max(0.2, 0.85 - Math.abs(rotation.x) / 160),
        }}
      />

      {/* FRONT COVER FACE (+Z) */}
      <div
        className="book-face book-face-front"
        style={{
          ...centered(bookWidth, bookHeight),
          backgroundImage: `url(${frontUrl})`,
          transform: `translateZ(${halfT}px)`,
        }}
      >
        <div className="book-front-lighting" />
        <div className={isRtl ? "book-spine-crease-right" : "book-spine-crease-left"} />
      </div>

      {/* BACK COVER FACE (-Z) */}
      <div
        className="book-face book-face-back"
        style={{
          ...centered(bookWidth, bookHeight),
          backgroundImage: `url(${backUrl})`,
          transform: `rotateY(180deg) translateZ(${halfT}px)`,
        }}
      >
        <div className="book-front-lighting" style={{ transform: 'scaleX(-1)' }} />
        <div className={isRtl ? "book-spine-crease-left" : "book-spine-crease-right"} />
      </div>

      {/* SPINE FACE (Right side +X for Arabic RTL, Left side -X for LTR) */}
      <div
        className="book-face book-face-spine"
        style={{
          ...centered(bookThickness, bookHeight),
          backgroundImage: `url(${spineUrl})`,
          transform: isRtl
            ? `rotateY(90deg) translateZ(${halfW}px)` // Right spine for Arabic
            : `rotateY(-90deg) translateZ(${halfW}px)`, // Left spine for LTR
        }}
      >
        <div className="book-spine-lighting" />
      </div>

      {/* PAPER BLOCK FACE (Left side -X for Arabic RTL, Right side +X for LTR) */}
      <div
        className="book-face book-face-paper-side"
        style={{
          ...centered(bookThickness - 3, bookHeight - 6),
          backgroundImage: `url(${paperTextureUrl})`,
          transform: isRtl
            ? `rotateY(-90deg) translateZ(${halfW - 2}px)` // Paper pages on Left for Arabic
            : `rotateY(90deg) translateZ(${halfW - 2}px)`, // Paper pages on Right for LTR
        }}
      />

      {/* TOP PAPER BLOCK FACE (-Y) */}
      <div
        className="book-face book-face-paper-top"
        style={{
          ...centered(bookWidth - 4, bookThickness - 3),
          backgroundImage: `url(${paperTextureUrl})`,
          transform: `rotateX(90deg) translateZ(${halfH - 2}px)`,
        }}
      />

      {/* BOTTOM PAPER BLOCK FACE (+Y) */}
      <div
        className="book-face book-face-paper-bottom"
        style={{
          ...centered(bookWidth - 4, bookThickness - 3),
          backgroundImage: `url(${paperTextureUrl})`,
          transform: `rotateX(-90deg) translateZ(${halfH - 2}px)`,
        }}
      />
    </div>
  );
};