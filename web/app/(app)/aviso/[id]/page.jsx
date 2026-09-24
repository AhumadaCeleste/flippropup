import Link from "next/link";
import { notFound } from "next/navigation";
import { supabaseServidor } from "@/lib/supabase/server";
import { precio, variacion, porcentaje, diasDesde, fechaCorta } from "@/lib/formato";
import { seguir, dejarDeSeguir, agregarNota, guardarObjetivo } from "@/app/acciones";
import GraficoPrecios from "@/components/GraficoPrecios";
import SelectorEstado from "@/components/SelectorEstado";

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
  const dias = diasDesde(p.fecha_publicacion || p.primera_vez);
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
          <a className="btn" href={p.url} target="_blank" rel="noopener noreferrer">Ver en La Voz</a>
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
              {p.estado === "dado_de_baja" && <span className="chip chip-peligro">Dado de baja</span>}
            </div>
            <dl>
              <dt>Precio por m²</dt><dd className="num">{p.precio_m2 ? precio(p.precio_m2, p.moneda) : "—"}</dd>
              <dt>Superficie total</dt><dd className="num">{p.superficie_total ? `${Math.round(p.superficie_total)} m²` : "—"}</dd>
              <dt>Dormitorios</dt><dd>{p.dormitorios || "—"}</dd>
              <dt>Baños</dt><dd>{p.banos || "—"}</dd>
              <dt>Apto escritura</dt><dd>{p.apto_escritura || "—"}</dd>
              <dt>Apto crédito</dt><dd>{p.apto_credito || "—"}</dd>
              <dt>Vendedor</dt><dd>{p.vendedor_tipo}{p.vendedor_nombre ? ` · ${p.vendedor_nombre}` : ""}</dd>
              <dt>Publicado</dt><dd>{dias !== null ? `hace ${dias} días` : "—"}</dd>
              <dt>Lo encontramos</dt><dd>{fechaCorta(p.primera_vez)}</dd>
            </dl>
            {p.lat && p.lng && (
              <a className="btn btn-chico" href={`https://www.google.com/maps?q=${p.lat},${p.lng}`} target="_blank" rel="noopener noreferrer">Ver en el mapa</a>
            )}
          </section>

          {seg && (
            <section className="panel" style={{ display: "grid", gap: 12 }}>
              <h2>Seguimiento</h2>
              <label className="campo"><span>Estado</span><SelectorEstado id={p.id} estado={seg.estado} /></label>
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
