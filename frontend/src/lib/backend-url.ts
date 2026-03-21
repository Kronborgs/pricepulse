/**
 * Resolves the backend URL for server-side route handlers.
 *
 * Priority:
 *  1. API_URL env var (server-only, never webpack-inlined)
 *  2. Auto-detect: same hostname as the incoming request, port 8000
 *     (works on Unraid where frontend :3000 and backend :8000 are on the same host)
 */
export function getBackendUrl(req: Request): string {
  // Accept either variable name — NEXT_PUBLIC_API_URL is what older Unraid templates inject
  const configured = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL;
  if (configured) return configured;

  // Default: reach backend by container name on dockernet
  return "http://pricepulse-backend:8000";
}
