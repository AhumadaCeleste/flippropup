"""Sondeo: con qué sistema están hechas las webs de las inmobiliarias de La Voz."""
import re
from collections import Counter, defaultdict
from playwright.sync_api import sync_playwright
from lavoz import LaVoz

GENERICOS = {"gmail.com", "hotmail.com", "yahoo.com", "yahoo.com.ar", "outlook.com", "live.com", "hotmail.com.ar",
             "icloud.com", "live.com.ar", "outlook.com.ar", "fibertel.com.ar", "arnet.com.ar", "lavoz.com.ar", "remax.com.ar"}
HUELLAS = {"tokko": r"tokkobroker|tokko", "xintel": r"xintel", "gvamax": r"gvamax", "mapaprop": r"mapaprop",
           "kiteprop": r"kiteprop", "wix": r"wixstatic|wix\.com", "wordpress": r"wp-content", "inmoclick": r"inmoclick",
           "zonaprop-widget": r"zonaprop", "properati": r"properati", "witei": r"witei", "2clics": r"2clics", "inmoup": r"inmoup",
           "baseprop": r"baseprop", "arg-prop": r"argenprop"}
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    pg = nav.new_context(locale="es-AR").new_page()
    lv = LaVoz(pg); lv.abrir()
    avisos = lv.buscar("tid:6330 ss_operacion:Venta tid:3173 tid_location_should:3194 ss_rol:Inmobiliaria", 40)
    doms = Counter()
    nombre = {}
    for a in avisos:
        u = a.get("user") or {}
        e = (u.get("email") or "").lower()
        d = e.split("@")[-1] if "@" in e else ""
        if d and d not in GENERICOS:
            doms[d] += 1
            nombre[d] = (u.get("trade_name") or u.get("name") or "").strip()
    ctx = nav.new_context(locale="es-AR", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
    resumen = Counter()
    for d, n in doms.most_common():
        p = ctx.new_page()
        estado, plataformas = "", []
        try:
            r = p.goto(f"https://{d}", wait_until="domcontentloaded", timeout=25000)
            p.wait_for_timeout(1500)
            html = p.content()
            plataformas = [k for k, rx in HUELLAS.items() if re.search(rx, html, re.I)]
            estado = f"{r.status if r else '?'} {p.url[:60]}"
            fichas = len(set(re.findall(r'href="([^"]*(?:propiedad|inmueble|ficha|/p/)[^"]*)"', html, re.I)))
        except Exception as e:
            estado, fichas = f"ERROR {str(e)[:60]}", 0
        p.close()
        for k in plataformas or ["ninguna/otra"]:
            resumen[k] += 1
        print(f"== WEB {n[:40]:40s} · {d:32s} · avisos {doms[d]:3d} · {estado} · {','.join(plataformas) or '-'} · enlaces a fichas {fichas}")
    print("== RESUMEN plataformas:", dict(resumen.most_common()))
    nav.close()
