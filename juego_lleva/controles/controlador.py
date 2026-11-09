"""Módulo de control que gestiona las entradas del teclado."""

import pygame
from juego_lleva.constantes_entrada import K_a, K_d, K_DOWN, K_LEFT, K_RIGHT, K_s, K_UP, K_w


class Controlador:
    """Clase que administra la configuración de teclas para los jugadores."""

    def __init__(self):
        """Inicializa el controlador con la configuración de teclas para dos jugadores."""
        self.teclas_jugador1 = {
            'arriba': K_w,
            'abajo': K_s,
            'izquierda': K_a,
            'derecha': K_d
        }
        self.teclas_jugador2 = {
            'arriba': K_UP,
            'abajo': K_DOWN,
            'izquierda': K_LEFT,
            'derecha': K_RIGHT
        }

    def obtener_teclas_jugador(self, id_jugador):
        """Obtiene la configuración de teclas para un jugador.

        Args:
            id_jugador (int): ID del jugador (0 o 1).

        Returns:
            dict: Diccionario con las teclas asignadas al jugador.
        """
        if id_jugador == 0:
            return self.teclas_jugador1
        elif id_jugador == 1:
            return self.teclas_jugador2
        return self.teclas_jugador1
