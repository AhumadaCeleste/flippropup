"""Detecta la misma propiedad publicada varias veces (en distintos portales o por distintas inmobiliarias).

Dos avisos se consideran la misma propiedad si son del mismo tipo, en la misma moneda, con precios
parecidos (hasta 12 % de diferencia), sin dormitorios contradictorios, y además se cumple alguna de estas:
  - mismo teléfono;
  - misma superficie (±3 % o ±2 m²) en el mismo barrio;
  - coordenadas a menos de 80 m y superficie parecida (o sin dato);
  - títulos muy parecidos en el mismo barrio.
Los grupos de más de 6 avisos suelen ser edificios en pozo con muchas unidades iguales: se descartan.
"""
import math
import re
import unicodedata

MAX_GRUPO = 6
PALABRAS_VACIAS = {"de", "en", "la", "el", "y", "con", "a", "del", "los", "las", "venta", "vendo", "se", "vende",
                   "casa", "departamento", "depto", "dpto", "terreno", "lote", "cordoba", "barrio", "b", "u$s", "usd"}


def _norm(t):
    t = "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", t)


def _palabras(t):
    return {w for w in _norm(t).split() if len(w) > 2 and w not in PALABRAS_VACIAS}


def _cerca(a, b, tol):
    return a and b and abs(a - b) <= tol * max(a, b)


def _metros(a, b):
    dx = (float(a["lng"]) - float(b["lng"])) * 111320 * math.cos(math.radians(float(a["lat"])))
    dy = (float(a["lat"]) - float(b["lat"])) * 110570
    return math.hypot(dx, dy)


def _misma(a, b):
    if a["tipo"] != b["tipo"] or a.get("moneda") != b.get("moneda"):
        return False
    if a["portal"] == b["portal"] and a["portal_id"] == b["portal_id"]:
        return False
    if a.get("dormitorios") and b.get("dormitorios") and a["dormitorios"] != b["dormitorios"]:
        return False
    pa, pb = float(a.get("precio") or 0), float(b.get("precio") or 0)
    if not (pa and pb and _cerca(pa, pb, 0.12)):
        return False
    sa, sb = float(a.get("superficie_total") or 0), float(b.get("superficie_total") or 0)
    sup_igual = sa and sb and (abs(sa - sb) <= 2 or _cerca(sa, sb, 0.03))
    sup_parecida = not (sa and sb) or _cerca(sa, sb, 0.08)
    mismo_barrio = bool(({a.get("barrio_id"), a.get("barrio_anuncio_id")} - {None})
                        & ({b.get("barrio_id"), b.get("barrio_anuncio_id")} - {None}))
    if a.get("telefono") and a.get("telefono") == b.get("telefono") and sup_parecida:
        return True
    if sup_igual and mismo_barrio and _cerca(pa, pb, 0.10):
        return True
    if a.get("lat") and b.get("lat") and a.get("lng") and b.get("lng") and _metros(a, b) <= 80 and sup_parecida and _cerca(pa, pb, 0.10):
        return True
    if mismo_barrio and sup_parecida and _cerca(pa, pb, 0.10):
        wa, wb = _palabras(a.get("titulo")), _palabras(b.get("titulo"))
        if len(wa) >= 3 and len(wb) >= 3 and len(wa & wb) / len(wa | wb) >= 0.55:
            return True
    return False


def agrupar(avisos):
    """avisos: lista de dicts. Devuelve {id: dict(grupo_id, grupo_n, grupo_min, grupo_max, grupo_anunciantes)}."""
    padre = {a["id"]: a["id"] for a in avisos}

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    def unir(x, y):
        rx, ry = raiz(x), raiz(y)
        if rx != ry:
            padre[max(rx, ry)] = min(rx, ry)

    cubetas = {}
    for a in avisos:
        claves = {("b", a["tipo"], a.get("barrio_id")), ("b", a["tipo"], a.get("barrio_anuncio_id"))}
        if a.get("telefono"):
            claves.add(("t", a["tipo"], a["telefono"]))
        if a.get("lat") and a.get("lng"):
            claves.add(("g", a["tipo"], round(float(a["lat"]), 3), round(float(a["lng"]), 3)))
        for c in claves:
            if None not in c:
                cubetas.setdefault(c, []).append(a)
    for lista in cubetas.values():
        if len(lista) > 2000:
            continue
        lista = sorted(lista, key=lambda x: float(x.get("precio") or 0))
        for i, a in enumerate(lista):
            pa = float(a.get("precio") or 0)
            for b in lista[i + 1:]:
                if pa and float(b.get("precio") or 0) > pa * 1.13:
                    break  # ordenados por precio: los siguientes ya difieren demasiado
                if _misma(a, b):
                    unir(a["id"], b["id"])

    grupos = {}
    for a in avisos:
        grupos.setdefault(raiz(a["id"]), []).append(a)
    res = {}
    for gid, miembros in grupos.items():
        if len(miembros) < 2 or len(miembros) > MAX_GRUPO:
            continue
        precios = [float(m["precio"]) for m in miembros if m.get("precio")]
        anunciantes = {_norm(m.get("vendedor_nombre")).strip() or f"{m['portal']}:{m['id']}" for m in miembros}
        for m in miembros:
            res[m["id"]] = {"grupo_id": gid, "grupo_n": len(miembros), "grupo_min": min(precios), "grupo_max": max(precios),
                            "grupo_anunciantes": len(anunciantes)}
    return res
