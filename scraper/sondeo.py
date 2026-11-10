"""Sondeo: IDECOR (OMI y valor de la tierra) desde GitHub y Facebook Marketplace sin sesión."""
import idecor
from playwright.sync_api import sync_playwright

pts = idecor.ofertas_omi()
print("== OMI ofertas USD vivienda:", len(pts))
ind = idecor.IndiceCasas(pts)
for nombre, lat, lng in [("Alberdi", -31.4105, -64.1949), ("Alta Córdoba", -31.3930, -64.1830), ("Jardín", -31.4400, -64.1750),
                         ("Cerro de las Rosas", -31.3700, -64.2300)]:
    print("  ", nombre, ind.valor(lat, lng))
print("== VUT parcela Alberdi:", idecor.vut_parcela(-31.4105, -64.1949))

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    ctx = nav.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900})
    pg = ctx.new_page()
    pg.goto("https://www.facebook.com/marketplace/category/propertyforsale?latitude=-31.4167&longitude=-64.1833&radius=20&exact=false",
            wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(6000)
    print("== Marketplace URL:", pg.url)
    print("   enlaces a item:", pg.evaluate("() => new Set([...document.querySelectorAll('a[href*=\"/marketplace/item/\"]')].map(a => a.href.split('?')[0])).size"))
    print("   texto:", pg.evaluate("() => document.body.innerText.slice(0, 600)").replace("\n", " | "))
    nav.close()
