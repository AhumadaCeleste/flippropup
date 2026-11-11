"use client";
import { useEffect } from "react";

// Registra el service worker y guarda el pedido de instalación de Chrome para usarlo desde el botón "Instalar app".
export default function RegistrarApp() {
  useEffect(() => {
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
    const guardar = (e) => {
      e.preventDefault();
      window.__flipInstalar = e;
      window.dispatchEvent(new Event("flip-instalable"));
    };
    const instalada = () => {
      window.__flipInstalar = null;
      window.dispatchEvent(new Event("flip-instalada"));
    };
    window.addEventListener("beforeinstallprompt", guardar);
    window.addEventListener("appinstalled", instalada);
    return () => {
      window.removeEventListener("beforeinstallprompt", guardar);
      window.removeEventListener("appinstalled", instalada);
    };
  }, []);
  return null;
}
