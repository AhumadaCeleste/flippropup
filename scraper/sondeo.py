"""Sondeo: prueba cómo responde cada portal desde GitHub Actions (se corre a mano)."""
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
URLS = {
    "cordobaprop": "https://www.cordobaprop.com/",
    "roomix": "https://roomix.ai/venta/departamentos/cordoba",
    "roomix_home": "https://roomix.ai/",
    "mapaprop": "https://www.mapaprop.com/es/propiedades/venta/cordoba",
}
INFO = r"""() => {
  const ld = [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => s.textContent.slice(0, 300));
  const nd = document.getElementById('__NEXT_DATA__');
  const links = [...new Set([...document.querySelectorAll('a[href]')].map(a => a.href))].filter(h => /propiedad|inmueble|ficha|listing|venta|aviso/i.test(h)).slice(0, 10);
  const precios = [...document.querySelectorAll('body *')].filter(e => e.children.length === 0 && /(US\$|USD|U\$S)\s?[\d.]{4,}/.test(e.textContent)).length;
  return {ld, nextData: nd ? nd.textContent.slice(0, 400) : null, links, precios};
}"""
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = nav.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900})
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    for nombre, url in URLS.items():
        pg = ctx.new_page()
        pedidos = []
        pg.on("request", lambda r: pedidos.append(f"{r.method} {r.url[:160]}") if r.resource_type in ("xhr", "fetch") else None)
        try:
            r = pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(7000)
            texto = " ".join(pg.evaluate("() => document.body ? document.body.innerText : ''").split())
            print(f"== {nombre}: status {r.status if r else None} · {pg.url} · título {pg.title()!r}")
            print("   TEXTO:", texto[:350])
            i = pg.evaluate(INFO)
            print("   PRECIOS EN PANTALLA:", i["precios"], "· LD:", i["ld"][:2], "· NEXT:", i["nextData"])
            print("   LINKS:", i["links"])
            print("   PEDIDOS:", " | ".join(p for p in pedidos if not any(x in p for x in ("google", "facebook", "analytics", "hotjar", "clarity", "doubleclick")))[:900])
        except Exception as e:
            print(f"== {nombre}: ERROR {e}")
        pg.close()
    nav.close()
