// Flip PropUp · captura de Zonaprop desde el navegador (con la sesión de Cele abierta en zonaprop.com.ar).
// Se pega en una pestaña de https://www.zonaprop.com.ar. Recorre los avisos en venta de Córdoba capital
// (deptos, casas, terrenos) con la API interna del sitio y deja cada página en Supabase (zonaprop_cargar).
// Corre en segundo plano: el avance queda en window.__zpEstado.
// Antes de usarlo, reemplazar CLAVE_ZONAPROP por la clave guardada en config_privada.
(() => {
  const SUPA = "https://cicutuobkpbifzvowvnx.supabase.co";
  const ANON = "sb_publishable_KdcDnQeEnxNDKgeEMjVjeA_dpkbT0AX"; // clave pública de la web
  const CLAVE = "CLAVE_ZONAPROP";
  const CIUDAD = "1001982"; // Córdoba Capital
  // Zonaprop no expone terrenos en esta API para la capital: se siguen con IDECOR y los demás portales.
  const TIPOS = [["departamento", "2"], ["casa", "1"]];
  const PAUSA = 900; // ms entre páginas, para no cargar al sitio
  if (window.__zpEstado && !window.__zpEstado.fin) return "ya hay una captura corriendo · lote " + window.__zpEstado.lote;
  const lote = new Date().toISOString().slice(0, 16);
  const estado = (window.__zpEstado = { lote, inicio: new Date().toISOString(), tipos: {}, errores: [], fin: null });
  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

  const fila = (x) => {
    const f = x.mainFeatures || {};
    const v = (k) => (f[k] ? f[k].value : null);
    const op = (x.priceOperationTypes || [])[0] || {};
    const pr = (op.prices || [])[0] || {};
    const loc = x.postingLocation || {};
    const l = loc.location || {};
    const geo = (loc.postingGeolocation || {}).geolocation || {};
    return {
      id: x.postingId, u: x.url, t: x.title, ti: (x.realEstateType || {}).name,
      p: pr.amount, m: pr.currency, st: v("CFT100"), sc: v("CFT101"), am: v("CFT1"), do: v("CFT2"),
      ba: v("CFT3"), an: v("CFT5"), b: l.name, bl: l.label, c: (l.parent || {}).name,
      dir: (loc.address || {}).name, la: geo.latitude, lo: geo.longitude,
      pu: (x.publisher || {}).name, pt: (x.publisher || {}).publisherTypeId,
      f: ((x.visiblePictures || {}).pictures || []).slice(0, 4).map((p) => p.url730x532),
      d: (x.descriptionNormalized || "").slice(0, 1200), r: x.reserved,
    };
  };

  const pagina = async (tipo, n) => {
    for (let i = 0; i < 3; i++) {
      try {
        const r = await fetch("/rplis-api/postings", {
          method: "POST", credentials: "include", headers: { "content-type": "application/json" },
          body: JSON.stringify({ tipoDePropiedad: tipo, tipoDeOperacion: "1", pagina: n, city: CIUDAD }),
        });
        if (r.ok) return await r.json();
      } catch (e) {}
      await dormir(4000 * (i + 1));
    }
    throw new Error(`Zonaprop no respondió la página ${n}`);
  };

  const guardar = async (tipo, n, paginas, filas) => {
    for (let i = 0; i < 3; i++) {
      const r = await fetch(`${SUPA}/rest/v1/rpc/zonaprop_cargar`, {
        method: "POST",
        headers: { apikey: ANON, "content-type": "application/json" },
        body: JSON.stringify({ clave: CLAVE, lote, tipo, pagina: n, paginas, filas }),
      });
      if (r.ok) return;
      if (r.status < 500) throw new Error(`Supabase ${r.status}: ${(await r.text()).slice(0, 200)}`);
      await dormir(3000);
    }
    throw new Error("Supabase no respondió");
  };

  // Dos lectores en paralelo (Zonaprop tarda ~4 s por página): la capital entera en ~30 minutos.
  const LECTORES = 2;
  (async () => {
    for (const [nombre, tipo] of TIPOS) {
      const e = (estado.tipos[nombre] = { paginas: null, hechas: 0, avisos: 0 });
      try {
        const primera = await pagina(tipo, 1);
        const total = Math.min((primera.paging && primera.paging.totalPages) || 0, 600);
        e.paginas = total;
        if (!total) continue;
        await guardar(nombre, 1, total, (primera.listPostings || []).map(fila));
        e.hechas = 1; e.avisos += (primera.listPostings || []).length;
        let siguiente = 2;
        const lector = async () => {
          while (siguiente <= total) {
            const n = siguiente++;
            const j = await pagina(tipo, n);
            const filas = (j.listPostings || []).map(fila);
            if (filas.length) await guardar(nombre, n, total, filas);
            e.hechas += 1; e.avisos += filas.length;
            await dormir(PAUSA);
          }
        };
        await Promise.all(Array.from({ length: LECTORES }, lector));
      } catch (err) {
        estado.errores.push(`${nombre}: ${err.message}`);
      }
    }
    estado.fin = new Date().toISOString();
  })();
  return "captura iniciada · lote " + lote;
})();
