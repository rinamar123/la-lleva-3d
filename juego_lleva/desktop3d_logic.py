"""Funciones puras compartidas por la capa 3D de escritorio."""

import math

ANCHO_LOGICO = 1280
ALTO_LOGICO = 720
ESCALA_MUNDO = 100.0


def mundo_desde_logico(x, y):
    """Convierte coordenadas 2D del juego al plano X/Z del mundo 3D."""
    return ((x - ANCHO_LOGICO / 2) / ESCALA_MUNDO,
            (y - ALTO_LOGICO / 2) / ESCALA_MUNDO)


def entrada_relativa(teclas, yaw_radianes):
    """Traduce WASD relativo a la cámara a las cuatro acciones del modelo.

    El modelo existente usa cuatro direcciones booleanas; por eso se conserva
    su contrato y se proyecta la dirección de cámara a esos cuatro ejes.
    """
    adelante = (math.sin(yaw_radianes), math.cos(yaw_radianes))
    derecha = (math.cos(yaw_radianes), -math.sin(yaw_radianes))
    dx = (adelante[0] * (int(bool(teclas.get("w"))) - int(bool(teclas.get("s"))))
          + derecha[0] * (int(bool(teclas.get("d"))) - int(bool(teclas.get("a")))))
    dy = (adelante[1] * (int(bool(teclas.get("w"))) - int(bool(teclas.get("s"))))
          + derecha[1] * (int(bool(teclas.get("d"))) - int(bool(teclas.get("a")))))
    return {
        "izquierda": dx < -0.12,
        "derecha": dx > 0.12,
        "arriba": dy < -0.12,
        "abajo": dy > 0.12,
    }
