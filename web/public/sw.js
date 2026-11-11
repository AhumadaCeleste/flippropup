// Service worker mínimo: permite instalar la app. No guarda datos en el teléfono:
// todo se pide siempre al servidor, así nadie ve avisos sin haber entrado con un email habilitado.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
