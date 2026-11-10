"""Barrios oficiales de la ciudad de Córdoba (Municipalidad, vía OpenDataCordoba) y zonas.

Cada aviso se ubica en un barrio oficial:
1. Por coordenadas, si las tiene (el punto cae dentro del polígono del barrio).
2. Por el nombre de barrio que trae el portal, normalizado (sin acentos, "B°", abreviaturas).
3. Buscando nombres de barrios en el título y la descripción.

La zona (centro, norte, sur, este, oeste) es la del barrio: centro si está a menos de
2,2 km de la plaza San Martín; si no, según el rumbo desde la plaza.
"""
import difflib
import json
import os
import re
import unicodedata

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

ARCHIVO = os.path.join(os.path.dirname(__file__), "datos", "barrios-cordoba.geojson")
ZONAS = ["centro", "norte", "sur", "este", "oeste"]

# Cómo escriben los portales algunos barrios → nombre oficial.
ALIAS = {
    "nueva cba": "NUEVA CORDOBA", "nva cordoba": "NUEVA CORDOBA", "nva cba": "NUEVA CORDOBA",
    "gral paz": "GENERAL PAZ", "alta cba": "ALTA CORDOBA", "cerro": "CERRO DE LAS ROSAS",
    "cerro de las rosas": "CERRO DE LAS ROSAS", "crisol": "CRISOL NORTE", "pueyrredon": "GENERAL PUEYRREDON",
    "junior": "JUNIORS", "juniors": "JUNIORS", "maipu": "MAIPU 1A SECCION", "barrio jardin": "JARDIN",
    "centro cordoba": "CENTRO", "microcentro": "CENTRO", "macrocentro": "CENTRO", "centro sur": "CENTRO",
    "guemes": "GUEMES", "paso de los andes": "ALBERDI", "barrio parque velez sarsfield": "PARQUE VELEZ SARSFIELD",
    "villa belgrano": "VILLA BELGRANO", "arguello": "ARGUELLO", "urca": "URCA", "san vicente": "SAN VICENTE",
    "las rosas": "LAS ROSAS", "chateau": "CHATEAU CARRERAS", "general bustos": "GENERAL BUSTOS",
    "observatorio": "OBSERVATORIO", "cofico": "COFICO", "alto alberdi": "ALTO ALBERDI",
}
CIUDAD_CORDOBA = {"cordoba", "cordoba capital", "capital", "ciudad de cordoba", "cordoba ciudad"}
# Palabras demasiado comunes para buscarlas sueltas en una descripción.
NO_BUSCAR_EN_TEXTO = {"CENTRO", "JARDIN", "PROVIDENCIA", "LAS ROSAS", "OBSERVATORIO", "COMERCIAL", "INDUSTRIAL",
                      "POLICIAL", "AEROPUERTO", "HOSPITAL", "ESTACION", "UNIVERSITARIO", "SAN MARTIN"}


def norm(t):
    t = "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")
    t = re.sub(r"\b(barrio|b[°º]|bo\.?|b\.)\s*", " ", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def bonito(nombre):
    """NUEVA CORDOBA → Nueva Córdoba (para mostrar)."""
    acentos = {"cordoba": "Córdoba", "guemes": "Güemes", "jardin": "Jardín", "maria": "María", "jose": "José",
               "arguello": "Argüello", "maipu": "Maipú", "ituzaingo": "Ituzaingó", "general": "General",
               "pueyrredon": "Pueyrredón", "velez": "Vélez", "sarsfield": "Sársfield", "ingles": "Inglés",
               "martin": "Martín", "fatima": "Fátima", "sebastian": "Sebastián", "ines": "Inés", "rio": "Río"}
    palabras = []
    for i, w in enumerate(nombre.lower().split()):
        if w in acentos:
            palabras.append(acentos[w])
        elif i and w in {"de", "del", "la", "las", "los", "y", "el"}:
            palabras.append(w)
        else:
            palabras.append(w.capitalize())
    return " ".join(palabras)


class Barrios:
    def __init__(self, archivo=ARCHIVO):
        datos = json.load(open(archivo, encoding="utf-8"))["features"]
        self.lista = [f["properties"] for f in datos]
        self.geoms = [shape(f["geometry"]) for f in datos]
        self.arbol = STRtree(self.geoms)
        self.por_nombre = {norm(b["nombre"]): b for b in self.lista}
        self.nombres_norm = sorted(self.por_nombre, key=len, reverse=True)
        self.patron = re.compile(r"\b(" + "|".join(re.escape(n) for n in self.nombres_norm
                                                    if len(n) >= 6 and self.por_nombre[n]["nombre"] not in NO_BUSCAR_EN_TEXTO) + r")\b")

    def por_punto(self, lat, lng):
        if lat is None or lng is None:
            return None
        pt = Point(float(lng), float(lat))
        for i in self.arbol.query(pt):
            if self.geoms[int(i)].contains(pt):
                return self.lista[int(i)]
        return None

    def por_texto_barrio(self, texto):
        n = norm(texto)
        if not n:
            return None
        if n in ALIAS:
            return self.por_nombre.get(norm(ALIAS[n]))
        if n in self.por_nombre:
            return self.por_nombre[n]
        parecidos = difflib.get_close_matches(n, self.nombres_norm, n=1, cutoff=0.9)
        return self.por_nombre[parecidos[0]] if parecidos else None

    def por_descripcion(self, texto):
        m = self.patron.search(norm(texto))
        return self.por_nombre.get(m.group(1)) if m else None

    def asignar(self, p):
        """Devuelve (barrio, origen) o (None, None). barrio es el dict con id, nombre, zona."""
        b = self.por_punto(p.get("lat"), p.get("lng"))
        if b:
            return b, "punto"
        ciudad = norm(p.get("ciudad"))
        if ciudad and ciudad not in CIUDAD_CORDOBA and ciudad not in self.por_nombre:
            return None, None  # es de otra localidad
        for campo in ("barrio", "ciudad"):
            b = self.por_texto_barrio(p.get(campo))
            if b:
                return b, "nombre"
        b = self.por_descripcion(f"{p.get('titulo') or ''} {p.get('descripcion') or ''}")
        return (b, "texto") if b else (None, None)
