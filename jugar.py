#!/usr/bin/env python3
"""Orquestador del juego La Lleva: levanta la versión completa con un comando.

Se encarga de todo el ciclo de ejecución:

1. Se relanza con el venv del proyecto para tener pygame disponible.
2. Verifica el build web y lo recompila con pygbag si falta o está viejo.
3. Levanta el servidor web (build + API de la sala en línea) en un subproceso.
4. Abre la ventana del juego de escritorio en el proceso principal.
5. Al salir del juego, detiene el servidor para no dejar procesos huérfanos.

Uso (desde la raíz del proyecto):
    ./jugar.py                          # build web + servidor + juego
    python3 jugar.py                    # igual que ./jugar.py
    python3 jugar.py --solo-web         # solo servidor y navegador
    python3 jugar.py --solo-juego       # solo la ventana del juego
    python3 jugar.py --puerto 9000 --max-jugadores 4
    python3 jugar.py --recompilar
"""

import argparse
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent


def _python_proyecto():
    """Elige el Python del entorno del proyecto, admitiendo .venv y venv."""
    for nombre in (".venv", "venv"):
        candidato = RAIZ / nombre / "bin" / "python"
        if candidato.exists():
            return candidato
    if sys.prefix != sys.base_prefix:
        candidato = pathlib.Path(sys.prefix) / "bin" / "python"
        if candidato.exists():
            return candidato
    return pathlib.Path(sys.executable)


VENV_PYTHON = _python_proyecto()
VENV_DIR = VENV_PYTHON.parent.parent
BUILD_WEB = RAIZ / "juego_lleva" / "build" / "web"
INDICE_WEB = BUILD_WEB / "index.html"
COMPILAR_WEB = RAIZ / "web" / "compilar_web.py"
SERVIDOR_WEB = RAIZ / "servidor_web.py"
PAQUETE = RAIZ / "juego_lleva"

PUERTO_DEFECTO = 8000
MAX_JUGADORES_DEFECTO = 3
CAPACIDADES = [2, 3, 4]

VARIABLE_URL_SALA = "LALLEVA_URL_SALA"

ESPERA_SERVIDOR_SEG = 20
GRACIA_SERVIDOR_SEG = 5
TIMEOUT_SOCKET_SEG = 0.3


# --------------------------------------------------------------------
# Intérprete y entorno
# --------------------------------------------------------------------


def dentro_del_venv():
    """True si el intérprete en uso coincide con el entorno seleccionado.

    Se compara ``sys.prefix`` y no el ejecutable: en un venv ``bin/python`` suele
    ser un symlink al intérprete del sistema, así que comparar rutas reales
    daría "ya estás en el venv" cuando en realidad no lo estás.
    """
    try:
        return pathlib.Path(sys.prefix).resolve() == VENV_DIR.resolve()
    except OSError:
        return False


def usar_venv():
    """Se relanza con el Python del proyecto si hace falta."""
    if not VENV_PYTHON.exists() or dentro_del_venv():
        return
    print(f"Relanzando con el venv del proyecto: {VENV_PYTHON}")
    os.execv(
        str(VENV_PYTHON), [str(VENV_PYTHON), str(pathlib.Path(__file__)), *sys.argv[1:]]
    )


def manejar_senales():
    """Convierte SIGTERM/SIGINT en KeyboardInterrupt para apagar el servidor.

    Así el bloque ``finally`` también corre cuando el proceso se detiene con
    ``kill`` y no con Ctrl-C, y no queda el servidor web huérfano.
    """

    def _interrumpir(numero_senal, marco):
        raise KeyboardInterrupt

    for nombre in ("SIGTERM", "SIGINT"):
        numero = getattr(signal, nombre, None)
        if numero is not None:
            signal.signal(numero, _interrumpir)


def verificar_pygame():
    """Comprueba que pygame esté instalado en el intérprete en uso."""
    try:
        import pygame
    except ImportError:
        sys.exit(
            "Falta pygame en este intérprete.\n"
            f"Instala las dependencias con:  {VENV_PYTHON} -m pip install -r "
            f"{RAIZ / 'requirements.txt'}"
        )
    version = ".".join(str(n) for n in pygame.version.ver)
    print(f"pygame-ce {version} listo")


def asegurar_ruta_importacion():
    """Agrega la raíz del proyecto al path para importar juego_lleva desde donde sea."""
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))


# --------------------------------------------------------------------
# Build web
# --------------------------------------------------------------------


def build_desactualizado():
    """True si el build web falta o algún fuente es más nuevo que el build."""
    if not INDICE_WEB.exists():
        return True
    referencia = INDICE_WEB.stat().st_mtime
    for fuente in PAQUETE.rglob("*.py"):
        if "build" in fuente.parts or "__pycache__" in fuente.parts:
            continue
        if fuente.stat().st_mtime > referencia:
            return True
    return False


def asegurar_build(args):
    """Deja el build web listo para servirse, compilándolo si hace falta."""
    if INDICE_WEB.exists() and not args.recompilar and not build_desactualizado():
        print(f"Build web al día: {INDICE_WEB}")
        return
    if args.sin_compilar:
        if not INDICE_WEB.exists():
            sys.exit(
                "No existe el build web y --sin-compilar impide generarlo.\n"
                f"Quita el flag o ejecuta: {VENV_PYTHON} web/compilar_web.py"
            )
        print("No se recompila (--sin-compilar)")
        return
    print("Generando el build web con pygbag (puede tardar varios minutos)...")
    resultado = subprocess.run([sys.executable, str(COMPILAR_WEB)], cwd=str(RAIZ))
    if resultado.returncode != 0 or not INDICE_WEB.exists():
        sys.exit("La compilación del build web falló. Revisa web/build.log")


# --------------------------------------------------------------------
# Servidor web
# --------------------------------------------------------------------


def puerto_ocupado(puerto):
    """True si algo ya está escuchando en el puerto indicado."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(TIMEOUT_SOCKET_SEG)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def esperar_puerto(puerto, segundos):
    """Espera a que el puerto acepte conexiones. True si respondió a tiempo."""
    limite = time.time() + segundos
    while time.time() < limite:
        if puerto_ocupado(puerto):
            return True
        time.sleep(0.2)
    return False


def ip_local():
    """Devuelve la IP local del equipo para entrar desde el celular."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def detener_servidor(proceso):
    """Termina el subproceso del servidor, forzándolo si no obedece."""
    if proceso is None or proceso.poll() is not None:
        return
    print("Deteniendo el servidor web...")
    proceso.terminate()
    try:
        proceso.wait(timeout=GRACIA_SERVIDOR_SEG)
    except subprocess.TimeoutExpired:
        proceso.kill()
        proceso.wait(timeout=GRACIA_SERVIDOR_SEG)


def esperar_servidor(proceso):
    """Espera al servidor hasta que se cierre, se interrumpa o muera solo."""
    try:
        if proceso is not None:
            codigo = proceso.wait()
            if codigo:
                print(f"El servidor web terminó con código {codigo}")
        else:
            while True:
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass


def iniciar_servidor(args):
    """Levanta el servidor web. Devuelve el subproceso o None si se reusó."""
    if puerto_ocupado(args.puerto):
        print(f"Ya hay un servidor escuchando en el puerto {args.puerto}; se reusa.")
        return None
    comando = [
        sys.executable,
        str(SERVIDOR_WEB),
        str(BUILD_WEB),
        "--puerto",
        str(args.puerto),
        "--max-jugadores",
        str(args.max_jugadores),
    ]
    proceso = subprocess.Popen(comando, cwd=str(RAIZ))
    if not esperar_puerto(args.puerto, ESPERA_SERVIDOR_SEG):
        detener_servidor(proceso)
        sys.exit(
            f"El servidor web no respondió en el puerto {args.puerto}.\n"
            "Prueba con otro puerto: python jugar.py --puerto 9000"
        )
    return proceso


def mostrar_urls(args):
    """Imprime las direcciones para jugar en el PC y en el celular."""
    url = f"http://localhost:{args.puerto}/"
    # La ventana de escritorio redirige al navegador con esta URL al pulsar
    # "En Línea", así que el juego debe conocer el puerto elegido.
    os.environ[VARIABLE_URL_SALA] = url
    print()
    print(f"En este equipo:  {url}")
    print(f"Desde el móvil:  http://{ip_local()}:{args.puerto}/")
    print(f"Sala en línea para {args.max_jugadores} jugadores")
    print("El modo en línea se juega en el navegador: menú 'En Línea'.")
    print()


# --------------------------------------------------------------------
# Juego de escritorio
# --------------------------------------------------------------------


def jugar():
    """Abre la ventana del juego y espera a que se cierre."""
    from juego_lleva.main import main as main_juego

    try:
        main_juego()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass


def main():
    """Punto de entrada: prepara build, servidor y juego, y los apaga al salir."""
    parser = argparse.ArgumentParser(
        description="Ejecuta La Lleva completo: build web, servidor y juego"
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--solo-web",
        action="store_true",
        help="no abrir la ventana, solo el servidor y el navegador",
    )
    grupo.add_argument(
        "--solo-juego",
        action="store_true",
        help="no tocar el build ni el servidor, solo la ventana",
    )
    parser.add_argument(
        "--recompilar",
        action="store_true",
        help="forzar la recompilación del build web con pygbag",
    )
    parser.add_argument(
        "--sin-compilar",
        action="store_true",
        help="no compilar aunque el build falte o este viejo",
    )
    parser.add_argument(
        "--puerto",
        type=int,
        default=PUERTO_DEFECTO,
        help=f"puerto del servidor web (default {PUERTO_DEFECTO})",
    )
    parser.add_argument(
        "--max-jugadores",
        type=int,
        default=MAX_JUGADORES_DEFECTO,
        choices=CAPACIDADES,
        help=f"capacidad de la sala en línea " f"(default {MAX_JUGADORES_DEFECTO})",
    )
    args = parser.parse_args()

    usar_venv()
    asegurar_ruta_importacion()
    manejar_senales()
    if not args.solo_web:
        verificar_pygame()

    proceso = None
    try:
        if not args.solo_juego:
            asegurar_build(args)
            proceso = iniciar_servidor(args)
            mostrar_urls(args)
            if args.solo_web:
                esperar_servidor(proceso)
        if not args.solo_web:
            print("Abriendo el juego... (cierra la ventana para salir)")
            jugar()
    finally:
        detener_servidor(proceso)
        print("Listo.")


if __name__ == "__main__":
    main()
