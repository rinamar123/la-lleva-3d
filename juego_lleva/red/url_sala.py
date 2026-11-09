"""Ubicación del juego web (y de la API de la sala) para el modo en línea.

El modo en línea corre en el navegador, no en la ventana de pygame: la versión
web habla por HTTP con la sala y usa la Fetch API del navegador. Por eso la
ventana de escritorio, al pulsar "En Línea", redirige a la página servida por
``servidor_web.py``.

La URL la fija ``jugar.py`` en la variable de entorno ``LALLEVA_URL_SALA`` (para
respetar un ``--puerto`` distinto del predeterminado). Si nadie la define se usa
el puerto 8000, que es el predeterminado de ``servidor_web.py``.
"""

import os
import urllib.parse

URL_DEFECTO = "http://localhost:8000/"
VARIABLE_URL = "LALLEVA_URL_SALA"
TIMEOUT_SEG = 0.4


def url_sala():
    """Devuelve la URL del juego web, con barra final.

    Returns:
        str: URL definida por ``LALLEVA_URL_SALA`` o ``URL_DEFECTO``.
    """
    url = (os.environ.get(VARIABLE_URL) or "").strip() or URL_DEFECTO
    return url if url.endswith("/") else url + "/"


def servidor_responde(url=None, timeout=TIMEOUT_SEG):
    """Comprueba si hay un servidor escuchando en la URL de la sala.

    Se usa un socket de la familia AF_INET porque en el navegador los sockets no
    sirven: esta función es solo del camino de escritorio.

    Args:
        url (str, optional): URL a comprobar. Por defecto, ``url_sala()``.
        timeout (float): Segundos de espera al conectar.

    Returns:
        bool: True si el puerto acepta conexiones.
    """
    partes = urllib.parse.urlparse(url or url_sala())
    puerto = partes.port or (443 if partes.scheme == "https" else 80)
    host = partes.hostname or "localhost"
    import socket
    try:
        with socket.create_connection((host, puerto), timeout=timeout):
            return True
    except OSError:
        return False
