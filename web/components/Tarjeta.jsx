import Link from "next/link";
import { seguir, dejarDeSeguir, descartar } from "@/app/acciones";
import { precio, diasDesde } from "@/lib/formato";

export default function Tarjeta({ p, seguido }) {
  const dias = diasDesde(p.fecha_publicacion || p.primera_vez);
  const datos = [
    p.dormitorios,
    p.superficie_total ? `${Math.round(p.superficie_total)} m²` : null,
    p.precio_m2 ? `${precio(p.precio_m2, p.moneda)}/m²` : null,
  ].filter(Boolean).join(" · ");
  return (
    <article className="tarjeta">
      <Link href={`/aviso/${p.id}`} className="foto">
        {p.foto_principal ? <img src={p.foto_principal} alt="" loading="lazy" /> : null}
        <span className="chip portal">La Voz</span>
      </Link>
      <div className="cuerpo">
        <div className="precio">{precio(p.precio, p.moneda)}</div>
        <Link href={`/aviso/${p.id}`} className="titulo">{p.titulo}</Link>
        <div className="datos">{[p.barrio, p.ciudad].filter(Boolean).join(", ")}</div>
        <div className="datos">{datos}</div>
        <div className="datos">
          {p.vendedor_tipo === "Particular" ? <span className="chip chip-acento">Dueño directo</span> : p.vendedor_tipo}
          {dias !== null ? ` · publicado hace ${dias} ${dias === 1 ? "día" : "días"}` : ""}
        </div>
      </div>
      <div className="acciones">
        {seguido ? (
          <form action={dejarDeSeguir.bind(null, p.id)}><button className="btn btn-chico btn-activo">★ Siguiendo</button></form>
        ) : (
          <form action={seguir.bind(null, p.id)}><button className="btn btn-chico btn-principal">☆ Seguir</button></form>
        )}
        <a className="btn btn-chico" href={p.url} target="_blank" rel="noopener noreferrer">Ver en el portal</a>
        {!seguido && (
          <form action={descartar.bind(null, p.id)}><button className="btn btn-chico btn-texto" title="No volver a mostrar">Descartar</button></form>
        )}
      </div>
    </article>
  );
}
