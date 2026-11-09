"""Compila el juego a WebAssembly con pygbag y completa los archivos del CDN.

El código se importa como paquete (`juego_lleva.*`), y pygbag exige que la
carpeta de la app contenga un `main.py` en su raíz. Por eso este script prepara
una carpeta temporal:

    app/main.py           -> ``from juego_lleva.main import main``
    app/juego_lleva/...   -> copia del paquete (sin build/tests)

compila esa carpeta con pygbag y publica el resultado en
``juego_lleva/build/web``.

pygbag 0.9.3 genera la web apuntando a su CDN público. Si ese CDN falla o
está bloqueado el navegador no tiene nada que ejecutar y la página queda en
negro sin aviso (reproducido: canvas 1x1 para siempre). Este script:

1. Prepara la carpeta de staging con el paquete y un main.py de entrada.
2. Ejecuta la compilación de pygbag.
3. Espera a que aparezcan los artefactos (index.html, *.apk, *.tar.gz).
4. Publica el build en juego_lleva/build/web.
5. Descarga el runtime a web/cdn/ si falta (web/descargar_runtime.py) y lo
   publica en build/web/cdn/ para que el build no dependa de internet.
6. Sirve browserfs.min.js desde local (el CDN dio 404).
7. Reescribe index.html a rutas relativas, inyecta un reescriptor de URLs del
   CDN y un aviso visible si el canvas no arranca en 30 s.
"""

import pathlib
import shutil
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
JUEGO = RAIZ / "juego_lleva"
STAGING = JUEGO / "build" / "app"
BUILD_PYGAG = STAGING / "build" / "web"
SALIDA = JUEGO / "build" / "web"


def _python_entorno():
    """Usa .venv/venv del proyecto o el intérprete activo como respaldo."""
    for nombre in (".venv", "venv"):
        candidato = RAIZ / nombre / "bin" / "python"
        if candidato.exists():
            return candidato
    if sys.prefix != sys.base_prefix:
        candidato = pathlib.Path(sys.prefix) / "bin" / "python"
        if candidato.exists():
            return candidato
    return pathlib.Path(sys.executable)


VENV_PY = _python_entorno()
VENDOR = RAIZ / "web" / "vendor"

VISOR = "browserfs.min.js"

MAX_ESPERA_SEG = 900

ENTRADA = "import pygame\n\nfrom juego_lleva.main import main\n\nmain()\n"

# Se inyecta al inicio del index.html: cualquier petición que el runtime haga
# al CDN público de pygbag se redirige al espejo local de cdn/ y los fallos
# quedan anotados para el aviso de carga.
REESCRITOR = """<script>
/* runtime local: redirige el CDN público de pygbag a la carpeta cdn/ */
(function () {
    var CDN = "https://pygame-web.github.io/cdn/";
    var LOCAL = new URL("cdn/", location.href).href;
    window.__cdn_local_fallidos = [];

    function reescribir(url) {
        if (typeof url === "string" && url.indexOf(CDN) === 0)
            return LOCAL + url.slice(CDN.length);
        return url;
    }

    function apuntar(url, detalle) {
        window.__cdn_local_fallidos.push({ url: url, detalle: detalle });
        console.error("[runtime local]", url, detalle);
    }

    if (window.fetch) {
        var fetchOriginal = window.fetch;
        window.fetch = function (recurso, init) {
            var url = typeof recurso === "string" ? recurso
                : (recurso && recurso.url) || "";
            var destino = reescribir(url);
            if (destino !== url) {
                try {
                    recurso = typeof recurso === "string" ? destino
                        : new Request(destino, recurso);
                } catch (exc) {
                    apuntar(url, "no se pudo reescribir: " + exc);
                }
            }
            return fetchOriginal.call(this, recurso, init).then(
                function (respuesta) {
                    if (!respuesta.ok)
                        apuntar(respuesta.url, "HTTP " + respuesta.status);
                    return respuesta;
                },
                function (error) {
                    apuntar(url, String(error));
                    throw error;
                });
        };
    }

    var abrirOriginal = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (metodo, url) {
        var args = Array.prototype.slice.call(arguments);
        args[1] = reescribir(url);
        return abrirOriginal.apply(this, args);
    };
})();
</script>
"""

# Si a los 30 s el canvas sigue en 1x1 el runtime no arrancó: se explica en
# pantalla en lugar de dejar la página en negro sin ningún indicio.
AVISO = """<script>
(function () {
    var ESPERA_MS = 30000;
    function listo() {
        var lienzo = document.querySelector("canvas");
        return !!(lienzo && lienzo.width > 8 && lienzo.height > 8);
    }
    function publicar() {
        if (listo() || document.getElementById("aviso-carga")) return;
        var fallos = window.__cdn_local_fallidos || [];
        var detalle = fallos.slice(0, 6).map(function (f) {
            return "<li><code>" + f.url + "</code> — " + f.detalle + "</li>";
        }).join("");
        if (!detalle) {
            detalle = "<li>Faltan los archivos de la carpeta <code>cdn/</code>"
                + " o no hay conexión.</li>";
        }
        var caja = document.createElement("div");
        caja.id = "aviso-carga";
        caja.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:9999;"
            + "background:#2b1a12;color:#ffe6c7;font:15px/1.5 sans-serif;"
            + "padding:12px 18px;border-bottom:3px solid #e8a33d;"
            + "box-shadow:0 2px 8px rgba(0,0,0,.4);";
        caja.innerHTML = "<strong>No se pudo cargar el juego web.</strong><br>"
            + "El runtime de Python no llegó a cargarse: revisa la conexión y"
            + " vuelve a intentarlo.<br>"
            + "<details><summary>Detalles</summary><ul>" + detalle + "</ul></details>";
        document.body.appendChild(caja);
    }
    var temporizador = setTimeout(publicar, ESPERA_MS);
    var sondeo = setInterval(function () {
        if (!listo()) return;
        clearTimeout(temporizador);
        clearInterval(sondeo);
        var previo = document.getElementById("aviso-carga");
        if (previo) previo.remove();
    }, 500);
})();
</script>
"""

# Fullscreen requiere una acción explícita del usuario en los navegadores.
# El botón vive fuera del canvas para funcionar también en móvil y desaparece
# cuando la página entra en fullscreen.
PANTALLA_COMPLETA = """<style>
    html, body {
        width: 100%;
        height: 100%;
        min-height: 100%;
        margin: 0;
        padding: 0;
        overflow: hidden;
        background: #19192d;
    }
    body { height: 100vh; height: 100dvh; }
    #boton-pantalla-completa {
        position: fixed;
        z-index: 1000001;
        top: max(12px, env(safe-area-inset-top));
        right: max(12px, env(safe-area-inset-right));
        border: 1px solid rgba(255,255,255,.35);
        border-radius: 10px;
        padding: 10px 14px;
        color: #fff;
        background: rgba(25,25,45,.82);
        font: 600 14px/1.2 Arial, sans-serif;
        cursor: pointer;
        touch-action: manipulation;
    }
    #boton-pantalla-completa:hover { background: rgba(55,55,85,.95); }
    :fullscreen #boton-pantalla-completa,
    :-webkit-full-screen #boton-pantalla-completa { display: none; }
</style>
<script>
(function () {
    function instalar() {
        if (document.getElementById("boton-pantalla-completa")) return;
        var boton = document.createElement("button");
        boton.id = "boton-pantalla-completa";
        boton.type = "button";
        boton.textContent = "Pantalla completa ⛶";
        boton.setAttribute("aria-label", "Activar pantalla completa");
        boton.addEventListener("click", function () {
            var raiz = document.documentElement;
            var entrar = raiz.requestFullscreen || raiz.webkitRequestFullscreen;
            if (!entrar) {
                boton.textContent = "Usa F11 para pantalla completa";
                return;
            }
            Promise.resolve(entrar.call(raiz)).then(function () {
                if (screen.orientation && screen.orientation.lock)
                    return screen.orientation.lock("landscape").catch(function () {});
            }).catch(function (error) {
                console.warn("No se pudo activar pantalla completa:", error);
            });
        });
        document.body.appendChild(boton);

        function ajustarCanvas() {
            var canvas = document.getElementById("canvas");
            if (!canvas || canvas.width <= 1 || canvas.height <= 1) return false;
            var escala = Math.min(
                window.innerWidth / canvas.width,
                window.innerHeight / canvas.height
            );
            canvas.style.position = "fixed";
            canvas.style.left = "50%";
            canvas.style.top = "50%";
            canvas.style.right = "auto";
            canvas.style.bottom = "auto";
            canvas.style.margin = "0";
            canvas.style.transform = "translate(-50%, -50%)";
            canvas.style.width = Math.floor(canvas.width * escala) + "px";
            canvas.style.height = Math.floor(canvas.height * escala) + "px";
            return true;
        }

        function programarAjuste() { setTimeout(ajustarCanvas, 180); }
        window.addEventListener("resize", programarAjuste);
        document.addEventListener("fullscreenchange", programarAjuste);
        window.addEventListener("orientationchange", programarAjuste);
        if (!ajustarCanvas()) {
            var esperaCanvas = setInterval(function () {
                if (ajustarCanvas()) clearInterval(esperaCanvas);
            }, 250);
        }
    }
    if (document.readyState === "loading")
        document.addEventListener("DOMContentLoaded", instalar, { once: true });
    else
        instalar();
})();
</script>
"""


def _preparar_staging():
    """Crea la carpeta de compilación con el paquete y un main.py de entrada."""
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    shutil.copytree(
        JUEGO,
        STAGING / "juego_lleva",
        ignore=shutil.ignore_patterns("build", "__pycache__", "tests", "*.pyc"),
    )
    (STAGING / "main.py").write_text(ENTRADA, encoding="utf-8")


def compilar():
    """Lanza pygbag y devuelve cuando los artefactos estén listos."""
    _preparar_staging()
    log = open(RAIZ / "web" / "build.log", "a", encoding="utf-8")
    log.write(f"\n--- compilacion {time.strftime('%H:%M:%S')} ---\n")
    proceso = subprocess.Popen(
        [str(VENV_PY), "-m", "pygbag", str(STAGING)],
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    inicio = time.time()
    inicio_ns = time.time_ns()
    while time.time() - inicio < MAX_ESPERA_SEG:
        if proceso.poll() is not None:
            log.flush()
            log.close()
            return
        try:
            index_nuevo = (BUILD_PYGAG / "index.html").stat().st_mtime_ns > inicio_ns
            apk_nuevo = any(
                p.stat().st_mtime_ns > inicio_ns for p in BUILD_PYGAG.glob("*.apk")
            )
            tar_nuevo = any(
                p.stat().st_mtime_ns > inicio_ns for p in BUILD_PYGAG.glob("*.tar.gz")
            )
        except FileNotFoundError:
            index_nuevo = apk_nuevo = tar_nuevo = False
        if index_nuevo and apk_nuevo and tar_nuevo:
            log.flush()
            break
        time.sleep(5)
    if proceso.poll() is None:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()
    log.flush()
    log.close()


def _publicar():
    """Copia el build de pygbag a juego_lleva/build/web."""
    if not BUILD_PYGAG.exists():
        sys.exit(f"No se genero el build de pygbag en {BUILD_PYGAG}")
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    shutil.copytree(BUILD_PYGAG, SALIDA)


def _reescribir_index(html):
    """Deja el index.html usando el runtime local, con reescriptor y aviso."""
    # Una única etiqueta viewport, importante para el tamaño del juego móvil.
    html = html.replace(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '    <meta name="viewport" content="height=device-height, initial-scale=1.0">',
        '<meta name="viewport" content="width=device-width, height=device-height, '
        "initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, "
        'user-scalable=no, viewport-fit=cover">',
    )

    # Estilos del viewport y botón explícito (fullscreen solo tras interacción).
    if "boton-pantalla-completa" not in html:
        if "<body>" not in html:
            sys.exit("index.html no contiene la etiqueta <body>")
        html = html.replace("<body>", "<body>\n" + PANTALLA_COMPLETA, 1)

    # 1. browserfs: el CDN lo servía con doble barra y con 404
    if '<script src="%s"></script>' % VISOR not in html:
        if "browserfs.min.js" in html:
            html = html.replace(
                "https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js", VISOR
            )
            html = html.replace('src="browserfs.min.js"', 'src="%s"' % VISOR)
        else:
            html = html.replace(
                '<script src="https://pygame-web.github.io/cdn/0.9.3/pythons.js"',
                '<script src="%s"></script>\n'
                '<script src="https://pygame-web.github.io/cdn/0.9.3/pythons.js"'
                % VISOR,
                1,
            )

    # 2. CDN público -> rutas relativas del propio build (funciona igual en
    #    localhost, IP de la red local y túnel)
    html = html.replace("https://pygame-web.github.io/cdn/0.9.3/", "cdn/0.9.3/")
    html = html.replace("https://pygame-web.github.io/cdn/", "cdn/")

    # config.cdn debe resolverse a URL absoluta: vtx.js hace
    # import(config.cdn + "../vt/xterm.js") y un import() no acepta un
    # especificador relativo sin ./ (en localhost pygbag lo reescribe solo,
    # en la IP local rompía con "Failed to resolve module specifier")
    html = html.replace(
        'cdn : "cdn/0.9.3/",', 'cdn : new URL("cdn/0.9.3/", location.href).href,'
    )

    # 3. reescriptor de URLs + aviso de carga, antes del arranque de pygbag
    marca = '<script src="cdn/0.9.3/pythons.js"'
    if marca not in html:
        sys.exit(
            "index.html no arranca con cdn/0.9.3/pythons.js: "
            "cambio la plantilla de pygbag, revisa _reescribir_index()"
        )
    if "window.__cdn_local_fallidos = [];" not in html:
        html = html.replace(marca, REESCRITOR + AVISO + "\n" + marca, 1)

    # 4. ninguna referencia funcional al CDN público
    residuos = html.replace(REESCRITOR, "").count("pygame-web.github.io")
    if residuos:
        sys.exit(f"index.html todavia referencia el CDN publico ({residuos} veces)")
    for requisito in (
        'cdn : new URL("cdn/0.9.3/", location.href).href',
        'src="cdn/0.9.3/empty.html"',
    ):
        if requisito not in html:
            sys.exit(f"falta {requisito} en index.html")
    return html


def completar_recursos():
    """Baja el runtime si falta, lo publica en el build y reescribe index.html."""
    try:
        from descargar_runtime import asegurar_runtime
    except ImportError:
        from web.descargar_runtime import asegurar_runtime
    try:
        asegurar_runtime()
    except RuntimeError as exc:
        sys.exit(
            f"Runtime web incompleto: {exc}\n"
            "Descargalo con: venv/bin/python web/descargar_runtime.py"
        )

    destino_cdn = SALIDA / "cdn"
    if destino_cdn.exists():
        shutil.rmtree(destino_cdn)
    shutil.copytree(
        RAIZ / "web" / "cdn",
        destino_cdn,
        ignore=shutil.ignore_patterns(".runtime.json"),
    )

    shutil.copy2(VENDOR / VISOR, SALIDA / VISOR)

    indice = SALIDA / "index.html"
    html = indice.read_text(encoding="utf-8")
    indice.write_text(_reescribir_index(html), encoding="utf-8")
    print("Recursos listos en", SALIDA)


def main():
    compilar()
    _publicar()
    completar_recursos()
    print(f"Listo. Servir con: {VENV_PY} servidor_web.py juego_lleva/build/web")


if __name__ == "__main__":
    main()
