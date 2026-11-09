"""Sondeo: paginación Tokko y diseño alternativo (López Baena, Neta, Banker, Caffaratti)."""
import re
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    ctx = nav.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()
    pedidos = []
    pg.on("request", lambda r: pedidos.append(f"{r.method} {r.url[:260]} {(r.post_data or '')[:200]}") if r.resource_type in ("xhr", "fetch", "document") and "bergo" in r.url else None)
    pg.goto("https://www.bergo.com.ar/Venta", wait_until="networkidle", timeout=60000)
    ids1 = pg.evaluate("() => [...document.querySelectorAll('li[prop-id]')].map(l => l.getAttribute('prop-id'))")
    print("== bergo pág 1:", len(ids1), ids1[:3])
    print("== controles:", pg.evaluate(r"""() => [...document.querySelectorAll('a, button, li, div, span')].filter(e => e.children.length < 3 && /^(2|siguiente|›|»|>|ver m[aá]s|cargar m[aá]s|mostrar m[aá]s)$/i.test(e.textContent.trim()))
        .slice(0, 8).map(e => e.tagName + '.' + e.className + ' [' + e.textContent.trim() + '] href=' + (e.getAttribute('href') || '') + ' onclick=' + (e.getAttribute('onclick') || '').slice(0, 150))"""))
    pedidos.clear()
    for _ in range(5):
        pg.mouse.wheel(0, 5000); pg.wait_for_timeout(1500)
    print("== tras scroll:", pg.evaluate("() => document.querySelectorAll('li[prop-id]').length"), "· pedidos:", pedidos[:5])
    sig = pg.locator("text=/^(2|Siguiente|›|»)$/").first
    if sig.count():
        pedidos.clear()
        sig.evaluate("e => e.click()"); pg.wait_for_timeout(4000)
        ids2 = pg.evaluate("() => [...document.querySelectorAll('li[prop-id]')].map(l => l.getAttribute('prop-id'))")
        print("== tras clic en 2:", pg.url, len(ids2), ids2[:3], "· pedidos:", pedidos[:5])
    for sitio in ["https://www.lopezbaena.com.ar/Venta", "https://www.inmobiliarianeta.com.ar/Venta", "https://www.grupobanker.com/Venta"]:
        p2 = ctx.new_page()
        p2.goto(sitio, wait_until="domcontentloaded", timeout=60000); p2.wait_for_timeout(4000)
        print(f"== {sitio} · {p2.url}")
        print("   TARJETA:", p2.evaluate(r"""() => { const a = document.querySelector('a[href*="/p/"]'); let c = a;
           for (let i = 0; c && i < 7; i++) { if (/USD|U\$S|\$\s?\d/.test(c.innerText || '') && c.querySelector('img')) break; c = c.parentElement; }
           return c ? c.outerHTML.replace(/\s+/g, ' ').replace(/<svg.*?<\/svg>/g, '<svg/>').slice(0, 1800) : null; }"""))
        print("   CANTIDAD:", p2.evaluate(r"() => new Set([...document.querySelectorAll('a[href*=\"/p/\"]')].map(a => a.href)).size"),
              "·", p2.evaluate(r"() => (document.body.innerText.match(/\d+\s+(propiedades|resultados)/i) || [''])[0]"))
        p2.close()
    nav.close()
