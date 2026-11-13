// Traduce el formulario de búsqueda (parámetros de la URL) a los filtros
// que guarda la base y usa el robot. Mismo formato en ambos lados.
export const TIPOS = [
  { valor: "casa", etiqueta: "Casa" },
  { valor: "departamento", etiqueta: "Departamento" },
  { valor: "terreno", etiqueta: "Terreno" },
];
export const DORMITORIOS = [
  { valor: "monoambiente", etiqueta: "Monoambiente", texto: "Monoambiente" },
  { valor: "1-dormitorio", etiqueta: "1", texto: "1 Dormitorio" },
  { valor: "2-dormitorios", etiqueta: "2", texto: "2 Dormitorios" },
  { valor: "3-dormitorios", etiqueta: "3", texto: "3 Dormitorios" },
  { valor: "4-dormitorios-o-mas", etiqueta: "4 o más", texto: "4 Dormitorios o más" },
];
export const PORTALES = [
  { valor: "lavoz", etiqueta: "La Voz" },
  { valor: "mercadolibre", etiqueta: "Mercado Libre" },
  { valor: "inmoup", etiqueta: "InmoUP" },
  { valor: "cordobaprop", etiqueta: "CórdobaProp" },
  { valor: "inmobiliarias", etiqueta: "Inmobiliarias" },
  { valor: "marketplace", etiqueta: "Marketplace" },
  { valor: "zonaprop", etiqueta: "Zonaprop" },
];
export const CORDOBA_PROVINCIA = 3173;
export const CORDOBA_CAPITAL = 3194;
export const ZONAS = [
  { valor: "centro", etiqueta: "Centro" },
  { valor: "norte", etiqueta: "Norte" },
  { valor: "sur", etiqueta: "Sur" },
  { valor: "este", etiqueta: "Este" },
  { valor: "oeste", etiqueta: "Oeste" },
];
// Antigüedad de la publicación: "publicado hace más de…" (días).
export const ANTIGUEDADES = [
  { valor: 30, etiqueta: "Más de 1 mes" },
  { valor: 60, etiqueta: "Más de 2 meses" },
  { valor: 90, etiqueta: "Más de 3 meses" },
  { valor: 180, etiqueta: "Más de 6 meses" },
];
export const DESCUENTOS = [10, 15, 20, 25, 30];
export const REPETIDOS = [
  { valor: "agrupar", etiqueta: "Mostrar cada propiedad una vez" },
  { valor: "solo", etiqueta: "Solo las publicadas más de una vez" },
  { valor: "todos", etiqueta: "Mostrar todos los avisos" },
];
export const nombreZona = (z) => ZONAS.find((x) => x.valor === z)?.etiqueta || z;
export const nombrePortal = (v) => PORTALES.find((x) => x.valor === v)?.etiqueta || v;
// Para mostrar de dónde viene un aviso: en "Inmobiliarias" va el nombre de la inmobiliaria.
export const origenAviso = (p) => (p?.portal === "inmobiliarias" && p.vendedor_nombre ? p.vendedor_nombre : nombrePortal(p?.portal));
export const PALABRAS_SUGERIDAS = ["a reciclar", "a refaccionar", "oportunidad", "sucesión", "dueño vende", "urgente"];
export const ESTADOS = ["Interesa", "Contactado", "Visitado", "Ofertado", "Descartado", "Comprado"];

const lista = (v) => (v === undefined ? [] : Array.isArray(v) ? v : [v]).filter(Boolean);
const numero = (v) => {
  const n = Number(String(v ?? "").replace(/\./g, "").replace(",", "."));
  return Number.isFinite(n) && n > 0 ? n : null;
};

export function filtrosDesdeParams(sp = {}) {
  return {
    portales: (() => {
      const elegidos = lista(sp.portal).filter((v) => PORTALES.some((x) => x.valor === v));
      return elegidos.length ? elegidos : PORTALES.map((x) => x.valor);
    })(),
    tipos: lista(sp.tipo),
    provincia_tid: numero(sp.provincia) ?? CORDOBA_PROVINCIA,
    // Córdoba capital por defecto; "todas" busca en toda la provincia.
    ciudad_tid: sp.ciudad === "todas" ? null : numero(sp.ciudad) ?? CORDOBA_CAPITAL,
    barrios_tid: lista(sp.barrio).map(Number).filter(Boolean),
    barrios_id: lista(sp.barrio_of).map(Number).filter(Boolean),
    zonas: lista(sp.zona).filter((z) => ZONAS.some((x) => x.valor === z)),
    descuento_min: DESCUENTOS.includes(Number(sp.descuento)) ? Number(sp.descuento) : null,
    repetidos: ["solo", "todos"].includes(sp.repetidos) ? sp.repetidos : "agrupar",
    antiguedad: ANTIGUEDADES.some((a) => String(a.valor) === String(sp.publicado)) ? Number(sp.publicado) : null,
    dormitorios: lista(sp.dorm),
    precio_desde: numero(sp.precio_desde),
    precio_hasta: numero(sp.precio_hasta),
    moneda: sp.moneda === "pesos" ? "pesos" : "dolares",
    superficie_desde: numero(sp.sup_desde),
    superficie_hasta: numero(sp.sup_hasta),
    vendedor: ["particular", "inmobiliaria"].includes(sp.vendedor) ? sp.vendedor : null,
    apto_escritura: sp.escritura === "si",
    palabras: lista(sp.palabra).concat(
      String(sp.palabras_libres || "").split(",").map((s) => s.trim()).filter(Boolean)
    ),
    orden: ["precio", "precio_m2", "puntaje", "antiguos"].includes(sp.orden) ? sp.orden : "nuevos",
  };
}

export function paramsDesdeFiltros(f) {
  const p = new URLSearchParams();
  (f.portales || []).forEach((v) => p.append("portal", v));
  (f.tipos || []).forEach((t) => p.append("tipo", t));
  if (f.provincia_tid) p.set("provincia", f.provincia_tid);
  p.set("ciudad", f.ciudad_tid || "todas");
  (f.barrios_tid || []).forEach((b) => p.append("barrio", b));
  (f.barrios_id || []).forEach((b) => p.append("barrio_of", b));
  (f.zonas || []).forEach((z) => p.append("zona", z));
  if (f.antiguedad) p.set("publicado", f.antiguedad);
  if (f.descuento_min) p.set("descuento", f.descuento_min);
  if (f.repetidos && f.repetidos !== "agrupar") p.set("repetidos", f.repetidos);
  (f.dormitorios || []).forEach((d) => p.append("dorm", d));
  if (f.precio_desde) p.set("precio_desde", f.precio_desde);
  if (f.precio_hasta) p.set("precio_hasta", f.precio_hasta);
  if (f.moneda) p.set("moneda", f.moneda);
  if (f.superficie_desde) p.set("sup_desde", f.superficie_desde);
  if (f.superficie_hasta) p.set("sup_hasta", f.superficie_hasta);
  if (f.vendedor) p.set("vendedor", f.vendedor);
  if (f.apto_escritura) p.set("escritura", "si");
  (f.palabras || []).forEach((w) => p.append("palabra", w));
  return p.toString();
}

export function resumenFiltros(f, ubicaciones = [], barrios = []) {
  const nombre = (tid) => ubicaciones.find((u) => u.tid === Number(tid))?.nombre;
  const oficial = (id) => barrios.find((b) => b.id === Number(id))?.bonito;
  const partes = [];
  if (f.portales?.length === 1) partes.push(`Solo ${nombrePortal(f.portales[0])}`);
  if (f.tipos?.length) partes.push(f.tipos.map((t) => TIPOS.find((x) => x.valor === t)?.etiqueta || t).join(" y "));
  const lugar = f.barrios_id?.length
    ? f.barrios_id.map(oficial).filter(Boolean).join(", ")
    : f.barrios_tid?.length ? f.barrios_tid.map(nombre).filter(Boolean).join(", ") : nombre(f.ciudad_tid) || (f.ciudad_tid ? "" : "Toda la provincia");
  if (lugar) partes.push(lugar);
  if (f.zonas?.length) partes.push("Zona " + f.zonas.map(nombreZona).join(", "));
  if (f.descuento_min) partes.push(`${f.descuento_min} % o más debajo del m² de la zona`);
  if (f.repetidos === "solo") partes.push("Publicadas más de una vez");
  if (f.antiguedad) partes.push(`Publicados hace ${ANTIGUEDADES.find((a) => a.valor === f.antiguedad)?.etiqueta.toLowerCase()}`);
  if (f.dormitorios?.length) partes.push(f.dormitorios.map((d) => DORMITORIOS.find((x) => x.valor === d)?.etiqueta).join(", ") + " dorm.");
  const mon = f.moneda === "pesos" ? "$" : "U$S";
  if (f.precio_desde || f.precio_hasta)
    partes.push(`${mon} ${f.precio_desde ? Number(f.precio_desde).toLocaleString("es-AR") : "0"} a ${f.precio_hasta ? Number(f.precio_hasta).toLocaleString("es-AR") : "sin tope"}`);
  if (f.superficie_desde) partes.push(`desde ${f.superficie_desde} m²`);
  if (f.vendedor) partes.push(f.vendedor === "particular" ? "Particulares" : "Inmobiliarias");
  if (f.apto_escritura) partes.push("Apto escritura");
  if (f.palabras?.length) partes.push(`“${f.palabras.join("”, “")}”`);
  return partes.join(" · ") || "Todas las publicaciones";
}
