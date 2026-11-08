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
    for url in [BASE, BASE + "?page=2", BASE + "?pagina=2", BASE + "/pagina-2", BASE + "?p=2", BASE + "?pag=2",
                "https://inmoup.com.ar/departamentos-en-venta-en-cordoba-de-cordoba"]:
        r = pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(2500)
        urls = pg.evaluate(LEER)
        print(f"== {url} · {r.status} · {pg.title()!r} · {len(urls)} avisos · primero {urls[0] if urls else None}")
    pg.goto(BASE, wait_until="domcontentloaded"); pg.wait_for_timeout(3000)
    print("== botones:", pg.evaluate("""() => [...document.querySelectorAll('a, button')].filter(e => /^(\\d+|siguiente|›|»|>|ver más|cargar más)$/i.test(e.textContent.trim()))
        .slice(0, 12).map(e => e.tagName + ' ' + e.textContent.trim() + ' ' + (e.href || e.getAttribute('wire:click') || e.getAttribute('onclick') || e.outerHTML.slice(0,160))).join(' || ')"""))
    nav.close()
