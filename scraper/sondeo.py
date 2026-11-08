"""Sondeo: listado de inmobiliarias de La Voz (cómo se cargan y qué datos traen)."""
import json
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    pg = nav.new_context(locale="es-AR", viewport={"width": 1366, "height": 900}).new_page()
    pedidos = []
    pg.on("response", lambda r: pedidos.append((r.url, r.status)) if r.request.resource_type in ("xhr", "fetch") and "lavoz" in r.url else None)
    pg.goto("https://clasificados.lavoz.com.ar/inmobiliarias", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(9000)
    print("== título:", pg.title(), "·", pg.url)
    texto = " ".join(pg.evaluate("() => document.body.innerText").split())
    print("== texto:", texto[:1200])
    print("== pedidos:", [f"{s} {u[:160]}" for u, s in pedidos][:15])
    for u, s in pedidos:
        if "/api/" in u and s == 200:
            body = pg.evaluate("async (u) => (await (await fetch(u)).text()).slice(0, 1500)", u)
            print("== API", u[:160], "→", body.replace("\n", " ")[:1500])
    print("== enlaces:", pg.evaluate("""() => [...new Set([...document.querySelectorAll('a[href]')].map(a => a.href))].filter(h => /sitio|inmobiliaria/i.test(h)).slice(0, 12)"""))
    nav.close()
