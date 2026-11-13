import Link from "next/link";
import { seguir, dejarDeSeguir, descartar } from "@/app/acciones";
import { precio, diasDesde } from "@/lib/formato";
import { origenAviso } from "@/lib/filtros";
import BotonWhatsApp from "@/components/BotonWhatsApp";
import BarraValor from "@/components/BarraValor";

export function Puntaje({ valor }) {
  if (valor === null || valor === undefined) return null;
  return <span className={`puntaje${valor >= 60 ? " alto" : ""}`} title="Puntaje de oportunidad (0 a 100): precio por m² frente a la zona, días publicado, bajas de precio y palabras clave">{valor} pts</span>;
}

export default function Tarjeta({ p, seguido }) {
  const dias = diasDesde(p.publicado_desde || p.fecha_publicacion || p.primera_vez);
  const datos = [
    p.dormitorios,
    p.superficie_total ? `${Math.round(p.superficie_total)} m²` : null,
    p.precio_m2 ? `${precio(p.precio_m2, p.moneda)}/m²` : null,
  ].filter(Boolean).join(" · ");
  return (
    <article className="tarjeta">
      <Link href={`/aviso/${p.id}`} className="foto">
        {p.foto_principal ? <img src={p.foto_principal} alt="" loading="lazy" /> : null}
        <span className="chip portal">{origenAviso(p)}</span>
      </Link>
      <div className="cuerpo">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
          <div className="precio">{precio(p.precio, p.moneda)}</div>
          <Puntaje valor={p.puntaje} />
        </div>
        <Link href={`/aviso/${p.id}`} className="titulo">{p.titulo}</Link>
        <div className="datos">{[p.barrio, p.ciudad].filter(Boolean).join(", ")}</div>
        <div className="datos">{datos}</div>
        {p.zp_m2 && p.precio_m2 ? (
          <BarraValor chica precioM2={p.precio_m2} referencia={p.zp_m2} titulo={`del m² Zonaprop ${p.zp_nivel === "barrio" ? "del barrio" : p.zp_nivel === "zona" ? "de la zona" : "de la ciudad"}`} />
        ) : p.tipo === "terreno" && p.idecor_m2 && p.precio_m2 ? (
          <BarraValor chica precioM2={p.precio_m2} referencia={p.idecor_m2} titulo="del índice IDECOR" />
        ) : p.ref_m2 && p.precio_m2 ? (
          <BarraValor chica precioM2={p.precio_m2} referencia={p.ref_m2} titulo="del m² de la zona" />
        ) : null}
        {p.grupo_n > 1 && (
          <a href={`/aviso/${p.id}#repetidos`} className="chip chip-repetido" title="La misma propiedad está publicada por varios anunciantes o portales: compará y negociá">
            Publicada {p.grupo_n} veces
            {Number(p.grupo_max) > Number(p.grupo_min) ? ` · ${precio(Number(p.grupo_max) - Number(p.grupo_min), p.moneda)} de diferencia` : ""}
          </a>
        )}
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
        <BotonWhatsApp p={p} />
        <a className="btn btn-chico" href={p.url} target="_blank" rel="noopener noreferrer">Ver en el portal</a>
        {!seguido && (
          <form action={descartar.bind(null, p.id)}><button className="btn btn-chico btn-texto" title="No volver a mostrar">Descartar</button></form>
        )}
      </div>
    </article>
  );
}
