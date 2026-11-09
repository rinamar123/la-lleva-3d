"""Modelo que representa el entorno del juego con obstáculos y partículas de fondo."""

import math
import random

from juego_lleva.core.config import Config
from juego_lleva.models.rect import Rect

from juego_lleva.models.obstaculo import Obstaculo


class Entorno:
    """Clase que gestiona el entorno del juego, incluyendo obstáculos y efectos visuales."""

    def __init__(self):
        """Inicializa el entorno con partículas de fondo y lista vacía de obstáculos."""
        self.config = Config()
        self.particulas_fondo = []
        self.obstaculos = []
        self._generar_particulas_fondo()

    def _generar_particulas_fondo(self):
        """Genera partículas decorativas para el fondo del juego."""
        for _ in range(30):
            self.particulas_fondo.append({
                'x': random.randint(0, self.config.ANCHO_PANTALLA),
                'y': random.randint(0, self.config.ALTO_PANTALLA),
                'tamaño': random.randint(1, 3),
                'velocidad': random.uniform(0.2, 0.8),
                'alpha': random.randint(30, 80),
                'angulo': random.uniform(0, math.pi * 2)
            })

    def generar_obstaculos(self, jugadores):
        """Genera obstáculos aleatorios sin solaparse con jugadores u otros obstáculos.

        Args:
            jugadores (list): Lista de jugadores para evitar solapamientos.
        """
        self.obstaculos = []
        cantidad = random.randint(self.config.CANTIDAD_OBSTACULOS_MIN,
                                 self.config.CANTIDAD_OBSTACULOS_MAX)

        intentos = 0
        while len(self.obstaculos) < cantidad and intentos < 100:
            intentos += 1
            tipo = random.choice([Obstaculo.TIPO_CAJA, Obstaculo.TIPO_ZONA])
            tamano = self.config.TAMAÑO_CAJA if tipo == Obstaculo.TIPO_CAJA else self.config.TAMAÑO_ZONA

            x = random.randint(50, self.config.ANCHO_PANTALLA - tamano - 50)
            y = random.randint(50, self.config.ALTO_PANTALLA - tamano - 50)

            nuevo_rect = Rect(x, y, tamano, tamano)

            solapado = False
            for j in jugadores:
                j_rect = j.obtener_rectangulo()
                j_rect.inflate_ip(60, 60)
                if nuevo_rect.colliderect(j_rect):
                    solapado = True
                    break

            if not solapado:
                for obs in self.obstaculos:
                    obs_rect = obs.obtener_rectangulo()
                    obs_rect.inflate_ip(20, 20)
                    if nuevo_rect.colliderect(obs_rect):
                        solapado = True
                        break

            if not solapado:
                self.obstaculos.append(Obstaculo(x, y, tipo))

    def actualizar(self, delta_tiempo):
        """Actualiza las posiciones de las partículas de fondo.

        Args:
            delta_tiempo (float): Tiempo transcurrido desde la última actualización.
        """
        for p in self.particulas_fondo:
            p['x'] += math.cos(p['angulo']) * p['velocidad']
            p['y'] += math.sin(p['angulo']) * p['velocidad']

            if p['x'] < 0:
                p['x'] = self.config.ANCHO_PANTALLA
            elif p['x'] > self.config.ANCHO_PANTALLA:
                p['x'] = 0
            if p['y'] < 0:
                p['y'] = self.config.ALTO_PANTALLA
            elif p['y'] > self.config.ALTO_PANTALLA:
                p['y'] = 0

            p['angulo'] += random.uniform(-0.1, 0.1)