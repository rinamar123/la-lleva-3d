"""Modelo que representa un obstáculo en el entorno del juego."""

from juego_lleva.core.config import Config
from juego_lleva.models.rect import Rect


class Obstaculo:
    """Clase que representa un obstáculo que puede ser caja o zona lenta."""

    TIPO_CAJA = "caja"
    TIPO_ZONA = "zona"

    def __init__(self, x, y, tipo):
        """Inicializa un obstáculo con posición y tipo.

        Args:
            x (int): Coordenada horizontal.
            y (int): Coordenada vertical.
            tipo (str): Tipo de obstáculo ("caja" o "zona").
        """
        self.x = x
        self.y = y
        self.tipo = tipo
        self.config = Config()

        if tipo == self.TIPO_CAJA:
            self.ancho = self.config.TAMAÑO_CAJA
            self.alto = self.config.TAMAÑO_CAJA
        else:
            self.ancho = self.config.TAMAÑO_ZONA
            self.alto = self.config.TAMAÑO_ZONA

    def obtener_rectangulo(self):
        """Obtiene el rectángulo de colisión del obstáculo.

        Returns:
            Rect: Rectángulo que define los límites del obstáculo.
        """
        return Rect(self.x, self.y, self.ancho, self.alto)

    def es_zona_lenta(self):
        """Verifica si el obstáculo es una zona que ralentiza.

        Returns:
            bool: True si es zona lenta, False en caso contrario.
        """
        return self.tipo == self.TIPO_ZONA