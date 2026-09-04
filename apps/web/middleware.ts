import { NextRequest, NextResponse } from "next/server";

const AUTH_COOKIE = "controls_auth";

/**
 * Controls is the private operator panel (strategy toggles, auto-trading,
 * risk settings) — everything else (Home, Performance) is intentionally
 * public since signals are already broadcast on Telegram. This is a
 * deliberately simple shared-password gate, not a full auth system: no
 * accounts, just one password in CONTROLS_PASSWORD compared against a
 * cookie set by /api/controls-auth after a correct login.
 */
export function middleware(request: NextRequest) {
  // The login page itself must stay reachable, or a redirect to it loops.
  if (request.nextUrl.pathname === "/controls/login") {
    return NextResponse.next();
  }

  const password = process.env.CONTROLS_PASSWORD;

  // Without a configured password, fail closed rather than leaving the
  // panel open — redirect to login, which will show a clear error.
  const cookie = request.cookies.get(AUTH_COOKIE)?.value;
  if (password && cookie === password) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/controls/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/controls/:path*"],
};
