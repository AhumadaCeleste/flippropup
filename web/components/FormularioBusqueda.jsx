"use client";
import { useMemo, useState } from "react";
import { TIPOS, DORMITORIOS, PALABRAS_SUGERIDAS, PORTALES, ZONAS, ANTIGUEDADES, CORDOBA_CAPITAL, CORDOBA_PROVINCIA as CORDOBA } from "@/lib/filtros";
import { guardarBusqueda } from "@/app/acciones";

function Opcion({ name, value, checked, children }) {
  return (
    <label className="opcion">
      <input type="checkbox" name={name} value={value} defaultChecked={checked} />
      <span>{children}</span>
    </label>
  );
}

export default function FormularioBusqueda({ ubicaciones, filtros, oficiales = [] }) {
  const provincias = ubicaciones.filter((u) => u.tipo === "provincia");
  const [provincia, setProvincia] = useState(String(filtros.provincia_tid || CORDOBA));
  const [ciudad, setCiudad] = useState(filtros.ciudad_tid ? String(filtros.ciudad_tid) : "todas");
  const capital = ciudad === String(CORDOBA_CAPITAL) && oficiales.length > 0;
  const [barrios, setBarrios] = useState((filtros.barrios_id.length ? filtros.barrios_id : filtros.barrios_tid).map(String));
  const [zonas, setZonas] = useState(filtros.zonas);
  const [filtroBarrio, setFiltroBarrio] = useState("");
  const [error, setError] = useState("");

  const ciudades = useMemo(() => {
    const lista = ubicaciones.filter((u) => u.tipo === "ciudad" && String(u.padre_tid) === provincia);
    return lista.length ? lista : [{ tid: CORDOBA_CAPITAL, nombre: "Córdoba" }];
  }, [ubicaciones, provincia]);
  // En Córdoba capital se usan los barrios oficiales de la Municipalidad (con su zona);
  // en el resto de las ciudades, los de La Voz.
  const barriosCiudad = useMemo(
    () => capital
      ? oficiales.map((b) => ({ tid: b.id, nombre: b.bonito, zona: b.zona }))
      : ubicaciones.filter((u) => u.tipo === "barrio" && String(u.padre_tid) === ciudad),
    [ubicaciones, oficiales, ciudad, capital]
  );
  const sinAcento = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const visibles = barriosCiudad.filter((b) =>
    sinAcento(b.nombre).includes(sinAcento(filtroBarrio)) && (!capital || !zonas.length || zonas.includes(b.zona)));
  const alternarZona = (z) => setZonas((l) => (l.includes(z) ? l.filter((x) => x !== z) : [...l, z]));
  const nombreBarrio = (tid) => barriosCiudad.find((b) => String(b.tid) === tid)?.nombre || tid;

  function alternarBarrio(tid) {
    setBarrios((b) => (b.includes(tid) ? b.filter((x) => x !== tid) : [...b, tid]));
  }

  function validar(e) {
    const f = new FormData(e.currentTarget);
    const n = (k) => Number(String(f.get(k) || "").replace(/\./g, "")) || 0;
    if (n("precio_desde") && n("precio_hasta") && n("precio_desde") > n("precio_hasta")) {
      e.preventDefault();
      setError("El precio “desde” no puede ser mayor que el “hasta”.");
      return;
    }
    if (n("sup_desde") && n("sup_hasta") && n("sup_desde") > n("sup_hasta")) {
      e.preventDefault();
      setError("La superficie “desde” no puede ser mayor que la “hasta”.");
      return;
    }
    setError("");
  }

  return (
    <form className="panel" method="get" action="/buscar" onSubmit={validar} style={{ display: "grid", gap: 20 }}>
      <div className="fila">
        <div className="campo">
          <span>Portales</span>
          <div className="opciones">
            {PORTALES.map((x) => (
              <Opcion key={x.valor} name="portal" value={x.valor} checked={filtros.portales.includes(x.valor)}>{x.etiqueta}</Opcion>
            ))}
          </div>
        </div>
        <div className="campo">
          <span>Tipo de propiedad</span>
          <div className="opciones">
            {TIPOS.map((t) => (
              <Opcion key={t.valor} name="tipo" value={t.valor} checked={filtros.tipos.includes(t.valor)}>{t.etiqueta}</Opcion>
            ))}
          </div>
        </div>
      </div>

      <div className="fila">
        <label className="campo">
          <span>Provincia</span>
          <select name="provincia" value={provincia} onChange={(e) => { setProvincia(e.target.value); setCiudad(""); setBarrios([]); }}>
            {(provincias.length ? provincias : [{ tid: CORDOBA, nombre: "Córdoba" }]).map((p) => (
              <option key={p.tid} value={p.tid}>{p.nombre}</option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span>Ciudad</span>
          <select name="ciudad" value={ciudad} onChange={(e) => { setCiudad(e.target.value); setBarrios([]); setZonas([]); }}>
            <option value="todas">Todas las ciudades</option>
            {ciudades.map((c) => <option key={c.tid} value={c.tid}>{c.nombre}</option>)}
          </select>
        </label>
        {capital && (
          <div className="campo">
            <span>Zona</span>
            <div className="opciones">
              {ZONAS.map((z) => (
                <label key={z.valor} className="opcion">
                  <input type="checkbox" name="zona" value={z.valor} checked={zonas.includes(z.valor)} onChange={() => alternarZona(z.valor)} />
                  <span>{z.etiqueta}</span>
                </label>
              ))}
            </div>
          </div>
        )}
        <div className="campo">
          <span>Barrios {barrios.length ? `(${barrios.length})` : ""}</span>
          {ciudad !== "todas" && barriosCiudad.length ? (
            <>
              <input type="search" placeholder="Escribí para filtrar barrios" value={filtroBarrio} onChange={(e) => setFiltroBarrio(e.target.value)} />
              <div className="lista-barrios">
                {visibles.map((b) => (
                  <label key={b.tid}>
                    <input type="checkbox" checked={barrios.includes(String(b.tid))} onChange={() => alternarBarrio(String(b.tid))} />
                    {b.nombre}
                  </label>
                ))}
                {!visibles.length && <span className="muted" style={{ padding: 6 }}>Ningún barrio coincide.</span>}
              </div>
            </>
          ) : (
            <span className="muted" style={{ fontSize: 14 }}>
              {ciudad !== "todas" ? "La lista de barrios se carga cuando el robot corre por primera vez." : "Elegí una ciudad para ver sus barrios."}
            </span>
          )}
          {barrios.length > 0 && (
            <div className="elegidos">
              {barrios.map((tid) => (
                <button type="button" key={tid} className="chip chip-acento" onClick={() => alternarBarrio(tid)} aria-label={`Quitar ${nombreBarrio(tid)}`}>
                  {nombreBarrio(tid)} ×
                </button>
              ))}
            </div>
          )}
          {barrios.map((tid) => <input key={tid} type="hidden" name={capital ? "barrio_of" : "barrio"} value={tid} />)}
        </div>
      </div>

      <div className="fila">
        <div className="campo">
          <span>Dormitorios</span>
          <div className="opciones">
            {DORMITORIOS.map((d) => (
              <Opcion key={d.valor} name="dorm" value={d.valor} checked={filtros.dormitorios.includes(d.valor)}>{d.etiqueta}</Opcion>
            ))}
          </div>
        </div>
        <div className="campo">
          <span>Precio</span>
          <div className="fila-2" style={{ gridTemplateColumns: "1fr 1fr 90px" }}>
            <input type="number" name="precio_desde" min="0" step="1000" placeholder="Desde" defaultValue={filtros.precio_desde || ""} aria-label="Precio desde" />
            <input type="number" name="precio_hasta" min="0" step="1000" placeholder="Hasta" defaultValue={filtros.precio_hasta || ""} aria-label="Precio hasta" />
            <select name="moneda" defaultValue={filtros.moneda} aria-label="Moneda">
              <option value="dolares">U$S</option>
              <option value="pesos">$</option>
            </select>
          </div>
        </div>
        <div className="campo">
          <span>Superficie total (m²)</span>
          <div className="fila-2">
            <input type="number" name="sup_desde" min="0" placeholder="Desde" defaultValue={filtros.superficie_desde || ""} aria-label="Superficie desde" />
            <input type="number" name="sup_hasta" min="0" placeholder="Hasta" defaultValue={filtros.superficie_hasta || ""} aria-label="Superficie hasta" />
          </div>
        </div>
      </div>

      <div className="fila">
        <label className="campo">
          <span>Vendedor</span>
          <select name="vendedor" defaultValue={filtros.vendedor || ""}>
            <option value="">Todos</option>
            <option value="particular">Particular (dueño directo)</option>
            <option value="inmobiliaria">Inmobiliaria</option>
          </select>
        </label>
        <label className="campo">
          <span>Antigüedad de la publicación</span>
          <select name="publicado" defaultValue={filtros.antiguedad || ""}>
            <option value="">Cualquiera</option>
            {ANTIGUEDADES.map((a) => <option key={a.valor} value={a.valor}>{a.etiqueta}</option>)}
          </select>
        </label>
        <div className="campo">
          <span>Condiciones</span>
          <div className="opciones">
            <Opcion name="escritura" value="si" checked={filtros.apto_escritura}>Apto escritura</Opcion>
          </div>
        </div>
        <label className="campo">
          <span>Ordenar por</span>
          <select name="orden" defaultValue={filtros.orden}>
            <option value="puntaje">Mejor oportunidad (puntaje)</option>
            <option value="nuevos">Más nuevos</option>
            <option value="antiguos">Publicados hace más tiempo</option>
            <option value="precio">Menor precio</option>
            <option value="precio_m2">Menor precio por m²</option>
          </select>
        </label>
      </div>

      <div className="campo">
        <span>Palabras clave (aparece al menos una)</span>
        <div className="opciones">
          {PALABRAS_SUGERIDAS.map((w) => (
            <Opcion key={w} name="palabra" value={w} checked={filtros.palabras.includes(w)}>{w}</Opcion>
          ))}
        </div>
        <input
          type="text"
          name="palabras_libres"
          placeholder="Otras palabras, separadas por coma"
          defaultValue={filtros.palabras.filter((w) => !PALABRAS_SUGERIDAS.includes(w)).join(", ")}
        />
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <button type="submit" className="btn btn-principal">Buscar</button>
        <details>
          <summary className="btn">Guardar búsqueda</summary>
          <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
            <input type="text" name="nombre" placeholder="Nombre, por ejemplo: Alta Córdoba a reciclar" style={{ minWidth: 280 }} />
            <button type="submit" formAction={guardarBusqueda} className="btn btn-principal">Guardar y sumar al email diario</button>
          </div>
        </details>
      </div>
    </form>
  );
}
