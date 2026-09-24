import { supabaseServidor } from "@/lib/supabase/server";
import { filtrosDesdeParams, resumenFiltros } from "@/lib/filtros";
import { buscarPublicaciones, ubicacionesLaVoz, idsSeguidos } from "@/lib/consultas";
import FormularioBusqueda from "@/components/FormularioBusqueda";
import Tarjeta from "@/components/Tarjeta";

export const metadata = { title: "Buscar · Flip PropUp" };

export default async function Buscar({ searchParams }) {
  const sp = await searchParams;
  const filtros = filtrosDesdeParams(sp);
  const supabase = await supabaseServidor();
  const ubicaciones = await ubicacionesLaVoz(supabase);
  const [resultados, seguidos] = await Promise.all([
    buscarPublicaciones(supabase, filtros, ubicaciones),
    idsSeguidos(supabase),
  ]);

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Buscar</h1>
          <p className="muted" style={{ margin: "4px 0 0" }}>Los resultados salen de lo que el robot guardó esta mañana.</p>
        </div>
      </div>
      <FormularioBusqueda ubicaciones={ubicaciones} filtros={filtros} />
      <div className="encabezado">
        <h2>{resultados.length === 60 ? "Más de 60" : resultados.length} resultados</h2>
        <span className="muted" style={{ fontSize: 14 }}>{resumenFiltros(filtros, ubicaciones)}</span>
      </div>
      {resultados.length ? (
        <div className="grilla">
          {resultados.map((p) => <Tarjeta key={p.id} p={p} seguido={seguidos.has(p.id)} />)}
        </div>
      ) : (
        <div className="panel vacio">
          <h2>Todavía no hay avisos con estos filtros</h2>
          <p>Guardá la búsqueda: el robot la corre enseguida y después todas las mañanas a las 8:00.</p>
        </div>
      )}
    </>
  );
}
