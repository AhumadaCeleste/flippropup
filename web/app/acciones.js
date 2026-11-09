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

// ---------- Relevar: buscar lo publicado cerca de un punto, por calle o por teléfono ----------
const CAMPOS_TARJETA = "id,portal,url,titulo,precio,moneda,foto_principal,barrio,ciudad,dormitorios,superficie_total,lat,lng,vendedor_tipo,vendedor_nombre,precio_m2,primera_vez,fecha_publicacion,estado";

export async function buscarCerca({ lat, lng, calle, altura, telefono, radio = 250 }) {
  const { supabase } = await conUsuario();
  const resultado = { cerca: [], calle: [], telefono: [], avisos: [] };
  if (lat && lng) {
    const dLat = radio / 111000;
    const dLng = radio / (111000 * Math.cos((lat * Math.PI) / 180));
    const { data } = await supabase.from("publicaciones").select(CAMPOS_TARJETA).eq("estado", "activo")
      .gte("lat", lat - dLat).lte("lat", lat + dLat).gte("lng", lng - dLng).lte("lng", lng + dLng).limit(80);
    const dist = (p) => {
      const R = 6371000, r = Math.PI / 180;
      const a = Math.sin(((p.lat - lat) * r) / 2) ** 2 + Math.cos(lat * r) * Math.cos(p.lat * r) * Math.sin(((p.lng - lng) * r) / 2) ** 2;
      return Math.round(2 * R * Math.asin(Math.sqrt(a)));
    };
    resultado.cerca = (data || []).map((p) => ({ ...p, distancia: dist(p) })).filter((p) => p.distancia <= radio)
      .sort((a, b) => a.distancia - b.distancia);
  }
  const limpio = (t) => String(t || "").replace(/[%,()]/g, " ").trim();
  if (calle && limpio(calle).length >= 4) {
    const c = limpio(calle);
    const filtros = [`titulo.ilike.%${c}%`, `descripcion.ilike.%${c}%`];
    const { data } = await supabase.from("publicaciones").select(CAMPOS_TARJETA).eq("estado", "activo").or(filtros.join(",")).limit(60);
    const centena = altura ? Math.floor(Number(altura) / 100) : null;
    resultado.calle = (data || []).map((p) => ({ ...p, mismaCuadra: centena != null && new RegExp(`\\b${centena}\\d{2}\\b|al\\s+${centena}00`, "i").test(p.titulo || "") }))
      .sort((a, b) => Number(b.mismaCuadra) - Number(a.mismaCuadra));
  }
  if (telefono) {
    const ult8 = telefono.slice(-8);
    const consultas = [supabase.from("publicaciones").select(CAMPOS_TARJETA).ilike("descripcion", `%${ult8.slice(0, 4)}%${ult8.slice(4)}%`).limit(30)];
    const conTel = await supabase.from("publicaciones").select("id").limit(1).eq("telefono", telefono);
    if (!conTel.error) consultas.push(supabase.from("publicaciones").select(CAMPOS_TARJETA).eq("telefono", telefono).limit(30));
    const res = await Promise.all(consultas);
    const vistos = new Set();
    resultado.telefono = res.flatMap((r) => r.data || []).filter((p) => !vistos.has(p.id) && vistos.add(p.id));
  }
  return resultado;
}

export async function guardarRelevamiento(datos) {
  const { supabase, email } = await conUsuario();
  const fila = {
    creado_por: email, lat: datos.lat ?? null, lng: datos.lng ?? null, direccion: datos.direccion || null,
    telefono: datos.telefono || null, nota: datos.nota || null, foto_path: datos.foto_path || null, activo: true,
  };
  const { error } = await supabase.from("relevamientos").insert(fila);
  if (error) return { error: error.message.includes("relevamientos") ? "Falta correr la migración en Supabase (tabla relevamientos)." : error.message };
  revalidatePath("/relevar");
  return { ok: true };
}

export async function cambiarAvisoRelevamiento(id, activo) {
  const { supabase } = await conUsuario();
  await supabase.from("relevamientos").update({ activo }).eq("id", id);
  revalidatePath("/relevar");
}
