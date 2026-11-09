"""Protocolo de mensajes entre el cliente y el servidor multijugador.

Los mensajes se intercambian como líneas JSON separadas por ``\\n``. Este módulo
centraliza los tipos de mensaje y la codificación/decodificación para que
cliente y servidor no dependan entre sí.
"""

import json

TIPO_CONEXION = "conexion"
TIPO_ESTADO = "estado"
TIPO_POSICION = "posicion"

ANCHO_BUFFER = 4096
PUERTO_DEFECTO = 5555
HOST_DEFECTO = "0.0.0.0"
HOST_CLIENTE_DEFECTO = "127.0.0.1"


def codificar_mensaje(mensaje):
    """Convierte un mensaje dict en bytes listos para enviar por el socket.

    Args:
        mensaje (dict): Mensaje a codificar.

    Returns:
        bytes: Mensaje JSON terminado en salto de línea.
    """
    return (json.dumps(mensaje) + "\n").encode("utf-8")


def extraer_linea(buffer):
    """Extrae la primera línea completa de un buffer de texto.

    Args:
        buffer (str): Texto acumulado de mensajes.

    Returns:
        tuple: (mensaje, buffer_restante). Si aún no hay línea completa o la
        línea está vacía devuelve ``(None, buffer)`` o ``(None, restante)``.
    """
    if "\n" not in buffer:
        return None, buffer
    linea, resto = buffer.split("\n", 1)
    if not linea:
        return None, resto
    try:
        mensaje = json.loads(linea)
    except json.JSONDecodeError:
        return None, resto
    if not isinstance(mensaje, dict):
        return None, resto
    return mensaje, resto