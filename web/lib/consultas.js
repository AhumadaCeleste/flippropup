import { DORMITORIOS } from "./filtros";

export async function ubicacionesLaVoz(supabase) {
  const { data } = await supabase
    .from("ubicaciones")
    .select("tid,nombre,tipo,padre_tid")
    .eq("portal", "lavoz")
    .order("nombre")
    .range(0, 9999);
  return data || [];
}

export async function buscarPublicaciones(supabase, f, ubicaciones, limite = 60) {
  const nombre = (tid) => ubicaciones.find((u) => u.tid === Number(tid))?.nombre;
  let q = supabase
    .from("publicaciones")
    .select("*")
    .eq("estado", "activo");

  if (f.tipos?.length) q = q.in("tipo", f.tipos);
  if (f.barrios_tid?.length) q = q.in("barrio", f.barrios_tid.map(nombre).filter(Boolean));
  else if (f.ciudad_tid && nombre(f.ciudad_tid)) q = q.eq("ciudad", nombre(f.ciudad_tid));
  if (f.dormitorios?.length)
    q = q.in("dormitorios", f.dormitorios.map((d) => DORMITORIOS.find((x) => x.valor === d)?.texto).filter(Boolean));
  if (f.precio_desde || f.precio_hasta) {
    q = q.eq("moneda", f.moneda === "pesos" ? "ARS" : "USD");
    if (f.precio_desde) q = q.gte("precio", f.precio_desde);
    if (f.precio_hasta) q = q.lte("precio", f.precio_hasta);
  }
  if (f.superficie_desde) q = q.gte("superficie_total", f.superficie_desde);
  if (f.superficie_hasta) q = q.lte("superficie_total", f.superficie_hasta);
  if (f.vendedor === "particular") q = q.eq("vendedor_tipo", "Particular");
  if (f.vendedor === "inmobiliaria") q = q.eq("vendedor_tipo", "Inmobiliaria");
  if (f.apto_escritura) q = q.eq("apto_escritura", "Sí");
  if (f.palabras?.length) {
    const limpio = (w) => w.replace(/[%,()]/g, " ").trim();
    q = q.or(f.palabras.flatMap((w) => [`titulo.ilike.%${limpio(w)}%`, `descripcion.ilike.%${limpio(w)}%`]).join(","));
  }

  const { data: descartes } = await supabase.from("descartes").select("publicacion_id");
  const ids = (descartes || []).map((d) => d.publicacion_id);
  if (ids.length) q = q.not("id", "in", `(${ids.join(",")})`);

  if (f.orden === "precio") q = q.order("precio", { ascending: true, nullsFirst: false });
  else if (f.orden === "precio_m2") q = q.order("precio_m2", { ascending: true, nullsFirst: false });
  else q = q.order("primera_vez", { ascending: false });

  const { data, error } = await q.limit(limite);
  if (error) throw new Error(error.message);
  return data || [];
}

export async function idsSeguidos(supabase) {
  const { data } = await supabase.from("seguimientos").select("publicacion_id");
  return new Set((data || []).map((s) => s.publicacion_id));
}
