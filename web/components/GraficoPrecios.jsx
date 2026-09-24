import { precio, fechaCorta } from "@/lib/formato";

// Línea de precio en el tiempo, dibujada a escala.
export default function GraficoPrecios({ historial, moneda }) {
  const puntos = historial.filter((h) => h.precio !== null);
  if (puntos.length < 2) {
    return <p className="muted">Sin cambios de precio desde que lo encontramos{puntos[0] ? ` (${fechaCorta(puntos[0].fecha)})` : ""}.</p>;
  }
  const W = 640, H = 200, M = { l: 90, r: 20, t: 16, b: 32 };
  const xs = puntos.map((p) => new Date(p.fecha).getTime());
  const ys = puntos.map((p) => Number(p.precio));
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const pad = (Math.max(...ys) - Math.min(...ys)) * 0.15 || Math.max(...ys) * 0.05;
  const y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
  const X = (t) => M.l + ((t - x0) / (x1 - x0 || 1)) * (W - M.l - M.r);
  const Y = (v) => M.t + (1 - (v - y0) / (y1 - y0)) * (H - M.t - M.b);
  // escalonada: el precio se mantiene hasta el cambio siguiente
  let d = `M${X(xs[0])},${Y(ys[0])}`;
  for (let i = 1; i < puntos.length; i++) d += ` H${X(xs[i])} V${Y(ys[i])}`;
  const marcas = [y1 - pad, (y0 + y1) / 2, y0 + pad];
  return (
    <div style={{ overflowX: "auto" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: W, display: "block" }} role="img" aria-label="Historial de precios">
        {marcas.map((m, i) => (
          <g key={i}>
            <line x1={M.l} x2={W - M.r} y1={Y(m)} y2={Y(m)} stroke="var(--line)" strokeDasharray="3 4" />
            <text x={M.l - 8} y={Y(m) + 4} textAnchor="end" fontSize="12" fill="var(--text-muted)">{precio(m, moneda)}</text>
          </g>
        ))}
        <path d={d} fill="none" stroke="var(--accent)" strokeWidth="2.5" />
        {puntos.map((p, i) => <circle key={i} cx={X(xs[i])} cy={Y(ys[i])} r="4" fill="var(--accent)" />)}
        <text x={M.l} y={H - 8} fontSize="12" fill="var(--text-muted)">{fechaCorta(puntos[0].fecha)}</text>
        <text x={W - M.r} y={H - 8} fontSize="12" fill="var(--text-muted)" textAnchor="end">{fechaCorta(puntos.at(-1).fecha)}</text>
      </svg>
    </div>
  );
}
