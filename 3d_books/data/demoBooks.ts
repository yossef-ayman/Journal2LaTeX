import type { BookData } from '../types/book';

/**
 * Creates high quality procedural SVG data URL cover spreads [ BACK | SPINE | FRONT ]
 * for realistic offline demo testing without external network assets.
 */
function createProceduralCoverSpread(
  title: string,
  author: string,
  bgColor: string,
  accentColor: string
): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="600" viewBox="0 0 1000 600">
    <defs>
      <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="${bgColor}" />
        <stop offset="100%" stop-color="${accentColor}" />
      </linearGradient>
      <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
      </pattern>
    </defs>
    
    <!-- Overall Background -->
    <rect width="1000" height="600" fill="url(#bg)" />
    <rect width="1000" height="600" fill="url(#grid)" />

    <!-- 1. BACK COVER (0 to 425) -->
    <g transform="translate(0, 0)">
      <rect width="425" height="600" fill="none" />
      <text x="212" y="220" font-family="system-ui, sans-serif" font-size="22" font-weight="bold" fill="#ffffff" text-anchor="middle" opacity="0.9">ABOUT THIS EDITION</text>
      <text x="212" y="270" font-family="system-ui, sans-serif" font-size="14" fill="rgba(255,255,255,0.75)" text-anchor="middle">A complete production-ready 3D physical</text>
      <text x="212" y="295" font-family="system-ui, sans-serif" font-size="14" fill="rgba(255,255,255,0.75)" text-anchor="middle">book showcase with realistic thickness,</text>
      <text x="212" y="320" font-family="system-ui, sans-serif" font-size="14" fill="rgba(255,255,255,0.75)" text-anchor="middle">spine mapping, and studio lighting.</text>
      
      <!-- Barcode mockup -->
      <rect x="152" y="480" width="120" height="50" fill="#ffffff" rx="4" />
      <path d="M 162 490 v 30 M 168 490 v 30 M 172 490 v 30 M 180 490 v 30 M 188 490 v 30 M 195 490 v 30 M 205 490 v 30 M 215 490 v 30 M 222 490 v 30 M 230 490 v 30 M 240 490 v 30 M 250 490 v 30 M 260 490 v 30" stroke="#000000" stroke-width="2" />
    </g>

    <!-- Spine divider line -->
    <line x1="425" y1="0" x2="425" y2="600" stroke="rgba(0,0,0,0.3)" stroke-width="2" />

    <!-- 2. SPINE (425 to 575) -->
    <g transform="translate(425, 0)">
      <rect width="150" height="600" fill="rgba(0,0,0,0.12)" />
      <!-- Vertical Spine Text -->
      <g transform="translate(75, 300) rotate(-90)">
        <text x="0" y="-10" font-family="system-ui, sans-serif" font-size="20" font-weight="bold" fill="#ffffff" text-anchor="middle">${title.toUpperCase()}</text>
        <text x="0" y="18" font-family="system-ui, sans-serif" font-size="13" fill="rgba(255,255,255,0.8)" text-anchor="middle">${author}</text>
      </g>
    </g>

    <!-- Spine right divider line -->
    <line x1="575" y1="0" x2="575" y2="600" stroke="rgba(0,0,0,0.3)" stroke-width="2" />

    <!-- 3. FRONT COVER (575 to 1000) -->
    <g transform="translate(575, 0)">
      <rect width="425" height="600" fill="none" />
      <circle cx="212" cy="180" r="60" fill="rgba(255,255,255,0.1)" stroke="rgba(255,255,255,0.2)" stroke-width="2"/>
      <path d="M 182 180 L 242 180 M 212 150 L 212 210" stroke="#ffffff" stroke-width="3" stroke-linecap="round" />

      <text x="212" y="310" font-family="system-ui, sans-serif" font-size="28" font-weight="900" fill="#ffffff" text-anchor="middle">${title}</text>
      <text x="212" y="350" font-family="system-ui, sans-serif" font-size="16" font-weight="500" fill="rgba(255,255,255,0.85)" text-anchor="middle">BY ${author.toUpperCase()}</text>
      
      <rect x="112" y="380" width="200" height="2" fill="rgba(255,255,255,0.3)" />
      <text x="212" y="520" font-family="system-ui, sans-serif" font-size="12" font-weight="600" fill="rgba(255,255,255,0.6)" letter-spacing="2" text-anchor="middle">HARDCOVER EDITION</text>
    </g>
  </svg>`;

  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

export const DEMO_BOOKS: BookData[] = [
  {
    id: 'book-sample-1',
    title: 'Uploaded Cover Sample 1',
    author: 'Journal2LaTeX',
    pages: 280,
    coverImage: '/sample-cover-1.jpg',
    description: 'Actual uploaded book cover spread image (280 pages).',
  },
  {
    id: 'book-sample-2',
    title: 'Uploaded Cover Sample 2',
    author: 'Journal2LaTeX',
    pages: 450,
    coverImage: '/sample-cover-2.jpg',
    description: 'Actual uploaded book cover spread image (450 pages).',
  },
  {
    id: 'book-001',
    title: 'Introduction to AI',
    author: 'Dr. Alex Vance',
    pages: 140, // Thin book (~16px thickness)
    coverImage: createProceduralCoverSpread('Introduction to AI', 'Dr. Alex Vance', '#1e3a8a', '#3b82f6'),
    description: 'A concise introduction to modern machine learning concepts (140 pages - Thin book).',
  },
  {
    id: 'book-002',
    title: 'Computer Networks',
    author: 'Prof. Sarah Jenkins',
    pages: 350, // Medium book (~42px thickness)
    coverImage: createProceduralCoverSpread('Computer Networks', 'Prof. Sarah Jenkins', '#064e3b', '#10b981'),
    description: 'Comprehensive guide on TCP/IP protocols and distributed architecture (350 pages - Medium book).',
  },
  {
    id: 'book-003',
    title: 'Quantum Physics & Geometry',
    author: 'Dr. Marcus Thorne',
    pages: 620, // Thick book (~74px thickness)
    coverImage: createProceduralCoverSpread('Quantum Physics', 'Dr. Marcus Thorne', '#581c87', '#a855f7'),
    description: 'In-depth research text exploring physical universe geometry (620 pages - Thick book).',
  },
];
