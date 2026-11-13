"""Sondeo: cobertura del m² de Zonaprop por portal y tipo."""
import os, collections
from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
filas, desde = [], 0
while True:
    r = (sb.table("publicaciones").select("portal,tipo,zp_m2,zp_nivel,precio_m2,moneda").eq("estado", "activo")
         .range(desde, desde + 999).execute().data)
    filas += r
    if len(r) < 1000: break
    desde += 1000
c = collections.Counter((f["portal"], f["tipo"], f["zp_nivel"] or "-") for f in filas)
for k, v in sorted(c.items()): print("==", k, v)
usd = [f for f in filas if f["moneda"] == "USD" and f["precio_m2"]]
print("== con barra Zonaprop:", sum(1 for f in usd if f["zp_m2"]), "de", len(usd), "en dólares con m²")
for t in ("departamento", "casa"):
    v = sorted(float(f["zp_m2"]) for f in filas if f["tipo"] == t and f["zp_nivel"] == "barrio" and f["zp_m2"])
    if v: print("==", t, "zp_m2 barrio: min", v[0], "mediana", v[len(v)//2], "max", v[-1])
