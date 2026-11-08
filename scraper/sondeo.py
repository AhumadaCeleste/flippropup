"""Sondeo: inmobiliarias que publican en La Voz (desde los avisos) y su posible web."""
import json, re
from collections import Counter, defaultdict
from playwright.sync_api import sync_playwright
from lavoz import LaVoz

GENERICOS = {"gmail.com", "hotmail.com", "yahoo.com", "yahoo.com.ar", "outlook.com", "live.com", "hotmail.com.ar",
             "icloud.com", "live.com.ar", "outlook.com.ar", "fibertel.com.ar", "arnet.com.ar", "lavoz.com.ar"}
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    pg = nav.new_context(locale="es-AR").new_page()
    lv = LaVoz(pg); lv.abrir()
    for ruta in ["/api/inmobiliarias", "/api/stores?category=inmuebles", "/api/users/stores", "/api/microsites?category=6330", "/api/search/stores?category=6330"]:
        try:
            r = pg.evaluate("async (p) => { const r = await fetch(p); return r.status + ' ' + (await r.text()).slice(0, 300); }", ruta)
            print("== API", ruta, "→", r.replace("\n", " "))
        except Exception as e:
            print("== API", ruta, "ERROR", e)
    avisos = lv.buscar("tid:6330 ss_operacion:Venta tid:3173 tid_location_should:3194 ss_rol:Inmobiliaria", 40)
    print("== avisos de inmobiliarias leídos:", len(avisos))
    datos = defaultdict(lambda: {"avisos": 0})
    for a in avisos:
        u = a.get("user") or {}
        nombre = (u.get("trade_name") or u.get("name") or "").strip()
        if not nombre:
            continue
        d = datos[nombre]
        d["avisos"] += 1
        email = (u.get("email") or "").lower()
        dom = email.split("@")[-1] if "@" in email else ""
        d["dominio"] = dom if dom and dom not in GENERICOS else d.get("dominio")
        d["micrositio"] = u.get("microsite_url")
        d["claves"] = sorted(k for k in u.keys())
    lista = sorted(datos.items(), key=lambda x: -x[1]["avisos"])
    print("== inmobiliarias distintas:", len(lista), "· con dominio propio:", sum(1 for _, d in lista if d.get("dominio")))
    print("== claves de user:", lista[0][1]["claves"] if lista else None)
    for n, d in lista[:80]:
        print(f"== INMO {d['avisos']:3d} · {n} · {d.get('dominio') or '-'} · {d.get('micrositio') or '-'}")
    nav.close()
