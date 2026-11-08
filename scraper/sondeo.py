"""Sondeo: prueba cómo responde cada portal desde GitHub Actions (se corre a mano)."""
import json
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
LEER = """() => { const out = [];
  document.querySelectorAll('script[type="application/ld+json"]').forEach(s => { try {
    const d = JSON.parse(s.textContent); const g = d['@graph'] || [d];
    g.forEach(n => { const l = n.mainEntity && n.mainEntity.mainEntity; if (l && l.itemListElement) l.itemListElement.forEach(i => out.push(i.item.url)); });
  } catch (e) {} }); return out; }"""
BASE = "https://inmoup.com.ar/inmuebles-en-venta-en-cordoba-de-cordoba"
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = nav.new_context(locale="es-AR", user_agent=UA)
    pg = ctx.new_page()
    pedidos = []
    pg.on("request", lambda r: pedidos.append(f"{r.method} {r.url[:200]} {(r.post_data or '')[:300]}") if r.resource_type in ("xhr", "fetch") else None)
    pg.goto(BASE, wait_until="networkidle", timeout=60000)
    antes = pg.evaluate(LEER)
    pedidos.clear()
    pg.click('button[aria-label="Ir a página 2"]')
    pg.wait_for_timeout(5000)
    despues = pg.evaluate(LEER)
    print("== url tras clic:", pg.url)
    print("== ld+json cambió:", antes[:1] != despues[:1], len(despues))
    print("== pedidos:", " || ".join(pedidos[:8]))
    dom = pg.evaluate("""() => [...new Set([...document.querySelectorAll('a[href*="/ficha/"]')].map(a => a.href))].slice(0, 3)""")
    print("== fichas en pantalla:", dom)
    sel = pg.evaluate("""() => [...document.querySelectorAll('select')].map(s => s.name + ':' + [...s.options].map(o => o.value).join(',')).join(' | ')""")
    print("== selects:", sel)
    nav.close()
