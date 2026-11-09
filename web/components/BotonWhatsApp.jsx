// Botón para escribirle por WhatsApp a quien publicó. El ícono es un globo de chat genérico.
import { origenAviso } from "@/lib/filtros";
import { telefonosEnTexto } from "@/lib/telefono";

// Teléfono guardado por el robot o, si no hay, el primero que aparezca en el título o la descripción.
export function telefonoDe(p) {
  if (p?.telefono) return p.telefono;
  return telefonosEnTexto(`${p?.titulo || ""}\n${p?.descripcion || ""}`)[0] || null;
}

export function mensajeConsulta(p) {
  return `Hola, vi tu publicación "${p?.titulo || "propiedad"}" en ${origenAviso(p)} (${p?.url}). ¿Sigue disponible?`;
}

export function enlaceWhatsApp(p) {
  const tel = telefonoDe(p);
  if (!tel) return null;
  return `https://wa.me/${tel}?text=${encodeURIComponent(mensajeConsulta(p))}`;
}

export function telefonoVisible(tel) {
  const d = String(tel || "").replace(/^549/, "");
  return d.length === 10 ? `${d.slice(0, 3)} ${d.slice(3, 6)}-${d.slice(6)}` : d;
}

const Icono = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
    <path d="M12 3C7 3 3 6.6 3 11c0 2.4 1.2 4.5 3 6l-.8 3.5 3.8-2c1 .3 2 .5 3 .5 5 0 9-3.6 9-8s-4-8-9-8zm-3 9.2a1.2 1.2 0 110-2.4 1.2 1.2 0 010 2.4zm3 0a1.2 1.2 0 110-2.4 1.2 1.2 0 010 2.4zm3 0a1.2 1.2 0 110-2.4 1.2 1.2 0 010 2.4z" />
  </svg>
);

// siempre = true: si no hay teléfono, abre WhatsApp con el mensaje armado para elegir a quién mandarlo.
export default function BotonWhatsApp({ p, chico = true, conNumero = false, siempre = false }) {
  const tel = telefonoDe(p);
  const clase = `btn btn-whatsapp${chico ? " btn-chico" : ""}`;
  if (!tel) {
    if (!siempre) return null;
    return (
      <a className={clase} href={`https://wa.me/?text=${encodeURIComponent(mensajeConsulta(p))}`} target="_blank" rel="noopener noreferrer"
         title="El aviso no muestra teléfono: se abre WhatsApp con la consulta escrita para que elijas el contacto">
        <Icono />Consultar por WhatsApp
      </a>
    );
  }
  return (
    <a className={clase} href={enlaceWhatsApp(p)} target="_blank" rel="noopener noreferrer"
       title={`Escribir por WhatsApp al ${telefonoVisible(tel)}`}>
      <Icono />
      {conNumero ? telefonoVisible(tel) : chico ? "WhatsApp" : "Consultar por WhatsApp"}
    </a>
  );
}
