"""Sondeo: teléfonos y coordenadas disponibles en cada portal."""
import json, re
from playwright.sync_api import sync_playwright
from lavoz import LaVoz

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
BUSCAR = r"""() => {
  const html = document.documentElement.outerHTML;
  const wa = [...new Set((html.match(/(wa\.me\/[\d+]+|api\.whatsapp\.com\/send\?phone=[\d+]+)/g) || []))].slice(0, 3);
  const tel = [...new Set([...document.querySelectorAll('a[href^="tel:"]')].map(a => a.getAttribute('href')))].slice(0, 3);
  const geo = (html.match(/"(lat|latitude|latitud)"\s*:\s*"?-?\d+\.\d+"?\s*,\s*"(lng|lon|longitude|longitud)"\s*:\s*"?-?\d+\.\d+/i) || [null])[0];
  const mapa = (html.match(/(maps\.google\.com|google\.com\/maps)[^"' ]{0,120}/) || [null])[0];
  const botones = [...document.querySelectorAll('a, button')].filter(e => /whats|tel[eé]fono|ver tel|contact/i.test(e.textContent + (e.getAttribute('aria-label') || ''))).slice(0, 5).map(e => e.tagName + ':' + e.textContent.trim().slice(0, 30));
  return {wa, tel, geo, mapa, botones};
}"""
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    # La Voz: claves del aviso crudo
    pg = nav.new_context(locale="es-AR").new_page()
    lv = LaVoz(pg); lv.abrir()
    a = lv.buscar('tid:6330 tid:6334 ss_operacion:Venta tid:3173 tid_location_should:3194', 1)[0]
    print("== lavoz claves:", sorted(a.keys()))
    print("== lavoz user:", json.dumps(a.get("user"), ensure_ascii=False)[:600])
    print("== lavoz address:", json.dumps(a.get("address"), ensure_ascii=False)[:300])
    tels = {k: v for k, v in a.items() if re.search(r"phone|tel|whats|contact", k, re.I)}
    print("== lavoz campos tel:", json.dumps(tels, ensure_ascii=False)[:400])
    url_lv = a.get("url")
    ctx = nav.new_context(locale="es-AR", user_agent=UA)
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    fichas = {
        "lavoz": url_lv,
        "mercadolibre": None,
        "inmoup": "https://inmoup.com.ar/306003-yelicich-bienes-raices-sociedad-simple/inmuebles/128/ficha/departamento-en-venta-en-av-pueyrredon-700",
        "cordobaprop": "https://www.cordobaprop.com/propiedad/3138-allende-suite-depto-a-estrenar-frente-a-los-aroza-villa-allende",
    }
    p2 = ctx.new_page()
    p2.goto("https://inmuebles.mercadolibre.com.ar/departamentos/venta/1-dormitorio/cordoba/cordoba/dueno-directo/", wait_until="domcontentloaded"); p2.wait_for_timeout(4000)
    fichas["mercadolibre"] = p2.evaluate("() => { const a = document.querySelector('a.poly-component__title'); return a && a.href.split('#')[0]; }")
    for nombre, url in fichas.items():
        if not url:
            continue
        pg2 = (pg if nombre == "lavoz" else ctx.new_page())
        pg2.goto(url, wait_until="domcontentloaded", timeout=60000); pg2.wait_for_timeout(5000)
        print(f"== {nombre} ficha {url[:90]}:", json.dumps(pg2.evaluate(BUSCAR), ensure_ascii=False)[:700])
    nav.close()
