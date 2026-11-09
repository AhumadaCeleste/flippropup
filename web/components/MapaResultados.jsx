"use client";
// Mapa de resultados con Leaflet (se carga solo en el navegador).
import { useEffect, useRef } from "react";
import "leaflet/dist/leaflet.css";

const COLORES = { lavoz: "#38BDF8", mercadolibre: "#FACC15", inmoup: "#C084FC", cordobaprop: "#FB923C", inmobiliarias: "#F472B6" };
const NOMBRES = { lavoz: "La Voz", mercadolibre: "Mercado Libre", inmoup: "InmoUP", cordobaprop: "CórdobaProp", inmobiliarias: "Inmobiliarias" };

const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const precio = (p, m) => (p == null ? "Consultar" : `${m === "USD" ? "U$S" : "$"} ${Math.round(p).toLocaleString("es-AR")}`);

export default function MapaResultados({ puntos, alto = 560, centro = null }) {
  const caja = useRef(null);
  useEffect(() => {
    let mapa;
    let cancelado = false;
    import("leaflet").then(({ default: L }) => {
      if (cancelado || !caja.current) return;
      mapa = L.map(caja.current, { scrollWheelZoom: true }).setView(centro || [-31.4167, -64.1833], 13);
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      }).addTo(mapa);
      const capas = [];
      puntos.forEach((p) => {
        const color = p.destacado ? "#00F5A0" : COLORES[p.portal] || "#00F5A0";
        const m = L.circleMarker([Number(p.lat), Number(p.lng)], {
          radius: p.destacado ? 11 : 8, color: "#0F172A", weight: 2, fillColor: color, fillOpacity: 0.95,
        }).addTo(mapa);
        if (p.id) {
          m.bindPopup(`
            <div style="width:220px;font-family:inherit">
              ${p.foto_principal ? `<img src="${esc(p.foto_principal)}" alt="" style="width:100%;height:120px;object-fit:cover;border-radius:6px">` : ""}
              <div style="font-weight:800;font-size:17px;margin-top:6px">${esc(precio(p.precio, p.moneda))}</div>
              <div style="font-size:13px;margin:2px 0 6px">${esc(p.titulo)}</div>
              <div style="font-size:12px;opacity:.75">${esc(NOMBRES[p.portal] || p.portal)}${p.dormitorios ? " · " + esc(p.dormitorios) : ""}${p.superficie_total ? " · " + Math.round(p.superficie_total) + " m²" : ""}</div>
              <a href="/aviso/${p.id}" style="display:inline-block;margin-top:8px;font-weight:700">Ver ficha →</a>
            </div>`);
        } else if (p.etiqueta) {
          m.bindPopup(`<strong>${esc(p.etiqueta)}</strong>`);
        }
        capas.push(m);
      });
      if (capas.length > 1 && !centro) mapa.fitBounds(L.featureGroup(capas).getBounds().pad(0.1));
    });
    return () => { cancelado = true; if (mapa) mapa.remove(); };
  }, [puntos, centro]);

  return (
    <div>
      <div ref={caja} style={{ height: alto, borderRadius: 12, border: "1px solid var(--line)", overflow: "hidden" }} />
      <div className="opciones" style={{ marginTop: 8, fontSize: 13 }}>
        {Object.entries(NOMBRES).map(([k, n]) => (
          <span key={k} className="muted" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: 99, background: COLORES[k], display: "inline-block" }} /> {n}
          </span>
        ))}
      </div>
    </div>
  );
}
