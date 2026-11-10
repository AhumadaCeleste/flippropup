"""Sondeo: qué URL de Marketplace respeta Córdoba en Apify."""
import os
import marketplace

for url in ["https://www.facebook.com/marketplace/cordoba/propertyforsale/",
            "https://www.facebook.com/marketplace/cordoba/search/?query=casa%20en%20venta",
            "https://www.facebook.com/marketplace/cordoba/"]:
    marketplace.URL_BUSQUEDA = url
    os.environ["MARKETPLACE_PAIS_PROXY"] = ""
    try:
        items = marketplace.traer(3)
    except Exception as e:
        print("== ERROR", url, e); continue
    print("== ", url, len(items))
    for x in items:
        p = marketplace.normalizar(x)
        print("    ", p["ciudad"], "|", p["titulo"][:60], "|", p["precio"], p["moneda"], "|", p["tipo"])
