"""Sondeo: vistas y paginación de CórdobaProp."""
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
B = "https://www.cordobaprop.com/propiedades/?operaciones=1&tipos=2"
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    ctx = nav.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()
    for url in [B, B + "&viewtype=list", B + "&viewtype=grid", B + "&page=2", B + "&pagina=2", B + "&p=2", B + "&dormitorios=1"]:
        r = pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(3500)
        i = pg.evaluate(r"""() => {
          const urls = [...document.querySelectorAll('[data-url]')].map(e => e.getAttribute('data-url'));
          const otras = [...new Set([...document.querySelectorAll('[class]')].map(e => e.className).filter(c => typeof c === 'string' && /card|property|propiedad|item|result/i.test(c)))].slice(0, 12);
          const cuenta = (document.body.innerText.match(/(\d[\d.]*)\s+(propiedades|resultados)/i) || [])[0];
          const pag = [...document.querySelectorAll('a[href], button')].filter(x => /page|pagina|siguiente|›|»|cargar|ver m/i.test((x.href || '') + ' ' + x.textContent)).slice(0, 5).map(x => x.textContent.trim().slice(0, 15) + ' ' + (x.href || ''));
          const primera = document.querySelector('a[href*="/propiedad/"]');
          return {n: urls.length, primero: urls[0], cuenta, otras, pag, link: primera ? primera.outerHTML.replace(/\s+/g, ' ').slice(0, 1200) : null};
        }""")
        print(f"== {url[50:]} · {r.status} · tarjetas {i['n']} · primero {i['primero']} · {i['cuenta']}")
        print("   pag:", i["pag"], "· clases:", i["otras"])
        if i["link"]:
            print("   LINK:", i["link"])
    pg.goto("https://www.cordobaprop.com/propiedad/3138-allende-suite-depto-a-estrenar-frente-a-los-aroza-villa-allende", wait_until="domcontentloaded")
    pg.wait_for_timeout(3000)
    t = " ".join(pg.evaluate("() => document.body.innerText").split())
    print("== FICHA:", t[:1500])
    nav.close()
