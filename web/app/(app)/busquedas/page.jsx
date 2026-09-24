import Link from "next/link";
import { supabaseServidor } from "@/lib/supabase/server";
import { ubicacionesLaVoz } from "@/lib/consultas";
import { paramsDesdeFiltros, resumenFiltros } from "@/lib/filtros";
import { alternarBusqueda, borrarBusqueda, actualizarAhora } from "@/app/acciones";
import { fechaCorta } from "@/lib/formato";

export const metadata = { title: "Búsquedas guardadas · Flip PropUp" };

export default async function Busquedas({ searchParams }) {
  const sp = await searchParams;
  const supabase = await supabaseServidor();
  const [{ data: busquedas }, ubicaciones, { data: ultima }] = await Promise.all([
    supabase.from("busquedas").select("*, busqueda_resultados(count)").order("creada", { ascending: false }),
    ubicacionesLaVoz(supabase),
    supabase.from("ejecuciones").select("*").order("inicio", { ascending: false }).limit(1),
  ]);
  const ej = ultima?.[0];

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Búsquedas guardadas</h1>
          <p className="muted" style={{ margin: "4px 0 0" }}>
            Las activas se corren todos los días a las 8:00 y sus novedades llegan por email.
            {ej && <> Última corrida: {fechaCorta(ej.inicio)} · {ej.estado === "ok" ? "sin errores" : ej.estado}.</>}
          </p>
        </div>
        <form action={actualizarAhora.bind(null, "")}><button className="btn">Actualizar ahora</button></form>
      </div>

      {sp.guardada && <p className="aviso-ok">Búsqueda guardada. El robot ya la está corriendo; en 1 a 3 minutos vas a ver los resultados en Buscar.</p>}
      {sp.actualizando && <p className="aviso-ok">El robot arrancó. En 1 a 3 minutos recargá la página de Buscar.</p>}
      {sp.sin_token && <p className="error">Para actualizar desde acá falta configurar GITHUB_TOKEN en Vercel (ver README). Mientras, podés correrlo desde GitHub › Actions › Robot diario.</p>}

      {busquedas?.length ? (
        <div style={{ display: "grid", gap: 12 }}>
          {busquedas.map((b) => (
            <div key={b.id} className="panel" style={{ display: "flex", gap: 16, justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", padding: 18 }}>
              <div style={{ display: "grid", gap: 4 }}>
                <h2>{b.nombre} {!b.activa && <span className="chip">Pausada</span>}</h2>
                <span className="muted" style={{ fontSize: 14 }}>{resumenFiltros(b.filtros, ubicaciones)}</span>
                <span className="muted" style={{ fontSize: 13 }}>
                  {b.busqueda_resultados?.[0]?.count ?? 0} avisos encontrados
                  {b.ultima_ejecucion ? ` · actualizada ${fechaCorta(b.ultima_ejecucion)}` : " · todavía no corrió"}
                </span>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Link className="btn btn-principal btn-chico" href={`/buscar?${paramsDesdeFiltros(b.filtros)}`}>Ver resultados</Link>
                <form action={actualizarAhora.bind(null, b.id)}><button className="btn btn-chico">Correr ahora</button></form>
                <form action={alternarBusqueda.bind(null, b.id, !b.activa)}><button className="btn btn-chico">{b.activa ? "Pausar" : "Activar"}</button></form>
                <form action={borrarBusqueda.bind(null, b.id)}><button className="btn btn-chico btn-texto">Borrar</button></form>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="panel vacio">
          <h2>No hay búsquedas guardadas</h2>
          <p>Armá una en <Link href="/buscar">Buscar</Link> y tocá “Guardar búsqueda”.</p>
        </div>
      )}
    </>
  );
}
