"""Sondeo: prueba cómo responde cada portal desde GitHub Actions (se corre a mano)."""
import json
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = nav.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900},
                          extra_http_headers={"Accept-Language": "es-AR,es;q=0.9"})
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    # Zonaprop: API interna desde la página (igual que La Voz)
    pg = ctx.new_page()
    pg.goto("https://www.zonaprop.com.ar/departamentos-venta-cordoba.html", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(8000)
    print("== zonaprop página:", pg.title())
    res = pg.evaluate("""async () => {
      const r = await fetch('/rplis-api/postings', {method: 'POST', headers: {'content-type': 'application/json'},
        body: JSON.stringify({pagina: 1, tipoDeOperacion: '1', tipoDePropiedad: '2', city: null, province: null})});
      return {status: r.status, body: (await r.text()).slice(0, 600)}; }""")
    print("== zonaprop API:", res["status"], res["body"].replace("\\n", " ")[:600])
    pg.close()

    # InmoUP: estructura de las tarjetas
    pg = ctx.new_page()
    pg.goto("https://inmoup.com.ar/inmuebles-en-venta-en-cordoba-de-cordoba", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(6000)
    info = pg.evaluate(r"""() => {
      const precios = [...document.querySelectorAll('body *')].filter(e => e.children.length === 0 && /U\$S|USD|\$\s?\d/.test(e.textContent)).slice(0, 3);
      let card = precios[0];
      for (let i = 0; card && i < 8; i++) { if (card.querySelector && card.querySelector('a[href]') && card.querySelector('img')) break; card = card.parentElement; }
      const ld = [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => s.textContent.slice(0, 500));
      const links = [...new Set([...document.querySelectorAll('a[href]')].map(a => a.href).filter(h => /propiedad|inmueble|ficha|\d{4,}/.test(h)))].slice(0, 6);
      const pag = [...document.querySelectorAll('a[href]')].filter(a => /pagina|page|siguiente/i.test(a.href + a.textContent)).slice(0, 4).map(a => a.textContent.trim().slice(0,15) + ' ' + a.href);
      return {card: card ? card.outerHTML.replace(/\s+/g, ' ').replace(/<svg.*?<\/svg>/g, '<svg/>').slice(0, 3500) : null,
              cardClass: card ? card.className : null, ld, links, pag,
              total: document.querySelectorAll(card ? '.' + [...card.classList].join('.') : 'x').length};
    }""")
    print("== inmoup clase tarjeta:", info["cardClass"], "· cantidad:", info["total"])
    print("== inmoup links:", info["links"])
    print("== inmoup paginación:", info["pag"])
    print("== inmoup ld+json:", info["ld"][:2])
    print("== inmoup TARJETA:", info["card"])
    nav.close()
