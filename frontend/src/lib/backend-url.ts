/**
 * Resolves the backend URL for server-side route handlers.
 *
 * Priority:
 *  1. API_URL env var (server-only, never webpack-inlined)
 *  2. Auto-detect: same hostname as the incoming request, port 8000
 *     (works on Unraid where frontend :3000 and backend :8000 are on the same host)
 */
export function getBackendUrl(req: Request): string {
  if (process.env.API_URL) return process.env.API_URL;

  // Default: reach the backend via Docker container name on the same network.
  // Works when frontend and backend are both on dockernet.
  return "http://pricepulse-backend:8000";
}
