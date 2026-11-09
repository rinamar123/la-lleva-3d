"""Vista que dibuja los power-ups sobre el campo de juego."""

import math

import pygame
from juego_lleva.fuentes import fuente

from juego_lleva.core.config import Config


class PowerUpView:
    """Clase que renderiza los power-ups con animación de gemas."""

    COLORES = {
        "velocidad": (0, 220, 100),
        "escudo": (100, 150, 255),
        "congelar": (80, 200, 255),
    }
    LETRAS = {
        "velocidad": "V",
        "escudo": "E",
        "congelar": "C",
    }

    def __init__(self):
        """Inicializa la vista de power-ups."""
        self.config = Config()
        self.fuente = fuente(30)
        self._halos = {}

    def _superficie_halo(self, color, radio, alpha):
        """Devuelve (cacheando) el halo translúcido de un power-up.

        Args:
            color (tuple): Color RGB del halo.
            radio (int): Radio del halo.
            alpha (int): Nivel de opacidad del halo (0-255).

        Returns:
            pygame.Surface: Halo pre-renderizado reutilizable.
        """
        clave = (color, radio, alpha)
        if len(self._halos) >= 256:
            self._halos.clear()
        if clave not in self._halos:
            superficie = pygame.Surface((70, 70), pygame.SRCALPHA)
            pygame.draw.circle(superficie, (*color, int(alpha * 0.35)),
                               (35, 35), radio)
            self._halos[clave] = superficie
        return self._halos[clave]

    def _dibujar_gema(self, pantalla, centro, radio, color, rotacion):
        """Dibuja una gema en forma de diamante rotado.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            centro (tuple): Centro de la gema.
            radio (int): Radio de la gema.
            color (tuple): Color RGB de la gema.
            rotacion (float): Ángulo de rotación en radianes.
        """
        puntos = []
        for i in range(4):
            angulo = rotacion + i * math.pi / 2
            puntos.append((
                int(centro[0] + math.cos(angulo) * radio),
                int(centro[1] + math.sin(angulo) * radio)
            ))
        pygame.draw.polygon(pantalla, color, puntos)
        brillo = [(puntos[0][0] + puntos[1][0]) // 2, (puntos[0][1] + puntos[1][1]) // 2]
        pygame.draw.circle(pantalla, (255, 255, 255), brillo, max(2, radio // 5))

    def renderizar(self, pantalla, power_ups, tiempo_animacion):
        """Dibuja todos los power-ups activos.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            power_ups (list): Lista de power-ups activos.
            tiempo_animacion (float): Tiempo acumulado para animar.
        """
        for pu in power_ups:
            alpha = 255
            if pu.vida < 2.0 and int(tiempo_animacion * 4) % 2 == 0:
                alpha = 110

            color = self.COLORES.get(pu.tipo, self.config.COLOR_DORADO)
            radio_halo = 26 + math.sin(tiempo_animacion * 3) * 4
            halo = self._superficie_halo(color, int(radio_halo), alpha)
            pantalla.blit(halo, (pu.x - 35, pu.y - 35))

            radio_gema = 14 + math.sin(tiempo_animacion * 4) * 2
            rotacion = tiempo_animacion * 1.5
            self._dibujar_gema(pantalla, (pu.x, pu.y), int(radio_gema), color, rotacion)

            texto = self.fuente.render(self.LETRAS.get(pu.tipo, "?"), True, (20, 20, 40))
            pantalla.blit(texto, (pu.x - texto.get_width() // 2, pu.y - texto.get_height() // 2))