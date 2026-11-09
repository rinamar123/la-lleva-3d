"""Descarga el runtime de pygbag 0.9.3 a web/cdn/ para no depender del CDN.

La web compilada necesita unos 22 MB de runtime de Python (main.wasm,
main.data, xterm, etc). Si esos archivos no estan, el navegador no tiene nada
que ejecutar: la pagina queda en negro sin ningun aviso. Por eso el runtime se
descarga una sola vez desde el CDN publico de pygbag y se guarda en
``web/cdn/`` (ignorado por git); web/compilar_web.py lo copia al build.

Uso directo:
    venv/bin/python web/descargar_runtime.py
"""

import json
import pathlib
import shutil
import sys
import urllib.error
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "web" / "cdn"
VENDOR = RAIZ / "web" / "vendor"
MANIFIESTO = DESTINO / ".runtime.json"
CDN = "https://pygame-web.github.io/cdn/"
VERSION = "0.9.3"
TIEMPO_ESPERA = 60
CHUNK = 1024 * 1024

WHEEL = "pygame_ce-2.5.7-cp312-cp312-wasm32_bi_emscripten.whl"

# Exactamente los recursos que la pagina pide al CDN, segun la captura de
# peticiones de web/probar_web.py --offline.
RECURSOS = [
    f"{VERSION}/pythons.js",
    f"{VERSION}/cpythonrc.py",
    f"{VERSION}/empty.html",
    f"{VERSION}/empty.ogg",
    f"{VERSION}/cpython312/main.js",
    f"{VERSION}/cpython312/main.wasm",
    f"{VERSION}/cpython312/main.data",
    "vtx.js",
    "vt/xterm.js",
    "vt/xterm.css",
    "vt/xterm-addon-image.js",
    f"index-{VERSION}-cp312.json",
    f"cp312/{WHEEL}",
]

# Copias verificadas que ya trae el repo: se reutilizan sin pasar por la red.
SEMILLA = {
    f"{VERSION}/pythons.js": "pythons.js",
    f"{VERSION}/empty.html": "empty.html",
}


def _peso(ruta):
    """Tamano en bytes del archivo, o 0 si no existe."""
    try:
        return ruta.stat().st_size
    except OSError:
        return 0


def _manifiesto():
    """Tamanos registrados en la descarga anterior (detectan cortes)."""
    try:
        datos = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos.get("tamanos", {})


def _guardar_manifiesto(tamanos):
    MANIFIESTO.parent.mkdir(parents=True, exist_ok=True)
    MANIFIESTO.write_text(
        json.dumps(
            {"version": VERSION, "tamanos": tamanos},
            ensure_ascii=False, indent=2),
        encoding="utf-8")


def _incompleto(relativo, previos):
    """True si falta el archivo, esta vacio o cambio de tamano respecto antes."""
    tamano = _peso(DESTINO / relativo)
    if tamano <= 0:
        return True
    if relativo in previos and previos[relativo] != tamano:
        return True
    return False


def _semilla(relativo, indice, total):
    """Copia desde web/vendor si el repo ya trae esa copia verificada."""
    origen = VENDOR / SEMILLA[relativo]
    if _peso(origen) <= 0:
        return False
    destino = DESTINO / relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origen, destino)
    print(f"[{indice}/{total}] {relativo} (del repo) {_peso(destino)} bytes")
    return True


def _descargar(relativo, indice, total):
    """Baja un recurso a web/cdn/ y devuelve su tamano. RuntimeError si falla."""
    url = CDN + relativo
    destino = DESTINO / relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + ".tmp")
    print(f"[{indice}/{total}] {relativo} ... ", end="", flush=True)
    try:
        with urllib.request.urlopen(url, timeout=TIEMPO_ESPERA) as respuesta:
            temporal.write_bytes(respuesta.read())
    except (urllib.error.URLError, OSError) as exc:
        temporal.unlink(missing_ok=True)
        print("error")
        raise RuntimeError(f"no se pudo bajar {url}: {exc}") from exc
    tamano = _peso(temporal)
    if tamano <= 0:
        temporal.unlink(missing_ok=True)
        raise RuntimeError(f"el CDN devolvio {url} vacio")
    temporal.replace(destino)
    print(f"{tamano} bytes")
    return tamano


def asegurar_runtime():
    """Descarga a web/cdn/ todo lo que falte. RuntimeError si no se puede."""
    previos = _manifiesto()
    pendientes = [r for r in RECURSOS if _incompleto(r, previos)]
    if not pendientes:
        return

    tamanos = {r: _peso(DESTINO / r) for r in RECURSOS}
    errores = []
    for posicion, relativo in enumerate(pendientes, 1):
        try:
            if relativo in SEMILLA and _semilla(relativo, posicion, len(pendientes)):
                tamanos[relativo] = _peso(DESTINO / relativo)
                continue
            tamanos[relativo] = _descargar(relativo, posicion, len(pendientes))
        except RuntimeError as exc:
            errores.append(str(exc))

    _guardar_manifiesto(tamanos)
    if errores:
        raise RuntimeError("; ".join(errores))


def main():
    try:
        asegurar_runtime()
    except RuntimeError as exc:
        sys.exit(
            f"Runtime web incompleto: {exc}\n"
            "Requiere conexion la primera vez; despues web/cdn/ queda local.")
    total = sum(_peso(DESTINO / r) for r in RECURSOS)
    print(f"Runtime web listo en {DESTINO} ({total} bytes en {len(RECURSOS)} archivos)")


if __name__ == "__main__":
    main()
