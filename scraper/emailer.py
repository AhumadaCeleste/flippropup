"""Arma y envía el resumen diario por Gmail."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

BASE = "#334155"
DEEP = "#1E293B"
TEXTO = "#F1F5F9"
MUTED = "#A9B6C8"
ACENTO = "#00F5A0"
PELIGRO = "#FDA4AF"


def precio_txt(precio, moneda):
    if precio is None:
        return "Consultar"
    simbolo = "U$S" if moneda == "USD" else "$"
    return f"{simbolo} {int(precio):,}".replace(",", ".")


def _tarjeta(p, sitio, extra=""):
    foto = p.get("foto_principal")
    img = (f'<img src="{escape(foto)}" width="180" height="120" alt="" '
           f'style="display:block;width:180px;height:120px;object-fit:cover;border-radius:8px">') if foto else ""
    datos = " · ".join(x for x in [
        p.get("dormitorios"),
        f"{int(p['superficie_total'])} m²" if p.get("superficie_total") else None,
        f"U$S {int(p['precio_m2'])}/m²" if p.get("precio_m2") and p.get("moneda") == "USD" else None,
        p.get("vendedor_tipo"),
    ] if x)
    lugar = ", ".join(x for x in [p.get("barrio"), p.get("ciudad")] if x)
    return f"""
<tr><td style="padding:10px 0;border-bottom:1px solid #475569">
 <table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr>
  <td width="190" valign="top">{img}</td>
  <td valign="top" style="font-family:Arial,sans-serif;color:{TEXTO}">
   <div style="font-size:20px;font-weight:bold">{precio_txt(p.get('precio'), p.get('moneda'))} {extra}</div>
   <div style="font-size:15px;margin:4px 0">{escape(p.get('titulo') or '')}</div>
   <div style="font-size:13px;color:{MUTED}">{escape(lugar)}</div>
   <div style="font-size:13px;color:{MUTED};margin-bottom:8px">{escape(datos)}</div>
   <a href="{escape(p.get('url') or '#')}" style="background:{ACENTO};color:#0F172A;text-decoration:none;font-weight:bold;font-size:13px;padding:7px 12px;border-radius:6px">Ver en el portal</a>
   <a href="{escape(sitio)}/aviso/{p['id']}" style="color:{ACENTO};font-size:13px;margin-left:12px">Ver ficha</a>
  </td></tr></table>
</td></tr>"""


def _bloque(titulo, filas):
    if not filas:
        return ""
    return (f'<tr><td style="padding:22px 0 4px;font-family:Arial,sans-serif;font-size:13px;'
            f'letter-spacing:1px;color:{MUTED};font-weight:bold">{escape(titulo.upper())} · {len(filas)}</td></tr>'
            + "".join(filas))


def armar_html(grupos, sitio, fecha_txt):
    """grupos: dict con listas de (publicacion, texto_extra) por tipo de novedad."""
    def filas(clave, limite=40):
        return [_tarjeta(p, sitio, extra) for p, extra in grupos.get(clave, [])[:limite]]

    cuerpo = (
        _bloque("Llegaron a tu precio objetivo", filas("precio_objetivo"))
        + _bloque("Bajaron de precio", filas("baja_precio"))
        + _bloque("Nuevos", filas("nuevo"))
        + _bloque("Subieron de precio", filas("suba_precio"))
        + _bloque("Dados de baja", filas("dado_de_baja"))
    )
    return f"""<!doctype html><html><body style="margin:0;background:{DEEP}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{DEEP}"><tr><td align="center">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:{BASE}">
<tr><td><img src="{escape(sitio)}/email-header.png" width="640" alt="Flip PropUp · Resumen diario de oportunidades" style="display:block;width:100%;height:auto"></td></tr>
<tr><td style="padding:8px 24px 24px">
 <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
 <tr><td style="font-family:Arial,sans-serif;color:{MUTED};font-size:14px;padding-top:12px">{escape(fecha_txt)}</td></tr>
 {cuerpo}
 </table>
 <p style="font-family:Arial,sans-serif;color:{MUTED};font-size:12px;margin-top:24px">
  Lo enviamos todos los días a las 8:00. Para cambiar qué buscamos, entrá a <a href="{escape(sitio)}/busquedas" style="color:{ACENTO}">Búsquedas guardadas</a>.</p>
</td></tr></table></td></tr></table></body></html>"""


def enviar(destinatarios, asunto, html):
    usuario = os.environ["GMAIL_USUARIO"]
    clave = os.environ["GMAIL_CLAVE_APP"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = f"Flip PropUp <{usuario}>"
    msg["To"] = ", ".join(destinatarios)
    msg.attach(MIMEText("Abrí este email en formato HTML para ver las novedades.", "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(usuario, clave)
        s.sendmail(usuario, destinatarios, msg.as_string())
