"""Sondeo: ¿Zonaprop responde desde GitHub Actions (sin cuenta)?

Prueba 1: abrir la home con Chromium y pedir la API de listados (rplis-api/postings)
desde la propia página. Prueba 2: lo mismo con Chromium "headed" vía xvfb no está
disponible acá, así que se prueba también con otro user agent.
"""
import json
from playwright.sync_api import sync_playwright
import mercadolibre as ml

CORDOBA = "1001982"
PEDIR = """async ([tipo, pagina, ciudad]) => {
  const r = await fetch('/rplis-api/postings', {method: 'POST', credentials: 'include',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({tipoDePropiedad: tipo, tipoDeOperacion: '1', pagina, city: ciudad})});
  const t = await r.text();
  let j = null; try { j = JSON.parse(t); } catch (e) {}
  return {status: r.status, len: t.length, head: j ? null : t.slice(0, 300),
          total: j && j.paging && j.paging.total, n: j && (j.listPostings || []).length,
          primero: j && j.listPostings && j.listPostings[0] && j.listPostings[0].postingId};
}"""

with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    pg = ml.nuevo_contexto(nav).new_page()
    resp = pg.goto("https://www.zonaprop.com.ar/departamentos-venta-cordoba-cb.html", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(6000)
    print("== home:", resp and resp.status, pg.title()[:120])
    for intento in range(3):
        try:
            for tipo in ("2", "1"):
                print("== API tipo", tipo, json.dumps(pg.evaluate(PEDIR, [tipo, 2, CORDOBA])))
            break
        except Exception as e:
            print("== error", intento, e)
            pg.wait_for_timeout(8000)
    # terrenos: probar ids posibles
    for tipo in ("1003", "3", "5", "6", "7", "8"):
        r = pg.evaluate(PEDIR, [tipo, 1, CORDOBA])
        print("== tipo", tipo, r.get("status"), r.get("total"))
    nav.close()
