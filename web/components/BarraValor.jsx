// Barra que muestra qué tan lejos está el precio por m² publicado de un valor de referencia.
// Verde = por debajo (posible oportunidad), amarillo = en línea, rosa = por encima.
import { precio } from "@/lib/formato";

const RANGO = 40; // la barra va de 40 % abajo a 40 % arriba

export function desvio(precioM2, referencia) {
  if (!precioM2 || !referencia) return null;
  return (Number(precioM2) / Number(referencia) - 1) * 100;
}

export function textoDesvio(d) {
  if (d === null) return "";
  const n = Math.abs(d).toLocaleString("es-AR", { maximumFractionDigits: 0 });
  if (Math.abs(d) < 5) return "en línea con";
  return d < 0 ? `${n} % por debajo de` : `${n} % por encima de`;
}

export default function BarraValor({ precioM2, referencia, moneda = "USD", titulo, detalle, chica = false }) {
  const d = desvio(precioM2, referencia);
  if (d === null) return null;
  const pos = ((Math.max(-RANGO, Math.min(RANGO, d)) + RANGO) / (2 * RANGO)) * 100;
  const clase = d <= -10 ? "baja" : d >= 10 ? "suba" : "";
  return (
    <div className={`barra-valor${chica ? " chica" : ""}`}>
      {!chica && <div className="barra-titulo">{titulo}</div>}
      <div className="barra-pista" role="img" aria-label={`${textoDesvio(d)} ${titulo}`}>
        <span className="barra-marca" style={{ left: `${pos}%` }} />
        <span className="barra-centro" />
      </div>
      <div className="barra-texto">
        <span className={clase}>{d < 0 ? "▼" : d > 0 ? "▲" : ""} {textoDesvio(d)}</span>{" "}
        {chica ? titulo : <>la referencia ({precio(referencia, moneda)}/m²)</>}
      </div>
      {!chica && detalle && <div className="muted" style={{ fontSize: 13 }}>{detalle}</div>}
    </div>
  );
}
