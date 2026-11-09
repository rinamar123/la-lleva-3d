"""Servicio que gestiona la generación y efectos de los power-ups."""

import random

from juego_lleva.core.config import Config
from juego_lleva.models.power_up import PowerUp
from juego_lleva.models.rect import Rect


class PowerUpService:
    """Crea power-ups en el campo y calcula a quién afectan sus efectos."""

    def __init__(self, config=None):
        """Inicializa el servicio de power-ups.

        Args:
            config: Instancia de Config con los parámetros del juego.
        """
        self.config = config if config is not None else Config()

    def crear(self, jugadores, activos):
        """Intenta crear un nuevo power-up en una posición libre.

        Args:
            jugadores (list): Jugadores activos en la ronda.
            activos (list): Power-ups actualmente en el campo.

        Returns:
            PowerUp o None: Power-up creado, o None si no hay cupo/espacio.
        """
        if len(activos) >= self.config.POWER_UP_MAX_ACTIVOS:
            return None
        tipo = random.choice(PowerUp.TIPOS)
        tamaño = self.config.POWER_UP_TAMAÑO
        margen = tamaño
        for _ in range(200):
            x = random.randint(margen, self.config.ANCHO_PANTALLA - margen)
            y = random.randint(70, self.config.ALTO_PANTALLA - margen)
            rect = Rect(x - tamaño // 2, y - tamaño // 2, tamaño, tamaño)
            if any(j.obtener_rectangulo().inflate(200, 200).colliderect(rect) for j in jugadores):
                continue
            return PowerUp(x, y, tipo, self.config)
        return None

    def efecto(self, colector, rival, tipo):
        """Calcula el efecto de un power-up según quién lo recoge.

        Args:
            colector: Jugador que recogió el power-up.
            rival: Jugador contrario (dado por la IA o el multijugador).
            tipo (str): Tipo de power-up.

        Returns:
            tuple: (id_objetivo, tipo_efecto, duracion) o None.
        """
        if tipo == "velocidad":
            return (colector.id, "velocidad", self.config.POWER_UP_EFECTO_VELOCIDAD_SEG)
        if tipo == "congelar":
            if rival is None:
                return None
            return (rival.id, "congelar", self.config.POWER_UP_CONGELAR_SEG)
        if tipo == "escudo":
            return (colector.id, "escudo", None)
        return None