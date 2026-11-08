"""Teléfonos argentinos: los busca en un texto y los deja listos para WhatsApp (549 + área + número)."""
import re

CANDIDATO = re.compile(r"(?:\+?54[\s.-]?)?(?:9[\s.-]?)?\(?0?\d{2,4}\)?[\s.-]?(?:15[\s.-]?)?\d{3,4}[\s.-]?\d{3,6}")


def normalizar(numero):
    """Devuelve '549' + 10 dígitos, o None si no parece un número argentino."""
    d = re.sub(r"\D", "", numero or "")
    if d.startswith("549"):
        d = d[3:]
    elif d.startswith("54"):
        d = d[2:]
    d = d.lstrip("0")
    if len(d) == 12:  # área + 15 + número (ej. 351 15 1234567)
        for largo in (2, 3, 4):
            if d[largo:largo + 2] == "15" and len(d) - 2 == 10:
                d = d[:largo] + d[largo + 2:]
                break
    if len(d) != 10 or d[0] not in "123":
        return None
    return "549" + d


def buscar(texto):
    """Primer teléfono válido que aparezca en el texto (descripciones de avisos)."""
    for m in CANDIDATO.finditer(texto or ""):
        tel = normalizar(m.group(0))
        if tel:
            return tel
    return None
