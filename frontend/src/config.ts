/**
 * Single source of truth for the backend API base URL.
 *
 * Resolution order:
 *  1. VITE_API_URL environment variable (see .env / .env.production)
 *  2. Local development backend at http://localhost:8000
 *
 * Production builds read VITE_API_URL from .env.production (or from the
 * platform env vars, e.g. Vercel dashboard).  The fallback below is intended
 * for local development only.
 *
 * All API access should go through `apiClient` (which reads this value)
 * or import { API_BASE_URL } from this module directly.
 */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";
