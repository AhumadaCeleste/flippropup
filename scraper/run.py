"""Robot diario de Flip PropUp.

1. Entra a Clasificados La Voz y ejecuta cada búsqueda guardada y activa.
2. Guarda o actualiza cada aviso, con su historial de precios.
3. Revisa los avisos seguidos que no aparecieron (¿siguen publicados? ¿cambió el precio?).
4. Envía el resumen por email con las novedades.

Variables de entorno (se cargan como Secrets en GitHub):
  SUPABASE_URL, SUPABASE_SERVICE_KEY, GMAIL_USUARIO, GMAIL_CLAVE_APP, SITIO_URL
Opcionales: BUSQUEDA_ID (correr solo una), SIN_EMAIL=1, MAX_PAGINAS (por defecto 10)
"""
import os
import sys
import time
import traceback
import unicodedata
from datetime import datetime, timedelta, timezone

from playwright.sync_api import sync_playwright
from supabase import create_client

import emailer
from lavoz import LaVoz, construir_consultas, normalizar

ART = timezone(timedelta(hours=-3))
MAX_PAGINAS = int(os.environ.get("MAX_PAGINAS", "10"))
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


class Robot:
    def __init__(self):
        self.sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        self.vistos = set()
        self.resumen = {"busquedas": 0, "avisos": 0, "nuevos": 0, "cambios": 0}

    # ---------- base de datos ----------
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
        actual = (self.sb.table("publicaciones").select("id,precio,moneda,estado")
                  .eq("portal", p["portal"]).eq("portal_id", p["portal_id"]).execute().data)
        if not actual:
            fila = dict(p, primera_vez=ahora(), ultima_vez=ahora())
            pub_id = self.sb.table("publicaciones").insert(fila).execute().data[0]["id"]
            self.sb.table("historial_precios").insert({"publicacion_id": pub_id, "precio": p["precio"], "moneda": p["moneda"]}).execute()
            return pub_id, True
        actual = actual[0]
        cambios = {k: p[k] for k in CAMPOS_ACTUALIZABLES}
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

    def procesar_busqueda(self, lv, b):
        f = b["filtros"] or {}
        if "lavoz" not in (f.get("portales") or ["lavoz"]):
            return
        primera_vez = b["ultima_ejecucion"] is None
        for tipo, consulta in construir_consultas(f):
            crudos = lv.buscar(consulta, MAX_PAGINAS)
            print(f"  [{b['nombre']}] {tipo}: {len(crudos)} avisos · {consulta}")
            for a in crudos:
                p = normalizar(a, tipo)
                if not pasa_filtros_locales(p, f):
                    continue
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
        self.sb.table("busquedas").update({"ultima_ejecucion": ahora()}).eq("id", b["id"]).execute()
        self.resumen["busquedas"] += 1

    def revisar_seguidos(self, lv):
        seguidos = (self.sb.table("seguimientos")
                    .select("publicacion_id, publicaciones(id,url,precio,moneda,estado,portal)")
                    .execute().data)
        for s in seguidos:
            p = s["publicaciones"]
            if not p or p["id"] in self.vistos or p["estado"] != "activo" or p["portal"] != "lavoz":
                continue
            estado = lv.estado_aviso(p["url"])
            if not estado["activo"]:
                self.sb.table("publicaciones").update({"estado": "dado_de_baja"}).eq("id", p["id"]).execute()
                self.alerta(p["id"], "dado_de_baja", p["precio"], None)
            else:
                if self.cambio_precio(p, estado.get("precio"), estado.get("moneda")):
                    self.sb.table("publicaciones").update({"precio": estado["precio"]}).eq("id", p["id"]).execute()
                self.sb.table("publicaciones").update({"ultima_vez": ahora()}).eq("id", p["id"]).execute()
            time.sleep(1)

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

    def correr(self):
        ej = self.sb.table("ejecuciones").insert({"estado": "corriendo"}).execute().data[0]["id"]
        try:
            q = self.sb.table("busquedas").select("*").eq("activa", True)
            if os.environ.get("BUSQUEDA_ID"):
                q = q.eq("id", os.environ["BUSQUEDA_ID"])
            busquedas = q.execute().data
            with sync_playwright() as pw:
                navegador = pw.chromium.launch(headless=True)
                pagina = navegador.new_context(locale="es-AR", viewport={"width": 1366, "height": 900}).new_page()
                lv = LaVoz(pagina)
                lv.abrir()
                self.actualizar_ubicaciones(lv)
                for b in busquedas:
                    self.procesar_busqueda(lv, b)
                self.revisar_seguidos(lv)
                navegador.close()
            if os.environ.get("SIN_EMAIL") != "1":
                self.enviar_resumen()
            detalle = ", ".join(f"{k}: {v}" for k, v in self.resumen.items())
            self.sb.table("ejecuciones").update({"fin": ahora(), "estado": "ok", "detalle": detalle}).eq("id", ej).execute()
            print("Listo ·", detalle)
        except Exception:
            self.sb.table("ejecuciones").update({"fin": ahora(), "estado": "error",
                                                 "detalle": traceback.format_exc()[-3000:]}).eq("id", ej).execute()
            raise


if __name__ == "__main__":
    try:
        Robot().correr()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
