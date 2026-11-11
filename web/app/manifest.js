// Hace que Flip PropUp se pueda instalar en el celular (ícono en la pantalla de inicio, se abre sin barra del navegador).
// Instalarla no da acceso: al abrirla pide entrar con Google y solo pasan los emails habilitados.
export default function manifest() {
  return {
    name: "Flip PropUp",
    short_name: "Flip PropUp",
    description: "Detectá propiedades subvaluadas antes que el mercado.",
    id: "/",
    start_url: "/buscar",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#0F172A",
    theme_color: "#1E293B",
    lang: "es-AR",
    icons: [
      { src: "/iconos/icono-192-v2.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/iconos/icono-512-v2.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/iconos/icono-maskable-512-v2.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "Buscar", url: "/buscar" },
      { name: "Mercado", url: "/mercado" },
      { name: "Relevar", url: "/relevar" },
    ],
  };
}
