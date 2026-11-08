"""Mercado Libre Inmuebles: arma las URLs de búsqueda y lee los avisos.

La API pública de búsqueda de Mercado Libre pide autorización desde 2025, así
que el robot abre las páginas de resultados con el mismo navegador (Playwright)
y lee las tarjetas. Las URLs son legibles, por ejemplo:
  /departamentos/venta/2-dormitorios/cordoba/cordoba/dueno-directo/_Desde_49

Los filtros que la URL no cubre (barrio, superficie, palabras) se controlan
después en run.py con pasa_filtros_locales y con coincide_ubicacion.
"""
import re
import time
import unicodedata

BASE = "https://inmuebles.mercadolibre.com.ar"
POR_PAGINA = 48
PAUSA_ENTRE_PAGINAS = 2.5  # segundos
TIPOS = {"casa": "casas", "departamento": "departamentos", "terreno": "terrenos"}
DORMITORIOS = {
    "monoambiente": "sin-dormitorios",
    "1-dormitorio": "1-dormitorio",
    "2-dormitorios": "2-dormitorios",
    "3-dormitorios": "3-dormitorios",
    "4-dormitorios-o-mas": "4-dormitorios-o-mas",
}
TEXTO_DORMITORIOS = {
    "monoambiente": "Monoambiente", "1-dormitorio": "1 Dormitorio", "2-dormitorios": "2 Dormitorios",
    "3-dormitorios": "3 Dormitorios", "4-dormitorios-o-mas": "4 Dormitorios o más",
}

# Lee las tarjetas del listado. Usa varias clases posibles porque Mercado Libre
# cambia el diseño de vez en cuando; si nada coincide, busca los enlaces a avisos.
LEER_TARJETAS = r"""() => {
  const q = (el, sels) => { for (const s of sels) { const x = el.querySelector(s); if (x) return x; } return null; };
  const txt = (el) => (el ? el.textContent.replace(/\s+/g, ' ').trim() : null);
  let items = [];
  for (const s of ['li.ui-search-layout__item', 'div.ui-search-result__wrapper', 'div.poly-card']) {
    items = [...document.querySelectorAll(s)];
    if (items.length) break;
  }
  if (!items.length) {
    items = [...new Set([...document.querySelectorAll('a[href*="MLA"]')].map(a => a.closest('li') || a.parentElement))];
  }
  return items.map(it => {
    const a = q(it, ['a.poly-component__title', 'h2 a', 'h3 a', 'a.ui-search-link', 'a[href*="MLA"]']);
    const monto = q(it, ['.poly-price__current .andes-money-amount', '.ui-search-price__second-line .andes-money-amount', '.andes-money-amount']);
    const img = q(it, ['img.poly-component__picture', 'img']);
    return {
      href: a ? a.href : null,
      titulo: txt(q(it, ['.poly-component__title', 'h2', 'h3'])) || txt(a),
      simbolo: monto ? txt(monto.querySelector('.andes-money-amount__currency-symbol')) : null,
      fraccion: monto ? txt(monto.querySelector('.andes-money-amount__fraction')) : null,
      atributos: [...it.querySelectorAll('.poly-attributes_list__item, .poly-attributes-list__item, .ui-search-card-attributes__attribute')].map(txt),
      ubicacion: txt(q(it, ['.poly-component__location', '.ui-search-item__location', '.ui-search-item__group__element--location'])),
      vendedor: txt(q(it, ['.poly-component__seller', '.ui-search-official-store-label'])),
      foto: img ? (img.getAttribute('data-src') || img.getAttribute('src')) : null,
      texto: it.innerText.slice(0, 600),
    };
  }).filter(x => x.href);
}"""


def slug(txt):
    t = "".join(c for c in unicodedata.normalize("NFD", (txt or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def construir_consultas(f, nombres):
    """Una URL por cada combinación tipo × dormitorio.

    nombres: dict tid -> nombre de las ubicaciones de La Voz (se usan los nombres
    para armar la ruta de Mercado Libre: provincia/ciudad).
    """
    tipos = f.get("tipos") or ["casa", "departamento"]
    dorms = f.get("dormitorios") or [None]
    lugar = [slug(nombres.get(f.get("provincia_tid")) or "Córdoba")]
    if f.get("ciudad_tid") and nombres.get(f["ciudad_tid"]):
        lugar.append(slug(nombres[f["ciudad_tid"]]))
    sufijo = ""
    desde, hasta = f.get("precio_desde"), f.get("precio_hasta")
    if desde or hasta:
        mon = "ARS" if f.get("moneda") == "pesos" else "USD"
        sufijo = f"_PriceRange_{int(desde or 0)}{mon}-{int(hasta) if hasta else '0'}{mon}"
    consultas = []
    for tipo in tipos:
        if tipo not in TIPOS:
            continue
        for d in dorms:
            partes = [TIPOS[tipo], "venta"]
            if d in DORMITORIOS and tipo != "terreno":
                partes.append(DORMITORIOS[d])
            partes += lugar
            if f.get("vendedor") == "particular":
                partes.append("dueno-directo")
            consultas.append((tipo, d, f"{BASE}/{'/'.join(partes)}/{sufijo}"))
    return consultas


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


def nuevo_contexto(navegador):
    """Mercado Libre muestra un error si detecta un navegador automatizado sin identificar:
    se usa un contexto propio con la identificación de un Chrome común."""
    ctx = navegador.new_context(locale="es-AR", user_agent=UA, viewport={"width": 1366, "height": 900},
                                extra_http_headers={"Accept-Language": "es-AR,es;q=0.9"})
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return ctx


class MercadoLibre:
    def __init__(self, page):
        self.page = page

    def abrir(self):
        self.page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(2000)

    def _pagina(self, url):
        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            self.page.wait_for_selector("li.ui-search-layout__item, div.poly-card, .ui-search-rescue", timeout=15000)
        except Exception:
            pass
        if "account-verification" in self.page.url or "/gz/" in self.page.url:
            raise RuntimeError(f"Mercado Libre pidió verificación (anti-robots) en {url}")
        tarjetas = self.page.evaluate(LEER_TARJETAS)
        if not tarjetas:
            texto = self.page.evaluate("() => document.body ? document.body.innerText.slice(0, 400) : ''")
            print(f"    Mercado Libre sin tarjetas · url final: {self.page.url} · título: {self.page.title()!r}")
            print("    Texto de la página:", " ".join(texto.split())[:400])
            clases = self.page.evaluate("""() => [...new Set([...document.querySelectorAll('[class]')]
                .flatMap(e => [...e.classList]).filter(c => /search|poly|result|card/i.test(c)))].slice(0, 40).join(' ')""")
            print("    Clases encontradas:", clases)
        return tarjetas

    def _es_error(self):
        return "Hubo un error accediendo" in (self.page.evaluate("() => document.body ? document.body.innerText.slice(0, 300) : ''") or "")

    def buscar(self, url, max_paginas=10):
        avisos, vistos = [], set()
        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if self._es_error():
            # Si la ruta de ciudad no existe, se busca a nivel provincia (la ciudad se controla después).
            m = re.match(r"(.*/venta/(?:[^/]+-dormitorios?/|sin-dormitorios/)?[^/]+/)[^/]+/(.*)", url)
            alternativa = (m.group(1) + m.group(2)) if m else None
            print(f"    Mercado Libre dio error en {url}; pruebo {alternativa}")
            if alternativa and alternativa != url:
                url = alternativa
        tarjetas = self._pagina(url)
        for n in range(max_paginas):
            nuevas = [t for t in tarjetas if _id(t["href"]) and _id(t["href"]) not in vistos]
            for t in nuevas:
                vistos.add(_id(t["href"]))
            avisos += nuevas
            print(f"    ML pág {n + 1}: {len(tarjetas)} tarjetas, {len(nuevas)} nuevas")
            if not nuevas or len(tarjetas) < POR_PAGINA or n + 1 >= max_paginas:
                break
            # El botón "Siguiente" cambia de página por script (su enlace apunta a la misma URL).
            boton = self.page.locator("li.andes-pagination__button--next a, a.andes-pagination__link:has-text('Siguiente')").first
            if not boton.count():
                break
            primera = tarjetas[0]["href"]
            time.sleep(PAUSA_ENTRE_PAGINAS)
            boton.click()
            try:
                self.page.wait_for_function(
                    "(h) => { const a = document.querySelector('a.poly-component__title, h3 a'); return a && a.href !== h; }",
                    arg=primera, timeout=20000)
            except Exception:
                print("    ML: la página siguiente no cargó")
                break
            self.page.wait_for_timeout(1500)
            tarjetas = self.page.evaluate(LEER_TARJETAS)
        return avisos

    def estado_aviso(self, url):
        resp = self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if resp is None or resp.status in (404, 410):
            return {"activo": False}
        cuerpo = self.page.content()
        if re.search(r"Publicaci[oó]n (finalizada|pausada)|Esta publicaci[oó]n no est[aá] disponible", cuerpo):
            return {"activo": False}
        m = re.search(r'"price"\s*:\s*"?([\d.]+)"?\s*,\s*"priceCurrency"\s*:\s*"([A-Z]+)"', cuerpo) or \
            re.search(r'"priceCurrency"\s*:\s*"([A-Z]+)"\s*,\s*"price"\s*:\s*"?([\d.]+)"?', cuerpo)
        if not m:
            return {"activo": True}
        a, b = m.groups()
        precio, moneda = (a, b) if a[0].isdigit() else (b, a)
        return {"activo": True, "precio": float(precio), "moneda": "USD" if moneda == "USD" else "ARS"}


def _id(href):
    m = re.search(r"MLA-?(\d+)", href or "")
    return f"MLA{m.group(1)}" if m else None


def _numero(txt):
    limpio = re.sub(r"[^\d]", "", txt or "")
    return float(limpio) if limpio else None


def _sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def coincide_ubicacion(p, f, nombres):
    """Barrio y ciudad: la URL solo filtra hasta ciudad, el barrio se controla acá."""
    texto = _sin_acentos(p.get("_ubicacion") or "")
    barrios = [nombres.get(b) for b in (f.get("barrios_tid") or []) if nombres.get(b)]
    if barrios:
        hallado = next((b for b in barrios if _sin_acentos(b) in texto), None)
        if not hallado:
            return False
        p["barrio"] = hallado
    ciudad = nombres.get(f.get("ciudad_tid"))
    if ciudad:
        if _sin_acentos(ciudad) not in texto:
            return False
        p["ciudad"] = ciudad
    return True


def normalizar(t, tipo, dorm, f):
    simbolo = (t.get("simbolo") or "").upper()
    precio = _numero(t.get("fraccion"))
    if precio is None:  # respaldo: busca "US$ 86.000" en el texto de la tarjeta
        m = re.search(r"(US\$|U\$S|\$)\s*([\d.]+)", t.get("texto") or "")
        if m:
            simbolo, precio = m.group(1), _numero(m.group(2))
    moneda = "USD" if "U" in simbolo else ("ARS" if "$" in simbolo else None)
    atributos = " · ".join(a for a in t.get("atributos") or [] if a)
    sup = re.search(r"([\d.,]+)\s*m²\s*tot", atributos) or re.search(r"([\d.,]+)\s*m²", atributos)
    dormis = re.search(r"(\d+)\s*dorm", atributos)
    banos = re.search(r"(\d+)\s*bañ", atributos)
    if dorm in TEXTO_DORMITORIOS:
        dormitorios = TEXTO_DORMITORIOS[dorm]
    elif dormis:
        n = int(dormis.group(1))
        dormitorios = "4 Dormitorios o más" if n >= 4 else f"{n} Dormitorio{'s' if n > 1 else ''}"
    else:
        dormitorios = None
    ubic = t.get("ubicacion") or ""
    partes = [x.strip() for x in ubic.split(",") if x.strip()]
    foto = t.get("foto") if (t.get("foto") or "").startswith("http") else None
    url = (t.get("href") or "").split("#")[0].split("?")[0]
    return {
        "portal": "mercadolibre",
        "portal_id": _id(url),
        "url": url,
        "titulo": t.get("titulo"),
        "descripcion": atributos or None,
        "tipo": tipo,
        "provincia": partes[-1] if partes else None,
        "ciudad": partes[-3] if len(partes) >= 3 else None,
        "barrio": partes[-2] if len(partes) >= 2 else None,
        "lat": None,
        "lng": None,
        "precio": precio,
        "moneda": moneda,
        "superficie_total": _numero(sup.group(1).split(",")[0]) if sup else None,
        "dormitorios": dormitorios,
        "banos": f"{banos.group(1)} Baño{'s' if banos.group(1) != '1' else ''}" if banos else None,
        "vendedor_tipo": "Particular" if f.get("vendedor") == "particular" else ("Inmobiliaria" if t.get("vendedor") else None),
        "vendedor_nombre": t.get("vendedor"),
        "apto_escritura": None,
        "apto_credito": None,
        "fotos": [foto] if foto else [],
        "foto_principal": foto,
        "fecha_publicacion": None,
        "_ubicacion": ubic,
    }
