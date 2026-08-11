import React from 'react';

interface BookFallbackProps {
  message?: string;
  error?: string;
}

export const BookFallback: React.FC<BookFallbackProps> = ({
  message = '3D Book Showcase Unavailable',
  error,
}) => {
  return (
    <div className="book-viewer-container" style={{ minHeight: '350px' }}>
      <div className="book-status-overlay">
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: '#ef4444' }}
        >
          <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
          <line x1="9" y1="9" x2="15" y2="15" />
          <line x1="15" y1="9" x2="9" y2="15" />
        </svg>
        <div style={{ fontSize: '16px', fontWeight: 600, color: '#f8fafc' }}>
          {message}
        </div>
        {error && (
          <div style={{ fontSize: '13px', color: '#94a3b8', maxWidth: '80%', textAlign: 'center' }}>
            {error}
          </div>
        )}
      </div>
    </div>
  );
};
