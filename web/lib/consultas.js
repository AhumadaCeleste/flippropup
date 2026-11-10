import { DORMITORIOS, PORTALES, CORDOBA_CAPITAL } from "./filtros";

export async function barriosOficiales(supabase) {
  const { data } = await supabase.from("barrios").select("id,bonito,zona").order("bonito").range(0, 999);
  return data || [];
}

export async function ubicacionesLaVoz(supabase) {
  const { data } = await supabase
    .from("ubicaciones")
    .select("tid,nombre,tipo,padre_tid")
    .eq("portal", "lavoz")
    .order("nombre")
    .range(0, 9999);
  return data || [];
}

// Arma la consulta de un portal con todos los filtros.
function consultaPortal(supabase, f, ubicaciones, portal, descartados) {
  const nombre = (tid) => ubicaciones.find((u) => u.tid === Number(tid))?.nombre;
  let q = supabase
    .from("publicaciones")
    .select("*", { count: "exact" })
    .eq("estado", "activo")
    .eq("portal", portal);

  if (f.tipos?.length) q = q.in("tipo", f.tipos);
  if (f.barrios_id?.length) q = q.in("barrio_id", f.barrios_id);
  else if (f.barrios_tid?.length) q = q.in("barrio", f.barrios_tid.map(nombre).filter(Boolean));
  else if (f.ciudad_tid === CORDOBA_CAPITAL) q = q.or("barrio_id.not.is.null,ciudad.ilike.c_rdoba,ciudad.ilike.c_rdoba capital,ciudad.ilike.capital");
  else if (f.ciudad_tid && nombre(f.ciudad_tid)) q = q.ilike("ciudad", nombre(f.ciudad_tid));
  if (f.zonas?.length) q = q.in("zona", f.zonas);
  if (f.antiguedad) {
    const hasta = new Date(Date.now() - f.antiguedad * 86400000).toISOString().slice(0, 10);
    q = q.lte("publicado_desde", hasta);
  }
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
  if (descartados.length) q = q.not("id", "in", `(${descartados.join(",")})`);

  if (f.orden === "precio") q = q.order("precio", { ascending: true, nullsFirst: false });
  else if (f.orden === "precio_m2") q = q.order("precio_m2", { ascending: true, nullsFirst: false });
  else if (f.orden === "puntaje") q = q.order("puntaje", { ascending: false, nullsFirst: false });
  else if (f.orden === "antiguos") q = q.order("publicado_desde", { ascending: true, nullsFirst: false });
  else q = q.order("primera_vez", { ascending: false });
  return q;
}

// Consulta cada portal por separado y los mezcla, para que un portal con muchos
// avisos recién cargados no tape a los demás. Devuelve también el total por portal.
export async function buscarPublicaciones(supabase, f, ubicaciones, limite = 90, { conCoordenadas = false } = {}) {
  const portales = f.portales?.length ? f.portales : PORTALES.map((x) => x.valor);
  const { data: descartes } = await supabase.from("descartes").select("publicacion_id");
  const descartados = (descartes || []).map((d) => d.publicacion_id);

  const respuestas = await Promise.all(
    portales.map((portal) => {
      let q = consultaPortal(supabase, f, ubicaciones, portal, descartados);
      if (conCoordenadas) q = q.not("lat", "is", null);
      return q.limit(limite);
    })
  );
  const totales = {};
  const listas = respuestas.map((r, i) => {
    if (r.error) throw new Error(r.error.message);
    totales[portales[i]] = r.count ?? (r.data || []).length;
    return r.data || [];
  });

  let lista;
  if (["precio", "precio_m2", "puntaje", "antiguos"].includes(f.orden)) {
    const valor = {
      precio: (p) => (p.precio == null ? Infinity : Number(p.precio)),
      precio_m2: (p) => (p.precio_m2 == null ? Infinity : Number(p.precio_m2)),
      puntaje: (p) => -(p.puntaje ?? -1),
      antiguos: (p) => (p.publicado_desde ? new Date(p.publicado_desde).getTime() : Infinity),
    }[f.orden];
    lista = listas.flat().sort((a, b) => valor(a) - valor(b));
  } else {
    // "Más nuevos": se intercalan los portales (uno de cada uno).
    lista = [];
    for (let i = 0; lista.length < limite && listas.some((l) => i < l.length); i++)
      listas.forEach((l) => { if (i < l.length) lista.push(l[i]); });
  }
  return { lista: lista.slice(0, limite), totales, total: Object.values(totales).reduce((a, b) => a + b, 0) };
}

export async function idsSeguidos(supabase) {
  const { data } = await supabase.from("seguimientos").select("publicacion_id");
  return new Set((data || []).map((s) => s.publicacion_id));
}
