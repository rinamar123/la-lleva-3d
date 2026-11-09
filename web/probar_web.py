"""Verifica la versión web compilada con un navegador headless.

Uso:
    venv/bin/python web/probar_web.py [url] [segundos] [png_salida]
    venv/bin/python web/probar_web.py --offline [url] [segundos] [png_salida]

Con --offline se lanza Chromium sin resolver ningún host externo (todo lo que
no sea el propio servidor falla en DNS). Si el build sigue dependiendo del CDN
público de pygbag, la prueba falla: ese era exactamente el bug de la página en
negro. En cualquier modo se comprueba que no hubo peticiones externas, que el
canvas arrancó y que no hubo errores de página.

Se imprime la consola del navegador, los errores de página y se guarda una
captura. Útil después de cada web/compilar_web.py.

Nota: no se usa page.route() porque interceptar respuestas rompe
WebAssembly.instantiateStreaming y el intérprete nunca arranca.
"""

import argparse
import sys
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

OPCIONES = argparse.ArgumentParser(description=__doc__)
OPCIONES.add_argument("url", nargs="?", default="http://localhost:8000/")
OPCIONES.add_argument("segundos", nargs="?", type=int, default=30)
OPCIONES.add_argument("png", nargs="?", default="/tmp/opencode/web_probar.png")
OPCIONES.add_argument("--offline", action="store_true",
                      help="sin DNS para hosts externos (build 100% local)")
ARGS = OPCIONES.parse_args()

HOST_LOCAL = urlparse(ARGS.url).hostname or "localhost"
PERMITIDOS = {"localhost", "127.0.0.1", HOST_LOCAL}

consola = []
errores = []
externas = []


def _externa(url):
    """Peticiones HTTP(S) que salen del servidor que estamos probando."""
    if not url.startswith(("http://", "https://")):
        return False
    return (urlparse(url).hostname or "") not in PERMITIDOS


def _resolver_hosts():
    """Reglas de Chromium: en modo offline nadie resuelve hosts externos."""
    if not ARGS.offline:
        return []
    excluye = [f"EXCLUDE {h}" for h in sorted(PERMITIDOS)]
    return ["--host-resolver-rules=" + ", ".join(
        ["MAP * ~NOTFOUND"] + excluye)]


with sync_playwright() as p:
    navegador = p.chromium.launch(
        headless=True,
        args=["--autoplay-policy=no-user-gesture-required"] + _resolver_hosts())
    pagina = navegador.new_page()
    pagina.on("console", lambda m: consola.append(f"[{m.type}] {m.text}"))
    pagina.on("pageerror", lambda e: errores.append(str(e)))
    pagina.on("request", lambda r: externas.append(r.url) if _externa(r.url)
              else None)
    pagina.goto(ARGS.url, wait_until="load", timeout=60000)
    time.sleep(ARGS.segundos)
    pagina.mouse.click(640, 360)
    time.sleep(5)
    pagina.screenshot(path=ARGS.png)
    lienzo = pagina.evaluate(
        "() => { const c = document.querySelector('canvas');"
        " return c ? [c.width, c.height] : [0, 0]; }")
    fallidos = pagina.evaluate(
        "() => (window.__cdn_local_fallidos || []).map("
        "f => f.url + ' -> ' + f.detalle)")
    navegador.close()

fallos = []
if errores:
    fallos.append(f"{len(errores)} errores de pagina")
if externas:
    fallos.append(f"{len(set(externas))} peticiones externas "
                  "(el build depende de internet)")
if lienzo[0] <= 8 or lienzo[1] <= 8:
    fallos.append("el canvas no arranco (pagina en negro)")
if fallidos:
    fallos.append(f"{len(fallidos)} recursos locales fallaron")

print("== Peticiones externas ==")
print("\n".join(dict.fromkeys(externas)) or "(ninguna)")
print("== Errores de página ==")
print("\n".join(errores) or "(ninguno)")
print(f"== Canvas: {lienzo[0]}x{lienzo[1]} ==")
if fallidos:
    print("== Runtime local con fallos ==")
    print("\n".join(fallidos[:8]))
print("== Consola ==" if fallos else "== Consola (últimas 25) ==")
print("\n".join(consola if fallos else consola[-25:]))
print("== Captura:", ARGS.png)

if fallos:
    sys.exit("FALLO: " + "; ".join(fallos))
print("OK")
