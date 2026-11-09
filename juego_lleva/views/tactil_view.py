"""Vista que dibuja las zonas de control táctil sobre la pantalla."""

import pygame
from juego_lleva.fuentes import fuente


class TactilView:
    """Renderiza los pads táctiles y el botón de pausa."""

    def __init__(self):
        self._fuente_cache = None

    def dibujar(self, pantalla, controlador):
        """Dibuja las zonas táctiles visibles sobre la pantalla.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            controlador: Instancia de ControladorTactil con las zonas a dibujar.
        """
        if not controlador.activo:
            return
        overlay = pygame.Surface((controlador.ancho, controlador.alto), pygame.SRCALPHA)
        for pad in (controlador.zonas_j1, controlador.zonas_j2):
            for nombre in ("arriba", "abajo", "izquierda", "derecha"):
                rect = pad[nombre]
                pygame.draw.rect(overlay, (45, 45, 75, 150), rect, border_radius=14)
                self._dibujar_flecha(overlay, rect, nombre)
            etiqueta = self._fuente().render(pad["etiqueta"], True, (220, 220, 220, 255))
            overlay.blit(etiqueta, etiqueta.get_rect(center=(pad["centro"][0], pad["centro"][1] + 130)))
        pygame.draw.rect(overlay, (70, 70, 110, 190), controlador.zona_pausa, border_radius=12)
        texto = self._fuente().render("PAUSA", True, (255, 255, 255, 255))
        overlay.blit(texto, texto.get_rect(center=controlador.zona_pausa.center))
        pantalla.blit(overlay, (0, 0))

    def _dibujar_flecha(self, overlay, rect, direccion):
        """Dibuja la flecha de una dirección dentro de su zona.

        Args:
            overlay: Superficie transparente del control.
            rect: Rect de la zona.
            direccion (str): Nombre de la dirección.
        """
        cx, cy = rect.center
        lado = 16
        if direccion == "arriba":
            puntos = [(cx, cy - lado), (cx - lado, cy + lado), (cx + lado, cy + lado)]
        elif direccion == "abajo":
            puntos = [(cx, cy + lado), (cx - lado, cy - lado), (cx + lado, cy - lado)]
        elif direccion == "izquierda":
            puntos = [(cx - lado, cy), (cx + lado, cy - lado), (cx + lado, cy + lado)]
        else:
            puntos = [(cx + lado, cy), (cx - lado, cy - lado), (cx - lado, cy + lado)]
        pygame.draw.polygon(overlay, (220, 220, 220, 220), puntos)

    def _fuente(self):
        """Devuelve una fuente pequeña (en caché) para las etiquetas."""
        if self._fuente_cache is None:
            self._fuente_cache = fuente(28)
        return self._fuente_cache
