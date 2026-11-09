"""Vista responsable del renderizado del entorno del juego."""

import pygame

from juego_lleva.views.obstaculo_view import ObstaculoView


class EntornoView:
    """Clase que maneja la presentación visual del entorno."""

    COLOR_PUNTO = (100, 100, 140)

    def __init__(self):
        """Inicializa la vista del entorno con un ObstaculoView delegado."""
        self.obstaculo_view = ObstaculoView()
        self._puntos_cache = {}

    def _superficie_punto(self, tamaño, alpha):
        """Devuelve (cacheando) la superficie de un punto de fondo.

        Args:
            tamaño (int): Tamaño del punto (radio).
            alpha (int): Opacidad deseada (0-255).

        Returns:
            pygame.Surface: Punto pre-renderizado reutilizable.
        """
        clave = (tamaño, alpha)
        if clave not in self._puntos_cache:
            lado = tamaño * 2
            superficie = pygame.Surface((lado, lado), pygame.SRCALPHA)
            pygame.draw.circle(superficie, (*self.COLOR_PUNTO, alpha),
                               (tamaño, tamaño), tamaño)
            self._puntos_cache[clave] = superficie
        return self._puntos_cache[clave]

    def renderizar(self, pantalla, entorno, tiempo_animacion=0):
        """Renderiza el entorno completo en la pantalla.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            entorno: Objeto entorno a renderizar.
            tiempo_animacion (float): Tiempo para animaciones.
        """
        for obs in entorno.obstaculos:
            self.obstaculo_view.renderizar(pantalla, obs, tiempo_animacion)

        for p in entorno.particulas_fondo:
            superficie = self._superficie_punto(p['tamaño'], p['alpha'])
            pantalla.blit(superficie, (int(p['x']) - p['tamaño'], int(p['y']) - p['tamaño']))