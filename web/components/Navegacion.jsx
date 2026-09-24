"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/buscar", texto: "Buscar" },
  { href: "/seguimientos", texto: "Mis seguimientos" },
  { href: "/busquedas", texto: "Búsquedas guardadas" },
];

export default function Navegacion() {
  const ruta = usePathname();
  return (
    <nav aria-label="Secciones">
      {LINKS.map((l) => (
        <Link key={l.href} href={l.href} aria-current={ruta.startsWith(l.href) ? "page" : undefined}>
          {l.texto}
        </Link>
      ))}
    </nav>
  );
}
