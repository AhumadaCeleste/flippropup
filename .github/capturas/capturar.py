"""Saca capturas de la página de demostración (escritorio y celular)."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, ancho, alto in (("escritorio", 1280, 900), ("celular", 390, 844)):
        pg = nav.new_page(viewport={"width": ancho, "height": alto}, device_scale_factor=2 if nombre == "celular" else 1)
        pg.goto("http://localhost:3000/login/demo", timeout=180000)
        pg.wait_for_timeout(8000)
        for seccion in ("tarjetas", "mapa", "relevar"):
            el = pg.locator(f"#{seccion}")
            el.scroll_into_view_if_needed()
            pg.wait_for_timeout(2500)
            el.screenshot(path=f"capturas/{nombre}-{seccion}.png")
        pg.close()
    nav.close()
