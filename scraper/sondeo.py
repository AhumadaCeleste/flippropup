"""Sondeo: listado y paginación de webs Tokko."""
import re
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    pg = nav.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900}).new_page()
    pg.goto("https://www.bergo.com.ar/Venta", wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(3000)
    print("== TARJETA:", pg.evaluate(r"""() => { const a = document.querySelector('a[href*="/p/"]'); let c = a;
       for (let i = 0; c && i < 6; i++) { if (/USD|\$/.test(c.innerText || '') && c.querySelector('img')) break; c = c.parentElement; }
       return c ? c.outerHTML.replace(/\s+/g, ' ').slice(0, 2500) : null; }"""))
    print("== total texto:", pg.evaluate(r"() => (document.body.innerText.match(/\d+\s+(propiedades|resultados)/i) || [''])[0]"))
    print("== paginación:", pg.evaluate(r"""() => [...document.querySelectorAll('a[href], [onclick]')].filter(e => /pag|page|siguiente|›|»/i.test((e.getAttribute('href') || '') + (e.getAttribute('onclick') || '') + e.textContent)).slice(0, 8)
        .map(e => e.tagName + ' ' + e.textContent.trim().slice(0, 12) + ' ' + (e.getAttribute('href') || '') + ' ' + (e.getAttribute('onclick') || '').slice(0, 120))"""))
    for u in ["https://www.bergo.com.ar/Venta?page=2", "https://www.bergo.com.ar/Departamentos-Venta", "https://www.bergo.com.ar/Venta/Departamentos"]:
        r = pg.goto(u, wait_until="domcontentloaded", timeout=40000); pg.wait_for_timeout(2500)
        f = sorted(set(re.findall(r'href="(/p/[^"]+)"', pg.content())))
        print(f"== {u} · {r.status if r else None} · {pg.url} · fichas {len(f)} · primera {f[0][:60] if f else None}")
    print("== scripts con datos:", pg.evaluate(r"""() => [...document.scripts].map(s => s.textContent).filter(t => /search_data|properties|tokko/i.test(t)).map(t => t.slice(0, 500)).slice(0, 3)"""))
    nav.close()
