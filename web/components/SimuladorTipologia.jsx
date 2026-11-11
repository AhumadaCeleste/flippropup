"use client";
// Simulador por barrio: con los precios típicos de un barrio estima compra, obra, venta y ganancia de un flip.
import { useMemo, useState } from "react";

const n0 = (v) => (Number.isFinite(v) ? Math.round(v).toLocaleString("es-AR") : "—");

export default function SimuladorTipologia({ barrios = [], tipo }) {
  const [id, setId] = useState(barrios[0]?.id ?? "");
  const b = barrios.find((x) => String(x.id) === String(id));
  const compraBase = b ? Math.round(b.reciclar || b.p25 || b.mediana) : 0;
  const ventaBase = b ? Math.round(b.listo || b.mediana * 1.1) : 0;

  const [m2, setM2] = useState(tipo === "casa" ? 120 : 60);
  const [compraM2, setCompraM2] = useState(null);
  const [ventaM2, setVentaM2] = useState(null);
  const [obraM2, setObraM2] = useState(tipo === "terreno" ? 0 : 250);
  const [gastos, setGastos] = useState(7);
  const [meses, setMeses] = useState(6);

  const cm2 = compraM2 ?? compraBase;
  const vm2 = ventaM2 ?? ventaBase;
  const r = useMemo(() => {
    const compra = cm2 * m2;
    const inversion = compra * (1 + gastos / 100) + obraM2 * m2;
    const venta = vm2 * m2 * 0.96; // 4 % de comisión y gastos de venta
    const ganancia = venta - inversion;
    const retorno = inversion ? ganancia / inversion : 0;
    const anual = meses > 0 ? Math.pow(1 + retorno, 12 / meses) - 1 : 0;
    return { compra, inversion, venta, ganancia, retorno, anual };
  }, [cm2, vm2, m2, obraM2, gastos, meses]);

  if (!barrios.length) return <p className="muted">Todavía no hay barrios con suficientes avisos para simular.</p>;

  const cambiarBarrio = (v) => { setId(v); setCompraM2(null); setVentaM2(null); };
  const num = (set) => (e) => set(e.target.value === "" ? 0 : Number(e.target.value));

  return (
    <div className="simulador">
      <div className="simulador-campos">
        <label>Barrio
          <select value={id} onChange={(e) => cambiarBarrio(e.target.value)}>
            {barrios.map((x) => <option key={x.id} value={x.id}>{x.nombre} ({x.activos})</option>)}
          </select>
        </label>
        <label>Superficie (m²)<input type="number" min="10" value={m2} onChange={num(setM2)} /></label>
        <label>Compra U$S/m²<input type="number" value={cm2} onChange={num(setCompraM2)} /></label>
        <label>Obra U$S/m²<input type="number" value={obraM2} onChange={num(setObraM2)} /></label>
        <label>Venta U$S/m²<input type="number" value={vm2} onChange={num(setVentaM2)} /></label>
        <label>Gastos de compra %<input type="number" value={gastos} onChange={num(setGastos)} /></label>
        <label>Meses hasta vender<input type="number" min="1" value={meses} onChange={num(setMeses)} /></label>
      </div>
      {b && (
        <p className="muted chico">
          En {b.nombre}: precio típico U$S {n0(b.mediana)}/m², el 25 % más barato desde U$S {n0(b.p25)}/m²
          {b.reciclar ? `, a reciclar U$S ${n0(b.reciclar)}/m²` : ""}{b.listo ? `, refaccionado U$S ${n0(b.listo)}/m²` : ""}.
          {b.vida ? ` Los que se vendieron o retiraron estuvieron publicados unos ${n0(b.vida)} días.` : ""}
        </p>
      )}
      <div className="simulador-resultado">
        <div><span>Comprás a</span><strong>U$S {n0(r.compra)}</strong></div>
        <div><span>Invertís en total</span><strong>U$S {n0(r.inversion)}</strong></div>
        <div><span>Vendés (neto)</span><strong>U$S {n0(r.venta)}</strong></div>
        <div className={r.ganancia >= 0 ? "resultado-bueno" : "resultado-malo"}>
          <span>Ganancia</span><strong>U$S {n0(r.ganancia)}</strong>
          <em>{(r.retorno * 100).toFixed(1)} % · {(r.anual * 100).toFixed(0)} % anual</em>
        </div>
      </div>
    </div>
  );
}
