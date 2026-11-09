"""Constantes de teclado y eventos, compatibles con escritorio y pygame-wasm.

En pygbag/wasm el módulo ``pygame.locals`` no existe y las constantes
``pygame.K_*`` pueden no estar disponibles al importar. Aquí se resuelve cada
constante desde ``pygame`` si existe y, si no, se usa el código SDL equivalente
(estable en ambas plataformas).
"""

import pygame


def _valor(nombre, predeterminado):
    """Devuelve la constante de pygame o el código SDL de respaldo."""
    valor = getattr(pygame, nombre, None)
    return predeterminado if valor is None else valor


QUIT = _valor("QUIT", 256)
KEYDOWN = _valor("KEYDOWN", 768)
KEYUP = _valor("KEYUP", 769)
MOUSEBUTTONDOWN = _valor("MOUSEBUTTONDOWN", 1025)
MOUSEBUTTONUP = _valor("MOUSEBUTTONUP", 1026)
FINGERDOWN = _valor("FINGERDOWN", 1792)
FINGERMOTION = _valor("FINGERMOTION", 1794)
FINGERUP = _valor("FINGERUP", 1793)

K_w = _valor("K_w", 119)
K_a = _valor("K_a", 97)
K_s = _valor("K_s", 115)
K_d = _valor("K_d", 100)
K_p = _valor("K_p", 112)
K_q = _valor("K_q", 113)
K_r = _valor("K_r", 114)
K_m = _valor("K_m", 109)
K_1 = _valor("K_1", 49)
K_2 = _valor("K_2", 50)
K_3 = _valor("K_3", 51)
K_UP = _valor("K_UP", 1073741906)
K_DOWN = _valor("K_DOWN", 1073741905)
K_LEFT = _valor("K_LEFT", 1073741904)
K_RIGHT = _valor("K_RIGHT", 1073741903)
K_RETURN = _valor("K_RETURN", 13)
K_ESCAPE = _valor("K_ESCAPE", 27)
K_SPACE = _valor("K_SPACE", 32)
K_TAB = _valor("K_TAB", 9)
K_BACKSPACE = _valor("K_BACKSPACE", 8)
K_F11 = _valor("K_F11", 1073741892)