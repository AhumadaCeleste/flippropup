"use client";
import { useState } from "react";
import { supabaseNavegador } from "@/lib/supabase/client";

export default function BotonGoogle() {
  const [cargando, setCargando] = useState(false);
  async function entrar() {
    setCargando(true);
    await supabaseNavegador().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  }
  return (
    <button className="btn btn-principal" onClick={entrar} disabled={cargando} style={{ width: "100%", padding: "12px 16px", fontSize: 15 }}>
      {cargando ? "Abriendo Google…" : "Entrar con Google"}
    </button>
  );
}
