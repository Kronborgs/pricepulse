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

  // Extract hostname from the Host header — e.g. "10.10.70.22:3000" → "10.10.70.22"
  const host = req.headers.get("host") ?? "localhost";
  const hostname = host.split(":")[0];
  return `http://${hostname}:8000`;
}
