"""Arma y envía el resumen diario por Gmail."""
import json
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

BASE = "#334155"
DEEP = "#1E293B"
TEXTO = "#F1F5F9"
MUTED = "#A9B6C8"
ACENTO = "#00F5A0"
PELIGRO = "#FDA4AF"
TEXTO_PLANO = "Abrí este email en formato HTML para ver las novedades."


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
    repetido = ""
    if (p.get("grupo_n") or 0) > 1:
        dif = float(p.get("grupo_max") or 0) - float(p.get("grupo_min") or 0)
        repetido = (f'<div style="font-size:13px;color:{ACENTO};margin-bottom:6px">Publicada {p["grupo_n"]} veces'
                    + (f' · hasta {precio_txt(dif, p.get("moneda"))} de diferencia entre avisos' if dif > 0 else "")
                    + ' · mirá todas en la ficha</div>')
    return f"""
<tr><td style="padding:10px 0;border-bottom:1px solid #475569">
 <table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr>
  <td width="190" valign="top">{img}</td>
  <td valign="top" style="font-family:Arial,sans-serif;color:{TEXTO}">
   <div style="font-size:20px;font-weight:bold">{precio_txt(p.get('precio'), p.get('moneda'))} {extra}</div>
   <div style="font-size:15px;margin:4px 0">{escape(p.get('titulo') or '')}</div>
   <div style="font-size:13px;color:{MUTED}">{escape(lugar)}</div>
   <div style="font-size:13px;color:{MUTED};margin-bottom:8px">{escape(datos)}</div>
   {repetido}
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
        _bloque("Oportunidades (puntaje alto o debajo de tu umbral)", filas("oportunidad"))
        + _bloque("Cerca de lugares que relevaste", filas("cerca_relevamiento"))
        + _bloque("Llegaron a tu precio objetivo", filas("precio_objetivo"))
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
  Lo enviamos todos los días a la mañana. Para cambiar qué buscamos, entrá a <a href="{escape(sitio)}/busquedas" style="color:{ACENTO}">Búsquedas guardadas</a>.</p>
</td></tr></table></td></tr></table></body></html>"""


def _armar_mensaje(usuario, destinatarios, asunto, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = f"Flip PropUp <{usuario}>"
    msg["To"] = ", ".join(destinatarios)
    msg.attach(MIMEText(TEXTO_PLANO, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def _enviar_gmail(destinatarios, asunto, html):
    """Prueba el puerto 465 (SSL) y, si Gmail corta la conexión, el 587 (STARTTLS)."""
    usuario = os.environ["GMAIL_USUARIO"].strip()
    # Google muestra la contraseña de aplicación en grupos con espacios: se quitan.
    clave = "".join(os.environ["GMAIL_CLAVE_APP"].split())
    if len(clave) != 16 or not clave.isascii():
        print(f"Aviso: GMAIL_CLAVE_APP tiene {len(clave)} caracteres; una contraseña de aplicación tiene 16 letras.")
    msg = _armar_mensaje(usuario, destinatarios, asunto, html).as_string()
    errores = []
    for puerto in (465, 587):
        try:
            if puerto == 465:
                s = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60)
            else:
                s = smtplib.SMTP("smtp.gmail.com", 587, timeout=60)
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
            with s:
                s.login(usuario, clave)
                s.sendmail(usuario, destinatarios, msg)
            print(f"Email enviado por Gmail (puerto {puerto}).")
            return
        except (smtplib.SMTPException, OSError) as e:
            errores.append(f"puerto {puerto}: {type(e).__name__}: {e}")
    raise RuntimeError(
        f"Gmail rechazó el inicio de sesión de {usuario} ({'; '.join(errores)}). "
        "Revisá GMAIL_USUARIO y GMAIL_CLAVE_APP (contraseña de aplicación de 16 letras de esa misma "
        "cuenta, con verificación en 2 pasos), o cargá BREVO_API_KEY para enviar por Brevo."
    )


def _enviar_brevo(destinatarios, asunto, html):
    """Envío por la API HTTP de Brevo (no usa SMTP, así que no la afecta el bloqueo de Gmail)."""
    remitente = (os.environ.get("BREVO_REMITENTE") or os.environ.get("GMAIL_USUARIO", "")).strip()
    cuerpo = json.dumps({
        "sender": {"name": "Flip PropUp", "email": remitente},
        "to": [{"email": d} for d in destinatarios],
        "subject": asunto,
        "htmlContent": html,
        "textContent": TEXTO_PLANO,
    }).encode("utf-8")
    pedido = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email", data=cuerpo, method="POST",
        headers={"api-key": os.environ["BREVO_API_KEY"].strip(), "content-type": "application/json",
                 "accept": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=60) as r:
            print(f"Email enviado por Brevo ({r.status}).")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Brevo rechazó el envío ({e.code}): {e.read().decode('utf-8', 'replace')[:500]}") from e


def _enviar_apps_script(destinatarios, asunto, html):
    """Envío por el "cartero" de Google Apps Script (scraper/cartero-apps-script.gs).
    EMAIL_WEBHOOK es la URL de la app web con ?clave=... al final. Usa la cuota de Gmail
    de la cuenta que publicó el script y no necesita SMTP ni contraseñas de aplicación."""
    url = os.environ["EMAIL_WEBHOOK"].strip()
    cuerpo = json.dumps({"para": destinatarios, "asunto": asunto, "html": html,
                         "texto": TEXTO_PLANO}).encode("utf-8")
    pedido = urllib.request.Request(url, data=cuerpo, method="POST",
                                    headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=90) as r:  # Google redirige; urllib sigue la redirección
            respuesta = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"El cartero de Apps Script respondió {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from e
    try:
        datos = json.loads(respuesta)
    except ValueError:
        raise RuntimeError(f"El cartero de Apps Script no respondió JSON (¿está publicado para 'Cualquier persona'?): {respuesta[:300]}")
    if not datos.get("ok"):
        raise RuntimeError(f"El cartero de Apps Script rechazó el envío: {datos.get('error')}")
    print(f"Email enviado por Apps Script (cuota restante hoy: {datos.get('cuota', '?')}).")


def configurado():
    return any(os.environ.get(k, "").strip() for k in ("EMAIL_WEBHOOK", "BREVO_API_KEY", "GMAIL_CLAVE_APP"))


def enviar(destinatarios, asunto, html):
    """Orden: cartero de Apps Script, Brevo, Gmail. Si uno falla, prueba el siguiente que esté configurado."""
    if os.environ.get("EMAIL_WEBHOOK", "").strip():
        try:
            return _enviar_apps_script(destinatarios, asunto, html)
        except Exception as e:
            if not (os.environ.get("BREVO_API_KEY", "").strip() or os.environ.get("GMAIL_CLAVE_APP", "").strip()):
                raise
            print(f"Apps Script falló ({e}); pruebo con el siguiente método.")
    if os.environ.get("BREVO_API_KEY", "").strip():
        try:
            return _enviar_brevo(destinatarios, asunto, html)
        except Exception as e:
            if not os.environ.get("GMAIL_CLAVE_APP", "").strip():
                raise
            print(f"Brevo falló ({e}); pruebo con Gmail.")
    return _enviar_gmail(destinatarios, asunto, html)
