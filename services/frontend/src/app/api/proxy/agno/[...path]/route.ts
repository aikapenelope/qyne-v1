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
  const body = await req.text();
  const ct = req.headers.get("content-type") || "application/json";
  try {
    const res = await fetch(`${AGNO_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": ct },
      body,
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Agno unavailable" }, { status: 502 });
  }
}
