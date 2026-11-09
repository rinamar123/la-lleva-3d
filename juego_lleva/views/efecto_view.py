"""Vista que dibuja los efectos visuales de corta duración (toques, colisiones)."""

import pygame


class EfectoView:
    """Clase que renderiza los efectos (anillo + partículas)."""

    COLOR_ANILLO = (255, 215, 0)
    _MAX_CACHE = 512

    def __init__(self):
        """Inicializa la vista de efectos con cachés de superficies."""
        self._anillos = {}
        self._particulas = {}

    def _superficie_anillo(self, color, radio, alfa):
        """Devuelve (cacheando) la superficie circular de un anillo.

        Args:
            color (tuple): Color RGB del anillo.
            radio (int): Radio del anillo.
            alfa (int): Opacidad del anillo (0-255).

        Returns:
            pygame.Surface: Anillo pre-renderizado reutilizable.
        """
        if len(self._anillos) >= self._MAX_CACHE:
            self._anillos.clear()
        clave = (color, radio, alfa)
        if clave not in self._anillos:
            capa = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
            pygame.draw.circle(capa, (*color, alfa), (radio, radio), radio, 4)
            self._anillos[clave] = capa
        return self._anillos[clave]

    def _superficie_particula(self, color, radio):
        """Devuelve (cacheando) la superficie circular de una partícula.

        Args:
            color (tuple): Color RGB de la partícula.
            radio (int): Radio de la partícula.

        Returns:
            pygame.Surface: Partícula pre-renderizada reutilizable.
        """
        if len(self._particulas) >= self._MAX_CACHE:
            self._particulas.clear()
        clave = (color, radio)
        if clave not in self._particulas:
            superficie = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
            pygame.draw.circle(superficie, color, (radio, radio), radio)
            self._particulas[clave] = superficie
        return self._particulas[clave]

    def renderizar(self, pantalla, efectos):
        """Dibuja los efectos activos sobre la pantalla.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            efectos (list): Lista de efectos activos.
        """
        for efecto in efectos:
            t = efecto['tiempo']
            progreso = t / 0.6
            alfa = int(255 * (1 - progreso))
            color = efecto.get('color', self.COLOR_ANILLO)

            x = efecto['x']
            y = efecto['y']

            anillo = self._superficie_anillo(color, int(12 + progreso * 150), alfa)
            pantalla.blit(anillo, (int(x) - anillo.get_width() // 2, int(y) - anillo.get_height() // 2))

            anillo_interno = self._superficie_anillo(color, int(10 + progreso * 85), min(255, int(alfa * 1.3)))
            pantalla.blit(anillo_interno, (int(x) - anillo_interno.get_width() // 2, int(y) - anillo_interno.get_height() // 2))

            radio_flash = max(2, int(16 * (1 - progreso)))
            flash = self._superficie_anillo((255, 255, 255), radio_flash, int(alfa * 0.6))
            pantalla.blit(flash, (int(x) - radio_flash, int(y) - radio_flash),
                          special_flags=pygame.BLEND_ADD)

            for particula in efecto['particulas']:
                radio_p = max(2, int(6 * particula['vida'] / 0.7))
                superficie = self._superficie_particula(color, radio_p)
                pantalla.blit(superficie, (int(particula['x']) - radio_p,
                                           int(particula['y']) - radio_p),
                              special_flags=pygame.BLEND_ADD)
