"""Clasificados La Voz: arma las consultas y normaliza los avisos.

La web de La Voz carga sus resultados desde su propia API (/api/search) y está
protegida por Cloudflare. Por eso el robot abre un navegador real (Playwright),
entra una vez al sitio y hace las consultas desde adentro de esa página.
"""
import json
import re
import time
from datetime import datetime

BASE = "https://clasificados.lavoz.com.ar"
CATEGORIA_INMUEBLES = 6330
TIPOS = {"casa": 6331, "departamento": 6334, "terreno": 6333}
DORMITORIOS = {
    "monoambiente": "Monoambiente",
    "1-dormitorio": "1 Dormitorio",
    "2-dormitorios": "2 Dormitorios",
    "3-dormitorios": "3 Dormitorios",
    "4-dormitorios-o-mas": "4 Dormitorios o más",
}
VENDEDOR = {"particular": "Particular", "inmobiliaria": "Inmobiliaria"}
MONEDA = {"dolares": "2", "pesos": "1"}
PAUSA_ENTRE_PAGINAS = 1.5  # segundos, para no cargar el sitio


def construir_consultas(f):
    """Convierte los filtros guardados en la lista de 'filters' de la API.

    Se hace una consulta por cada combinación tipo × dormitorio, así el
    resultado no depende de cómo combine la API varios valores.
    """
    tipos = f.get("tipos") or ["casa", "departamento"]
    dorms = f.get("dormitorios") or [None]
    comunes = ["ss_operacion:Venta"]
    if f.get("provincia_tid"):
        comunes.append(f"tid:{int(f['provincia_tid'])}")
    barrios = f.get("barrios_tid") or []
    if barrios:
        comunes += [f"tid_location_should:{int(b)}" for b in barrios]
    elif f.get("ciudad_tid"):
        comunes.append(f"tid_location_should:{int(f['ciudad_tid'])}")
    if f.get("vendedor") in VENDEDOR:
        comunes.append(f"ss_rol:{VENDEDOR[f['vendedor']]}")
    if f.get("apto_escritura"):
        comunes.append("ss_apto_escritura:Sí")
    desde, hasta = f.get("precio_desde"), f.get("precio_hasta")
    if desde or hasta:
        comunes.append(f"fs_precio:[{int(desde) if desde else '*'} TO {int(hasta) if hasta else '*'}]")
        comunes.append(f"is_moneda_k:{MONEDA.get(f.get('moneda') or 'dolares', '2')}")
    sd, sh = f.get("superficie_desde"), f.get("superficie_hasta")
    if sd or sh:
        comunes.append(f"fs_superficie_total:[{int(sd) if sd else '*'} TO {int(sh) if sh else '*'}]")

    consultas = []
    for tipo in tipos:
        if tipo not in TIPOS:
            continue
        for d in dorms:
            partes = [f"tid:{CATEGORIA_INMUEBLES}", f"tid:{TIPOS[tipo]}"] + comunes
            if d in DORMITORIOS:
                partes.append(f'ss_cantidad_dormitorios:"{DORMITORIOS[d]}"')
            consultas.append((tipo, " ".join(partes)))
    return consultas


class LaVoz:
    def __init__(self, page):
        self.page = page

    def abrir(self):
        self.page.goto(f"{BASE}/inmuebles", wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(4000)  # deja terminar el control de Cloudflare

    def _get_json(self, path):
        res = self.page.evaluate(
            """async (p) => { const r = await fetch(p, {headers: {accept: 'application/json'}});
                              return {status: r.status, body: await r.text()} }""",
            path,
        )
        if res["status"] != 200:
            raise RuntimeError(f"La Voz respondió {res['status']} en {path}")
        return json.loads(res["body"])

    def buscar(self, filtros_api, max_paginas=10):
        """Devuelve la lista de avisos crudos de todas las páginas."""
        from urllib.parse import quote
        avisos, pagina = [], 1
        while pagina <= max_paginas:
            data = self._get_json(f"/api/search?page={pagina}&filters={quote(filtros_api)}")
            res = data.get("data", {}).get("results", {})
            avisos += res.get("data", [])
            ultima = (res.get("meta") or {}).get("last_page") or 1
            if pagina >= ultima:
                break
            pagina += 1
            time.sleep(PAUSA_ENTRE_PAGINAS)
        return avisos

    def ubicaciones(self):
        """Provincias, ciudades y barrios tal como los usa La Voz."""
        data = self._get_json("/api/filters/location").get("data", [])
        filas = []
        for prov in data:
            filas.append({"portal": "lavoz", "tid": prov["tid"], "nombre": prov["name"], "tipo": "provincia", "padre_tid": None})
            for ciu in prov.get("child_data") or []:
                filas.append({"portal": "lavoz", "tid": ciu["tid"], "nombre": ciu["name"], "tipo": "ciudad", "padre_tid": prov["tid"]})
                for bar in ciu.get("child_data") or []:
                    filas.append({"portal": "lavoz", "tid": bar["tid"], "nombre": bar["name"], "tipo": "barrio", "padre_tid": ciu["tid"]})
        return filas

    def estado_aviso(self, url):
        """Para avisos seguidos que no aparecieron en la búsqueda: sigue activo y a qué precio."""
        res = self.page.evaluate(
            """async (u) => { const r = await fetch(u, {redirect: 'follow'});
                              return {status: r.status, url: r.url, body: r.status === 200 ? await r.text() : ''} }""",
            url,
        )
        if res["status"] in (404, 410) or "/avisos/" not in res["url"]:
            return {"activo": False}
        m = re.search(r'"offers"\s*:\s*\{[^}]*"price"\s*:\s*"?([\d.,]+)"?[^}]*"priceCurrency"\s*:\s*"([^"]+)"', res["body"])
        if not m:
            return {"activo": True}
        return {"activo": True, "precio": _numero(m.group(1)), "moneda": _moneda(m.group(2))}


def _numero(txt):
    if txt is None:
        return None
    if isinstance(txt, (int, float)):
        return float(txt)
    limpio = re.sub(r"[^\d,]", "", str(txt)).replace(",", ".")
    try:
        return float(limpio) if limpio else None
    except ValueError:
        return None


def _coord(txt):
    try:
        return float(txt) if txt not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _moneda(txt):
    t = (txt or "").upper()
    if "U" in t or "USD" in t:
        return "USD"
    if "$" in t or "ARS" in t:
        return "ARS"
    return None


def _fecha(txt):
    try:
        return datetime.strptime(txt, "%d.%m.%Y").date().isoformat()
    except (TypeError, ValueError):
        return None


def normalizar(a, tipo):
    precio = a.get("price") or {}
    dire = a.get("address") or {}
    re_ = a.get("real_estate") or {}
    user = a.get("user") or {}
    fotos = []
    for img in ((a.get("multimedia") or {}).get("images") or {}).get("carousel") or []:
        thumbs = img.get("thumbnails") or {}
        grande = (thumbs.get("super_featured") or [{}])[0].get("url")
        fotos.append(grande or (img.get("original") or {}).get("url"))
    fotos = [f for f in fotos if f]
    return {
        "portal": "lavoz",
        "portal_id": str(a["id"]),
        "url": a.get("url"),
        "titulo": a.get("title"),
        "descripcion": (a.get("body") or "")[:4000],
        "tipo": tipo,
        "provincia": dire.get("province"),
        "ciudad": dire.get("city"),
        "barrio": dire.get("neighborhood"),
        "lat": _coord(dire.get("latitude")),
        "lng": _coord(dire.get("longitude")),
        "precio": _numero(precio.get("amount")),
        "moneda": _moneda(precio.get("currency")),
        "superficie_total": _numero(re_.get("total_area")),
        "dormitorios": re_.get("number_bedrooms"),
        "banos": re_.get("number_bathrooms"),
        "vendedor_tipo": user.get("role_name"),
        "vendedor_nombre": user.get("trade_name") or user.get("name"),
        "apto_escritura": re_.get("apt_deed"),
        "apto_credito": re_.get("apt_credit"),
        "fotos": fotos,
        "foto_principal": fotos[0] if fotos else None,
        "fecha_publicacion": _fecha(a.get("publish_date")),
    }
