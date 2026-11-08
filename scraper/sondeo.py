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
    texto = " ".join(pg.evaluate("() => document.body.innerText").split())
    print("== texto:", texto[:700])
    info = pg.evaluate(r"""() => {
      const a = [...document.querySelectorAll('a[href*="/propiedad/"]')];
      let card = a[0]; for (let i = 0; card && i < 6; i++) { if (card.querySelector && card.querySelectorAll('img').length && /\d/.test(card.innerText)) break; card = card.parentElement; }
      const pag = [...document.querySelectorAll('a[href]')].filter(x => /page|pagina|pag=/i.test(x.href)).slice(0, 5).map(x => x.textContent.trim() + ' ' + x.href);
      return {n: new Set(a.map(x => x.href)).size, card: card ? card.outerHTML.replace(/\s+/g, ' ').replace(/<svg.*?<\/svg>/g, '<svg/>').slice(0, 2500) : null, pag};
    }""")
    print("== avisos en pantalla:", info["n"])
    print("== paginación:", info["pag"])
    print("== TARJETA:", info["card"])
    print("== pedidos:", " || ".join(p for p in pedidos if "cordobaprop" in p and "rum" not in p)[:1500])
    nav.close()
