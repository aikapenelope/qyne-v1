import { NextRequest, NextResponse } from "next/server";

const AGNO_URL = process.env.AGNO_INTERNAL_URL || "http://agno:8000";

export async function GET(req: NextRequest) {
  const path = req.nextUrl.pathname.replace("/api/proxy/agno", "");
  const search = req.nextUrl.search;
  try {
    const res = await fetch(`${AGNO_URL}${path}${search}`, {
      headers: { "Content-Type": "application/json" },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Agno unavailable" }, { status: 502 });
  }
}

export async function POST(req: NextRequest) {
  const path = req.nextUrl.pathname.replace("/api/proxy/agno", "");
  const contentType = req.headers.get("content-type") || "";

  try {
    // Pass through the request body as-is (supports JSON and FormData)
    const body = await req.arrayBuffer();
    const headers: Record<string, string> = {};
    if (contentType) {
      headers["Content-Type"] = contentType;
    }

    const res = await fetch(`${AGNO_URL}${path}`, {
      method: "POST",
      headers,
      body: Buffer.from(body),
    });

    const text = await res.text();
    try {
      return NextResponse.json(JSON.parse(text), { status: res.status });
    } catch {
      return new NextResponse(text, {
        status: res.status,
        headers: { "Content-Type": res.headers.get("content-type") || "text/plain" },
      });
    }
  } catch {
    return NextResponse.json({ error: "Agno unavailable" }, { status: 502 });
  }
}
