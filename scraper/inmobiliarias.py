"""Webs propias de inmobiliarias de Córdoba hechas con Tokko Broker (todas tienen la misma estructura).

Salió del sondeo del 08/11/2026: de las inmobiliarias que publican en La Voz, estas tienen web Tokko.
Listado de venta: https://<sitio>/Venta?page=N (40 por página). Cada aviso es un <li prop-id="…"> con
enlace /p/<id>-<Tipo>-en-Venta-en-<Barrio>…, foto, m², ambientes, "Tipo en Venta en Barrio, Ciudad",
dirección y precio ("USD180.000"). En la web se muestran juntas como "Inmobiliarias".
"""
import re
import time
import unicodedata

SITIOS = {
    "López Baena Propiedades": "https://www.lopezbaena.com.ar",
    "Bergo Servicios Inmobiliarios": "https://www.bergo.com.ar",
    "Neta Inmobiliaria": "https://www.inmobiliarianeta.com.ar",
    "Vegas In": "https://www.vegas-in.com",
    "Grupo Banker": "https://www.grupobanker.com",
    "ZF Propiedades": "https://www.zfpropiedades.com.ar",
    "Domus Propiedades": "https://www.domuspropiedades.com.ar",
    "Inmobiliaria Caffaratti": "https://www.rcaffaratti.com",
    "Consultia Inmobiliaria": "https://www.consultiainmo.com",
    "Merguerian Bienes Raíces": "https://www.merguerian.com.ar",
    "SOYS Inmobiliaria": "https://www.soysinmobiliaria.com.ar",
    "Malbran Operadores Inmobiliarios": "https://www.eduardomalbran.com",
    "Oronel Fay": "https://www.oronelfay.com.ar",
    "Fabregas Molina": "https://www.fabregasmolina.com",
}
PAUSA = 1.2
TIPOS = {"departamento": "departamento", "casa": "casa", "duplex": "casa", "ph": "casa", "terreno": "terreno", "lote": "terreno"}

LEER = r"""() => [...document.querySelectorAll('li[prop-id]')].map(li => {
  const t = (s) => { const e = li.querySelector(s); return e ? e.textContent.replace(/\s+/g, ' ').trim() : null; };
  const a = li.querySelector('a[href*="/p/"]');
  const img = li.querySelector('img.dest-img');
  const valor = li.querySelector('.prop-valor-nro');
  return {id: li.getAttribute('prop-id'), href: a ? a.href : null, tipoUb: t('.prop-desc-tipo-ub'), dir: t('.prop-desc-dir'),
          m2: t('.prop-data div'), amb: t('.prop-data2 div'), foto: img ? img.getAttribute('src') : null,
          precio: valor ? valor.childNodes[0].textContent.replace(/\s+/g, ' ').trim() : null};
})"""


def _sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn").strip()


class Inmobiliarias:
    def __init__(self, page):
        self.page = page
        self._todos = None

    def abrir(self):
        pass

    def todos(self, max_paginas=10):
        """Avisos en venta de todas las inmobiliarias (una vez por corrida)."""
        if self._todos is not None:
            return self._todos
        avisos = []
        for nombre, base in SITIOS.items():
            vistos, cantidad = set(), 0
            try:
                for n in range(1, max_paginas + 1):
                    url = f"{base}/Venta" + (f"?page={n}" if n > 1 else "")
                    resp = self.page.goto(url, wait_until="domcontentloaded", timeout=40000)
                    if resp is not None and resp.status >= 400:
                        break
                    self.page.wait_for_timeout(800)
                    nuevos = [x for x in self.page.evaluate(LEER) if x["id"] and x["id"] not in vistos]
                    if not nuevos:
                        break
                    for x in nuevos:
                        vistos.add(x["id"])
                        x["inmobiliaria"] = nombre
                    avisos += nuevos
                    cantidad += len(nuevos)
                    time.sleep(PAUSA)
            except Exception as e:
                print(f"    {nombre}: no pude leer la web ({e})")
            print(f"    {nombre}: {cantidad} avisos en venta")
        self._todos = avisos
        return avisos

    def estado_aviso(self, url):
        resp = self.page.goto(url, wait_until="domcontentloaded", timeout=40000)
        if resp is None or resp.status in (404, 410) or "/p/" not in self.page.url:
            return {"activo": False}
        m = re.search(r"Venta\s+(USD|\$)\s*([\d.]+)", self.page.evaluate("() => document.body.innerText"))
        if not m:
            return {"activo": True}
        return {"activo": True, "precio": float(m.group(2).replace(".", "")), "moneda": "USD" if m.group(1) == "USD" else "ARS"}


def normalizar(x):
    tipo_ub = x.get("tipoUb") or ""
    m = re.match(r"\s*(\S+)\s+en\s+Venta(?:\s*-\s*\S+)?\s+en\s+([^,]+),?\s*(.*)", tipo_ub, re.I)
    tipo = TIPOS.get(_sin_acentos(m.group(1))) if m else None
    barrio = m.group(2).strip() if m else None
    ciudad = (m.group(3).strip() if m else "") or None
    if ciudad and _sin_acentos(ciudad) in ("cordoba capital", "capital", "cordoba"):
        ciudad = "Córdoba"
    pm = re.search(r"(USD|U\$S|\$)\s*([\d.]+)", x.get("precio") or "")
    precio = float(pm.group(2).replace(".", "")) if pm else None
    moneda = ("USD" if "U" in pm.group(1) else "ARS") if pm else None
    sup = re.search(r"([\d.,]+)\s*m", x.get("m2") or "")
    try:
        superficie = float(sup.group(1).replace(".", "").replace(",", ".")) if sup else None
    except ValueError:
        superficie = None
    amb = re.search(r"\d+", x.get("amb") or "")
    dormitorios = None
    if amb and tipo != "terreno":
        n = int(amb.group(0)) - 1  # estimado: ambientes menos el living
        dormitorios = "Monoambiente" if n <= 0 else "4 Dormitorios o más" if n >= 4 else f"{n} Dormitorio{'s' if n > 1 else ''}"
    titulo = " · ".join(t for t in [tipo_ub.split(",")[0], x.get("dir")] if t and t != "-")
    return {
        "portal": "inmobiliarias",
        "portal_id": f"tokko-{x['id']}",
        "url": (x.get("href") or "").split("?")[0],
        "titulo": titulo,
        "descripcion": f"{tipo_ub}. {x.get('dir') or ''}".strip(),
        "tipo": tipo,
        "provincia": "Córdoba",
        "ciudad": ciudad,
        "barrio": barrio,
        "lat": None,
        "lng": None,
        "precio": precio,
        "moneda": moneda,
        "superficie_total": superficie,
        "dormitorios": dormitorios,
        "banos": None,
        "vendedor_tipo": "Inmobiliaria",
        "vendedor_nombre": x.get("inmobiliaria"),
        "apto_escritura": None,
        "apto_credito": None,
        "fotos": [x["foto"]] if x.get("foto") else [],
        "foto_principal": x.get("foto"),
        "fecha_publicacion": None,
    }


def coincide(p, f, nombres, textos_dorm):
    if p["tipo"] not in (f.get("tipos") or ["casa", "departamento"]):
        return False
    dorms = [textos_dorm[d] for d in (f.get("dormitorios") or []) if d in textos_dorm]
    if dorms and p["dormitorios"] not in dorms:
        return False
    ciudad = nombres.get(f.get("ciudad_tid"))
    if ciudad and _sin_acentos(ciudad) != _sin_acentos(p.get("ciudad")):
        return False
    barrios = [nombres.get(b) for b in (f.get("barrios_tid") or []) if nombres.get(b)]
    if barrios:
        texto = _sin_acentos(f"{p.get('barrio')} {p.get('descripcion')}")
        hallado = next((b for b in barrios if _sin_acentos(b) in texto), None)
        if not hallado:
            return False
        p["barrio"] = hallado
    return True
