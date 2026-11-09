"""Vista responsable del renderizado de obstáculos en pantalla."""

import math
import pygame


class ObstaculoView:
    """Clase que maneja la presentación visual de obstáculos."""

    def __init__(self):
        """Inicializa la vista del obstáculo."""
        self._sombras = {}

    def _sombra(self, ancho, alto):
        """Devuelve (cacheando) la sombra de una caja.

        Args:
            ancho (int): Ancho de la caja.
            alto (int): Alto de la caja.

        Returns:
            pygame.Surface: Sombra pre-renderizada reutilizable.
        """
        clave = (ancho, alto)
        if clave not in self._sombras:
            sombra = pygame.Surface((ancho + 4, alto + 4), pygame.SRCALPHA)
            pygame.draw.rect(sombra, (0, 0, 0, 80), (2, 2, ancho, alto), border_radius=6)
            self._sombras[clave] = sombra
        return self._sombras[clave]

    def renderizar(self, pantalla, obstaculo, tiempo_animacion=0):
        """Renderiza un obstáculo en la pantalla.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            obstaculo: Objeto obstáculo a renderizar.
            tiempo_animacion (float): Tiempo para animaciones.
        """
        if obstaculo.tipo == obstaculo.TIPO_CAJA:
            self._renderizar_caja(pantalla, obstaculo)
        else:
            self._renderizar_zona(pantalla, obstaculo, tiempo_animacion)

    def _renderizar_caja(self, pantalla, obstaculo):
        """Renderiza un obstáculo tipo caja.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            obstaculo: Objeto obstáculo a renderizar.
        """
        sombra = self._sombra(obstaculo.ancho, obstaculo.alto)
        pantalla.blit(sombra, (obstaculo.x, obstaculo.y))

        pygame.draw.rect(pantalla, (80, 70, 60),
                        (obstaculo.x, obstaculo.y, obstaculo.ancho, obstaculo.alto),
                        border_radius=6)
        pygame.draw.rect(pantalla, (110, 100, 85),
                        (obstaculo.x + 2, obstaculo.y + 2, obstaculo.ancho - 4, obstaculo.alto - 4),
                        border_radius=5)
        pygame.draw.rect(pantalla, (140, 130, 110),
                        (obstaculo.x + 4, obstaculo.y + 4, obstaculo.ancho - 8, obstaculo.alto // 2 - 4),
                        border_radius=4)
        pygame.draw.rect(pantalla, (60, 55, 45),
                        (obstaculo.x, obstaculo.y, obstaculo.ancho, obstaculo.alto),
                        2, border_radius=6)

    def _renderizar_zona(self, pantalla, obstaculo, tiempo_animacion):
        """Renderiza un obstáculo tipo zona lenta.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            obstaculo: Objeto obstáculo a renderizar.
            tiempo_animacion (float): Tiempo para animaciones.
        """
        pulso = math.sin(tiempo_animacion * 2) * 0.1 + 0.9

        superficie = pygame.Surface((obstaculo.ancho, obstaculo.alto), pygame.SRCALPHA)
        pygame.draw.ellipse(superficie, (40, 120, 200, 50),
                           (0, 0, obstaculo.ancho, obstaculo.alto))
        pygame.draw.ellipse(superficie, (60, 150, 230, 80),
                           (4, 4, obstaculo.ancho - 8, obstaculo.alto - 8))
        pygame.draw.ellipse(superficie, (80, 180, 255, 40),
                           (8, 8, obstaculo.ancho - 16, obstaculo.alto - 16))

        for i in range(3):
            offset = math.sin(tiempo_animacion * 3 + i * 2) * 3
            alpha = int(30 - i * 8)
            pygame.draw.ellipse(superficie, (100, 200, 255, max(alpha, 10)),
                               (int(obstaculo.ancho * 0.2) + int(offset), int(obstaculo.alto * 0.3),
                                int(obstaculo.ancho * 0.6), int(obstaculo.alto * 0.4)))

        pantalla.blit(superficie, (obstaculo.x, obstaculo.y))