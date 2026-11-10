import Link from "next/link";
import { notFound } from "next/navigation";
import { supabaseServidor } from "@/lib/supabase/server";
import { precio, variacion, porcentaje, diasDesde, fechaCorta } from "@/lib/formato";
import { seguir, dejarDeSeguir, agregarNota, guardarObjetivo, guardarCierre } from "@/app/acciones";
import GraficoPrecios from "@/components/GraficoPrecios";
import SelectorEstado from "@/components/SelectorEstado";
import { origenAviso } from "@/lib/filtros";
import BotonWhatsApp, { telefonoVisible, telefonoDe } from "@/components/BotonWhatsApp";
import MapaResultados from "@/components/MapaResultados";
import BarraValor from "@/components/BarraValor";
import CalculadoraFlip from "@/components/CalculadoraFlip";
import { Puntaje } from "@/components/Tarjeta";
import { nombreZona } from "@/lib/filtros";

const NIVEL = { barrio: "del mismo barrio", zona: "de la misma zona", ciudad: "de toda la ciudad", tipo: "del mismo tipo" };

export default async function Aviso({ params }) {
  const { id } = await params;
  const supabase = await supabaseServidor();
  const { data: p } = await supabase.from("publicaciones").select("*").eq("id", id).single();
  if (!p) notFound();
  const [{ data: historial }, { data: seg }, { data: notas }] = await Promise.all([
    supabase.from("historial_precios").select("precio,moneda,fecha").eq("publicacion_id", id).order("fecha"),
    supabase.from("seguimientos").select("*").eq("publicacion_id", id).maybeSingle(),
    supabase.from("notas").select("*").eq("publicacion_id", id).order("creada", { ascending: false }),
  ]);
  const cambio = seg ? variacion(seg.precio_inicial, p.precio) : null;
  const dias = diasDesde(p.publicado_desde || p.fecha_publicacion || p.primera_vez);
  const { data: barrioOficial } = p.barrio_id
    ? await supabase.from("barrios").select("bonito,zona").eq("id", p.barrio_id).maybeSingle()
    : { data: null };
  const { data: hermanos } = p.grupo_id
    ? await supabase.from("publicaciones")
        .select("id,portal,url,titulo,precio,moneda,precio_m2,superficie_total,vendedor_tipo,vendedor_nombre,telefono,descripcion,publicado_desde,fecha_publicacion,primera_vez,estado")
        .eq("grupo_id", p.grupo_id).order("precio", { ascending: true })
    : { data: [] };
  // Lo que cerraron en operaciones propias de la misma zona: cuánto debajo de lo publicado.
  const { data: cierres } = await supabase.from("seguimientos")
    .select("precio_cierre, publicaciones!inner(precio, moneda, zona)")
    .not("precio_cierre", "is", null).eq("publicaciones.zona", p.zona || "-");
  const descuentosCierre = (cierres || [])
    .filter((c) => c.publicaciones?.precio && c.publicaciones.moneda === p.moneda)
    .map((c) => (1 - Number(c.precio_cierre) / Number(c.publicaciones.precio)) * 100)
    .filter((d) => d > -20 && d < 60);
  const descuentoZona = descuentosCierre.length ? descuentosCierre.reduce((a, b) => a + b, 0) / descuentosCierre.length : null;
  const mapaIdecor = p.lat && p.lng ? `https://mapascordoba.gob.ar/viewer/mapa/548?lat=${p.lat}&lng=${p.lng}&zoom=18` : "https://mapascordoba.gob.ar/viewer/mapa/548";
  const fotos = p.fotos || [];

  return (
    <>
      <div className="encabezado">
        <div style={{ display: "grid", gap: 6 }}>
          <Link href="/buscar" className="muted" style={{ fontSize: 14 }}>← Volver a resultados</Link>
          <h1>{p.titulo}</h1>
          <span className="muted">{[p.barrio, p.ciudad, p.provincia].filter(Boolean).join(", ")}</span>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {seg ? (
            <form action={dejarDeSeguir.bind(null, p.id)}><button className="btn btn-activo">★ Siguiendo</button></form>
          ) : (
            <form action={seguir.bind(null, p.id)}><button className="btn btn-principal">☆ Seguir</button></form>
          )}
          <BotonWhatsApp p={p} chico={false} siempre />
          <a className="btn" href={p.url} target="_blank" rel="noopener noreferrer">Ver en {origenAviso(p)}</a>
        </div>
      </div>

      <div className="ficha">
        <div style={{ display: "grid", gap: 24 }}>
          {fotos.length > 0 && (
            <div className="galeria">
              {fotos.map((f, i) => <a key={i} href={f} target="_blank" rel="noopener noreferrer"><img src={f} alt={`Foto ${i + 1}`} loading="lazy" /></a>)}
            </div>
          )}
          <section className="panel" style={{ display: "grid", gap: 12 }}>
            <h2>Historial de precios</h2>
            <GraficoPrecios historial={historial || []} moneda={p.moneda} />
          </section>
          <section className="panel" style={{ display: "grid", gap: 12 }}>
            <h2>Descripción</h2>
            <p style={{ whiteSpace: "pre-line", margin: 0 }}>{p.descripcion}</p>
          </section>
        </div>

        <aside style={{ display: "grid", gap: 24 }}>
          <section className="panel" style={{ display: "grid", gap: 16 }}>
            <div>
              <div className="precio" style={{ fontSize: 32, lineHeight: "38px" }}>{precio(p.precio, p.moneda)}</div>
              {cambio ? <div className={cambio < 0 ? "baja" : "suba"}>{porcentaje(cambio)} desde que la seguimos</div> : null}
              {p.puntaje !== null && p.puntaje !== undefined && (
                <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
                  <Puntaje valor={p.puntaje} /><span className="muted" style={{ fontSize: 13 }}>puntaje de oportunidad (0 a 100)</span>
                </div>
              )}
              {p.estado === "dado_de_baja" && <span className="chip chip-peligro">Dado de baja</span>}
            </div>
            {p.idecor_m2 && p.precio_m2 ? (
              <BarraValor precioM2={p.precio_m2} referencia={p.idecor_m2} titulo="Índice IDECOR"
                detalle={<>{p.idecor_base}{p.idecor_parcela ? ` · parcela ${p.idecor_parcela}` : ""} · <a href={mapaIdecor} target="_blank" rel="noopener noreferrer">ver en Mapas Córdoba</a></>} />
            ) : p.tipo === "departamento" ? (
              <p className="muted" style={{ margin: 0, fontSize: 13 }}>IDECOR no publica valores de departamentos: se compara con el mercado.</p>
            ) : null}
            {p.ref_m2 && p.precio_m2 ? (
              <BarraValor precioM2={p.precio_m2} referencia={p.ref_m2} titulo="Mercado (avisos parecidos)"
                detalle={`Mediana de ${p.ref_n} avisos ${NIVEL[p.ref_nivel] || ""}${p.dormitorios ? `, ${p.dormitorios.toLowerCase()}` : ""}.`} />
            ) : null}
            <dl>
              <dt>Precio por m²</dt><dd className="num">{p.precio_m2 ? precio(p.precio_m2, p.moneda) : "—"}</dd>
              <dt>Superficie total</dt><dd className="num">{p.superficie_total ? `${Math.round(p.superficie_total)} m²` : "—"}</dd>
              <dt>Dormitorios</dt><dd>{p.dormitorios || "—"}</dd>
              <dt>Baños</dt><dd>{p.banos || "—"}</dd>
              <dt>Apto escritura</dt><dd>{p.apto_escritura || "—"}</dd>
              <dt>Apto crédito</dt><dd>{p.apto_credito || "—"}</dd>
              <dt>Vendedor</dt><dd>{p.vendedor_tipo}{p.vendedor_nombre ? ` · ${p.vendedor_nombre}` : ""}</dd>
              <dt>Teléfono</dt><dd>{telefonoDe(p) ? <a href={`tel:+${telefonoDe(p)}`}>{telefonoVisible(telefonoDe(p))}</a> : <span className="muted">Pedilo en el portal</span>}</dd>
              <dt>Publicado</dt><dd>{dias !== null ? `hace ${dias} días` : "—"}{p.fecha_publicacion ? ` (${fechaCorta(p.fecha_publicacion)})` : ""}</dd>
              <dt>Lo encontramos</dt><dd>{fechaCorta(p.primera_vez)}</dd>
              {barrioOficial && <><dt>Barrio oficial</dt><dd>{barrioOficial.bonito} · zona {nombreZona(barrioOficial.zona).toLowerCase()}</dd></>}
            </dl>
            {p.lat && p.lng && (
              <>
                <MapaResultados alto={240} centro={[Number(p.lat), Number(p.lng)]}
                  puntos={[{ lat: p.lat, lng: p.lng, portal: p.portal, destacado: true, etiqueta: p.titulo }]} />
                <span className="muted" style={{ fontSize: 13 }}>Ubicación aproximada: la mayoría de los portales no publica la altura exacta.</span>
                <a className="btn btn-chico" href={`https://www.google.com/maps?q=${p.lat},${p.lng}`} target="_blank" rel="noopener noreferrer">Abrir en Google Maps (Street View)</a>
              </>
            )}
          </section>

          {(hermanos || []).length > 1 && (() => {
            const activos = hermanos.filter((h) => h.estado === "activo");
            const precios = activos.map((h) => Number(h.precio)).filter(Boolean);
            const min = Math.min(...precios), max = Math.max(...precios);
            const anunciantes = new Set(activos.map((h) => (h.vendedor_nombre || origenAviso(h)).toLowerCase())).size;
            const dueno = activos.find((h) => h.vendedor_tipo === "Particular");
            const primero = [...activos].sort((a, b) => String(a.publicado_desde || a.primera_vez).localeCompare(String(b.publicado_desde || b.primera_vez)))[0];
            return (
              <section className="panel" id="repetidos" style={{ display: "grid", gap: 12 }}>
                <h2>Publicada {activos.length} veces</h2>
                <p style={{ margin: 0 }}>
                  La misma propiedad aparece en {activos.length} avisos de {anunciantes} anunciante{anunciantes === 1 ? "" : "s"}.
                  {max > min && <> Entre el más barato y el más caro hay <strong className="baja">{precio(max - min, p.moneda)}</strong> ({((max / min - 1) * 100).toLocaleString("es-AR", { maximumFractionDigits: 1 })} %).</>}
                </p>
                <table className="tabla-repetidos">
                  <thead><tr><th>Anunciante</th><th style={{ textAlign: "right" }}>Precio</th><th style={{ textAlign: "right" }}>Publicado</th><th>Contacto</th></tr></thead>
                  <tbody>
                    {activos.map((h) => {
                      const dias = diasDesde(h.publicado_desde || h.fecha_publicacion || h.primera_vez);
                      const dif = Number(h.precio) - min;
                      return (
                        <tr key={h.id} className={`${h.id === p.id ? "este" : ""}${Number(h.precio) === min ? " mejor" : ""}`}>
                          <td>
                            <strong>{h.vendedor_tipo === "Particular" ? "Dueño directo" : h.vendedor_nombre || origenAviso(h)}</strong>
                            <div className="muted" style={{ fontSize: 13 }}>{origenAviso(h)}{h.id === p.id ? " · este aviso" : ""}</div>
                          </td>
                          <td className="num">{precio(h.precio, h.moneda)}{dif > 0 && <div className="muted" style={{ fontSize: 12 }}>+{precio(dif, h.moneda)}</div>}</td>
                          <td className="num">{dias !== null ? `hace ${dias} días` : "—"}</td>
                          <td>
                            <div className="acciones">
                              <BotonWhatsApp p={h} siempre />
                              {telefonoDe(h) && <a className="btn btn-chico" href={`tel:+${telefonoDe(h)}`}>{telefonoVisible(telefonoDe(h))}</a>}
                              <a className="btn btn-chico" href={h.url} target="_blank" rel="noopener noreferrer">Ver</a>
                              {h.id !== p.id && <a className="btn btn-chico" href={`/aviso/${h.id}`}>Ficha</a>}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <div className="muted" style={{ fontSize: 14, display: "grid", gap: 4 }}>
                  <strong style={{ color: "var(--text)" }}>Cómo usarlo para negociar</strong>
                  {max > min && <span>· Consultá a los más caros mencionando que la viste a {precio(min, p.moneda)}: suelen igualar o mejorar.</span>}
                  {dueno && <span>· Hay un aviso de dueño directo: empezá por ahí, sin comisión de por medio.</span>}
                  {anunciantes > 1 && <span>· Con {anunciantes} anunciantes, preguntá a cada uno cuánto acepta el propietario y cuál es su comisión.</span>}
                  {primero && <span>· El aviso más antiguo ({primero.vendedor_nombre || origenAviso(primero)}) suele ser quien tiene la relación directa con el dueño.</span>}
                </div>
              </section>
            );
          })()}

          {p.moneda === "USD" && (
            <section className="panel" style={{ display: "grid", gap: 12 }}>
              <h2>Calculadora de flip</h2>
              <CalculadoraFlip precio={p.precio} m2={p.superficie_total} referenciaM2={p.ref_m2 || p.idecor_m2}
                descuentoZona={descuentoZona} cierres={descuentosCierre.length} minimoPublicado={p.grupo_n > 1 ? Number(p.grupo_min) : null} />
            </section>
          )}

          {seg && (
            <section className="panel" style={{ display: "grid", gap: 12 }}>
              <h2>Seguimiento</h2>
              <label className="campo"><span>Estado</span><SelectorEstado id={p.id} estado={seg.estado} /></label>
              <form action={guardarCierre.bind(null, p.id)} className="campo">
                <span>Precio de cierre (si se vendió o lo compraste)</span>
                <div style={{ display: "flex", gap: 8 }}>
                  <input type="number" name="cierre" min="0" step="500" defaultValue={seg.precio_cierre ?? ""} placeholder={`Publicado ${precio(p.precio, p.moneda)}`} />
                  <button className="btn btn-chico">Guardar</button>
                </div>
                {seg.precio_cierre ? (
                  <small className="muted">
                    Cerró {((1 - Number(seg.precio_cierre) / Number(p.precio)) * 100).toLocaleString("es-AR", { maximumFractionDigits: 1 })} % debajo de lo publicado. Este dato alimenta el descuento de negociación de la zona.
                  </small>
                ) : <small className="muted">Cargalo cuando sepas el precio real: así la app aprende cuánto se negocia en cada zona.</small>}
              </form>
              <form action={guardarObjetivo.bind(null, p.id)} className="campo">
                <span>Precio objetivo (te avisamos si llega)</span>
                <div style={{ display: "flex", gap: 8 }}>
                  <input type="number" name="objetivo" min="0" step="1000" defaultValue={seg.precio_objetivo ?? ""} />
                  <button className="btn btn-chico">Guardar</button>
                </div>
              </form>
            </section>
          )}

          <section className="panel notas" id="notas">
            <h2>Notas</h2>
            <form action={agregarNota.bind(null, p.id)} style={{ display: "grid", gap: 8 }}>
              <textarea name="texto" placeholder="Por ejemplo: llamé, acepta ofertas; techo a revisar." required />
              <button className="btn btn-chico" style={{ justifySelf: "start" }}>Agregar nota</button>
            </form>
            {(notas || []).map((n) => (
              <div key={n.id} className="nota">
                <div style={{ whiteSpace: "pre-line" }}>{n.texto}</div>
                <div className="muted" style={{ fontSize: 13 }}>{n.autor} · {fechaCorta(n.creada)}</div>
              </div>
            ))}
          </section>
        </aside>
      </div>
    </>
  );
}
