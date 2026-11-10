import { supabaseServidor } from "@/lib/supabase/server";
import { filtrosDesdeParams, resumenFiltros, nombrePortal } from "@/lib/filtros";
import { buscarPublicaciones, ubicacionesLaVoz, idsSeguidos, barriosOficiales } from "@/lib/consultas";
import FormularioBusqueda from "@/components/FormularioBusqueda";
import Tarjeta from "@/components/Tarjeta";
import MapaResultados from "@/components/MapaResultados";

export const metadata = { title: "Buscar · Flip PropUp" };

export default async function Buscar({ searchParams }) {
  const sp = await searchParams;
  const filtros = filtrosDesdeParams(sp);
  const supabase = await supabaseServidor();
  const [ubicaciones, oficiales] = await Promise.all([ubicacionesLaVoz(supabase), barriosOficiales(supabase)]);
  const enMapa = sp.vista === "mapa";
  const [{ lista: resultados, totales, total }, seguidos] = await Promise.all([
    enMapa
      ? buscarPublicaciones(supabase, filtros, ubicaciones, 500, { conCoordenadas: true })
      : buscarPublicaciones(supabase, filtros, ubicaciones),
    idsSeguidos(supabase),
  ]);

  const params = new URLSearchParams();
  Object.entries(sp).forEach(([k, v]) => (Array.isArray(v) ? v : [v]).forEach((x) => k !== "vista" && x != null && params.append(k, x)));
  const enlaceVista = (v) => `/buscar?${new URLSearchParams([...params, ...(v === "mapa" ? [["vista", "mapa"]] : [])])}`;
  const puntos = enMapa
    ? resultados.map(({ id, lat, lng, portal, precio, moneda, titulo, foto_principal, dormitorios, superficie_total }) =>
        ({ id, lat, lng, portal, precio, moneda, titulo, foto_principal, dormitorios, superficie_total }))
    : [];

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Buscar</h1>
          <p className="muted" style={{ margin: "4px 0 0" }}>Los resultados salen de lo que el robot guardó esta mañana.</p>
        </div>
      </div>
      <FormularioBusqueda ubicaciones={ubicaciones} filtros={filtros} oficiales={oficiales} />
      <div className="encabezado">
        <div>
          <h2 style={{ margin: 0 }}>{total.toLocaleString("es-AR")} resultados{enMapa ? " con ubicación" : ""}</h2>
          <span className="muted" style={{ fontSize: 14 }}>
            {Object.entries(totales).map(([p, n]) => `${nombrePortal(p)}: ${n.toLocaleString("es-AR")}`).join(" · ")}
            {total > resultados.length ? ` · se muestran ${resultados.length}; afiná los filtros para ver otros` : ""}
          </span>
        </div>
        <div style={{ display: "grid", gap: 6, justifyItems: "end" }}>
          <nav className="pestanas" aria-label="Vista de resultados">
            <a href={enlaceVista("lista")} aria-current={!enMapa ? "page" : undefined}>Lista</a>
            <a href={enlaceVista("mapa")} aria-current={enMapa ? "page" : undefined}>Mapa</a>
          </nav>
          <span className="muted" style={{ fontSize: 14 }}>{resumenFiltros(filtros, ubicaciones, oficiales)}</span>
        </div>
      </div>
      {enMapa ? (
        resultados.length ? (
          <section style={{ display: "grid", gap: 8 }}>
            <p className="muted" style={{ margin: 0, fontSize: 14 }}>
              En el mapa: {resultados.length.toLocaleString("es-AR")} avisos con ubicación. Los que todavía no la tienen la
              van sumando a medida que el robot lee sus fichas (unas 120 por día).
            </p>
            <MapaResultados puntos={puntos} />
          </section>
        ) : (
          <div className="panel vacio"><h2>Ninguno de estos avisos tiene ubicación todavía</h2><p>El robot las va completando cada mañana.</p></div>
        )
      ) : resultados.length ? (
        <div className="grilla">
          {resultados.map((p) => <Tarjeta key={p.id} p={p} seguido={seguidos.has(p.id)} />)}
        </div>
      ) : (
        <div className="panel vacio">
          <h2>Todavía no hay avisos con estos filtros</h2>
          <p>Probá con menos filtros, o guardá la búsqueda: el robot la corre enseguida y después todas las mañanas.</p>
        </div>
      )}
    </>
  );
}
