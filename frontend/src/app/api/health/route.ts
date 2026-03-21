import { NextResponse } from "next/server";

export async function GET() {
  // API_URL is a server-only env var — always read at runtime, never inlined by webpack
  const apiUrl = process.env.API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
