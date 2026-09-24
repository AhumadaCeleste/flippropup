export function precio(valor, moneda) {
  if (valor === null || valor === undefined) return "Consultar";
  const simbolo = moneda === "USD" ? "U$S" : "$";
  return `${simbolo} ${Math.round(Number(valor)).toLocaleString("es-AR")}`;
}

export function variacion(antes, ahora) {
  if (!antes || ahora === null || ahora === undefined) return null;
  return ((Number(ahora) - Number(antes)) / Number(antes)) * 100;
}

export function porcentaje(v) {
  return `${v < 0 ? "▼" : "▲"} ${Math.abs(v).toLocaleString("es-AR", { maximumFractionDigits: 1 })} %`;
}

export function diasDesde(fecha) {
  if (!fecha) return null;
  return Math.max(0, Math.floor((Date.now() - new Date(fecha).getTime()) / 86400000));
}

export function fechaCorta(fecha) {
  return new Date(fecha).toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });
}
