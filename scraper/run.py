"""Robot diario de Flip PropUp.

1. Entra a Clasificados La Voz y a Mercado Libre y ejecuta cada búsqueda guardada y activa.
   Si un portal falla, se sigue con el otro y el error queda en el resumen.
2. Guarda o actualiza cada aviso, con su historial de precios.
3. Revisa los avisos seguidos que no aparecieron (¿siguen publicados? ¿cambió el precio?).
4. Envía el resumen por email con las novedades.

Variables de entorno (se cargan como Secrets en GitHub):
  SUPABASE_URL, SUPABASE_SERVICE_KEY, GMAIL_USUARIO, GMAIL_CLAVE_APP, SITIO_URL
Opcionales: BUSQUEDA_ID (correr solo una), SIN_EMAIL=1, MAX_PAGINAS (por defecto 10),
  PRUEBA_EMAIL=1 (solo manda un email de prueba, sin buscar), BREVO_API_KEY y BREVO_REMITENTE
"""
import math
import os
import sys
import time
import traceback
import unicodedata
from datetime import datetime, timedelta, timezone

from playwright.sync_api import sync_playwright
from supabase import create_client

import emailer
import telefonos
import cordobaprop as cp
import inmobiliarias as inmo
import inmoup
import mercadolibre as ml
from lavoz import LaVoz, construir_consultas, normalizar

ART = timezone(timedelta(hours=-3))
MAX_PAGINAS = int(os.environ.get("MAX_PAGINAS", "10"))
ENRIQUECER_MAX = int(os.environ.get("ENRIQUECER_MAX", "120"))  # fichas a leer por corrida (ubicación y teléfono)
PORTALES_CON_FICHA = ["cordobaprop", "inmobiliarias", "mercadolibre", "inmoup"]

# Lee de la ficha de un aviso las coordenadas y el teléfono (si el portal los muestra sin pedir clic).
LEER_FICHA = r"""() => {
  const html = document.documentElement.outerHTML;
  let m = html.match(/"latitude"\s*:\s*"?(-?\d+\.\d+)"?\s*,\s*"longitude"\s*:\s*"?(-?\d+\.\d+)/)
       || html.match(/[?&;]ll=(-?\d+\.\d+),(-?\d+\.\d+)/)
       || html.match(/"lat"\s*:\s*"?(-?\d+\.\d+)"?\s*,\s*"(?:lng|lon)"\s*:\s*"?(-?\d+\.\d+)/);
  const wa = html.match(/(?:wa\.me\/|api\.whatsapp\.com\/send\?phone=)\+?(\d{8,15})/);
  const tel = document.querySelector('a[href^="tel:"]');
  return {lat: m ? Number(m[1]) : null, lng: m ? Number(m[2]) : null,
          telefono: wa ? wa[1] : (tel ? tel.getAttribute('href').slice(4) : null)};
}"""
CAMPOS_ACTUALIZABLES = ["url", "titulo", "descripcion", "provincia", "ciudad", "barrio", "lat", "lng",
                        "superficie_total", "dormitorios", "banos", "vendedor_tipo", "vendedor_nombre",
                        "apto_escritura", "apto_credito", "fotos", "foto_principal", "fecha_publicacion"]


def ahora():
    return datetime.now(timezone.utc).isoformat()


def sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def pasa_filtros_locales(p, f):
    """Controles extra por si la API del portal ignora algún filtro."""
    moneda_f = "USD" if (f.get("moneda") or "dolares") == "dolares" else "ARS"
    if p["precio"] is not None and p["moneda"] == moneda_f:
        if f.get("precio_desde") and p["precio"] < float(f["precio_desde"]):
            return False
        if f.get("precio_hasta") and p["precio"] > float(f["precio_hasta"]):
            return False
    if p["superficie_total"]:
        if f.get("superficie_desde") and p["superficie_total"] < float(f["superficie_desde"]):
            return False
        if f.get("superficie_hasta") and p["superficie_total"] > float(f["superficie_hasta"]):
            return False
    if f.get("vendedor") == "particular" and p["vendedor_tipo"] and p["vendedor_tipo"] != "Particular":
        return False
    palabras = [sin_acentos(x) for x in (f.get("palabras") or []) if x.strip()]
    if palabras:
        texto = sin_acentos((p["titulo"] or "") + " " + (p["descripcion"] or ""))
        if not any(w in texto for w in palabras):
            return False
    return True


PORTALES_POR_DEFECTO = ["lavoz", "mercadolibre", "inmoup", "cordobaprop", "inmobiliarias"]


# Las búsquedas guardadas antes de sumar Mercado Libre tienen ["lavoz"] porque era
# la única opción: a esas se les aplican todos los portales.
ANTES_DE_MERCADOLIBRE = "2026-11-09"


def portales_de(f, b=None):
    elegidos = f.get("portales") or PORTALES_POR_DEFECTO
    if b and elegidos == ["lavoz"] and (b.get("creada") or "") < ANTES_DE_MERCADOLIBRE:
        return PORTALES_POR_DEFECTO
    # Quien tenía marcados todos los portales disponibles recibe también los que se suman después.
    if {"lavoz", "mercadolibre"} <= set(elegidos):
        return PORTALES_POR_DEFECTO
    return elegidos


class Robot:
    def __init__(self):
        self.sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        self.vistos = set()
        self.resumen = {"busquedas": 0, "avisos": 0, "nuevos": 0, "cambios": 0}
        self.errores = []
        self.tiene_contacto = self._columnas_contacto()
        self._nombres = None

    # ---------- base de datos ----------
    def _columnas_contacto(self):
        """Las columnas telefono y enriquecido_en se agregan con database/migraciones/2026-11-08-contacto-y-mapa.sql."""
        try:
            self.sb.table("publicaciones").select("telefono,enriquecido_en").limit(1).execute()
            return True
        except Exception:
            print("Aviso: falta correr la migración 2026-11-08-contacto-y-mapa.sql (teléfonos). Sigo sin guardarlos.")
            return False

    def alerta(self, pub_id, tipo, antes=None, despues=None, busqueda_id=None):
        self.sb.table("alertas").insert({
            "publicacion_id": pub_id, "tipo": tipo, "valor_anterior": antes,
            "valor_nuevo": despues, "busqueda_id": busqueda_id,
        }).execute()

    def revisar_objetivo(self, pub_id, precio):
        seg = self.sb.table("seguimientos").select("precio_objetivo").eq("publicacion_id", pub_id).execute().data
        if not seg or not seg[0]["precio_objetivo"] or precio is None:
            return
        if precio <= float(seg[0]["precio_objetivo"]):
            ya = self.sb.table("alertas").select("id").eq("publicacion_id", pub_id).eq("tipo", "precio_objetivo").execute().data
            if not ya:
                self.alerta(pub_id, "precio_objetivo", float(seg[0]["precio_objetivo"]), precio)

    def cambio_precio(self, actual, precio, moneda):
        pub_id = actual["id"]
        antes = float(actual["precio"]) if actual["precio"] is not None else None
        if precio is None or antes is None or moneda != actual["moneda"] or abs(precio - antes) < 1:
            return False
        self.sb.table("historial_precios").insert({"publicacion_id": pub_id, "precio": precio, "moneda": moneda}).execute()
        self.alerta(pub_id, "baja_precio" if precio < antes else "suba_precio", antes, precio)
        self.revisar_objetivo(pub_id, precio)
        self.resumen["cambios"] += 1
        return True

    def guardar(self, p):
        p = dict(p)
        if not self.tiene_contacto or not p.get("telefono"):
            p.pop("telefono", None)
        actual = (self.sb.table("publicaciones").select("id,precio,moneda,estado")
                  .eq("portal", p["portal"]).eq("portal_id", p["portal_id"]).execute().data)
        if not actual:
            fila = dict(p, primera_vez=ahora(), ultima_vez=ahora())
            pub_id = self.sb.table("publicaciones").insert(fila).execute().data[0]["id"]
            self.sb.table("historial_precios").insert({"publicacion_id": pub_id, "precio": p["precio"], "moneda": p["moneda"]}).execute()
            return pub_id, True
        actual = actual[0]
        cambios = {k: p[k] for k in CAMPOS_ACTUALIZABLES}
        if p.get("telefono"):
            cambios["telefono"] = p["telefono"]
        for k in ("lat", "lng"):
            if cambios.get(k) is None:
                cambios.pop(k, None)
        cambios.update(ultima_vez=ahora(), estado="activo")
        if self.cambio_precio(actual, p["precio"], p["moneda"]) or actual["precio"] is None:
            cambios.update(precio=p["precio"], moneda=p["moneda"])
        self.sb.table("publicaciones").update(cambios).eq("id", actual["id"]).execute()
        return actual["id"], False

    # ---------- pasos ----------
    def actualizar_ubicaciones(self, lv):
        hay = self.sb.table("ubicaciones").select("tid", count="exact").limit(1).execute().count or 0
        if hay and datetime.now(ART).weekday() != 0:  # se refresca los lunes
            return
        filas = lv.ubicaciones()
        for i in range(0, len(filas), 500):
            self.sb.table("ubicaciones").upsert(filas[i:i + 500], on_conflict="portal,tid").execute()
        print(f"Ubicaciones actualizadas: {len(filas)}")

    def nombres_ubicaciones(self):
        if self._nombres is None:
            filas = (self.sb.table("ubicaciones").select("tid,nombre").eq("portal", "lavoz")
                     .range(0, 9999).execute().data)
            self._nombres = {u["tid"]: u["nombre"] for u in filas}
        return self._nombres

    def registrar(self, b, p, tipo, primera_vez):
        p = {k: v for k, v in p.items() if not k.startswith("_")}
        pub_id, es_nuevo = self.guardar(p)
        self.vistos.add(pub_id)
        self.resumen["avisos"] += 1
        self.sb.table("busqueda_resultados").upsert(
            {"busqueda_id": b["id"], "publicacion_id": pub_id},
            on_conflict="busqueda_id,publicacion_id", ignore_duplicates=True).execute()
        if es_nuevo:
            self.resumen["nuevos"] += 1
            if not primera_vez:  # la primera vez no avisamos todo como "nuevo"
                self.alerta(pub_id, "nuevo", None, p["precio"], b["id"])

    def buscar_lavoz(self, lv, b, primera_vez):
        f = b["filtros"] or {}
        for tipo, consulta in construir_consultas(f):
            crudos = lv.buscar(consulta, MAX_PAGINAS)
            print(f"  [{b['nombre']}] La Voz · {tipo}: {len(crudos)} avisos · {consulta}")
            for a in crudos:
                p = normalizar(a, tipo)
                if pasa_filtros_locales(p, f):
                    self.registrar(b, p, tipo, primera_vez)

    def buscar_mercadolibre(self, mlp, b, primera_vez):
        f = b["filtros"] or {}
        nombres = self.nombres_ubicaciones()
        for tipo, dorm, url in ml.construir_consultas(f, nombres):
            crudos = mlp.buscar(url, MAX_PAGINAS)
            validos = 0
            for t in crudos:
                p = ml.normalizar(t, tipo, dorm, f)
                if p["portal_id"] and ml.coincide_ubicacion(p, f, nombres) and pasa_filtros_locales(p, f):
                    self.registrar(b, p, tipo, primera_vez)
                    validos += 1
            print(f"  [{b['nombre']}] Mercado Libre · {tipo}: {len(crudos)} avisos, {validos} pasan los filtros · {url}")

    def buscar_inmoup(self, iu, b, primera_vez):
        f = b["filtros"] or {}
        nombres = self.nombres_ubicaciones()
        ciudad = nombres.get(f.get("ciudad_tid")) or "Córdoba"
        crudos = iu.todos(ciudad, MAX_PAGINAS * 2)
        validos = 0
        for a in crudos:
            p = inmoup.normalizar(a, ciudad)
            if inmoup.coincide(p, f, nombres, ml.TEXTO_DORMITORIOS) and pasa_filtros_locales(p, f):
                self.registrar(b, p, p["tipo"], primera_vez)
                validos += 1
        print(f"  [{b['nombre']}] InmoUP · {validos} de {len(crudos)} avisos pasan los filtros")

    def buscar_cordobaprop(self, cpp, b, primera_vez):
        f = b["filtros"] or {}
        nombres = self.nombres_ubicaciones()
        for tipo, dorm, url in cpp.construir_consultas(f, nombres):
            crudos = cpp.buscar(url, MAX_PAGINAS * 2)
            validos = 0
            for t in crudos:
                p = cp.normalizar(t, tipo, dorm, ml.TEXTO_DORMITORIOS)
                if p["portal_id"] and cp.coincide_ubicacion(p, f, nombres) and pasa_filtros_locales(p, f):
                    self.registrar(b, p, tipo, primera_vez)
                    validos += 1
            print(f"  [{b['nombre']}] CórdobaProp · {tipo}: {len(crudos)} avisos, {validos} pasan los filtros · {url}")

    def buscar_inmobiliarias(self, im, b, primera_vez):
        f = b["filtros"] or {}
        nombres = self.nombres_ubicaciones()
        crudos = im.todos(MAX_PAGINAS)
        validos = 0
        for x in crudos:
            p = inmo.normalizar(x)
            if inmo.coincide(p, f, nombres, ml.TEXTO_DORMITORIOS) and pasa_filtros_locales(p, f):
                self.registrar(b, p, p["tipo"], primera_vez)
                validos += 1
        print(f"  [{b['nombre']}] Inmobiliarias (webs Tokko) · {validos} de {len(crudos)} avisos pasan los filtros")

    def procesar_busqueda(self, portales, b):
        f = b["filtros"] or {}
        primera_vez = b["ultima_ejecucion"] is None
        for nombre, buscador in (("lavoz", self.buscar_lavoz), ("mercadolibre", self.buscar_mercadolibre),
                                 ("inmoup", self.buscar_inmoup), ("cordobaprop", self.buscar_cordobaprop),
                                 ("inmobiliarias", self.buscar_inmobiliarias)):
            if nombre not in portales_de(f, b) or portales.get(nombre) is None:
                continue
            try:
                buscador(portales[nombre], b, primera_vez)
            except Exception as e:
                self.errores.append(f"{nombre} · {b['nombre']}: {e}")
                print(f"  ERROR en {nombre} ({b['nombre']}): {e}")
                traceback.print_exc()
        self.sb.table("busquedas").update({"ultima_ejecucion": ahora()}).eq("id", b["id"]).execute()
        self.resumen["busquedas"] += 1

    def revisar_seguidos(self, portales):
        seguidos = (self.sb.table("seguimientos")
                    .select("publicacion_id, publicaciones(id,url,precio,moneda,estado,portal)")
                    .execute().data)
        for s in seguidos:
            p = s["publicaciones"]
            if not p or p["id"] in self.vistos or p["estado"] != "activo" or portales.get(p["portal"]) is None:
                continue
            try:
                estado = portales[p["portal"]].estado_aviso(p["url"])
            except Exception as e:
                print(f"  No pude revisar {p['url']}: {e}")
                continue
            if not estado["activo"]:
                self.sb.table("publicaciones").update({"estado": "dado_de_baja"}).eq("id", p["id"]).execute()
                self.alerta(p["id"], "dado_de_baja", p["precio"], None)
            else:
                if self.cambio_precio(p, estado.get("precio"), estado.get("moneda")):
                    self.sb.table("publicaciones").update({"precio": estado["precio"]}).eq("id", p["id"]).execute()
                self.sb.table("publicaciones").update({"ultima_vez": ahora()}).eq("id", p["id"]).execute()
            time.sleep(1)

    def enriquecer(self, portales):
        """Entra a la ficha de los avisos nuevos para sacar ubicación (para el mapa) y teléfono."""
        activos = [x for x in PORTALES_CON_FICHA if portales.get(x)]
        if not activos or ENRIQUECER_MAX <= 0:
            return
        q = (self.sb.table("publicaciones").select("id,url,portal,lat,telefono" if self.tiene_contacto else "id,url,portal,lat")
             .eq("estado", "activo").in_("portal", activos).order("primera_vez", desc=True).limit(ENRIQUECER_MAX))
        q = q.is_("enriquecido_en", "null") if self.tiene_contacto else q.is_("lat", "null")
        pendientes = q.execute().data
        con_lugar = con_tel = 0
        for p in pendientes:
            pagina = portales[p["portal"]].page
            try:
                resp = pagina.goto(p["url"], wait_until="domcontentloaded", timeout=45000)
                pagina.wait_for_timeout(1200)
                datos = pagina.evaluate(LEER_FICHA) if resp is not None and resp.status < 400 else {}
            except Exception as e:
                print(f"  No pude leer la ficha {p['url']}: {e}")
                datos = {}
            cambios = {}
            lat, lng = datos.get("lat"), datos.get("lng")
            if lat and lng and -56 < lat < -21 and -74 < lng < -53 and p.get("lat") is None:
                cambios.update(lat=lat, lng=lng)
                con_lugar += 1
            if self.tiene_contacto:
                tel = telefonos.normalizar(datos.get("telefono") or "")
                if tel and not p.get("telefono"):
                    cambios["telefono"] = tel
                    con_tel += 1
                cambios["enriquecido_en"] = ahora()
            if cambios:
                self.sb.table("publicaciones").update(cambios).eq("id", p["id"]).execute()
            time.sleep(0.8)
        print(f"Fichas leídas: {len(pendientes)} · con ubicación: {con_lugar} · con teléfono: {con_tel}")

    def alertar_relevamientos(self):
        """Avisos nuevos a menos de 200 m de un lugar relevado, o con el teléfono del cartel."""
        try:
            relevados = self.sb.table("relevamientos").select("*").eq("activo", True).execute().data
        except Exception:
            return  # todavía no se corrió la migración
        nuevas = 0
        for r in relevados:
            candidatos = []
            if r.get("lat") and r.get("lng"):
                lat, lng = float(r["lat"]), float(r["lng"])
                d_lat, d_lng = 200 / 111000, 200 / (111000 * math.cos(math.radians(lat)))
                candidatos += (self.sb.table("publicaciones").select("id,precio").eq("estado", "activo")
                               .gte("lat", lat - d_lat).lte("lat", lat + d_lat).gte("lng", lng - d_lng).lte("lng", lng + d_lng)
                               .gte("primera_vez", r["creado"]).execute().data)
            if r.get("telefono") and self.tiene_contacto:
                candidatos += self.sb.table("publicaciones").select("id,precio").eq("telefono", r["telefono"]).execute().data
            vistos = set()
            for c in candidatos:
                if c["id"] in vistos:
                    continue
                vistos.add(c["id"])
                ya = (self.sb.table("alertas").select("id").eq("relevamiento_id", r["id"])
                      .eq("publicacion_id", c["id"]).limit(1).execute().data)
                if not ya:
                    self.sb.table("alertas").insert({"publicacion_id": c["id"], "tipo": "cerca_relevamiento",
                                                     "valor_nuevo": c["precio"], "relevamiento_id": r["id"]}).execute()
                    nuevas += 1
        if relevados:
            print(f"Relevamientos activos: {len(relevados)} · avisos nuevos relacionados: {nuevas}")

    def enviar_resumen(self):
        pendientes = (self.sb.table("alertas").select("*, publicaciones(*)")
                      .eq("enviada", False).order("fecha").execute().data)
        if not pendientes:
            print("Sin novedades: no se envía email.")
            return
        grupos = {}
        for a in pendientes:
            p = a["publicaciones"]
            if not p:
                continue
            extra = ""
            if a["tipo"] in ("baja_precio", "suba_precio") and a["valor_anterior"]:
                pct = (a["valor_nuevo"] - a["valor_anterior"]) / a["valor_anterior"] * 100
                flecha = "▼" if pct < 0 else "▲"
                extra = (f'<span style="font-size:14px;color:{emailer.ACENTO if pct < 0 else emailer.PELIGRO}">'
                         f'{flecha} {abs(pct):.1f}'.replace(".", ",") + f' % (antes {emailer.precio_txt(a["valor_anterior"], p["moneda"])})</span>')
            grupos.setdefault(a["tipo"], []).append((p, extra))
        destinatarios = [u["email"] for u in self.sb.table("usuarios_habilitados").select("email").execute().data]
        hoy = datetime.now(ART)
        total = len(pendientes)
        asunto = f"Flip PropUp · {total} novedad{'es' if total != 1 else ''} · {hoy:%d/%m}"
        html = emailer.armar_html(grupos, os.environ.get("SITIO_URL", "").rstrip("/"), f"Novedades del {hoy:%d/%m/%Y}")
        emailer.enviar(destinatarios, asunto, html)
        ids = [a["id"] for a in pendientes]
        for i in range(0, len(ids), 200):
            self.sb.table("alertas").update({"enviada": True}).in_("id", ids[i:i + 200]).execute()
        print(f"Email enviado a {', '.join(destinatarios)} con {total} novedades.")

    def prueba_email(self):
        destinatarios = [u["email"] for u in self.sb.table("usuarios_habilitados").select("email").execute().data]
        hoy = datetime.now(ART)
        html = emailer.armar_html({}, os.environ.get("SITIO_URL", "").rstrip("/"),
                                  f"Email de prueba · {hoy:%d/%m/%Y %H:%M}. Si lo ves, el envío funciona.")
        emailer.enviar(destinatarios, f"Flip PropUp · prueba de email · {hoy:%d/%m %H:%M}", html)
        print(f"Prueba enviada a {', '.join(destinatarios)}.")

    def correr(self):
        ej = self.sb.table("ejecuciones").insert({"estado": "corriendo"}).execute().data[0]["id"]
        try:
            q = self.sb.table("busquedas").select("*").eq("activa", True)
            if os.environ.get("BUSQUEDA_ID"):
                q = q.eq("id", os.environ["BUSQUEDA_ID"])
            busquedas = q.execute().data
            with sync_playwright() as pw:
                navegador = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
                contexto = navegador.new_context(locale="es-AR", viewport={"width": 1366, "height": 900})
                portales = {}
                try:
                    lv = LaVoz(contexto.new_page())
                    lv.abrir()
                    self.actualizar_ubicaciones(lv)
                    portales["lavoz"] = lv
                except Exception as e:
                    self.errores.append(f"lavoz · al abrir: {e}")
                    traceback.print_exc()
                if any("mercadolibre" in portales_de(b["filtros"] or {}, b) for b in busquedas):
                    try:
                        mlp = ml.MercadoLibre(ml.nuevo_contexto(navegador).new_page())
                        mlp.abrir()
                        portales["mercadolibre"] = mlp
                    except Exception as e:
                        self.errores.append(f"mercadolibre · al abrir: {e}")
                        traceback.print_exc()
                if any("inmoup" in portales_de(b["filtros"] or {}, b) for b in busquedas):
                    try:
                        iu = inmoup.InmoUP(ml.nuevo_contexto(navegador).new_page())
                        iu.abrir()
                        portales["inmoup"] = iu
                    except Exception as e:
                        self.errores.append(f"inmoup · al abrir: {e}")
                        traceback.print_exc()
                if any("cordobaprop" in portales_de(b["filtros"] or {}, b) for b in busquedas):
                    try:
                        cpp = cp.CordobaProp(ml.nuevo_contexto(navegador).new_page())
                        cpp.abrir()
                        portales["cordobaprop"] = cpp
                    except Exception as e:
                        self.errores.append(f"cordobaprop · al abrir: {e}")
                        traceback.print_exc()
                if any("inmobiliarias" in portales_de(b["filtros"] or {}, b) for b in busquedas):
                    portales["inmobiliarias"] = inmo.Inmobiliarias(ml.nuevo_contexto(navegador).new_page())
                for b in busquedas:
                    self.procesar_busqueda(portales, b)
                self.revisar_seguidos(portales)
                try:
                    self.enriquecer(portales)
                except Exception as e:
                    self.errores.append(f"fichas: {e}")
                    traceback.print_exc()
                navegador.close()
            try:
                self.alertar_relevamientos()
            except Exception as e:
                self.errores.append(f"relevamientos: {e}")
                traceback.print_exc()
            if os.environ.get("SIN_EMAIL") != "1":
                self.enviar_resumen()
            detalle = ", ".join(f"{k}: {v}" for k, v in self.resumen.items())
            if self.errores:
                detalle += " · errores: " + " | ".join(self.errores)
            estado = "ok" if not self.errores else "error"
            self.sb.table("ejecuciones").update({"fin": ahora(), "estado": estado, "detalle": detalle[:3000]}).eq("id", ej).execute()
            print("Listo ·", detalle)
            if self.errores and not self.resumen["avisos"]:
                raise RuntimeError("Ningún portal devolvió avisos: " + " | ".join(self.errores))
        except Exception:
            self.sb.table("ejecuciones").update({"fin": ahora(), "estado": "error",
                                                 "detalle": traceback.format_exc()[-3000:]}).eq("id", ej).execute()
            raise


if __name__ == "__main__":
    try:
        if os.environ.get("PRUEBA_EMAIL") == "1":
            Robot().prueba_email()
        else:
            Robot().correr()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
