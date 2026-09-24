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
export const PALABRAS_SUGERIDAS = ["a reciclar", "a refaccionar", "oportunidad", "sucesión", "dueño vende", "urgente"];
export const ESTADOS = ["Interesa", "Contactado", "Visitado", "Ofertado", "Descartado", "Comprado"];

const lista = (v) => (v === undefined ? [] : Array.isArray(v) ? v : [v]).filter(Boolean);
const numero = (v) => {
  const n = Number(String(v ?? "").replace(/\./g, "").replace(",", "."));
  return Number.isFinite(n) && n > 0 ? n : null;
};

export function filtrosDesdeParams(sp = {}) {
  return {
    portales: ["lavoz"],
    tipos: lista(sp.tipo),
    provincia_tid: numero(sp.provincia) ?? 3173,
    ciudad_tid: numero(sp.ciudad),
    barrios_tid: lista(sp.barrio).map(Number).filter(Boolean),
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
    orden: ["precio", "precio_m2"].includes(sp.orden) ? sp.orden : "nuevos",
  };
}

export function paramsDesdeFiltros(f) {
  const p = new URLSearchParams();
  (f.tipos || []).forEach((t) => p.append("tipo", t));
  if (f.provincia_tid) p.set("provincia", f.provincia_tid);
  if (f.ciudad_tid) p.set("ciudad", f.ciudad_tid);
  (f.barrios_tid || []).forEach((b) => p.append("barrio", b));
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

export function resumenFiltros(f, ubicaciones = []) {
  const nombre = (tid) => ubicaciones.find((u) => u.tid === Number(tid))?.nombre;
  const partes = [];
  if (f.tipos?.length) partes.push(f.tipos.map((t) => TIPOS.find((x) => x.valor === t)?.etiqueta || t).join(" y "));
  const lugar = f.barrios_tid?.length ? f.barrios_tid.map(nombre).filter(Boolean).join(", ") : nombre(f.ciudad_tid);
  if (lugar) partes.push(lugar);
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
