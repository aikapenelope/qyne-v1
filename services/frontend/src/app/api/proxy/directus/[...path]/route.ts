import { NextRequest, NextResponse } from "next/server";

const DIRECTUS_URL =
  process.env.DIRECTUS_INTERNAL_URL || "http://directus:8055";
const DIRECTUS_TOKEN = process.env.DIRECTUS_TOKEN || "";

export async function GET(req: NextRequest) {
  const path = req.nextUrl.pathname.replace("/api/proxy/directus", "");
  const search = req.nextUrl.search;
  try {
    const res = await fetch(`${DIRECTUS_URL}${path}${search}`, {
      headers: {
        Authorization: `Bearer ${DIRECTUS_TOKEN}`,
        "Content-Type": "application/json",
      },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { error: "Directus unavailable" },
      { status: 502 }
    );
  }
}

export async function POST(req: NextRequest) {
  const path = req.nextUrl.pathname.replace("/api/proxy/directus", "");
  const body = await req.text();
  try {
    const res = await fetch(`${DIRECTUS_URL}${path}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${DIRECTUS_TOKEN}`,
        "Content-Type": "application/json",
      },
      body,
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { error: "Directus unavailable" },
      { status: 502 }
    );
  }
}
