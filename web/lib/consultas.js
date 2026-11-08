import { DORMITORIOS, PORTALES } from "./filtros";

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
  if (descartados.length) q = q.not("id", "in", `(${descartados.join(",")})`);

  if (f.orden === "precio") q = q.order("precio", { ascending: true, nullsFirst: false });
  else if (f.orden === "precio_m2") q = q.order("precio_m2", { ascending: true, nullsFirst: false });
  else q = q.order("primera_vez", { ascending: false });
  return q;
}

// Consulta cada portal por separado y los mezcla, para que un portal con muchos
// avisos recién cargados no tape a los demás. Devuelve también el total por portal.
export async function buscarPublicaciones(supabase, f, ubicaciones, limite = 90) {
  const portales = f.portales?.length ? f.portales : PORTALES.map((x) => x.valor);
  const { data: descartes } = await supabase.from("descartes").select("publicacion_id");
  const descartados = (descartes || []).map((d) => d.publicacion_id);

  const respuestas = await Promise.all(
    portales.map((portal) => consultaPortal(supabase, f, ubicaciones, portal, descartados).limit(limite))
  );
  const totales = {};
  const listas = respuestas.map((r, i) => {
    if (r.error) throw new Error(r.error.message);
    totales[portales[i]] = r.count ?? (r.data || []).length;
    return r.data || [];
  });

  let lista;
  if (f.orden === "precio" || f.orden === "precio_m2") {
    const campo = f.orden === "precio" ? "precio" : "precio_m2";
    const valor = (p) => (p[campo] == null ? Infinity : Number(p[campo]));
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
