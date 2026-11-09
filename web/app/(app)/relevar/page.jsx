import { supabaseServidor } from "@/lib/supabase/server";
import { cambiarAvisoRelevamiento } from "@/app/acciones";
import Relevar from "@/components/Relevar";

export const metadata = { title: "Relevar · Flip PropUp" };

const fecha = (f) => new Date(f).toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });
const telVisible = (t) => { const d = String(t || "").replace(/^549/, ""); return d.length === 10 ? `${d.slice(0, 3)} ${d.slice(3, 6)}-${d.slice(6)}` : d; };

export default async function PaginaRelevar() {
  const supabase = await supabaseServidor();
  const { data, error } = await supabase.from("relevamientos").select("*").order("creado", { ascending: false }).limit(50);
  const lista = data || [];
  const rutas = lista.map((r) => r.foto_path).filter(Boolean);
  const firmadas = {};
  if (rutas.length) {
    const { data: urls } = await supabase.storage.from("relevamientos").createSignedUrls(rutas, 3600);
    (urls || []).forEach((u) => { if (u.signedUrl) firmadas[u.path] = u.signedUrl; });
  }

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Relevar</h1>
          <p className="muted" style={{ margin: "4px 0 0" }}>
            Pasaste por una propiedad interesante: sacale una foto y fijate si está publicada en algún portal.
          </p>
        </div>
      </div>
      <Relevar />
      <section style={{ display: "grid", gap: 12 }}>
        <h2>Mis relevamientos</h2>
        {error ? (
          <div className="panel vacio"><p>Para guardar relevamientos falta correr la migración en Supabase (archivo database/migraciones/2026-11-08-contacto-y-mapa.sql).</p></div>
        ) : lista.length ? (
          <div className="grilla">
            {lista.map((r) => (
              <article key={r.id} className="tarjeta">
                <div className="foto">{firmadas[r.foto_path] ? <img src={firmadas[r.foto_path]} alt="" loading="lazy" /> : null}</div>
                <div className="cuerpo">
                  <strong>{r.direccion || "Sin dirección"}</strong>
                  <span className="datos">{fecha(r.creado)} · {r.creado_por}{r.telefono ? ` · ☎ ${telVisible(r.telefono)}` : ""}</span>
                  {r.nota && <span style={{ fontSize: 14 }}>{r.nota}</span>}
                </div>
                <div className="acciones">
                  {r.telefono && <a className="btn btn-whatsapp btn-chico" target="_blank" rel="noopener noreferrer" href={`https://wa.me/${r.telefono}`}>WhatsApp</a>}
                  {r.lat && <a className="btn btn-chico" target="_blank" rel="noopener noreferrer" href={`https://www.google.com/maps?q=${r.lat},${r.lng}`}>Mapa</a>}
                  <form action={cambiarAvisoRelevamiento.bind(null, r.id, !r.activo)}>
                    <button className={`btn btn-chico${r.activo ? " btn-activo" : ""}`}>{r.activo ? "🔔 Avisando" : "🔕 Sin aviso"}</button>
                  </form>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="panel vacio"><p>Todavía no guardaste relevamientos.</p></div>
        )}
      </section>
    </>
  );
}
