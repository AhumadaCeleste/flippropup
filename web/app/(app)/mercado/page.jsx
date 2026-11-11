// Módulo Mercado: oportunidades destacadas y análisis del mercado de Córdoba capital, escrito para que
// cualquiera lo pueda leer. Los números salen de la foto diaria que guarda el robot (tabla mercado_diario)
// y de las señales de cada aviso (bajas de precio, días publicado, precio frente a la zona).
import Link from "next/link";
import { supabaseServidor } from "@/lib/supabase/server";
import { precio, diasDesde } from "@/lib/formato";
import { ZONAS, nombreZona, origenAviso } from "@/lib/filtros";
import SimuladorTipologia from "@/components/SimuladorTipologia";

export const dynamic = "force-dynamic";

const TIPOS = [
  { valor: "departamento", etiqueta: "Departamentos" },
  { valor: "casa", etiqueta: "Casas" },
  { valor: "terreno", etiqueta: "Terrenos" },
];
const OBRA_M2 = 250; // costo de refacción de referencia, U$S por m²

const n0 = (v) => (v === null || v === undefined ? "—" : Math.round(Number(v)).toLocaleString("es-AR"));
const pct = (v, dec = 0) => (v === null || v === undefined ? "—" : `${(Number(v) * 100).toLocaleString("es-AR", { maximumFractionDigits: dec })} %`);
const hoyMenos = (dias) => new Date(Date.now() - dias * 86400000).toISOString().slice(0, 10);

function Explicacion({ children }) {
  return <p className="como-leer"><strong>Cómo leerlo:</strong> {children}</p>;
}

function Dato({ titulo, valor, detalle }) {
  return (
    <div className="dato-mercado">
      <div className="dato-titulo">{titulo}</div>
      <div className="dato-valor">{valor}</div>
      {detalle && <div className="dato-detalle">{detalle}</div>}
    </div>
  );
}

function Barra({ valor, maximo }) {
  const ancho = maximo > 0 ? Math.max(2, Math.min(100, (Number(valor) / maximo) * 100)) : 0;
  return <span className="barra-h" aria-hidden="true"><span style={{ width: `${ancho}%` }} /></span>;
}

function Item({ p, senal }) {
  const dias = diasDesde(p.publicado_desde || p.primera_vez);
  return (
    <li className="item-oportunidad">
      <Link href={`/aviso/${p.id}`} className="item-enlace">
        {p.foto_principal ? <img src={p.foto_principal} alt="" loading="lazy" /> : <span className="item-sin-foto" />}
        <span className="item-texto">
          <span className="item-senal">{senal}</span>
          <strong>{precio(p.precio, p.moneda)}</strong>
          <span className="item-titulo">{p.titulo}</span>
          <span className="muted">
            {[p.barrio, p.dormitorios, p.superficie_total ? `${n0(p.superficie_total)} m²` : null, dias !== null ? `${dias} días publicado` : null]
              .filter(Boolean).join(" · ")}
          </span>
          <span className="muted">{p.vendedor_tipo === "Particular" ? "Dueño directo" : p.vendedor_nombre || origenAviso(p)}{p.grupo_n > 1 ? ` · publicada ${p.grupo_n} veces` : ""}</span>
        </span>
      </Link>
    </li>
  );
}

export default async function Mercado({ searchParams }) {
  const sp = await searchParams;
  const tipo = TIPOS.some((t) => t.valor === sp.tipo) ? sp.tipo : "departamento";
  const zona = ZONAS.some((z) => z.valor === sp.zona) ? sp.zona : null;
  const supabase = await supabaseServidor();

  const { data: ultima } = await supabase.from("mercado_diario").select("fecha").order("fecha", { ascending: false }).limit(1);
  const fecha = ultima?.[0]?.fecha;
  if (!fecha) {
    return (
      <div>
        <h1>Mercado</h1>
        <p className="muted">Todavía no hay datos: el robot arma la foto del mercado en su próxima corrida.</p>
      </div>
    );
  }

  const base = (q) => {
    q = q.eq("estado", "activo").eq("tipo", tipo).not("barrio_id", "is", null);
    return zona ? q.eq("zona", zona) : q;
  };
  const campos = "id,titulo,precio,moneda,precio_m2,superficie_total,dormitorios,barrio,foto_principal,publicado_desde,primera_vez,vendedor_tipo,vendedor_nombre,portal,grupo_n,bajas_n,baja_total_pct,precio_maximo,ultima_baja,desvio_ref,ref_m2";
  const hace90 = hoyMenos(90);

  const [
    { data: filas },
    { data: anteriores },
    { data: barrios },
    { data: bajaron },
    { data: apurados },
    { data: baratos },
    { data: captacion },
    { data: anunciantes },
  ] = await Promise.all([
    supabase.from("mercado_diario").select("*").eq("fecha", fecha).eq("tipo", tipo),
    supabase.from("mercado_diario").select("barrio_id,zona,mediana_m2,activos,fecha").eq("tipo", tipo)
      .lte("fecha", hoyMenos(28)).gte("fecha", hoyMenos(45)).order("fecha", { ascending: false }),
    supabase.from("barrios").select("id,bonito,zona").range(0, 999),
    base(supabase.from("publicaciones").select(campos)).gte("ultima_baja", new Date(Date.now() - 7 * 86400000).toISOString())
      .order("baja_total_pct", { ascending: false }).limit(8),
    base(supabase.from("publicaciones").select(campos)).or(`bajas_n.gte.2,and(bajas_n.gte.1,publicado_desde.lte.${hace90})`)
      .order("baja_total_pct", { ascending: false }).limit(8),
    base(supabase.from("publicaciones").select(campos)).lte("desvio_ref", -0.2).order("desvio_ref", { ascending: true }).limit(8),
    base(supabase.from("publicaciones").select(campos)).eq("vendedor_tipo", "Particular").lte("publicado_desde", hace90)
      .or("bajas_n.is.null,bajas_n.eq.0").order("publicado_desde", { ascending: true }).limit(8),
    supabase.rpc("ranking_anunciantes", { p_tipo: tipo, p_zona: zona }),
  ]);

  const nombre = Object.fromEntries((barrios || []).map((b) => [b.id, b.bonito]));
  const porBarrio = (filas || []).filter((f) => f.barrio_id !== 0 && (!zona || f.zona === zona));
  const ciudad = (filas || []).find((f) => f.barrio_id === 0);
  const anterior = {};
  for (const a of anteriores || []) if (!anterior[a.barrio_id]) anterior[a.barrio_id] = a;

  // Resumen de la zona elegida (o de la ciudad)
  const suma = (k) => porBarrio.reduce((s, f) => s + (f[k] || 0), 0);
  const resumen = zona
    ? { activos: suma("activos"), bajaron_7d: suma("bajaron_7d"), con_bajas: suma("con_bajas"), salidas_30d: suma("salidas_30d"),
        mediana_m2: null, dias_publicado: null, descuento_salida: null }
    : ciudad || {};

  // Dónde conviene reciclar: diferencia entre el m² refaccionado y el m² a reciclar del mismo barrio.
  const reciclar = porBarrio
    .filter((f) => f.m2_reciclar && f.m2_listo && f.n_reciclar >= 2 && f.n_listo >= 3)
    .map((f) => ({ ...f, diferencia: f.m2_listo - f.m2_reciclar, margen: (f.m2_listo - f.m2_reciclar - OBRA_M2) / (f.m2_reciclar + OBRA_M2) }))
    .sort((a, b) => b.margen - a.margen)
    .slice(0, 12);
  const maxDif = Math.max(1, ...reciclar.map((f) => f.diferencia));

  // Por zona: velocidad y tendencia
  const zonas = ZONAS.map((z) => {
    const fs = (filas || []).filter((f) => f.barrio_id !== 0 && f.zona === z.valor);
    const act = fs.reduce((s, f) => s + (f.activos || 0), 0);
    const ponderado = (k) => {
      const v = fs.filter((f) => f[k] !== null && f.activos);
      const peso = v.reduce((s, f) => s + f.activos, 0);
      return peso ? v.reduce((s, f) => s + Number(f[k]) * f.activos, 0) / peso : null;
    };
    const antes = fs.map((f) => anterior[f.barrio_id]).filter(Boolean);
    const pesoAntes = antes.reduce((s, a) => s + (a.activos || 0), 0);
    const m2Antes = pesoAntes ? antes.reduce((s, a) => s + Number(a.mediana_m2 || 0) * (a.activos || 0), 0) / pesoAntes : null;
    const m2 = ponderado("mediana_m2");
    return {
      ...z, activos: act, m2, dias: ponderado("dias_publicado"),
      conBajas: act ? fs.reduce((s, f) => s + (f.con_bajas || 0), 0) / act : null,
      salidas: fs.reduce((s, f) => s + (f.salidas_30d || 0), 0),
      descuento: ponderado("descuento_salida"),
      tendencia: m2 && m2Antes ? m2 / m2Antes - 1 : null,
    };
  }).filter((z) => z.activos > 0 && (!zona || z.valor === zona));

  // Barrios con más oferta
  const oferta = [...porBarrio].sort((a, b) => b.activos - a.activos).slice(0, 15);
  const maxOferta = Math.max(1, ...oferta.map((f) => f.activos));

  const opcionesSimulador = porBarrio
    .filter((f) => f.mediana_m2 && f.activos >= 5)
    .map((f) => ({ id: f.barrio_id, nombre: nombre[f.barrio_id] || `Barrio ${f.barrio_id}`, mediana: f.mediana_m2, p25: f.p25_m2,
                   reciclar: f.m2_reciclar, listo: f.m2_listo, vida: f.vida_salidas, dias: f.dias_publicado, activos: f.activos }))
    .sort((a, b) => a.nombre.localeCompare(b.nombre));

  const etiquetaTipo = TIPOS.find((t) => t.valor === tipo).etiqueta.toLowerCase();

  return (
    <div className="mercado" style={{ display: "grid", gap: 28 }}>
      <header style={{ display: "grid", gap: 12 }}>
        <h1 style={{ margin: 0 }}>Mercado · Córdoba capital</h1>
        <p className="muted" style={{ margin: 0 }}>
          Lo que conviene mirar hoy y cómo se mueve el mercado de {etiquetaTipo}{zona ? ` en la zona ${nombreZona(zona).toLowerCase()}` : ""}.
          Datos del {new Date(fecha + "T12:00:00").toLocaleDateString("es-AR")}, de todos los portales que recorre el robot.
        </p>
        <form className="filtros-mercado" method="get">
          <select name="tipo" defaultValue={tipo} aria-label="Tipo de propiedad">
            {TIPOS.map((t) => <option key={t.valor} value={t.valor}>{t.etiqueta}</option>)}
          </select>
          <select name="zona" defaultValue={zona || ""} aria-label="Zona">
            <option value="">Toda la ciudad</option>
            {ZONAS.map((z) => <option key={z.valor} value={z.valor}>Zona {z.etiqueta.toLowerCase()}</option>)}
          </select>
          <button className="btn btn-chico">Ver</button>
        </form>
      </header>

      <section className="datos-mercado" aria-label="Resumen">
        <Dato titulo="Avisos activos" valor={n0(resumen.activos)} detalle={`${etiquetaTipo} publicados hoy`} />
        <Dato titulo="Precio típico" valor={resumen.mediana_m2 ? `U$S ${n0(resumen.mediana_m2)}/m²` : "—"} detalle={zona ? "ver tabla por zona" : "la mitad está por debajo"} />
        <Dato titulo="Bajaron de precio" valor={n0(resumen.bajaron_7d)} detalle="en los últimos 7 días" />
        <Dato titulo="Tiempo publicado" valor={resumen.dias_publicado ? `${n0(resumen.dias_publicado)} días` : "—"} detalle="mitad de los avisos activos" />
        <Dato titulo="Salieron del mercado" valor={n0(resumen.salidas_30d)} detalle={resumen.descuento_salida ? `habían bajado ${pct(resumen.descuento_salida)} antes` : "últimos 30 días"} />
      </section>

      <section className="panel" style={{ display: "grid", gap: 16 }}>
        <div>
          <h2 style={{ margin: 0 }}>Oportunidades para mirar hoy</h2>
          <Explicacion>cada lista junta avisos con una señal distinta de que el precio puede negociarse. Tocá uno para ver su ficha, el historial de precios y si está publicado varias veces.</Explicacion>
        </div>
        <div className="columnas-oportunidades">
          <div>
            <h3>Bajaron de precio esta semana</h3>
            <p className="muted chico">Ordenados por cuánto bajaron desde su precio más alto.</p>
            {bajaron?.length ? (
              <ul className="lista-oportunidades">
                {bajaron.map((p) => <Item key={p.id} p={p} senal={<span className="senal-caliente">▼ {pct(p.baja_total_pct, 1)} · antes {precio(p.precio_maximo, p.moneda)}</span>} />)}
              </ul>
            ) : <p className="muted chico">Ninguno esta semana. El historial se arma día a día: en unas semanas esta lista va a tener movimiento.</p>}
          </div>
          <div>
            <h3>Vendedores apurados</h3>
            <p className="muted chico">Bajaron dos veces o más, o llevan más de 3 meses y ya bajaron.</p>
            {apurados?.length ? (
              <ul className="lista-oportunidades">
                {apurados.map((p) => <Item key={p.id} p={p} senal={<span className="senal-caliente">{p.bajas_n} baja{p.bajas_n === 1 ? "" : "s"} · ▼ {pct(p.baja_total_pct, 1)} en total</span>} />)}
              </ul>
            ) : <p className="muted chico">Todavía no hay avisos con varias bajas registradas.</p>}
          </div>
          <div>
            <h3>Más baratos que su barrio</h3>
            <p className="muted chico">Precio por m² 20 % o más debajo de avisos parecidos del mismo barrio.</p>
            {baratos?.length ? (
              <ul className="lista-oportunidades">
                {baratos.map((p) => <Item key={p.id} p={p} senal={<span className="senal-caliente">{pct(-p.desvio_ref)} más barato · zona U$S {n0(p.ref_m2)}/m²</span>} />)}
              </ul>
            ) : <p className="muted chico">Ninguno con este filtro.</p>}
          </div>
        </div>
      </section>

      {tipo !== "terreno" && (
        <section className="panel" style={{ display: "grid", gap: 12 }}>
          <h2 style={{ margin: 0 }}>Dónde conviene reciclar</h2>
          <Explicacion>
            para cada barrio comparamos el precio por m² de lo que se publica "a reciclar" contra lo refaccionado o a estrenar.
            La diferencia es lo que gana valor una propiedad al arreglarla. El margen ya descuenta una obra de U$S {OBRA_M2}/m²
            y está calculado sobre lo invertido (compra + obra). Con pocos avisos el dato es orientativo.
          </Explicacion>
          {reciclar.length ? (
            <div className="tabla-scroll">
              <table className="tabla-mercado">
                <thead><tr><th>Barrio</th><th className="num">A reciclar</th><th className="num">Refaccionado</th><th>Diferencia por m²</th><th className="num">Margen después de obra</th><th className="num">Avisos</th></tr></thead>
                <tbody>
                  {reciclar.map((f) => (
                    <tr key={f.barrio_id}>
                      <td><strong>{nombre[f.barrio_id]}</strong><div className="muted chico">zona {nombreZona(f.zona).toLowerCase()}</div></td>
                      <td className="num">U$S {n0(f.m2_reciclar)}</td>
                      <td className="num">U$S {n0(f.m2_listo)}</td>
                      <td><span className="celda-barra"><Barra valor={f.diferencia} maximo={maxDif} /><span className="num">U$S {n0(f.diferencia)}</span></span></td>
                      <td className={`num ${f.margen > 0.15 ? "senal-caliente" : f.margen < 0 ? "muted" : ""}`}><strong>{pct(f.margen)}</strong></td>
                      <td className="num">{f.n_reciclar} / {f.n_listo}{f.n_reciclar < 4 && <div className="muted chico">pocos datos</div>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="muted">Todavía hay pocos avisos que digan "a reciclar" en estos barrios para comparar.</p>}
        </section>
      )}

      <section className="panel" style={{ display: "grid", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Qué tan rápido se mueve cada zona</h2>
        <Explicacion>
          "Con bajas" es la parte de los avisos que ya bajó de precio alguna vez: cuanto más alto, más dispuestos a negociar están los vendedores.
          "Salieron" son los avisos que dejaron de publicarse en los últimos 30 días (vendidos o retirados) y cuánto habían bajado antes de salir:
          es lo más parecido a un precio de cierre que se puede saber. La tendencia compara el m² típico de hoy con el de hace un mes.
        </Explicacion>
        <div className="tabla-scroll">
          <table className="tabla-mercado">
            <thead><tr><th>Zona</th><th className="num">Avisos</th><th className="num">m² típico</th><th className="num">Días publicado</th><th className="num">Con bajas</th><th className="num">Salieron (30 días)</th><th className="num">Bajaron antes de salir</th><th className="num">Tendencia del m²</th></tr></thead>
            <tbody>
              {zonas.map((z) => (
                <tr key={z.valor}>
                  <td><Link href={`/mercado?tipo=${tipo}&zona=${z.valor}`}><strong>{z.etiqueta}</strong></Link></td>
                  <td className="num">{n0(z.activos)}</td>
                  <td className="num">U$S {n0(z.m2)}</td>
                  <td className="num">{z.dias ? n0(z.dias) : "—"}</td>
                  <td className="num">{pct(z.conBajas)}</td>
                  <td className="num">{n0(z.salidas)}</td>
                  <td className="num">{z.descuento !== null ? pct(z.descuento, 1) : "—"}</td>
                  <td className="num">{z.tendencia === null ? <span className="muted">en un mes</span> : <span className={z.tendencia < 0 ? "senal-caliente" : ""}>{z.tendencia < 0 ? "▼" : "▲"} {pct(Math.abs(z.tendencia), 1)}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel" style={{ display: "grid", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Barrios con más oferta</h2>
        <Explicacion>
          los barrios con más avisos activos. "El 25 % más barato" es el precio por m² por debajo del cual está una de cada cuatro propiedades:
          comprar ahí o más abajo es comprar barato para ese barrio. Mucha oferta y muchas bajas suelen dar más margen para negociar.
        </Explicacion>
        <div className="tabla-scroll">
          <table className="tabla-mercado">
            <thead><tr><th>Barrio</th><th>Avisos activos</th><th className="num">m² típico</th><th className="num">El 25 % más barato</th><th className="num">Bajaron (7 días)</th><th className="num">Nuevos (7 días)</th></tr></thead>
            <tbody>
              {oferta.map((f) => (
                <tr key={f.barrio_id}>
                  <td><strong>{nombre[f.barrio_id]}</strong><div className="muted chico">zona {nombreZona(f.zona).toLowerCase()}</div></td>
                  <td><span className="celda-barra"><Barra valor={f.activos} maximo={maxOferta} /><span className="num">{n0(f.activos)}</span></span></td>
                  <td className="num">U$S {n0(f.mediana_m2)}</td>
                  <td className="num">U$S {n0(f.p25_m2)}</td>
                  <td className="num">{n0(f.bajaron_7d)}</td>
                  <td className="num">{n0(f.nuevos_7d)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel" style={{ display: "grid", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Simulador por barrio</h2>
        <Explicacion>
          elegí un barrio y una superficie. La compra se toma al precio del 25 % más barato del barrio (o al de los avisos "a reciclar" si hay),
          y la venta al precio de lo refaccionado (o al típico más un 10 %). Cambiá cualquier valor para probar otros escenarios.
        </Explicacion>
        <SimuladorTipologia barrios={opcionesSimulador} tipo={tipo} />
      </section>

      <section className="panel" style={{ display: "grid", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Inmobiliarias con más avisos</h2>
        <Explicacion>
          quién tiene más {etiquetaTipo} publicados{zona ? " en esta zona" : ""}. "Con bajas" muestra qué parte de su cartera ya bajó de precio;
          "frente al barrio" dice si suele publicar más caro (+) o más barato (−) que el resto; "repetidas" son propiedades que también publica otro anunciante.
        </Explicacion>
        <div className="tabla-scroll">
          <table className="tabla-mercado">
            <thead><tr><th>Inmobiliaria</th><th className="num">Avisos</th><th className="num">Con bajas</th><th className="num">Frente al barrio</th><th className="num">Repetidas</th></tr></thead>
            <tbody>
              {(anunciantes || []).map((a) => (
                <tr key={a.anunciante}>
                  <td><strong>{a.anunciante}</strong></td>
                  <td className="num">{n0(a.avisos)}</td>
                  <td className="num">{pct(a.avisos ? a.con_bajas / a.avisos : null)}</td>
                  <td className="num">{a.desvio_mediano === null ? "—" : `${a.desvio_mediano > 0 ? "+" : "−"}${pct(Math.abs(a.desvio_mediano))}`}</td>
                  <td className="num">{n0(a.repetidos)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel" style={{ display: "grid", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Dueños directos para captar</h2>
        <Explicacion>
          particulares que publican hace más de 3 meses y todavía no bajaron el precio. Suelen estar cansados de vender solos:
          son candidatos para ofrecerles el servicio de una inmobiliaria o para hacerles una oferta directa.
        </Explicacion>
        {captacion?.length ? (
          <ul className="lista-oportunidades lista-horizontal">
            {captacion.map((p) => <Item key={p.id} p={p} senal={<span>Dueño directo · {diasDesde(p.publicado_desde)} días sin bajar</span>} />)}
          </ul>
        ) : <p className="muted">Ninguno por ahora: aparecen a medida que el historial de los avisos crece.</p>}
      </section>

      <p className="muted chico">
        En Córdoba no existe un registro público de precios de cierre: las salidas del mercado y los descuentos se estiman con los avisos.
        El historial empezó el 10/11/2026, así que las tendencias y las bajas se vuelven más confiables con cada semana.
      </p>
    </div>
  );
}
