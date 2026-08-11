# 3D Book Showcase (`3d_books`)

A complete, self-contained, production-ready **3D Book Showcase system** for displaying realistic 3D physical hardcover books directly inside any web application.

---

## 📖 System Overview

The `3d_books` module takes a 3-spread artwork image `[ BACK COVER | SPINE | FRONT COVER ]` along with page count metadata and renders a physical 3D hardcover book in real perspective space.

- **Realistic 3D Geometry**: Renders 6 physical box faces (Front Cover, Back Cover, Spine, Top Paper Block, Right Paper Block, Bottom Paper Block).
- **Physical Page Thickness**: Automatically computes exact physical thickness in pixels based on page count (`pages`).
- **Spread Cover Slicing**: Slices the cover spread artwork automatically without distortion, stretching, or mirroring.
- **Interactive Studio Lighting & Camera**:
  - Drag / Swipe to rotate (Pitch & Yaw clamped smoothly).
  - Scroll Wheel / Pinch gesture to Zoom.
  - Floating controls bar: Zoom (+ / -), Reset camera, and Auto-rotate toggle.
- **Zero External Dependencies**: Works purely with browser-native HTML5 Canvas and CSS 3D Matrix Transforms without requiring external CDNs or extra npm packages.

---

## 🛠️ Folder Structure

```text
3d_books/
├── components/
│   ├── Book3D.tsx         # Physical 6-faced 3D book box renderer
│   ├── BookViewer.tsx     # Canvas container & touch/mouse camera manager
│   ├── BookControls.tsx   # Floating UI controls overlay (zoom/reset/rotate)
│   ├── BookFallback.tsx   # Graceful fallback display for errors
│   └── DemoShowcase.tsx   # Library demonstration component
├── utils/
│   ├── thickness.ts       # Mathematical page-to-thickness clamping calculator
│   └── coverMapping.ts    # Spread image slicing & procedural paper texture engine
├── types/
│   └── book.ts            # TypeScript interfaces & types
├── data/
│   └── demoBooks.ts       # Sample books with procedural cover spreads
├── styles/
│   └── book3d.css         # Modern dark studio styling & lighting gradients
├── index.ts               # Public entry point exports
└── README.md              # Technical documentation
```

---

## 🚀 How to Use `Book3D` / `BookViewer`

### 1. Basic Single Book Viewer Integration

```tsx
import React from 'react';
import { BookViewer, BookData } from './3d_books';

const myBook: BookData = {
  id: 'book-101',
  title: 'Design Patterns',
  author: 'Erich Gamma',
  pages: 416,
  coverImage: '/path/to/cover-spread.jpg', // Spread image: [ BACK | SPINE | FRONT ]
};

export const BookPage = () => {
  return (
    <div style={{ width: '100%', maxWidth: '800px', margin: '0 auto' }}>
      <BookViewer book={myBook} heightPx={320} autoRotateDefault={false} />
    </div>
  );
};
```

---

## 🖼️ Cover Image Requirement

The input image **MUST** be a complete cover spread layout containing 3 sections in order:

```text
┌─────────────────┬─────────┬─────────────────┐
│                 │         │                 │
│   BACK COVER    │  SPINE  │  FRONT COVER    │
│                 │         │                 │
└─────────────────┴─────────┴─────────────────┘
```

Default region proportions:
- Back Cover: `42.5%`
- Spine: `15.0%`
- Front Cover: `42.5%`

If your cover image has custom proportions, configure `coverLayout`:

```ts
const myBook: BookData = {
  id: 'custom-book',
  title: 'Custom Proportions',
  pages: 250,
  coverImage: '/covers/spread.png',
  coverLayout: {
    backRatio: 0.40,  // 40%
    spineRatio: 0.20, // 20%
    frontRatio: 0.40, // 40%
  }
};
```

---

## 📏 Physical Thickness Formula

Book depth is computed by `calculateBookThickness(pages, config)` inside `utils/thickness.ts`:

\[
\text{thickness} = \text{clamp}(\text{pages} \times 0.12\text{px}, \, 10\text{px}, \, 75\text{px})
\]

Examples:
- **100 pages** → `12px` (Thin)
- **350 pages** → `42px` (Medium)
- **600+ pages** → `75px` (Thick - clamped to maximum)

Configurable via `DEFAULT_THICKNESS_CONFIG`.

---

## 🔌 Parent Project Integration Steps

To use this feature in the main application later:
1. Import `BookViewer` or `DemoShowcase` directly from `./3d_books`.
2. Ensure `3d_books/styles/book3d.css` is included (auto-imported by `BookViewer`).
3. No modifications to `package.json` or global project dependencies are required.

---

## 🌐 Dependencies & Upgrade Pathways

- **Current Implementation**: Zero npm dependencies. Built using React, TypeScript, HTML5 Canvas, and CSS 3D preserve-3d matrix engine.
- **Three.js Upgrade (Optional)**: If `@react-three/fiber` or `three` are installed in `package.json` in a future release, `Book3D.tsx` can be swapped with a custom Three.js WebGL Mesh without changing `BookViewer`'s props API!
