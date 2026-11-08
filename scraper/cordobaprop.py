"""CórdobaProp: portal oficial del Colegio Profesional de Inmobiliarios de Córdoba (CPI).

Todas las publicaciones son de corredores matriculados. Las páginas de resultados
se arman en el servidor; con viewtype=list cada aviso es un <article class="property-card">
con título, barrio, dormitorios, baños, m², precio y logo de la inmobiliaria.
Paginación: &offset=24, 48, ...

Parámetros: operaciones=1 (venta), tipos (1 casa, 2 depto, 5 dúplex, 7 terreno),
localidades (1 = Córdoba capital; el resto se lee del formulario), dormitorios (0 a 4),
moneda (D dólares / P pesos), preciodesde, preciohasta.
"""
import re
import time
import unicodedata
from urllib.parse import urlencode

BASE = "https://www.cordobaprop.com"
POR_PAGINA = 24
PAUSA_ENTRE_PAGINAS = 1.5
TIPOS = {"casa": [1, 5], "departamento": [2], "terreno": [7]}
DORMITORIOS = {"monoambiente": 0, "1-dormitorio": 1, "2-dormitorios": 2, "3-dormitorios": 3, "4-dormitorios-o-mas": 4}

LEER_TARJETAS = r"""() => [...document.querySelectorAll('article.property-card')].map(c => {
  const txt = (s) => { const e = c.querySelector(s); return e ? e.textContent.replace(/\s+/g, ' ').trim() : null; };
  const a = c.querySelector('a[href*="/propiedad/"]');
  const img = c.querySelector('.card-image img');
  const ag = c.querySelector('.card-agency');
  return {href: a ? a.href : null, titulo: txt('.card-title'), ubicacion: txt('.card-location'),
          specs: [...c.querySelectorAll('.card-spec')].map(e => e.textContent.replace(/\s+/g, ' ').trim()),
          precio: txt('.card-price'), foto: img ? img.getAttribute('src') : null,
          inmobiliaria: ag ? ag.getAttribute('title') : null};
})"""


def _sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn").strip()


class CordobaProp:
    def __init__(self, page):
        self.page = page
        self.localidades = {}

    def abrir(self):
        self.page.goto(f"{BASE}/propiedades/?operaciones=1&viewtype=list", wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(2000)
        opciones = self.page.evaluate("""() => [...document.querySelectorAll('select[name=localidades] option')]
            .filter(o => o.value).map(o => [o.value, o.textContent.trim()])""")
        self.localidades = {_sin_acentos(n): v for v, n in opciones}

    def construir_consultas(self, f, nombres):
        ciudad = nombres.get(f.get("ciudad_tid"))
        localidad = self.localidades.get(_sin_acentos(ciudad)) if ciudad else None
        if ciudad and not localidad:
            print(f"    CórdobaProp no tiene la localidad {ciudad!r}: busco en toda la provincia y filtro después")
        comunes = {"operaciones": 1, "viewtype": "list"}
        if localidad:
            comunes["localidades"] = localidad
        desde, hasta = f.get("precio_desde"), f.get("precio_hasta")
        if desde or hasta:
            comunes["moneda"] = "P" if f.get("moneda") == "pesos" else "D"
            if desde:
                comunes["preciodesde"] = int(desde)
            if hasta:
                comunes["preciohasta"] = int(hasta)
        consultas = []
        for tipo in f.get("tipos") or ["casa", "departamento"]:
            for codigo in TIPOS.get(tipo, []):
                for d in f.get("dormitorios") or [None]:
                    params = dict(comunes, tipos=codigo)
                    if d in DORMITORIOS and tipo != "terreno":
                        params["dormitorios"] = DORMITORIOS[d]
                    consultas.append((tipo, d, f"{BASE}/propiedades/?{urlencode(params)}"))
        return consultas

    def buscar(self, url, max_paginas=10):
        avisos, vistos = [], set()
        for n in range(max_paginas):
            pag = url if n == 0 else f"{url}&offset={n * POR_PAGINA}"
            resp = self.page.goto(pag, wait_until="domcontentloaded", timeout=60000)
            if resp is not None and resp.status >= 400:
                raise RuntimeError(f"CórdobaProp respondió {resp.status} en {pag}")
            tarjetas = self.page.evaluate(LEER_TARJETAS)
            nuevas = [t for t in tarjetas if t["href"] and t["href"] not in vistos]
            for t in nuevas:
                vistos.add(t["href"])
            avisos += nuevas
            if len(tarjetas) < POR_PAGINA or not nuevas:
                break
            time.sleep(PAUSA_ENTRE_PAGINAS)
        return avisos

    def estado_aviso(self, url):
        resp = self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if resp is None or resp.status in (404, 410) or "/propiedad/" not in self.page.url:
            return {"activo": False}
        texto = self.page.evaluate("() => document.body.innerText")
        m = re.search(r"(USD|AR\$)\s*([\d.,]+)", texto)
        if not m:
            return {"activo": True}
        return {"activo": True, "precio": _numero(m.group(2)), "moneda": "USD" if m.group(1) == "USD" else "ARS"}


def _numero(txt):
    limpio = re.sub(r"[^\d]", "", txt or "")
    return float(limpio) if limpio else None


def _superficie(txt):
    """CórdobaProp usa coma de miles ("1,200 m²")."""
    try:
        return float(txt.replace(",", "")) or None
    except ValueError:
        return None


def normalizar(t, tipo, dorm, textos_dorm):
    m = re.search(r"/propiedad/(\d+)", t.get("href") or "")
    precio_m = re.search(r"(USD|AR\$|U\$S|\$)\s*([\d.,]+)", t.get("precio") or "")
    precio = _numero(precio_m.group(2)) if precio_m else None
    moneda = ("USD" if "U" in precio_m.group(1) else "ARS") if precio_m else None
    specs = " · ".join(t.get("specs") or [])
    dm = re.search(r"(\d+)\s*dorm", specs)
    bm = re.search(r"(\d+)\s*bañ", specs)
    sm = re.search(r"([\d.,]+)\s*m²", specs)
    if dorm in textos_dorm:
        dormitorios = textos_dorm[dorm]
    elif dm:
        n = int(dm.group(1))
        dormitorios = "Monoambiente" if n == 0 else "4 Dormitorios o más" if n >= 4 else f"{n} Dormitorio{'s' if n > 1 else ''}"
    else:
        dormitorios = None
    ubic = t.get("ubicacion") or ""
    barrio, _, ciudad = ubic.partition(" - ")
    foto = t.get("foto")
    if foto and foto.startswith("/"):
        foto = BASE + foto
    return {
        "portal": "cordobaprop",
        "portal_id": m.group(1) if m else t.get("href"),
        "url": t.get("href"),
        "titulo": t.get("titulo"),
        "descripcion": specs or None,
        "tipo": tipo,
        "provincia": "Córdoba",
        "ciudad": (ciudad or barrio or None),
        "barrio": barrio or None,
        "lat": None,
        "lng": None,
        "precio": precio if precio and precio > 100 else None,  # algunos avisos cargan "USD 34" por error
        "moneda": moneda,
        "superficie_total": _superficie(sm.group(1)) if sm else None,
        "dormitorios": dormitorios,
        "banos": f"{bm.group(1)} Baño{'s' if bm.group(1) != '1' else ''}" if bm else None,
        "vendedor_tipo": "Inmobiliaria",
        "vendedor_nombre": t.get("inmobiliaria"),
        "apto_escritura": None,
        "apto_credito": None,
        "fotos": [foto] if foto else [],
        "foto_principal": foto,
        "fecha_publicacion": None,
    }


def coincide_ubicacion(p, f, nombres):
    """Barrio (y ciudad, si el portal no la tenía) se controlan con el texto de la tarjeta."""
    texto = _sin_acentos((p.get("barrio") or "") + " - " + (p.get("ciudad") or ""))
    barrios = [nombres.get(b) for b in (f.get("barrios_tid") or []) if nombres.get(b)]
    if barrios:
        hallado = next((b for b in barrios if _sin_acentos(b) in texto), None)
        if not hallado:
            return False
        p["barrio"] = hallado
    ciudad = nombres.get(f.get("ciudad_tid"))
    if ciudad and _sin_acentos(ciudad) not in texto:
        return False
    if ciudad:
        p["ciudad"] = ciudad
    return True
