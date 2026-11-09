"""Sondeo: estructura de las webs hechas con Tokko Broker."""
import re
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
SITIOS = ["https://www.lopezbaena.com.ar/", "https://www.bergo.com.ar/", "https://www.zfpropiedades.com.ar/"]
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    ctx = nav.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900})
    for s in SITIOS:
        pg = ctx.new_page()
        pedidos = []
        pg.on("request", lambda r: pedidos.append(f"{r.method} {r.url[:220]}") if r.resource_type in ("xhr", "fetch") else None)
        pg.goto(s, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(3000)
        html = pg.content()
        enlaces = sorted(set(re.findall(r'href="([^"]+)"', html)))
        print(f"== {s} · {pg.title()!r}")
        print("   FICHAS:", [e for e in enlaces if re.search(r"/p/|propiedad|ficha", e)][:5])
        print("   LISTADOS:", [e for e in enlaces if re.search(r"venta|search|propiedades|resultados|buscar", e, re.I)][:10])
        print("   TOKKO:", sorted(set(re.findall(r"[a-z0-9.-]*tokko[a-z0-9./_-]*", html, re.I)))[:10])
        print("   KEY:", bool(re.search(r"key=[0-9a-f]{20,}", html)))
        print("   PEDIDOS:", [p for p in pedidos if s.split('/')[2].split('www.')[-1] in p or "tokko" in p][:8])
        pg.close()
    # listado de venta del primero
    pg = ctx.new_page()
    pedidos = []
    pg.on("request", lambda r: pedidos.append(f"{r.method} {r.url[:300]}") if r.resource_type in ("xhr", "fetch", "document") else None)
    for intento in ["https://www.lopezbaena.com.ar/Propiedades?operation=1", "https://www.lopezbaena.com.ar/Buscar?operation=1", "https://www.lopezbaena.com.ar/Venta"]:
        r = pg.goto(intento, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(3500)
        n = len(set(re.findall(r'href="([^"]*/p/[^"]+)"', pg.content())))
        print(f"== LISTADO {intento} · {r.status if r else None} · {pg.url} · fichas {n}")
    print("   PEDIDOS:", pedidos[-10:])
    fichas = sorted(set(re.findall(r'href="([^"]*/p/[^"]+)"', pg.content())))
    if fichas:
        f = fichas[0] if fichas[0].startswith("http") else "https://www.lopezbaena.com.ar" + fichas[0]
        pg.goto(f, wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
        print("== FICHA", f)
        print("   TEXTO:", " ".join(pg.evaluate("() => document.body.innerText").split())[:1200])
        print("   LD:", [x[:400] for x in pg.evaluate("() => [...document.querySelectorAll('script[type=\"application/ld+json\"]')].map(s => s.textContent)")][:2])
        print("   GEO/TEL:", re.findall(r"(?:lat|lng|latitude|longitude)\W{1,4}-?\d+\.\d+", pg.content())[:4], re.findall(r"(?:wa\.me|whatsapp\.com/send\?phone=)[^\"'&]+", pg.content())[:2])
    nav.close()
