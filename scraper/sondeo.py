"""Sondeo: tarjeta en lista, página 2 y parámetros del formulario de CórdobaProp."""
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
B = "https://www.cordobaprop.com/propiedades/?operaciones=1&tipos=2&dormitorios=1&viewtype=list"
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    pg = nav.new_context(locale="es-AR", user_agent=UA).new_page()
    pg.goto(B, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(3000)
    print("== TARJETA:", pg.evaluate("() => document.querySelector('.property-card').outerHTML.replace(/\\s+/g, ' ').slice(0, 2500)"))
    print("== cantidad:", pg.evaluate("() => document.querySelectorAll('.property-card').length"))
    print("== FORM:", pg.evaluate(r"""() => [...document.querySelectorAll('input[name], select[name]')].map(e => e.tagName + ' ' + e.name + '=' + (e.tagName === 'SELECT' ? [...e.options].slice(0, 12).map(o => o.value + ':' + o.textContent.trim()).join(',') : e.value + (e.type === 'checkbox' || e.type === 'radio' ? '(' + (e.closest('label') ? e.closest('label').textContent.trim().slice(0, 20) : '') + ')' : ''))).slice(0, 60).join(' | ')"""))
    print("== barrios ejemplo:", pg.evaluate(r"""() => [...document.querySelectorAll('[data-value], option, li[data-id]')].filter(e => /Nueva C|Alberdi|General Paz/.test(e.textContent)).slice(0, 6).map(e => e.outerHTML.slice(0, 200)).join(' || ')"""))
    pg.goto(B + "&page=2", wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
    print("== página 2 primero:", pg.evaluate("() => { const a = document.querySelector('.property-card a[href*=\"/propiedad/\"]'); return a && a.getAttribute('href'); }"))
    print("== página 1 primero:", "(ver TARJETA)")
    for t in (1, 3, 4, 5, 6):
        pg.goto(f"https://www.cordobaprop.com/propiedades/?operaciones=1&tipos={t}&viewtype=list", wait_until="domcontentloaded"); pg.wait_for_timeout(2000)
        print(f"== tipos={t}:", pg.title(), "·", pg.evaluate(r"() => (document.body.innerText.match(/\d[\d.,]*\s+resultados/) || [''])[0]"))
    nav.close()
