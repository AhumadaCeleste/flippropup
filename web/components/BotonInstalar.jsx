"use client";
import { useEffect, useState } from "react";

// Botón para instalar la app en el celular. Si Chrome ofrece instalarla, abre su ventana;
// si no (iPhone u otro navegador), muestra los pasos para hacerlo a mano.
export default function BotonInstalar({ className = "btn btn-chico" }) {
  const [visible, setVisible] = useState(false);
  const [ayuda, setAyuda] = useState(null);

  useEffect(() => {
    const yaInstalada = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone;
    const celular = /android|iphone|ipad|ipod/i.test(navigator.userAgent);
    if (yaInstalada) return;
    setVisible(celular || !!window.__flipInstalar);
    const mostrar = () => setVisible(true);
    const ocultar = () => setVisible(false);
    window.addEventListener("flip-instalable", mostrar);
    window.addEventListener("flip-instalada", ocultar);
    return () => {
      window.removeEventListener("flip-instalable", mostrar);
      window.removeEventListener("flip-instalada", ocultar);
    };
  }, []);

  if (!visible) return null;

  const instalar = async () => {
    const pedido = window.__flipInstalar;
    if (pedido) {
      pedido.prompt();
      const { outcome } = await pedido.userChoice;
      if (outcome === "accepted") setVisible(false);
      window.__flipInstalar = null;
      return;
    }
    const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
    setAyuda(ios
      ? "En Safari, tocá Compartir (el cuadrado con la flecha hacia arriba) y elegí \"Agregar a inicio\"."
      : "Tocá el menú de los tres puntos del navegador y elegí \"Instalar app\" o \"Agregar a la pantalla principal\".");
  };

  return (
    <span className="instalar">
      <button type="button" className={className} onClick={instalar}>Instalar app</button>
      {ayuda && <span className="instalar-ayuda" role="status">{ayuda}</span>}
    </span>
  );
}
