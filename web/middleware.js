import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

const PUBLICAS = ["/login", "/auth"];

export async function middleware(request) {
  let respuesta = NextResponse.next({ request });
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (lista) => {
          lista.forEach(({ name, value }) => request.cookies.set(name, value));
          respuesta = NextResponse.next({ request });
          lista.forEach(({ name, value, options }) => respuesta.cookies.set(name, value, options));
        },
      },
    }
  );
  // getClaims valida la sesión en el mismo servidor (sin ir a Supabase en cada clic, como hacía getUser).
  const { data } = await supabase.auth.getClaims();
  const user = data?.claims;
  const publica = PUBLICAS.some((p) => request.nextUrl.pathname.startsWith(p));
  if (!user && !publica) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }
  return respuesta;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|manifest.webmanifest|sw.js|icon.svg|apple-icon.png|opengraph-image.png|.*\\.(?:svg|png|jpg|webp)$).*)"],
};
