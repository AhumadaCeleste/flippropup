"""Facebook Marketplace (propiedades en venta en Córdoba) a través de Apify.

Facebook no deja leer Marketplace sin iniciar sesión desde servidores, así que se usa el actor
oficial apify/facebook-marketplace-scraper (≈ U$S 5 cada 1.000 avisos; el plan gratis de Apify
trae U$S 5 por mes). Hace falta el secret APIFY_TOKEN. Por corrida se piden MARKETPLACE_MAX avisos
(30 por defecto), una sola vez por día.
"""
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request

ACTOR = os.environ.get("MARKETPLACE_ACTOR", "apify~facebook-marketplace-scraper")
MAX = int(os.environ.get("MARKETPLACE_MAX", "30"))
# Sin sesión, Facebook solo respeta la ciudad en las búsquedas por texto (la categoría inmuebles
# devuelve avisos de otro país). Cada búsqueda define el tipo si el título no lo dice.
BUSQUEDAS = {
    "casa": "https://www.facebook.com/marketplace/cordoba/search/?query=casa%20en%20venta",
    "departamento": "https://www.facebook.com/marketplace/cordoba/search/?query=departamento%20en%20venta",
    "terreno": "https://www.facebook.com/marketplace/cordoba/search/?query=terreno%20en%20venta",
}


def _sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def disponible():
    return bool(os.environ.get("APIFY_TOKEN", "").strip())


def traer(maximo=MAX):
    token = os.environ["APIFY_TOKEN"].strip()
    url = (f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
           f"?token={token}&timeout=600&format=json&clean=true")
    entrada = {"startUrls": [{"url": u} for u in BUSQUEDAS.values()], "resultsLimit": max(1, maximo // len(BUSQUEDAS))}
    cuerpo = json.dumps(entrada).encode()
    pedido = urllib.request.Request(url, data=cuerpo, method="POST", headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=660) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Apify respondió {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from e


def _tipo(texto):
    t = _sin_acentos(texto)
    if re.search(r"\b(terreno|lote|loteo)\b", t):
        return "terreno"
    if re.search(r"\b(depto|departamento|dpto|monoambiente|ph|duplex|piso)\b", t):
        return "departamento"
    if re.search(r"\b(casa|chalet|vivienda)\b", t):
        return "casa"
    return None


def _dormitorios(texto):
    t = _sin_acentos(texto)
    if "monoambiente" in t:
        return "Monoambiente"
    m = re.search(r"(\d)\s*(dormitorios?|dorm\.?|habitaciones|hab\.?|ambientes?)", t)
    if not m:
        return None
    n = int(m.group(1)) - (1 if m.group(2).startswith("ambiente") else 0)
    if n <= 0:
        return "Monoambiente"
    return "1 Dormitorio" if n == 1 else ("4 Dormitorios o más" if n >= 4 else f"{n} Dormitorios")


def _superficie(texto):
    m = re.search(r"(\d{2,5}(?:[.,]\d+)?)\s*(m2|m²|mts2?|metros cuadrados)", _sin_acentos(texto))
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def normalizar(x):
    precio = x.get("listing_price") or {}
    formato = precio.get("formatted_amount") or (x.get("formatted_price") or {}).get("text") or ""
    monto = None
    try:
        if precio.get("amount") is not None:
            monto = float(precio["amount"])
        elif precio.get("amount_with_offset_in_currency") is not None:
            monto = float(precio["amount_with_offset_in_currency"]) / 100
    except (TypeError, ValueError):
        monto = None
    if not monto:
        digitos = re.sub(r"[^0-9]", "", formato)
        monto = float(digitos) if digitos else None
    moneda = "USD" if re.search(r"US\$|USD|U\$S|d[oó]lar", formato, re.I) else ("ARS" if monto else None)
    titulo = x.get("marketplace_listing_title") or x.get("custom_title") or ""
    subt = " ".join(s.get("subtitle", "") if isinstance(s, dict) else str(s)
                    for s in (x.get("custom_sub_titles_with_rendering_flags") or []))
    desc = (x.get("redacted_description") or {}).get("text") if isinstance(x.get("redacted_description"), dict) else x.get("description")
    texto = f"{titulo} {subt} {desc or ''}"
    geo = ((x.get("location") or {}).get("reverse_geocode") or {})
    fp = x.get("primary_listing_photo") or {}
    foto = (fp.get("image") or {}).get("uri") or fp.get("photo_image_url")
    vendedor = (x.get("marketplace_listing_seller") or {}).get("name")
    lat = (x.get("location") or {}).get("latitude")
    lng = (x.get("location") or {}).get("longitude")
    sup = _superficie(texto)
    tipo = _tipo(texto)
    if not tipo:  # el de la búsqueda que lo trajo
        tipo = next((t for t, u in BUSQUEDAS.items() if u == x.get("facebookUrl")), None)
    # En Marketplace casi todos publican en "pesos" un número que en realidad son dólares.
    if moneda == "ARS" and monto and 5000 <= monto <= 2000000 and not re.search(r"\bpesos\b|millones", texto, re.I):
        moneda = "USD"
    return {
        "portal": "marketplace",
        "portal_id": str(x.get("id")),
        "url": x.get("listingUrl") or f"https://www.facebook.com/marketplace/item/{x.get('id')}/",
        "titulo": titulo[:300],
        "descripcion": (desc or subt or "")[:4000],
        "tipo": tipo,
        "provincia": geo.get("state") or "Córdoba",
        "ciudad": geo.get("city") or "Córdoba",
        "barrio": None,
        "lat": lat,
        "lng": lng,
        "precio": monto if monto else None,
        "moneda": moneda,
        "superficie_total": sup,
        "dormitorios": _dormitorios(texto),
        "banos": None,
        "vendedor_tipo": "Particular",
        "vendedor_nombre": vendedor,
        "apto_escritura": None,
        "apto_credito": None,
        "fotos": [foto] if foto else [],
        "foto_principal": foto,
        "fecha_publicacion": None,
        "telefono": None,
    }


def coincide(p, f, nombres, textos_dorm):
    if not p["portal_id"] or p["portal_id"] == "None" or not p["tipo"]:
        return False
    if re.search(r"\balquil", _sin_acentos(p["titulo"] + " " + (p["descripcion"] or ""))):
        return False
    if p["tipo"] not in (f.get("tipos") or ["casa", "departamento"]):
        return False
    dorms = [textos_dorm[d] for d in (f.get("dormitorios") or []) if d in textos_dorm]
    if dorms and p["dormitorios"] not in dorms:
        return False
    ciudad = nombres.get(f.get("ciudad_tid"))
    if ciudad and _sin_acentos(ciudad) != _sin_acentos(p.get("ciudad")):
        return False
    return True
