// Botón para escribirle por WhatsApp a quien publicó. El ícono es un globo de chat genérico.
import { nombrePortal } from "@/lib/filtros";

export function enlaceWhatsApp(p) {
  if (!p?.telefono) return null;
  const texto = `Hola, vi tu publicación "${p.titulo || "propiedad"}" en ${nombrePortal(p.portal)} (${p.url}). ¿Sigue disponible?`;
  return `https://wa.me/${p.telefono}?text=${encodeURIComponent(texto)}`;
}

export function telefonoVisible(tel) {
  const d = String(tel || "").replace(/^549/, "");
  return d.length === 10 ? `${d.slice(0, 3)} ${d.slice(3, 6)}-${d.slice(6)}` : d;
}

export default function BotonWhatsApp({ p, chico = true, conNumero = false }) {
  const href = enlaceWhatsApp(p);
  if (!href) return null;
  return (
    <a className={`btn btn-whatsapp${chico ? " btn-chico" : ""}`} href={href} target="_blank" rel="noopener noreferrer"
       title={`Escribir por WhatsApp al ${telefonoVisible(p.telefono)}`}>
      <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
        <path d="M12 3C7 3 3 6.6 3 11c0 2.4 1.2 4.5 3 6l-.8 3.5 3.8-2c1 .3 2 .5 3 .5 5 0 9-3.6 9-8s-4-8-9-8zm-3 9.2a1.2 1.2 0 110-2.4 1.2 1.2 0 010 2.4zm3 0a1.2 1.2 0 110-2.4 1.2 1.2 0 010 2.4zm3 0a1.2 1.2 0 110-2.4 1.2 1.2 0 010 2.4z" />
      </svg>
      {conNumero ? telefonoVisible(p.telefono) : "WhatsApp"}
    </a>
  );
}
