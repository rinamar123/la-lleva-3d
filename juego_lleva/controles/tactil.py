"""Control táctil para jugar desde pantallas táctiles (móviles y tablets)."""

import pygame
from juego_lleva.constantes_entrada import (
    K_a, K_d, K_DOWN, K_LEFT, K_RIGHT, K_s, K_UP, K_w,
    FINGERDOWN, FINGERMOTION, FINGERUP,
)


class ControladorTactil:
    """Traduce los toques de pantalla en teclas virtuales y gestiona la pausa."""

    def __init__(self, ancho, alto, visible=False):
        """Inicializa las zonas táctiles del jugador 1 y 2.

        Args:
            ancho (int): Ancho lógico de la pantalla.
            alto (int): Alto lógico de la pantalla.
            visible (bool): Mostrar las cruces desde el inicio (web).
        """
        self.ancho = ancho
        self.alto = alto
        self.activo = visible
        self.dedos = {}
        self.pausa_pedida = False
        self.zona_pausa = pygame.Rect(ancho - 170, 24, 140, 60)
        self.zonas_j1 = self._crear_pad(190, alto - 190, "J1")
        self.zonas_j2 = self._crear_pad(ancho - 190, alto - 190, "J2")

    def _crear_pad(self, cx, cy, etiqueta):
        """Crea la cruz de control de un jugador.

        Args:
            cx (int): Centro horizontal de la cruz.
            cy (int): Centro vertical de la cruz.
            etiqueta (str): Nombre del jugador.

        Returns:
            dict: Rectángulos de cada dirección y su etiqueta.
        """
        return {
            "arriba": pygame.Rect(cx - 60, cy - 150, 120, 90),
            "abajo": pygame.Rect(cx - 60, cy + 60, 120, 90),
            "izquierda": pygame.Rect(cx - 150, cy - 45, 90, 90),
            "derecha": pygame.Rect(cx + 60, cy - 45, 90, 90),
            "etiqueta": etiqueta,
            "centro": (cx, cy),
        }

    def procesar_evento(self, evento):
        """Actualiza la posición de los dedos tras un evento táctil.

        Args:
            evento: Evento de pygame (FINGERDOWN, FINGERMOTION o FINGERUP).
        """
        if evento.type == FINGERDOWN:
            self.activo = True
            pos = (evento.x * self.ancho, evento.y * self.alto)
            self.dedos[evento.finger_id] = pos
            if self.zona_pausa.collidepoint(pos):
                self.pausa_pedida = True
        elif evento.type == FINGERMOTION:
            self.dedos[evento.finger_id] = (evento.x * self.ancho, evento.y * self.alto)
        elif evento.type == FINGERUP:
            self.dedos.pop(evento.finger_id, None)

    def teclas_activas(self):
        """Devuelve las teclas virtuales presionadas por los toques.

        Returns:
            list: Códigos de tecla (pygame.K_*) activos por el tacto.
        """
        direcciones = ["arriba", "abajo", "izquierda", "derecha"]
        pads = [
            (self.zonas_j1, [K_w, K_s, K_a, K_d]),
            (self.zonas_j2, [K_UP, K_DOWN, K_LEFT, K_RIGHT]),
        ]
        activas = []
        for pos in self.dedos.values():
            for pad, codigos in pads:
                for nombre in direcciones:
                    if pad[nombre].collidepoint(pos):
                        activas.append(codigos[direcciones.index(nombre)])
        return activas

    def consumir_pausa(self):
        """Consume el pulso de pausa si el jugador tocó el botón.

        Returns:
            bool: True si hubo un toque pendiente sobre pausa.
        """
        valor = self.pausa_pedida
        self.pausa_pedida = False
        return valor
