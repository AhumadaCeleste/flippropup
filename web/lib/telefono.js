// Teléfonos argentinos → "549" + área + número (misma lógica que scraper/telefonos.py).
const CANDIDATO = /(?:\+?54[\s.-]?)?(?:9[\s.-]?)?\(?0?\d{2,4}\)?[\s.-]?(?:15[\s.-]?)?\d{3,4}[\s.-]?\d{3,6}/g;

export function normalizarTelefono(numero) {
  let d = String(numero || "").replace(/\D/g, "");
  if (d.startsWith("549")) d = d.slice(3);
  else if (d.startsWith("54")) d = d.slice(2);
  d = d.replace(/^0+/, "");
  if (d.length === 12) {
    for (const largo of [2, 3, 4]) {
      if (d.slice(largo, largo + 2) === "15") { d = d.slice(0, largo) + d.slice(largo + 2); break; }
    }
  }
  if (d.length !== 10 || !"123".includes(d[0])) return null;
  return "549" + d;
}

export function telefonosEnTexto(texto) {
  const encontrados = [];
  for (const m of String(texto || "").matchAll(CANDIDATO)) {
    const t = normalizarTelefono(m[0]);
    if (t && !encontrados.includes(t)) encontrados.push(t);
  }
  return encontrados;
}
