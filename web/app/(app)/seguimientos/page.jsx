import Link from "next/link";
import { supabaseServidor } from "@/lib/supabase/server";
import { ESTADOS } from "@/lib/filtros";
import { precio, variacion, porcentaje, diasDesde } from "@/lib/formato";
import { dejarDeSeguir, guardarObjetivo } from "@/app/acciones";
import SelectorEstado from "@/components/SelectorEstado";

export const metadata = { title: "Mis seguimientos · Flip PropUp" };

export default async function Seguimientos({ searchParams }) {
  const { estado, orden } = await searchParams;
  const supabase = await supabaseServidor();
  let q = supabase.from("seguimientos").select("*, publicaciones(*)");
  if (ESTADOS.includes(estado)) q = q.eq("estado", estado);
  const [{ data }, { data: notas }] = await Promise.all([
    q.order("agregado", { ascending: false }),
    supabase.from("notas").select("publicacion_id"),
  ]);
  const conteo = {};
  (notas || []).forEach((n) => { conteo[n.publicacion_id] = (conteo[n.publicacion_id] || 0) + 1; });
  let filas = (data || []).filter((s) => s.publicaciones).map((s) => ({
    ...s,
    p: s.publicaciones,
    cambio: variacion(s.precio_inicial, s.publicaciones.precio),
    cantNotas: conteo[s.publicacion_id] || 0,
  }));
  if (orden === "baja") filas = filas.sort((a, b) => (a.cambio ?? 0) - (b.cambio ?? 0));

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Mis seguimientos</h1>
          <p className="muted" style={{ margin: "4px 0 0" }}>Compartidos entre todos los usuarios habilitados.</p>
        </div>
        <form method="get" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <select name="estado" defaultValue={estado || ""} aria-label="Filtrar por estado">
            <option value="">Todos los estados</option>
            {ESTADOS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select name="orden" defaultValue={orden || ""} aria-label="Ordenar">
            <option value="">Agregados recientemente</option>
            <option value="baja">Mayor baja de precio</option>
          </select>
          <button className="btn">Aplicar</button>
        </form>
      </div>

      {filas.length ? (
        <div className="tabla-envoltorio">
          <table>
            <thead>
              <tr>
                <th>Propiedad</th><th>Estado</th><th>Precio inicial</th><th>Precio actual</th>
                <th>Precio objetivo</th><th>Días publicado</th><th>Notas</th><th></th>
              </tr>
            </thead>
            <tbody>
              {filas.map(({ p, ...s }) => {
                const dias = diasDesde(p.fecha_publicacion || p.primera_vez);
                return (
                  <tr key={p.id}>
                    <td>
                      <div style={{ display: "flex", gap: 12, alignItems: "center", minWidth: 280 }}>
                        {p.foto_principal && <img className="mini" src={p.foto_principal} alt="" />}
                        <div>
                          <Link href={`/aviso/${p.id}`} style={{ color: "var(--text)", fontWeight: 700 }}>{p.titulo}</Link>
                          <div className="muted">{[p.barrio, p.ciudad].filter(Boolean).join(", ")}</div>
                          {p.estado === "dado_de_baja" && <span className="chip chip-peligro">Dado de baja</span>}
                        </div>
                      </div>
                    </td>
                    <td><SelectorEstado id={p.id} estado={s.estado} /></td>
                    <td className="num">{precio(s.precio_inicial, p.moneda)}</td>
                    <td className="num">
                      {precio(p.precio, p.moneda)}
                      {s.cambio ? <div className={s.cambio < 0 ? "baja" : "suba"}>{porcentaje(s.cambio)}</div> : null}
                    </td>
                    <td>
                      <form action={guardarObjetivo.bind(null, p.id)} style={{ display: "flex", gap: 6 }}>
                        <input type="number" name="objetivo" min="0" step="1000" defaultValue={s.precio_objetivo ?? ""} placeholder="—" style={{ width: 120 }} aria-label="Precio objetivo" />
                        <button className="btn btn-chico">Guardar</button>
                      </form>
                    </td>
                    <td className="num">{dias ?? "—"}</td>
                    <td className="num"><Link href={`/aviso/${p.id}#notas`}>{s.cantNotas}</Link></td>
                    <td>
                      <form action={dejarDeSeguir.bind(null, p.id)}><button className="btn btn-chico btn-texto">Quitar</button></form>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="panel vacio">
          <h2>Todavía no seguís ninguna propiedad</h2>
          <p>En <Link href="/buscar">Buscar</Link>, tocá “☆ Seguir” en las que te interesen.</p>
        </div>
      )}
    </>
  );
}
