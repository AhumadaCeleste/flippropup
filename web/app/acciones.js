"use server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { supabaseServidor } from "@/lib/supabase/server";
import { filtrosDesdeParams } from "@/lib/filtros";

async function conUsuario() {
  const supabase = await supabaseServidor();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  return { supabase, email: user.email };
}

function refrescar() {
  ["/buscar", "/seguimientos", "/busquedas"].forEach((p) => revalidatePath(p));
  revalidatePath("/aviso/[id]", "page");
}

export async function seguir(id) {
  const { supabase, email } = await conUsuario();
  const { data: p } = await supabase.from("publicaciones").select("precio").eq("id", id).single();
  await supabase.from("seguimientos").upsert(
    { publicacion_id: id, agregado_por: email, precio_inicial: p?.precio ?? null },
    { onConflict: "publicacion_id", ignoreDuplicates: true }
  );
  refrescar();
}

export async function dejarDeSeguir(id) {
  const { supabase } = await conUsuario();
  await supabase.from("seguimientos").delete().eq("publicacion_id", id);
  refrescar();
}

export async function descartar(id) {
  const { supabase, email } = await conUsuario();
  await supabase.from("descartes").upsert({ publicacion_id: id, por: email }, { onConflict: "publicacion_id" });
  refrescar();
}

export async function cambiarEstado(id, estado) {
  const { supabase } = await conUsuario();
  await supabase.from("seguimientos").update({ estado }).eq("publicacion_id", id);
  refrescar();
}

export async function guardarObjetivo(id, formData) {
  const { supabase } = await conUsuario();
  const n = Number(String(formData.get("objetivo") || "").replace(/\./g, ""));
  await supabase.from("seguimientos").update({ precio_objetivo: n > 0 ? n : null }).eq("publicacion_id", id);
  refrescar();
}

export async function agregarNota(id, formData) {
  const { supabase, email } = await conUsuario();
  const texto = String(formData.get("texto") || "").trim();
  if (texto) await supabase.from("notas").insert({ publicacion_id: id, autor: email, texto });
  refrescar();
}

export async function guardarBusqueda(formData) {
  const { supabase, email } = await conUsuario();
  const sp = {};
  for (const [k, v] of formData.entries()) {
    if (k.startsWith("$")) continue;
    sp[k] = sp[k] === undefined ? v : [].concat(sp[k], v);
  }
  const { orden, ...filtros } = filtrosDesdeParams(sp);
  const nombre = String(formData.get("nombre") || "").trim() || "Búsqueda sin nombre";
  const { data } = await supabase.from("busquedas").insert({ nombre, filtros, creada_por: email }).select("id").single();
  refrescar();
  if (data?.id) await dispararRobot(data.id);
  redirect("/busquedas?guardada=1");
}

export async function alternarBusqueda(id, activa) {
  const { supabase } = await conUsuario();
  await supabase.from("busquedas").update({ activa }).eq("id", id);
  refrescar();
}

export async function borrarBusqueda(id) {
  const { supabase } = await conUsuario();
  await supabase.from("busquedas").delete().eq("id", id);
  refrescar();
}

// Pide a GitHub que corra el robot ahora (tarda 1 a 3 minutos).
async function dispararRobot(busquedaId = "") {
  if (!process.env.GITHUB_TOKEN || !process.env.GITHUB_REPO) return false;
  const r = await fetch(
    `https://api.github.com/repos/${process.env.GITHUB_REPO}/actions/workflows/robot-diario.yml/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
      },
      body: JSON.stringify({ ref: "main", inputs: { busqueda_id: busquedaId, sin_email: "1" } }),
    }
  );
  return r.ok;
}

export async function actualizarAhora(busquedaId = "") {
  await conUsuario();
  const ok = await dispararRobot(busquedaId);
  redirect(ok ? "/busquedas?actualizando=1" : "/busquedas?sin_token=1");
}

export async function salir() {
  const supabase = await supabaseServidor();
  await supabase.auth.signOut();
  redirect("/login");
}
