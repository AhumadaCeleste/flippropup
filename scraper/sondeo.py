"""Sondeo: abre páginas de cada portal desde GitHub Actions y guarda el HTML para analizarlo."""
import os, sys
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
URLS = {
    "ml": "https://inmuebles.mercadolibre.com.ar/departamentos/venta/1-dormitorio/cordoba/",
    "zonaprop": "https://www.zonaprop.com.ar/departamentos-venta-cordoba-1-habitacion.html",
}
os.makedirs("sondeo", exist_ok=True)
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = nav.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900},
                          extra_http_headers={"Accept-Language": "es-AR,es;q=0.9"})
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    for nombre, url in URLS.items():
        pg = ctx.new_page()
        try:
            r = pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(30000 if nombre == "zonaprop" else 8000)
            html = pg.content()
            open(f"sondeo/{nombre}.html", "w").write(html)
            texto = " ".join(pg.evaluate("() => document.body ? document.body.innerText : ''").split())
            print(f"== {nombre}: status {r.status if r else None} · {pg.url} · título {pg.title()!r} · {len(html)} bytes")
            print("   ", texto[:300])
            info = pg.evaluate(r"""() => {
              const cls = {};
              document.querySelectorAll('[class]').forEach(e => e.classList.forEach(c => {
                if (/poly|ui-search|andes-money|posting|card|price|location|feature/i.test(c)) cls[c] = (cls[c]||0)+1; }));
              const top = Object.entries(cls).sort((a,b)=>b[1]-a[1]).slice(0,40).map(x=>x[0]+':'+x[1]).join(' ');
              const card = document.querySelector('li.ui-search-layout__item, div.poly-card, [data-qa="posting PROPERTY"], div.postingCard, [class*="postingCard"]');
              return {top, card: card ? card.outerHTML.replace(/\s+/g,' ').replace(/<svg.*?<\/svg>/g,'<svg/>').slice(0, 4000) : null};
            }""")
            print("   CLASES:", info["top"])
            print("   TARJETA:", info["card"])
        except Exception as e:
            print(f"== {nombre}: ERROR {e}")
        pg.close()
    nav.close()
