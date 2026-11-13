"""Zonaprop: avisos capturados desde el navegador de Cele.

Zonaprop está detrás de Cloudflare y bloquea a los servidores de GitHub. Una tarea programada
en la computadora de Cele (con la app de Claude abierta) recorre la API de listados de Zonaprop
para Córdoba capital (deptos, casas y terrenos) y deja cada página en la tabla zonaprop_crudo
(ver captura/zonaprop.js). El robot toma el último lote completo y lo guarda como cualquier portal.

Campos compactos de cada fila (los arma captura/zonaprop.js):
  id, u (url), t (título), ti (tipo Zonaprop), p (precio), m (moneda), st / sc (m² totales / cubiertos),
  am, do, ba, an (ambientes, dormitorios, baños, antigüedad), b / bl (barrio y su nivel), c (ciudad),
  dir, la, lo, pu / pt (anunciante y tipo), f (fotos), d (descripción), r (reservado)
"""
import re
import unicodedata
from datetime import datetime, timedelta, timezone

BASE = "https://www.zonaprop.com.ar"
TIPOS = {"Departamentos": "departamento", "Casas": "casa", "Terrenos": "terreno", "PH": "departamento"}


def _sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def _num(v):
    try:
        return float(str(v).replace(",", ".")) if v not in (None, "") else None
    except ValueError:
        return None


def reciente(lote, horas=36):
    """El lote es la fecha y hora UTC de la captura (2026-11-13T01:24)."""
    try:
        cuando = datetime.fromisoformat(lote).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return False
    return datetime.now(timezone.utc) - cuando < timedelta(hours=horas)


def traer(sb):
    """Filas del lote más nuevo. Si tiene más de 36 h (la compu estuvo apagada), no se usa."""
    ult = sb.table("zonaprop_crudo").select("lote,creado").order("creado", desc=True).limit(1).execute().data
    if not ult:
        print("    Zonaprop: todavía no hay capturas")
        return [], None, False
    lote = ult[0]["lote"]
    if not reciente(lote):
        print(f"    Zonaprop: la última captura ({lote} UTC) es vieja; ¿la compu estuvo apagada?")
        return [], lote, False
    filas, completo, desde = [], True, 0
    paginas = {}
    while True:
        r = (sb.table("zonaprop_crudo").select("tipo,pagina,paginas,filas").eq("lote", lote)
             .order("id").range(desde, desde + 49).execute().data)
        for x in r:
            filas += [dict(f, _tipo=x["tipo"]) for f in x["filas"]]
            paginas.setdefault(x["tipo"], [x["paginas"], set()])[1].add(x["pagina"])
        if len(r) < 50:
            break
        desde += 50
    for tipo, (total, vistas) in paginas.items():
        if len(vistas) < total:
            completo = False
            print(f"    Zonaprop {tipo}: llegaron {len(vistas)} de {total} páginas")
    vistos, unicos = set(), []
    for f in filas:
        if f.get("id") and f["id"] not in vistos:
            vistos.add(f["id"])
            unicos.append(f)
    print(f"    Zonaprop lote {lote}: {len(unicos)} avisos ({'completo' if completo else 'incompleto'})")
    return unicos, lote, completo


def normalizar(a):
    tipo = TIPOS.get(a.get("ti")) or a.get("_tipo")
    if a.get("ti") and a["ti"] not in TIPOS:  # emprendimientos, cocheras, etc.
        tipo = None
    precio = _num(a.get("p"))
    moneda = {"USD": "USD", "U$S": "USD", "$": "ARS", "ARS": "ARS"}.get(a.get("m"))
    dorm = _num(a.get("do"))
    dormitorios = None if dorm is None else ("Monoambiente" if dorm == 0 else
                                            "4 Dormitorios o más" if dorm >= 4 else f"{int(dorm)} Dormitorio{'s' if dorm > 1 else ''}")
    banos = _num(a.get("ba"))
    sup = _num(a.get("st")) or _num(a.get("sc"))
    # En los terrenos la superficie que cuenta es la total; en el resto, la cubierta si es la única.
    # La captura ya pide solo Córdoba Capital; Zonaprop anida algunos countries (Valle Escondido, DOCTA)
    # como "ciudad" dentro de la capital, así que la ciudad se fija y el barrio sale del aviso o de las coordenadas.
    barrio = a.get("b") if a.get("bl") == "ZONA" else None
    ciudad = "Córdoba"
    desc = a.get("d") or ""
    fotos = [f for f in (a.get("f") or []) if f]
    return {
        "portal": "zonaprop",
        "portal_id": str(a["id"]),
        "url": BASE + a["u"] if (a.get("u") or "").startswith("/") else a.get("u"),
        "titulo": a.get("t"),
        "descripcion": desc[:4000],
        "tipo": tipo,
        "provincia": "Córdoba",
        "ciudad": (ciudad or "Córdoba").strip(),
        "barrio": barrio,
        "lat": _num(a.get("la")),
        "lng": _num(a.get("lo")),
        "precio": precio,
        "moneda": moneda,
        "superficie_total": sup,
        "dormitorios": dormitorios,
        "banos": f"{int(banos)} Baño{'s' if banos > 1 else ''}" if banos else None,
        "vendedor_tipo": "Particular" if str(a.get("pt")) == "1" else "Inmobiliaria",
        "vendedor_nombre": a.get("pu"),
        "apto_escritura": None,
        "apto_credito": "Sí" if re.search(r"apto\s+cr[eé]dito", _sin_acentos(desc + " " + (a.get("t") or ""))) else None,
        "fotos": fotos,
        "foto_principal": fotos[0] if fotos else None,
        "fecha_publicacion": None,
    }


def es_capital(p):
    return _sin_acentos(p.get("ciudad")) in ("cordoba", "cordoba capital")


def coincide(p, f, nombres, textos_dorm):
    """Filtros que se controlan de nuestro lado: tipo, dormitorios, ciudad y barrio."""
    if not p["tipo"] or not p["portal_id"] or not es_capital(p):
        return False
    tipos = f.get("tipos") or ["casa", "departamento"]
    if p["tipo"] not in tipos:
        return False
    dorms = [textos_dorm[d] for d in (f.get("dormitorios") or []) if d in textos_dorm]
    if dorms and p["dormitorios"] not in dorms:
        return False
    barrios = [nombres.get(b) for b in (f.get("barrios_tid") or []) if nombres.get(b)]
    if barrios and _sin_acentos(p.get("barrio")) not in {_sin_acentos(b) for b in barrios}:
        return False
    return True
