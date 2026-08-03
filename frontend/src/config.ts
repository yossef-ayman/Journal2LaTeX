/**
 * Single source of truth for the backend API base URL.
 *
 * Resolution order:
 *  1. VITE_API_URL environment variable (see frontend/.env)
 *  2. The deployed Railway production backend
 *
 * All API access should go through `apiClient` (which reads this value)
 * or import { API_BASE_URL } from this module directly.
 */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_URL ??
  "https://journal2latex-production.up.railway.app";
