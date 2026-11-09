"""Ayudante de fuentes seguras para el navegador (pygame-wasm)."""

import pygame


def fuente(tamano):
    """Devuelve la fuente por defecto de pygame.

    Usa ``pygame.font.Font(None, tamano)`` en lugar de ``SysFont``, porque en
    ``pygame-wasm`` la búsqueda de fuentes del sistema (fc-list) no existe y
    ``SysFont`` puede bloquear el arranque en el navegador.
    """
    return pygame.font.Font(None, tamano)