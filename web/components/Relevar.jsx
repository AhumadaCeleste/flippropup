"use client";
// Relevar en la calle: foto + ubicación → ¿está publicado? (cerca, por calle o por el teléfono del cartel)
import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import MapaResultados from "@/components/MapaResultados";
import { buscarCerca, guardarRelevamiento } from "@/app/acciones";
import { supabaseNavegador } from "@/lib/supabase/client";
import { telefonosEnTexto } from "@/lib/telefono";
import { origenAviso } from "@/lib/filtros";

const precioTxt = (p, m) => (p == null ? "Consultar" : `${m === "USD" ? "U$S" : "$"} ${Math.round(p).toLocaleString("es-AR")}`);
const telVisible = (t) => { const d = String(t || "").replace(/^549/, ""); return d.length === 10 ? `${d.slice(0, 3)} ${d.slice(3, 6)}-${d.slice(6)}` : d; };
const NOMINATIM = "https://nominatim.openstreetmap.org";

function separarDireccion(texto) {
  const m = String(texto || "").match(/^\s*(.*?[a-záéíóúñ.]{3,}.*?)\s+(?:al\s+)?(\d{1,5})\b/i);
  return m ? { calle: m[1].replace(/^(av\.?|avenida|calle|bv\.?|bulevar|boulevard)\s+/i, "").trim(), altura: m[2] } : { calle: String(texto || "").split(",")[0].trim(), altura: "" };
}

async function achicarFoto(archivo, lado = 1600) {
  const img = await createImageBitmap(archivo);
  const escala = Math.min(1, lado / Math.max(img.width, img.height));
  const lienzo = document.createElement("canvas");
  lienzo.width = Math.round(img.width * escala);
  lienzo.height = Math.round(img.height * escala);
  lienzo.getContext("2d").drawImage(img, 0, 0, lienzo.width, lienzo.height);
  return new Promise((ok) => lienzo.toBlob(ok, "image/jpeg", 0.82));
}

function Resultado({ p }) {
  return (
    <Link href={`/aviso/${p.id}`} className="resultado-relevar">
      {p.foto_principal ? <img src={p.foto_principal} alt="" loading="lazy" /> : <span className="sin-foto" />}
      <span style={{ display: "grid", gap: 2, minWidth: 0 }}>
        <strong className="num">{precioTxt(p.precio, p.moneda)}</strong>
        <span className="titulo-corto">{p.titulo}</span>
        <span className="muted" style={{ fontSize: 13 }}>
          {origenAviso(p)}{p.barrio ? ` · ${p.barrio}` : ""}{p.distancia != null ? ` · a ${p.distancia} m` : ""}
          {p.mismaCuadra ? " · misma cuadra" : ""}{p.estado === "dado_de_baja" ? " · dado de baja" : ""}
        </span>
      </span>
    </Link>
  );
}

export default function Relevar() {
  const entrada = useRef(null);
  const [foto, setFoto] = useState(null);
  const [vista, setVista] = useState(null);
  const [punto, setPunto] = useState(null);
  const [direccion, setDireccion] = useState("");
  const [telefonos, setTelefonos] = useState([]);
  const [telefono, setTelefono] = useState("");
  const [nota, setNota] = useState("");
  const [res, setRes] = useState(null);
  const [estado, setEstado] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [guardado, setGuardado] = useState(false);

  async function nombreDelLugar(lat, lng) {
    try {
      const r = await fetch(`${NOMINATIM}/reverse?format=jsonv2&lat=${lat}&lon=${lng}&accept-language=es&addressdetails=1`);
      const d = await r.json();
      const a = d.address || {};
      return [a.road && `${a.road}${a.house_number ? " " + a.house_number : ""}`, a.suburb || a.neighbourhood || a.quarter, a.city || a.town || a.village]
        .filter(Boolean).join(", ") || d.display_name || "";
    } catch { return ""; }
  }

  function usarUbicacion() {
    if (!navigator.geolocation) { setEstado("Este navegador no da la ubicación. Escribí la dirección."); return; }
    setEstado("Buscando tu ubicación…");
    navigator.geolocation.getCurrentPosition(async (pos) => {
      const lat = pos.coords.latitude, lng = pos.coords.longitude;
      setPunto({ lat, lng, precision: Math.round(pos.coords.accuracy) });
      const dir = await nombreDelLugar(lat, lng);
      if (dir) setDireccion(dir);
      setEstado(`Ubicación tomada (precisión ±${Math.round(pos.coords.accuracy)} m). Revisá la dirección y tocá Buscar.`);
    }, () => setEstado("No pude tomar la ubicación (¿permiso denegado?). Escribí la dirección."), { enableHighAccuracy: true, timeout: 15000 });
  }

  async function ubicarDireccion() {
    if (!direccion.trim()) return null;
    setEstado("Ubicando la dirección…");
    try {
      const q = encodeURIComponent(`${direccion}, Córdoba, Argentina`);
      const r = await fetch(`${NOMINATIM}/search?format=jsonv2&limit=1&countrycodes=ar&accept-language=es&q=${q}`);
      const d = (await r.json())[0];
      if (d) { const p = { lat: Number(d.lat), lng: Number(d.lon) }; setPunto(p); return p; }
    } catch {}
    setEstado("No encontré esa dirección en el mapa; busco igual por la calle.");
    return null;
  }

  async function elegirFoto(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFoto(f); setVista(URL.createObjectURL(f)); setGuardado(false); setTelefonos([]);
    if (!punto) usarUbicacion();
  }

  async function leerCartel() {
    if (!foto) return;
    setOcupado(true); setEstado("Leyendo el cartel… (la primera vez tarda unos segundos)");
    try {
      const { createWorker } = await import("tesseract.js");
      const worker = await createWorker("spa");
      const { data } = await worker.recognize(foto);
      await worker.terminate();
      const tels = telefonosEnTexto(data.text);
      setTelefonos(tels);
      if (tels[0]) setTelefono(tels[0]);
      setEstado(tels.length ? `Encontré ${tels.length === 1 ? "un teléfono" : tels.length + " teléfonos"} en el cartel.` : "No pude leer un teléfono. Probá con una foto más cerca y derecha, o escribilo.");
    } catch (err) {
      setEstado("No pude leer la foto: " + err.message);
    }
    setOcupado(false);
  }

  async function buscar() {
    setOcupado(true);
    let p = punto;
    if (!p && direccion) p = await ubicarDireccion();
    const { calle, altura } = separarDireccion(direccion);
    setEstado("Buscando en lo publicado…");
    const tel = telefono ? telefonosEnTexto(telefono)[0] || null : null;
    const r = await buscarCerca({ lat: p?.lat, lng: p?.lng, calle, altura, telefono: tel });
    setRes({ ...r, calle, altura });
    const total = r.cerca.length + r.calle.length + r.telefono.length;
    setEstado(total ? "" : "No encontré nada publicado con estos datos en los portales que seguimos.");
    setOcupado(false);
  }

  async function guardar() {
    setOcupado(true); setEstado("Guardando…");
    let foto_path = null;
    try {
      if (foto) {
        const blob = await achicarFoto(foto);
        const ruta = `${new Date().toISOString().slice(0, 10)}/${Date.now()}.jpg`;
        const { error } = await supabaseNavegador().storage.from("relevamientos").upload(ruta, blob, { contentType: "image/jpeg" });
        if (error) throw new Error(error.message);
        foto_path = ruta;
      }
      const r = await guardarRelevamiento({ lat: punto?.lat, lng: punto?.lng, direccion, telefono: telefonosEnTexto(telefono)[0] || null, nota, foto_path });
      if (r?.error) throw new Error(r.error);
      setGuardado(true);
      setEstado("Guardado. Te avisamos por email si aparece un aviso cerca o con ese teléfono.");
    } catch (err) {
      setEstado("No se pudo guardar: " + err.message);
    }
    setOcupado(false);
  }

  const { calle, altura } = separarDireccion(direccion);
  const consultaWeb = encodeURIComponent(`${calle} ${altura} Córdoba venta`.trim());
  const puntos = useMemo(() => (res ? [
    ...(punto ? [{ lat: punto.lat, lng: punto.lng, destacado: true, etiqueta: "Acá estás" }] : []),
    ...res.cerca,
  ] : []), [res, punto]);
  const centroMapa = useMemo(() => (punto ? [punto.lat, punto.lng] : null), [punto]);

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section className="panel" style={{ display: "grid", gap: 16 }}>
        <div className="fila">
          <div style={{ display: "grid", gap: 10, alignContent: "start" }}>
            <span className="label">1 · Foto</span>
            <input ref={entrada} type="file" accept="image/*" capture="environment" onChange={elegirFoto} hidden />
            <button className="btn btn-principal" onClick={() => entrada.current?.click()}>📷 {foto ? "Sacar otra foto" : "Sacar foto"}</button>
            {vista && <img src={vista} alt="Foto del lugar" style={{ borderRadius: 10, maxHeight: 260, objectFit: "cover" }} />}
            {foto && <button className="btn" onClick={leerCartel} disabled={ocupado}>Leer teléfono del cartel</button>}
          </div>
          <div style={{ display: "grid", gap: 10, alignContent: "start" }}>
            <span className="label">2 · Dónde</span>
            <button className="btn" onClick={usarUbicacion} disabled={ocupado}>📍 Usar mi ubicación</button>
            <label className="campo"><span>Dirección</span>
              <input type="text" value={direccion} onChange={(e) => { setDireccion(e.target.value); setPunto(null); }} placeholder="Ej.: Av. Colón 1200, Alberdi" />
            </label>
            <label className="campo"><span>Teléfono del cartel (opcional)</span>
              <input type="text" inputMode="tel" value={telefono} onChange={(e) => setTelefono(e.target.value)} placeholder="351 123-4567" />
            </label>
            {telefonos.length > 1 && (
              <div className="opciones">{telefonos.map((t) => (
                <button key={t} className={`btn btn-chico${telefono === t ? " btn-activo" : ""}`} onClick={() => setTelefono(t)}>{telVisible(t)}</button>
              ))}</div>
            )}
            <button className="btn btn-principal" onClick={buscar} disabled={ocupado || (!punto && !direccion && !telefono)}>¿Está publicado?</button>
          </div>
        </div>
        {estado && <p className="muted" style={{ margin: 0 }} role="status">{estado}</p>}
      </section>

      {res && (
        <section className="panel" style={{ display: "grid", gap: 16 }}>
          <h2>Resultados</h2>
          {telefonosEnTexto(telefono)[0] && (
            <a className="btn btn-whatsapp" style={{ justifySelf: "start" }} target="_blank" rel="noopener noreferrer"
               href={`https://wa.me/${telefonosEnTexto(telefono)[0]}?text=${encodeURIComponent(`Hola, vi el cartel de venta en ${direccion || "la propiedad"}. ¿Me pasás precio y datos?`)}`}>
              Escribir por WhatsApp al {telVisible(telefonosEnTexto(telefono)[0])}
            </a>
          )}
          {res.telefono.length > 0 && (<div className="bloque-relevar"><span className="label">Con el teléfono del cartel · {res.telefono.length}</span>{res.telefono.map((p) => <Resultado key={p.id} p={p} />)}</div>)}
          {punto && (
            <div style={{ display: "grid", gap: 8 }}>
              <span className="label">A menos de 250 m · {res.cerca.length}</span>
              <MapaResultados puntos={puntos} alto={320} centro={centroMapa} />
              {res.cerca.map((p) => <Resultado key={p.id} p={p} />)}
            </div>
          )}
          {res.calle.length > 0 && (<div className="bloque-relevar"><span className="label">Que mencionan “{res.calle && calle}” · {res.calle.length}</span>{res.calle.slice(0, 20).map((p) => <Resultado key={p.id} p={p} />)}</div>)}
          <div style={{ display: "grid", gap: 8 }}>
            <span className="label">Buscar en otros lados</span>
            <div className="opciones">
              {punto && <a className="btn btn-chico" target="_blank" rel="noopener noreferrer" href={`https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${punto.lat},${punto.lng}`}>Street View</a>}
              <a className="btn btn-chico" target="_blank" rel="noopener noreferrer" href={`https://www.google.com/search?q=${consultaWeb}`}>Google</a>
              <a className="btn btn-chico" target="_blank" rel="noopener noreferrer" href={`https://www.google.com/search?q=site%3Azonaprop.com.ar+${consultaWeb}`}>Zonaprop</a>
              <a className="btn btn-chico" target="_blank" rel="noopener noreferrer" href={`https://www.google.com/search?q=site%3Aargenprop.com+${consultaWeb}`}>Argenprop</a>
              <a className="btn btn-chico" target="_blank" rel="noopener noreferrer" href={`https://www.google.com/search?q=site%3Amercadolibre.com.ar+${consultaWeb}`}>Mercado Libre</a>
            </div>
          </div>
        </section>
      )}

      {(foto || direccion) && (
        <section className="panel" style={{ display: "grid", gap: 12 }}>
          <h2>Guardar relevamiento</h2>
          <textarea value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Ej.: casa a reciclar, techo de chapa, cartel de dueño. Vecino dice que piden U$S 70 mil." />
          <button className="btn btn-principal" style={{ justifySelf: "start" }} onClick={guardar} disabled={ocupado || guardado}>
            {guardado ? "Guardado ✓" : "Guardar y avisarme si se publica"}
          </button>
        </section>
      )}
    </div>
  );
}
