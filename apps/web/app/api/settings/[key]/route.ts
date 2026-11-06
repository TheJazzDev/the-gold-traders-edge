import { NextRequest, NextResponse } from "next/server";

const AUTH_COOKIE = "controls_auth";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Setting changes from /controls. Checks the login, then adds the admin key
 * here on the server so the browser never holds it.
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ key: string }> }
) {
  const password = process.env.CONTROLS_PASSWORD;
  const cookie = request.cookies.get(AUTH_COOKIE)?.value;
  if (!password || cookie !== password) {
    return NextResponse.json({ detail: "Not logged in." }, { status: 401 });
  }

  const adminKey = process.env.ADMIN_API_KEY;
  if (!adminKey) {
    return NextResponse.json({ detail: "ADMIN_API_KEY is not configured." }, { status: 500 });
  }

  const { key } = await params;
  const upstream = await fetch(`${API_URL}/v1/settings/${encodeURIComponent(key)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-Admin-Key": adminKey },
    body: await request.text(),
  });
  return new NextResponse(await upstream.text(), {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
