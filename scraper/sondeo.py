"""Sondeo: paginación de CórdobaProp (vista lista)."""
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
B = "https://www.cordobaprop.com/propiedades/?operaciones=1&tipos=2&dormitorios=1&viewtype=list"
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    pg = nav.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900}).new_page()
    pedidos = []
    pg.on("request", lambda r: pedidos.append(f"{r.method} {r.url[:200]} {(r.post_data or '')[:200]}") if r.resource_type in ("xhr", "fetch", "document") and "cordobaprop" in r.url else None)
    pg.goto(B, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(3000)
    print("== localidades Córdoba:", pg.evaluate(r"""() => [...document.querySelectorAll('select[name=localidades] option')].filter(o => /^C[oó]rdoba|Capital/i.test(o.textContent.trim())).map(o => o.value + ':' + o.textContent.trim()).join(', ')"""))
    print("== pie:", pg.evaluate(r"""() => { const g = document.querySelector('.property-grid'); let n = g && g.nextElementSibling; const out = [];
       for (let i = 0; n && i < 4; i++, n = n.nextElementSibling) out.push(n.outerHTML.replace(/\s+/g, ' ').slice(0, 900)); return out.join(' ### '); }"""))
    pedidos.clear()
    for _ in range(6):
        pg.mouse.wheel(0, 4000); pg.wait_for_timeout(1500)
    print("== tras scroll:", pg.evaluate("() => document.querySelectorAll('.property-card').length"), "· pedidos:", pedidos[:5])
    sig = pg.locator("a:has-text('Siguiente'), a:has-text('›'), a:has-text('»'), button:has-text('Ver más'), button:has-text('Cargar más'), .pagination a").all()
    print("== controles:", [(s.inner_text().strip()[:12], s.get_attribute('href'), s.get_attribute('onclick')) for s in sig[:8]])
    nav.close()
