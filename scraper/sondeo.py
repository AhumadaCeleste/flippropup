"""Sondeo: qué devuelve Apify para Marketplace y cómo lo normalizamos."""
import json
import marketplace

items = marketplace.traer(5)
print("== cantidad:", len(items))
for x in items[:3]:
    print("== CRUDO:", json.dumps(x, ensure_ascii=False)[:2500])
    p = marketplace.normalizar(x)
    print("== NORMALIZADO:", {k: p[k] for k in ("portal_id", "titulo", "tipo", "ciudad", "precio", "moneda", "dormitorios", "superficie_total", "lat")})
