// Termómetro de oportunidad: compara el precio por m² publicado con una referencia.
// A la derecha (rojo, "caliente") = más barato que la referencia = mejor oportunidad.
// A la izquierda (gris) = más caro. El punto se ubica en el porcentaje real, en una escala de ±50 %.
import { precio } from "@/lib/formato";

const RANGO = 50;
const M2_VALIDO = (v) => Number(v) >= 100 && Number(v) <= 10000; // fuera de esto, la superficie está mal cargada

export function desvio(precioM2, referencia) {
  if (!precioM2 || !referencia || !M2_VALIDO(precioM2)) return null;
  return (Number(precioM2) / Number(referencia) - 1) * 100;
}

const pct = (d) => Math.abs(d).toLocaleString("es-AR", { maximumFractionDigits: 0 });

export function textoDesvio(d) {
  if (d === null) return "";
  if (Math.abs(d) < 5) return "en línea con";
  return d < 0 ? `${pct(d)} % más barato que` : `${pct(d)} % más caro que`;
}

export default function BarraValor({ precioM2, referencia, moneda = "USD", titulo, detalle, chica = false }) {
  const d = desvio(precioM2, referencia);
  if (d === null) return null;
  // descuento positivo = más barato; 0 % queda al centro, +50 % a la derecha, −50 % a la izquierda
  const descuento = -d;
  const fuera = Math.abs(descuento) > RANGO;
  const pos = ((Math.max(-RANGO, Math.min(RANGO, descuento)) + RANGO) / (2 * RANGO)) * 100;
  const clase = descuento >= 10 ? "oportunidad" : descuento <= -10 ? "caro" : "";
  return (
    <div className={`barra-valor${chica ? " chica" : ""}`}>
      {!chica && <div className="barra-titulo">{titulo}</div>}
      <div className="barra-pista" role="img" aria-label={`${textoDesvio(d)} ${titulo}`}>
        <span className="barra-centro" />
        <span className={`barra-marca${fuera ? " fuera" : ""}`} style={{ left: `${pos}%` }} />
      </div>
      {!chica && (
        <div className="barra-escala" aria-hidden="true">
          <span>50 % más caro</span><span>igual</span><span>50 % más barato</span>
        </div>
      )}
      <div className="barra-texto">
        <span className={clase}>{descuento >= 5 ? "▼" : descuento <= -5 ? "▲" : ""} {textoDesvio(d)}</span>{" "}
        {chica ? titulo : <>la referencia ({precio(referencia, moneda)}/m²)</>}
      </div>
      {!chica && detalle && <div className="muted" style={{ fontSize: 13 }}>{detalle}</div>}
    </div>
  );
}
