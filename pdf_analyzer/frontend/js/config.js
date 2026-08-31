// ==========================================
// Frontend API Configuration
// ==========================================
// In standalone mode (e.g. VS Code Live Server, Vite, or direct file open),
// requests will be sent to the backend server running at http://127.0.0.1:8080.
// When served directly from FastAPI, it automatically uses the same origin.

window.API_BASE_URL = window.API_BASE_URL || (
    (window.location.protocol === 'file:' || (window.location.port !== '8080' && window.location.port !== ''))
        ? 'http://127.0.0.1:8080'
        : ''
);

console.log('[PDF Analyzer UI] Configured API Base URL:', window.API_BASE_URL || '(Same Origin)');
