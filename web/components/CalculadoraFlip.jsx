"use client";
// Calculadora rápida de compra, refacción y reventa. Todo en dólares; los valores iniciales salen del aviso.
import { useState } from "react";

const usd = (v) => `U$S ${Math.round(v).toLocaleString("es-AR")}`;

export default function CalculadoraFlip({ precio, m2, referenciaM2, descuentoZona = null, cierres = 0, minimoPublicado = null }) {
  const negociacion = descuentoZona !== null ? Math.max(0, Math.round(descuentoZona * 10) / 10) : 8;
  const base = minimoPublicado && minimoPublicado < precio ? minimoPublicado : precio;
  const [v, setV] = useState({
    compra: base ? Math.round(base) : "",
    descCompra: negociacion,
    descVenta: descuentoZona !== null ? negociacion : 5,
    m2: m2 ? Math.round(m2) : "",
    gastosCompra: 7,
    refaccionM2: 250,
    ventaM2: referenciaM2 ? Math.round(referenciaM2 * 1.1) : "",
    gastosVenta: 4,
    meses: 6,
  });
  const n = (k) => Number(v[k]) || 0;
  const cambiar = (k) => (e) => setV({ ...v, [k]: e.target.value });

  const compraReal = n("compra") * (1 - n("descCompra") / 100);
  const inversion = compraReal * (1 + n("gastosCompra") / 100) + n("refaccionM2") * n("m2");
  const venta = n("ventaM2") * n("m2") * (1 - n("descVenta") / 100);
  const ventaNeta = venta * (1 - n("gastosVenta") / 100);
  const ganancia = ventaNeta - inversion;
  const roi = inversion > 0 ? (ganancia / inversion) * 100 : 0;
  const anual = n("meses") > 0 ? (Math.pow(1 + roi / 100, 12 / n("meses")) - 1) * 100 : 0;
  const listo = n("compra") > 0 && n("m2") > 0 && n("ventaM2") > 0;

  const Campo = ({ k, etiqueta, paso = 1 }) => (
    <label className="fila-calc">
      <span>{etiqueta}</span>
      <input type="number" min="0" step={paso} value={v[k]} onChange={cambiar(k)} />
    </label>
  );

  return (
    <div className="calculadora">
      {Campo({ k: "compra", etiqueta: minimoPublicado && minimoPublicado < precio ? "Precio publicado (el más bajo de sus avisos, U$S)" : "Precio publicado (U$S)", paso: 1000 })}
      {Campo({ k: "descCompra", etiqueta: "Descuento que esperás negociar al comprar (%)", paso: 0.5 })}
      {Campo({ k: "m2", etiqueta: "Superficie (m²)" })}
      {Campo({ k: "gastosCompra", etiqueta: "Gastos de compra (escritura y comisión, %)", paso: 0.5 })}
      {Campo({ k: "refaccionM2", etiqueta: "Refacción (U$S por m²)", paso: 10 })}
      {Campo({ k: "ventaM2", etiqueta: "Precio de lista al revender (U$S por m²)", paso: 10 })}
      {Campo({ k: "descVenta", etiqueta: "Descuento al cerrar la venta (%)", paso: 0.5 })}
      {Campo({ k: "gastosVenta", etiqueta: "Gastos de venta (%)", paso: 0.5 })}
      {Campo({ k: "meses", etiqueta: "Meses hasta vender" })}
      {listo ? (
        <div className="resultado">
          <span>Compra negociada</span><strong>{usd(compraReal)}</strong>
          <span>Inversión total</span><strong>{usd(inversion)}</strong>
          <span>Venta neta</span><strong>{usd(ventaNeta)}</strong>
          <span>Ganancia</span><strong className={ganancia >= 0 ? "baja" : "suba"}>{usd(ganancia)}</strong>
          <span>Retorno</span><strong className={roi >= 0 ? "baja" : "suba"}>{roi.toLocaleString("es-AR", { maximumFractionDigits: 1 })} %</strong>
          <span>Retorno anualizado</span><strong>{anual.toLocaleString("es-AR", { maximumFractionDigits: 1 })} %</strong>
        </div>
      ) : (
        <p className="muted" style={{ margin: 0, fontSize: 14 }}>Completá precio, superficie y precio de venta por m² para ver el resultado.</p>
      )}
      <p className="muted" style={{ margin: 0, fontSize: 13 }}>
        El precio de lista sugerido es la referencia de la zona más un 10 % por estar refaccionado.{" "}
        {cierres > 0
          ? `Los descuentos salen de ${cierres} cierre${cierres === 1 ? "" : "s"} que cargaste en esta zona.`
          : "Los descuentos son un valor inicial: a medida que cargues precios de cierre en tus seguimientos, se calculan por zona."}
      </p>
    </div>
  );
}
