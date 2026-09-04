import { NextRequest, NextResponse } from "next/server";

const AUTH_COOKIE = "controls_auth";
const THIRTY_DAYS_SECONDS = 60 * 60 * 24 * 30;

export async function POST(request: NextRequest) {
  const password = process.env.CONTROLS_PASSWORD;
  if (!password) {
    return NextResponse.json(
      { error: "CONTROLS_PASSWORD is not configured on the server." },
      { status: 500 }
    );
  }

  const { password: submitted } = await request.json().catch(() => ({ password: "" }));
  if (submitted !== password) {
    return NextResponse.json({ error: "Incorrect password." }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(AUTH_COOKIE, password, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: THIRTY_DAYS_SECONDS,
  });
  return response;
}
