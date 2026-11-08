"""InmoUP: portal de inmobiliarias de Córdoba y Cuyo.

Cada página de resultados trae los avisos en un bloque JSON-LD (schema.org
ItemList) con precio, moneda, descripción, foto, dormitorios y superficie.
Las páginas siguen el formato ...-de-cordoba-y-pag-2. Como son pocos avisos
(unos 240 en Córdoba capital), se traen todos una vez por corrida y cada
búsqueda guardada se filtra de nuestro lado.
"""
import json
import math
import re
import time
import unicodedata

BASE = "https://inmoup.com.ar"
POR_PAGINA = 24
PAUSA_ENTRE_PAGINAS = 1.5
TIPO_POR_SLUG = {"casa": "casa", "departamento": "departamento", "terreno": "terreno", "lote": "terreno"}

LEER_LD = """() => { const out = []; let total = null;
  document.querySelectorAll('script[type="application/ld+json"]').forEach(s => { try {
    const d = JSON.parse(s.textContent);
    (d['@graph'] || [d]).forEach(n => {
      const lista = n.mainEntity && n.mainEntity.mainEntity;
      if (lista && lista.itemListElement) lista.itemListElement.forEach(i => out.push(i.item));
      const m = /^(\\d+)\\s/.exec(n.name || ''); if (m && total === null) total = Number(m[1]);
    });
  } catch (e) {} });
  return {avisos: out, total}; }"""


def slug(txt):
    t = "".join(c for c in unicodedata.normalize("NFD", (txt or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def _sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


class InmoUP:
    def __init__(self, page):
        self.page = page
        self._cache = {}

    def abrir(self):
        self.page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(1500)

    def _leer(self, url):
        resp = self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if resp is not None and resp.status >= 400:
            raise RuntimeError(f"InmoUP respondió {resp.status} en {url}")
        self.page.wait_for_timeout(1500)
        return self.page.evaluate(LEER_LD)

    def todos(self, ciudad, max_paginas=20):
        """Todos los avisos en venta de una ciudad de Córdoba (se guardan por corrida)."""
        clave = slug(ciudad or "Córdoba")
        if clave in self._cache:
            return self._cache[clave]
        base = f"{BASE}/inmuebles-en-venta-en-{clave}-de-cordoba"
        primera = self._leer(base)
        avisos, vistos = [], set()
        paginas = min(max_paginas, math.ceil((primera["total"] or POR_PAGINA) / POR_PAGINA))
        datos = primera
        for n in range(1, paginas + 1):
            if n > 1:
                time.sleep(PAUSA_ENTRE_PAGINAS)
                datos = self._leer(f"{base}-y-pag-{n}")
            nuevos = [a for a in datos["avisos"] if a.get("url") and a["url"] not in vistos]
            for a in nuevos:
                vistos.add(a["url"])
            avisos += nuevos
            if not nuevos:
                break
        print(f"    InmoUP {ciudad or 'Córdoba'}: {len(avisos)} avisos (el sitio informa {primera['total']}) en {paginas} páginas")
        self._cache[clave] = avisos
        return avisos

    def estado_aviso(self, url):
        resp = self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if resp is None or resp.status in (404, 410) or "/ficha/" not in self.page.url:
            return {"activo": False}
        html = self.page.content()
        m = re.search(r'"price"\s*:\s*"?([\d.]+)"?\s*,\s*"priceCurrency"\s*:\s*"([A-Z]+)"', html)
        if not m:
            return {"activo": True}
        return {"activo": True, "precio": float(m.group(1)), "moneda": "USD" if m.group(2) == "USD" else "ARS"}


def _prop(a, nombre):
    for p in a.get("additionalProperty") or []:
        if _sin_acentos(p.get("name")) == _sin_acentos(nombre):
            return p.get("value")
    return None


def normalizar(a, ciudad):
    url = (a.get("url") or "").split("?")[0]
    m = re.search(r"inmoup\.com\.ar/(\d+)[^/]*/inmuebles/(\d+)/ficha/([^/?#]+)", url)
    ficha = m.group(3) if m else ""
    tipo_slug = ficha.split("-en-")[0] if ficha else ""
    tipo = TIPO_POR_SLUG.get(tipo_slug)
    oferta = a.get("offers") or {}
    try:
        precio = float(oferta.get("price")) if oferta.get("price") not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        precio = None
    moneda = {"USD": "USD", "ARS": "ARS"}.get((oferta.get("priceCurrency") or "").upper())
    dorm = _prop(a, "Dormitorios")
    try:
        n = int(float(dorm)) if dorm not in (None, "") else None
    except ValueError:
        n = None
    dormitorios = None if n is None else ("Monoambiente" if n == 0 else
                                          "4 Dormitorios o más" if n >= 4 else f"{n} Dormitorio{'s' if n > 1 else ''}")
    banos = _prop(a, "Baños")
    try:
        sup = float(_prop(a, "Superficie")) or None
    except (TypeError, ValueError):
        sup = None
    titulo = ficha.replace("-", " ").capitalize() if ficha else a.get("name")
    proveedor = a.get("provider") or {}
    foto = a.get("image") if isinstance(a.get("image"), str) else None
    return {
        "portal": "inmoup",
        "portal_id": f"{m.group(1)}-{m.group(2)}" if m else url,
        "url": url,
        "titulo": titulo,
        "descripcion": (a.get("description") or "")[:4000],
        "tipo": tipo,
        "provincia": "Córdoba",
        "ciudad": ciudad or "Córdoba",
        "barrio": None,
        "lat": None,
        "lng": None,
        "precio": precio,
        "moneda": moneda,
        "superficie_total": sup,
        "dormitorios": dormitorios,
        "banos": f"{banos} Baño{'s' if str(banos) != '1' else ''}" if banos else None,
        "vendedor_tipo": "Inmobiliaria",
        "vendedor_nombre": proveedor.get("name"),
        "apto_escritura": None,
        "apto_credito": "Sí" if re.search(r"apto\s+cr[eé]dito", _sin_acentos(a.get("description")), re.I) else None,
        "fotos": [foto] if foto else [],
        "foto_principal": foto,
        "fecha_publicacion": None,
    }


def coincide(p, f, nombres, textos_dorm):
    """Filtros que en InmoUP se controlan de nuestro lado: tipo, dormitorios y barrio."""
    tipos = f.get("tipos") or ["casa", "departamento"]
    if p["tipo"] not in tipos:
        return False
    dorms = [textos_dorm[d] for d in (f.get("dormitorios") or []) if d in textos_dorm]
    if dorms and p["dormitorios"] not in dorms:
        return False
    barrios = [nombres.get(b) for b in (f.get("barrios_tid") or []) if nombres.get(b)]
    if barrios:
        texto = _sin_acentos((p["titulo"] or "") + " " + (p["descripcion"] or ""))
        hallado = next((b for b in barrios if _sin_acentos(b) in texto), None)
        if not hallado:
            return False
        p["barrio"] = hallado
    return True
