"""Sondeo: La Voz vs la base para 'casa / depto, 4 dormitorios o más, barrio Centro'."""
import os
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from supabase import create_client
import lavoz as lv
import mercadolibre as ml
from barrios import Barrios

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    pg = ml.nuevo_contexto(nav).new_page()
    v = lv.LaVoz(pg); v.abrir()
    ubic = v.ubicaciones()
    centro = [u for u in ubic if u["tipo"] == "barrio" and u["padre_tid"] == 3194 and u["nombre"].lower() in ("centro",)]
    print("== tid Centro:", centro)
    for tipo in ("casa", "departamento"):
        for dorm in (None, "4-dormitorios-o-mas"):
            f = {"tipos": [tipo], "provincia_tid": 3173, "ciudad_tid": 3194, "barrios_tid": [c["tid"] for c in centro]}
            if dorm: f["dormitorios"] = [dorm]
            for t, consulta in lv.construir_consultas(f):
                data = v._get_json(f"/api/search?page=1&filters={quote(consulta)}")
                res = data.get("data", {}).get("results", {})
                meta = res.get("meta") or {}
                print(f"== La Voz {tipo} {dorm or 'todos'} Centro: total={meta.get("total")} paginas={meta.get('last_page')} · {consulta}")
                for a in res.get("data", [])[:4]:
                    p = lv.normalizar(a, tipo)
                    if p:
                        b, o = Barrios().asignar(p)
                        print("     ", p["portal_id"], p.get("barrio"), p.get("dormitorios"), p.get("lat"), p.get("lng"), "->", b and b["nombre"], o)
    # totales ciudad
    for tipo in ("casa", "departamento", "terreno"):
        f = {"tipos": [tipo], "provincia_tid": 3173, "ciudad_tid": 3194}
        for t, consulta in lv.construir_consultas(f):
            meta = (v._get_json(f"/api/search?page=1&filters={quote(consulta)}").get("data", {}).get("results", {}).get("meta") or {})
            print(f"== La Voz total ciudad {tipo}: {meta.get('total')} ({meta.get('last_page')} páginas)")
    nav.close()

# base
for tipo in ("casa", "departamento"):
    for dorm in (None, "4 Dormitorios o más"):
        q = sb.table("publicaciones").select("id,portal,barrio,barrio_id,barrio_origen", count="exact").eq("estado", "activo").eq("tipo", tipo).eq("portal", "lavoz").ilike("barrio", "centro")
        if dorm: q = q.eq("dormitorios", dorm)
        r = q.execute()
        print(f"== Base La Voz {tipo} {dorm or 'todos'} barrio texto 'Centro': {r.count} · barrio oficial: {[ (x['barrio_id'], x['barrio_origen']) for x in r.data[:8]]}")
cen = sb.table("barrios").select("id").eq("nombre", "CENTRO").execute().data
print("== id oficial CENTRO:", cen)
for tipo in ("casa", "departamento"):
    r = sb.table("publicaciones").select("portal", count="exact").eq("estado", "activo").eq("tipo", tipo).eq("barrio_id", cen[0]["id"]).eq("dormitorios", "4 Dormitorios o más").execute()
    print(f"== Base todos los portales {tipo} 4+ barrio oficial CENTRO: {r.count} · {sorted(x['portal'] for x in r.data)}")
r = sb.table("publicaciones").select("dormitorios", count="exact").eq("estado", "activo").eq("portal", "lavoz").eq("tipo", "casa").limit(2000).execute()
import collections
print("== dormitorios casas La Voz:", collections.Counter(x["dormitorios"] for x in r.data).most_common(8))
