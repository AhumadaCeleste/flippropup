"""Índice IDECOR: valor de referencia del Estado provincial para comparar con el precio publicado.

- Casas: mediana de U$S por m² construido de las ofertas que relevó el Observatorio del Mercado
  Inmobiliario (capas omi_edificado_2024 y omi_edificado_2025 del geoservicio de IDECOR) cerca del aviso.
- Terrenos: Valor Unitario de la Tierra 2025 (capa vut_2025, pesos por m² a mayo de 2025) de la parcela,
  pasado a dólares con TC_VUT (dólar oficial de mayo de 2025, por defecto 1150).
- Departamentos: IDECOR no publica valores de propiedad horizontal; para ellos se usa la referencia
  de mercado que arma la base con los avisos (función recalcular_referencias).
"""
import json
import math
import os
import statistics
import urllib.parse
import urllib.request

WFS = "https://gn-idecor.mapascordoba.gob.ar/geoserver/wfs"
BBOX_CORDOBA = (-64.36, -31.55, -64.02, -31.27)  # lng_min, lat_min, lng_max, lat_max
TC_VUT = float(os.environ.get("TC_VUT", "1150"))
UA = {"User-Agent": "FlipPropUp/1.0 (+robot de avisos)"}


def _get(params, timeout=90):
    url = WFS + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ofertas_omi(anios=("2024", "2025")):
    """Ofertas de viviendas en dólares dentro de Córdoba capital: lista de (lat, lng, usd_m2)."""
    puntos = []
    for anio in anios:
        datos = _get({
            "service": "WFS", "version": "1.0.0", "request": "GetFeature", "outputFormat": "application/json",
            "srsName": "EPSG:4326", "typeName": f"idecor:omi_edificado_{anio}",
            "propertyName": "geom,valor,moneda,superficie_construida,uso_edificado,tipo_valor",
            "bbox": ",".join(str(x) for x in BBOX_CORDOBA) + ",EPSG:4326",
        })
        for f in datos.get("features", []):
            p, g = f.get("properties") or {}, f.get("geometry") or {}
            try:
                valor, sup = float(p.get("valor") or 0), float(p.get("superficie_construida") or 0)
                lng, lat = g["coordinates"][:2]
            except (TypeError, ValueError, KeyError):
                continue
            if "USD" not in (p.get("moneda") or "") or p.get("uso_edificado") != "Vivienda" or sup < 25:
                continue
            m2 = valor / sup
            if 150 <= m2 <= 4000:
                puntos.append((lat, lng, m2))
    return puntos


class IndiceCasas:
    def __init__(self, puntos):
        self.celdas = {}
        for lat, lng, v in puntos:
            self.celdas.setdefault((round(lat, 2), round(lng, 2)), []).append((lat, lng, v))
        self.total = len(puntos)

    def _cerca(self, lat, lng, metros):
        res = []
        paso = 0.01
        alcance = int(metros / 900) + 1
        for i in range(-alcance, alcance + 1):
            for j in range(-alcance, alcance + 1):
                for plat, plng, v in self.celdas.get((round(lat + i * paso, 2), round(lng + j * paso, 2)), []):
                    dx = (plng - lng) * 111320 * math.cos(math.radians(lat))
                    dy = (plat - lat) * 110570
                    if dx * dx + dy * dy <= metros * metros:
                        res.append(v)
        return res

    def valor(self, lat, lng, desde_barrio=False):
        """(mediana U$S/m², cantidad, descripción) o None."""
        for metros in ((800, 1200, 1800) if desde_barrio else (600, 1000, 1500)):
            vals = self._cerca(lat, lng, metros)
            if len(vals) >= 5:
                base = f"OMI · {len(vals)} ofertas a menos de {metros} m" + (" del centro del barrio" if desde_barrio else "")
                return round(statistics.median(vals)), len(vals), base
        return None


def vut_parcela(lat, lng):
    """(U$S/m² de la tierra, nomenclatura) de la parcela en ese punto, o None."""
    datos = _get({
        "service": "WFS", "version": "1.0.0", "request": "GetFeature", "outputFormat": "application/json",
        "typeName": "idecor:vut_2025", "propertyName": "vut_pesos,nomenclatura", "maxFeatures": "1",
        "CQL_FILTER": f"DWITHIN(geom,SRID=4326;POINT({lng} {lat}),25,meters)",
    }, timeout=45)
    for f in datos.get("features", []):
        p = f.get("properties") or {}
        if p.get("vut_pesos"):
            return round(float(p["vut_pesos"]) / TC_VUT), p.get("nomenclatura")
    return None
