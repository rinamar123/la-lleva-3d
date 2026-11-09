"""Genera los fondos de alta resolución del juego de forma procedural.

El juego carga campo.png y menu_bg.jpg como imágenes de fondo. Este script las
recrea sin depender de descargas externas:

    SDL_VIDEODRIVER=dummy python juego_lleva/assets/generar_assets.py

Genera:
  - fondos/campo.png   (1920x1080 y 1280x720)  campo de juego estilo parque.
  - fondos/menu_bg.jpg (1920x1080)             plaza nocturna para el menú.
"""

import math
import os
import random

import pygame

pygame.init()

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
FONDOS_DIR = os.path.join(ASSETS_DIR, "fondos")
os.makedirs(FONDOS_DIR, exist_ok=True)

VERDE_OSCURO = (24, 76, 40)
VERDE = (44, 112, 58)
VERDE_CLARO = (64, 148, 80)
ARENA = (196, 166, 122)
ARENA_OSCURO = (160, 132, 94)


def _mascara_vineta(ancho, alto, max_alpha=90, poder=1.45):
    """Devuelve una superficie que oscurece los bordes de la pantalla.

    Args:
        ancho (int): Ancho objetivo.
        alto (int): Alto objetivo.
        max_alpha (int): Opacidad máxima de los bordes.
        poder (float): Exponente para suavizar la transición.

    Returns:
        pygame.Surface: Máscara con transparencia lista para superponer.
    """
    escala_w = 240
    escala_h = max(50, int(escala_w * alto / ancho))
    fuente = pygame.Surface((escala_w, escala_h), pygame.SRCALPHA)
    cx, cy = escala_w / 2, escala_h / 2
    max_radio = (escala_w ** 2 + escala_h ** 2) ** 0.5 / 2
    for i in range(1, 90):
        t = i / 90
        radio = max_radio * (0.12 + t * 0.88)
        alpha = int(max_alpha * (t ** poder))
        pygame.draw.circle(fuente, (0, 0, 0, alpha),
                           (int(cx), int(cy)), int(radio), 4)
    return pygame.transform.smoothscale(fuente, (ancho, alto))


def _base_gradiente(dest, color_alto, color_bajo):
    """Pinta un degradado vertical de alto a bajo en una superficie.

    Args:
        dest: Superficie de pygame de destino.
        color_alto (tuple): Color superior.
        color_bajo (tuple): Color inferior.
    """
    ancho, alto = dest.get_size()
    for y in range(alto):
        t = y / alto
        color = tuple(int(color_alto[i] + (color_bajo[i] - color_alto[i]) * t)
                      for i in range(3))
        pygame.draw.line(dest, color, (0, y), (ancho, y))


def _arbol(surface, rng, x, y, escala=1.0, hoja=VERDE_OSCURO):
    """Dibuja un árbol de copa redondeada en x, y.

    Args:
        surface: Superficie donde dibujar.
        rng: Generador aleatorio con semilla.
        x (int): Centro horizontal de la base.
        y (int): Base del árbol.
        escala (float): Escala del tamaño.
        hoja (tuple): Color principal del follaje.
    """
    ancho_tronco = int(14 * escala)
    alto_tronco = int(30 * escala)
    pygame.draw.rect(surface, (72, 52, 36),
                     (int(x - ancho_tronco / 2), int(y - alto_tronco),
                      ancho_tronco, alto_tronco))
    radio = int(42 * escala)
    for _ in range(5):
        cx = x + int(rng.uniform(-radio, radio) * 0.4)
        cy = y - alto_tronco + int(rng.uniform(-40, 30) * escala)
        pygame.draw.circle(surface, hoja, (cx, cy), int(rng.uniform(radio * 0.5, radio)))
    pygame.draw.circle(surface, (52, 120, 66) if hoja == VERDE_OSCURO else (72, 150, 88),
                       (x - int(12 * escala), y - alto_tronco - int(16 * escala)),
                       int(radio * 0.5))


def crear_campo(ancho=1920, alto=1080, ruta=None):
    """Genera el fondo del campo de juego (parque nocturno).

    Args:
        ancho (int): Ancho del fondo.
        alto (int): Alto del fondo.
        ruta (str, optional): Ruta de salida. Por defecto el estándar.
    """
    rng = random.Random(1234)
    superficie = pygame.Surface((ancho, alto))
    _base_gradiente(superficie, (30, 90, 50), (58, 140, 76))

    for banda in range(6):
        y0 = int(alto * (0.28 + banda * 0.12))
        franja = pygame.Surface((ancho, int(alto * 0.07)), pygame.SRCALPHA)
        franja.fill((255, 255, 255, 14 if banda % 2 == 0 else 0))
        superficie.blit(franja, (0, y0))

    elipse = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    pygame.draw.ellipse(elipse, (*VERDE_CLARO, 90),
                        (int(ancho * 0.08), int(alto * 0.12),
                         int(ancho * 0.84), int(alto * 0.7)))
    superficie.blit(elipse, (0, 0))

    bordes = [
        (6, 0, 0.12, 0.95, 60),
        (ancho * 0.88, 0, 0.12, 0.95, 60),
    ]
    for bx, by, bw, bh, radio in bordes:
        pygame.draw.ellipse(superficie, ARENA_OSCURO,
                            (bx - 6, by - 6, ancho * bw + 12, alto * bh + 12))
        pygame.draw.ellipse(superficie, ARENA,
                            (bx, by, ancho * bw, alto * bh))

    for x, y in [(0, alto * 0.45), (0, alto * 0.85), (ancho, alto * 0.5), (ancho, alto * 0.9)]:
        pygame.draw.ellipse(superficie, (58, 40, 26),
                            (x, y - alto * 0.22, ancho * 0.12, alto * 0.24))

    for i in range(12):
        x = rng.uniform(0.02, 0.98) * ancho
        y = rng.uniform(0.05, 0.95) * alto
        _arbol(superficie, rng, int(x), int(y),
               escala=rng.uniform(0.7, 1.3),
               hoja=VERDE_OSCURO if rng.random() < 0.6 else VERDE_CLARO)

    for i in range(80):
        x = rng.uniform(0.02, 0.98) * ancho
        y = rng.uniform(0.05, 0.95) * alto
        color = rng.choice([(255, 235, 120), (255, 160, 180), (180, 220, 255)])
        radio_f = rng.randint(2, 4)
        capa = pygame.Surface((radio_f * 2, radio_f * 2), pygame.SRCALPHA)
        pygame.draw.circle(capa, (*color, 160), (radio_f, radio_f), radio_f)
        superficie.blit(capa, (int(x - radio_f), int(y - radio_f)))

    superficie.blit(_mascara_vineta(ancho, alto, max_alpha=80), (0, 0))

    ruta = ruta or os.path.join(FONDOS_DIR, "campo.png")
    pygame.image.save(superficie, ruta)
    print(f"Creado: {ruta} ({ancho}x{alto})")


def crear_menu(ancho=1920, alto=1080, ruta=None):
    """Genera el fondo del menú principal (plaza nocturna).

    Args:
        ancho (int): Ancho del fondo.
        alto (int): Alto del fondo.
        ruta (str, optional): Ruta de salida. Por defecto el estándar.
    """
    rng = random.Random(5678)
    horizonte = int(alto * 0.7)
    superficie = pygame.Surface((ancho, alto))
    _base_gradiente(superficie, (16, 22, 60), (36, 26, 60))

    for _ in range(90):
        x = rng.uniform(0, 1) * ancho
        y = rng.uniform(0, 0.55) * alto
        pygame.draw.circle(superficie, (210, 210, 230), (int(x), int(y)), rng.randint(1, 2))

    radio_luna = int(alto * 0.1)
    luna_x = int(ancho * 0.78)
    luna_y = int(alto * 0.18)
    brillo = pygame.Surface((radio_luna * 5, radio_luna * 5), pygame.SRCALPHA)
    for i in range(1, 40):
        pygame.draw.circle(brillo, (255, 230, 160, 22),
                           (brillo.get_width() // 2, brillo.get_height() // 2),
                           radio_luna * 2.2 - i * 2, 4)
    superficie.blit(brillo, (luna_x - radio_luna * 2.5, luna_y - radio_luna * 2.5))
    pygame.draw.circle(superficie, (252, 238, 196), (luna_x, luna_y), radio_luna)
    pygame.draw.circle(superficie, (238, 220, 175),
                       (luna_x + int(radio_luna * 0.28), luna_y - int(radio_luna * 0.2)),
                       int(radio_luna * 0.22))

    for x in range(0, ancho, int(ancho * 0.07)):
        h = rng.randint(int(alto * 0.02), int(alto * 0.16))
        ancho_edif = int(ancho * 0.055)
        pygame.draw.rect(superficie, (14, 16, 34),
                         (x, horizonte - h, ancho_edif + int(ancho * 0.015), h))
        if rng.random() < 0.5:
            for vy in range(horizonte - h + 10, horizonte - 6, 26):
                pygame.draw.rect(superficie, (255, 200, 120),
                                 (x + 8, vy, 8, 6))

    faro_x = int(ancho * 0.72)
    radio_faro = int(alto * 0.03)
    pygame.draw.circle(superficie, (252, 238, 196),
                       (int(faro_x * 0.92), horizonte - int(alto * 0.26)), radio_faro)
    pygame.draw.rect(superficie, (20, 20, 38),
                     (int(faro_x * 0.92) - int(radio_faro * 0.5),
                      horizonte - int(radio_faro * 2.2),
                      radio_faro, int(radio_faro * 2.2)))

    rueda_x = int(ancho * 0.5)
    rueda_y = horizonte - int(alto * 0.28)
    radio_rueda = int(alto * 0.2)
    pygame.draw.circle(superficie, (18, 20, 40), (rueda_x, rueda_y), radio_rueda, 6)
    for i in range(8):
        angulo = -math.pi / 2 + i * math.pi / 4
        dx = int(radio_rueda * math.cos(angulo))
        dy = int(radio_rueda * math.sin(angulo))
        pygame.draw.line(superficie, (18, 20, 40),
                         (rueda_x, rueda_y), (rueda_x + dx, rueda_y + dy), 4)
    for i in range(6):
        angulo = -math.pi / 2 + i * math.pi / 3
        cx = rueda_x + int(radio_rueda * 0.78 * math.cos(angulo))
        cy = rueda_y + int(radio_rueda * 0.78 * math.sin(angulo))
        pygame.draw.rect(superficie, (16, 18, 36), (cx - 8, cy - 8, 16, 16))
    pygame.draw.line(superficie, (30, 32, 54), (rueda_x, rueda_y + radio_rueda),
                     (rueda_x, rueda_y + radio_rueda + int(alto * 0.12)), 5)

    suelo = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    pygame.draw.rect(suelo, (*VERDE_OSCURO, 200), (0, horizonte, ancho, alto - horizonte))
    superficie.blit(suelo, (0, 0))
    for _ in range(40):
        x = rng.uniform(0, 1) * ancho
        y = horizonte + (rng.random() ** 2) * (alto - horizonte)
        pygame.draw.circle(superficie, (52, 120, 66), (int(x), int(y)), rng.randint(3, 8))

    for _ in range(4):
        x = rng.uniform(0.05, 0.95) * ancho
        y = horizonte + int(alto * 0.02)
        _arbol(superficie, rng, int(x), y, escala=rng.uniform(0.9, 1.3))

    superficie.blit(_mascara_vineta(ancho, alto, max_alpha=110), (0, 0))

    ruta = ruta or os.path.join(FONDOS_DIR, "menu_bg.jpg")
    pygame.image.save(superficie, ruta)
    print(f"Creado: {ruta} ({ancho}x{alto})")


if __name__ == "__main__":
    crear_campo(1920, 1080, os.path.join(FONDOS_DIR, "campo.png"))
    crear_menu(1920, 1080, os.path.join(FONDOS_DIR, "menu_bg.jpg"))
    print("\nFondos generados correctamente.")