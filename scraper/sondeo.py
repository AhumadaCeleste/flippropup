"""Sondeo: estructura del listado de CórdobaProp."""
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = nav.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()
    pedidos = []
    pg.on("request", lambda r: pedidos.append(f"{r.method} {r.url[:220]} {(r.post_data or '')[:200]}") if r.resource_type in ("xhr", "fetch") else None)
    pg.goto("https://www.cordobaprop.com/", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(4000)
    print("== selects:", pg.evaluate("""() => [...document.querySelectorAll('select')].map(s => (s.name || s.id) + ': ' + [...s.options].slice(0, 30).map(o => o.value + '=' + o.textContent.trim()).join(', ')).join(' || ')"""))
    pg.goto("https://www.cordobaprop.com/propiedades/?operaciones=1&tipos=2", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(6000)
    print("== título:", pg.title(), "·", pg.url)
    pg.mouse.wheel(0, 3000); pg.wait_for_timeout(3000)
    texto = " ".join(pg.evaluate("() => document.body.innerText").split())
    i = max(texto.find("USD"), texto.find("U$S"))
    print("== total texto:", len(texto), "· alrededor de USD:", texto[max(0, i - 600): i + 900] if i >= 0 else texto[-1200:])
    info = pg.evaluate(r"""() => {
      const precio = [...document.querySelectorAll('body *')].find(e => e.children.length === 0 && /(USD|U\$S)\s?[\d.]{4,}/.test(e.textContent));
      let card = precio; for (let i = 0; card && i < 7; i++) { if (card.querySelector && card.querySelector('a[href]') && card.querySelector('img')) break; card = card.parentElement; }
      const enlaces = [...new Set([...document.querySelectorAll('a[href]')].map(a => a.href))].filter(h => /cordobaprop\.com\/(?!propiedades\/\?)/.test(h)).slice(0, 15);
      const pag = [...document.querySelectorAll('a, button')].filter(x => /^(\d+|siguiente|›|»|ver más|cargar más)$/i.test(x.textContent.trim())).slice(0, 6).map(x => x.tagName + ' ' + x.textContent.trim() + ' ' + (x.href || x.getAttribute('onclick') || ''));
      return {card: card ? card.outerHTML.replace(/\s+/g, ' ').replace(/<svg.*?<\/svg>/g, '<svg/>').slice(0, 2500) : null, enlaces, pag};
    }""")
    print("== enlaces:", info["enlaces"])
    print("== paginación:", info["pag"])
    print("== TARJETA:", info["card"])
    print("== pedidos:", " || ".join(p for p in pedidos if "cordobaprop" in p and "rum" not in p and "google" not in p)[:1500])
    nav.close()
