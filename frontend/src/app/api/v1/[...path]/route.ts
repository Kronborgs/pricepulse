import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend-url";

async function proxy(req: NextRequest, path: string[]): Promise<NextResponse> {
  const upstream = `${getBackendUrl(req)}/api/v1/${path.join("/")}${req.nextUrl.search}`;

  const headers = new Headers(req.headers);
  // Strip Next.js/browser-only headers that confuse the upstream
  headers.delete("host");
  headers.delete("x-forwarded-for");
  headers.delete("x-forwarded-host");
  headers.delete("x-forwarded-port");
  headers.delete("x-forwarded-proto");

  try {
    const res = await fetch(upstream, {
      method: req.method,
      headers,
      body: ["GET", "HEAD"].includes(req.method) ? undefined : req.body,
      cache: "no-store",
      // @ts-expect-error Node18+ duplex required for streaming body
      duplex: "half",
      signal: AbortSignal.timeout(30000),
    });

    const nextRes = new NextResponse(res.body, {
      status: res.status,
      statusText: res.statusText,
    });

    // Kopiér alle response-headers undtagen Set-Cookie (håndteres separat)
    res.headers.forEach((value, key) => {
      if (key.toLowerCase() !== "set-cookie") {
        nextRes.headers.set(key, value);
      }
    });

    // Set-Cookie skal kopieres én ad gangen — Headers-klassen joiner dem
    // ellers med komma, hvilket ødelægger browser-parsingen.
    const setCookies =
      typeof (res.headers as Headers & { getSetCookie?(): string[] }).getSetCookie === "function"
        ? (res.headers as Headers & { getSetCookie(): string[] }).getSetCookie()
        : [];
    setCookies.forEach((c) => nextRes.headers.append("set-cookie", c));

    return nextRes;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 502 });
  }
}

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(req, params.path);
}
export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(req, params.path);
}
export async function PUT(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(req, params.path);
}
export async function PATCH(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(req, params.path);
}
export async function DELETE(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(req, params.path);
}
