import { NextRequest, NextResponse } from "next/server";

const AGNO_URL = process.env.AGNO_INTERNAL_URL || "http://agno:8000";

/**
 * Proxy all GET/POST requests to Agno API.
 * Browser calls /api/proxy/agno/agents → server calls http://agno:8000/agents
 */
export async function GET(req: NextRequest) {
  const path = req.nextUrl.pathname.replace("/api/proxy/agno", "");
  const search = req.nextUrl.search;
  const res = await fetch(`${AGNO_URL}${path}${search}`, {
    headers: { "Content-Type": "application/json" },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST(req: NextRequest) {
  const path = req.nextUrl.pathname.replace("/api/proxy/agno", "");
  const body = await req.text();
  const contentType = req.headers.get("content-type") || "application/json";
  const res = await fetch(`${AGNO_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": contentType },
    body,
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
