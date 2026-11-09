"""Modelo de power-up que aparece en el campo durante la ronda."""

from juego_lleva.core.config import Config
from juego_lleva.models.rect import Rect


class PowerUp:
    """Representa un power-up colocable en el campo de juego."""

    TIPOS = ("velocidad", "escudo", "congelar")

    def __init__(self, x, y, tipo, config=None):
        """Inicializa un power-up en el campo.

        Args:
            x (float): Coordenada horizontal del centro.
            y (float): Coordenada vertical del centro.
            tipo (str): Tipo de power-up ("velocidad", "escudo", "congelar").
            config: Instancia de Config con los parámetros del juego.
        """
        if tipo not in self.TIPOS:
            raise ValueError(f"Tipo de power-up inválido: {tipo}")
        self.config = config if config is not None else Config()
        self.x = int(x)
        self.y = int(y)
        self.tipo = tipo
        self.vida = self.config.POWER_UP_VIDA_SEG

    def obtener_rectangulo(self):
        """Devuelve el rectángulo del power-up centrado en su posición.

        Returns:
            Rect: Rectángulo que ocupa el power-up.
        """
        tamaño = self.config.POWER_UP_TAMAÑO
        return Rect(self.x - tamaño // 2, self.y - tamaño // 2, tamaño, tamaño)

    def expirado(self):
        """Indica si el power-up agotó su tiempo en el campo.

        Returns:
            bool: True si debe desaparecer.
        """
        return self.vida <= 0