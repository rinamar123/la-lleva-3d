"""Configuración central del juego con todas las constantes y parámetros."""

import os
import sys

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    """Clase que contiene toda la configuración del juego."""

    PLATAFORMA_WEB = sys.platform == "emscripten"

    if PLATAFORMA_WEB:
        ANCHO_PANTALLA = 1280
        ALTO_PANTALLA = 720
    else:
        ANCHO_PANTALLA = 1908
        ALTO_PANTALLA = 1080
    FPS = 60
    TAMAÑO_JUGADOR = 95
    VELOCIDAD_JUGADOR = 300
    VELOCIDAD_IA = 260
    ACELERACION = 900
    ROZAMIENTO = 6.0
    DURACION_TROPIEZO = 0.15
    ALCANCE_TOQUE = 90
    INTERVALO_PASOS = 0.30
    FACTOR_IA_HUYENDO = 0.9
    VARIACION_IA = 40
    DURACION_RONDA = 60

    DIFICULTADES = {
        "facil": {"VELOCIDAD_IA": 200, "VARIACION_IA": 60, "FACTOR_IA_HUYENDO": 0.8, "TIEMPO_REACCION": 0.30},
        "normal": {"VELOCIDAD_IA": 260, "VARIACION_IA": 40, "FACTOR_IA_HUYENDO": 0.9, "TIEMPO_REACCION": 0.20},
        "dificil": {"VELOCIDAD_IA": 320, "VARIACION_IA": 25, "FACTOR_IA_HUYENDO": 1.0, "TIEMPO_REACCION": 0.06},
    }

    DURACIONES_RONDA = [30, 60, 90]

    # Colores principales
    COLOR_FONDO = (25, 25, 45)
    COLOR_JUGADOR_1 = (0, 180, 255)
    COLOR_JUGADOR_2 = (255, 100, 50)
    COLOR_JUGADOR_3 = (170, 80, 220)
    COLOR_JUGADOR_4 = (110, 230, 60)
    COLOR_LLEVA = (255, 50, 50)
    COLOR_LIBRE = (0, 220, 100)

    @classmethod
    def color_jugador(cls, id_jugador):
        """Devuelve el color del jugador según su id (4 esquemas en rotación).

        Args:
            id_jugador (int): Identificador del jugador.

        Returns:
            tuple: Color RGB del jugador.
        """
        esquemas = (cls.COLOR_JUGADOR_1, cls.COLOR_JUGADOR_2,
                    cls.COLOR_JUGADOR_3, cls.COLOR_JUGADOR_4)
        return esquemas[id_jugador % len(esquemas)]

    # Acentos
    COLOR_DORADO = (255, 215, 0)
    COLOR_PLATA = (192, 192, 192)

    # Obstaculos
    CANTIDAD_OBSTACULOS_MIN = 3
    CANTIDAD_OBSTACULOS_MAX = 8
    TAMAÑO_CAJA = 100
    TAMAÑO_ZONA = 80
    FACTOR_RALENTIZACION = 0.4
    FUERZA_REBOTE = 300

    # UI
    COLOR_BOTON = (50, 50, 80)
    COLOR_BOTON_HOVER = (70, 70, 110)
    COLOR_BORDE = (100, 100, 140)
    BOTONES_MENU = 7

    # Assets
    ASSETS_DIR = os.path.join(_BASE_DIR, "assets")
    FONDOS_DIR = os.path.join(ASSETS_DIR, "fondos")

    FONDO = os.path.join(FONDOS_DIR, "campo.png")
    FONDO_MENU = os.path.join(FONDOS_DIR, "menu_bg.jpg")
    RANKING_PATH = os.path.join(ASSETS_DIR, "ranking.json")
    SETTINGS_PATH = os.path.join(ASSETS_DIR, "settings.json")

    # Power-ups
    POWER_UP_TAMAÑO = 45
    POWER_UP_VIDA_SEG = 7.0
    POWER_UP_FRECUENCIA_SEG = 8.0
    POWER_UP_MAX_ACTIVOS = 2
    FACTOR_VELOCIDAD_POWER = 1.6
    POWER_UP_EFECTO_VELOCIDAD_SEG = 5.0
    POWER_UP_CONGELAR_SEG = 3.0

    # Transiciones
    DURACION_FUNDIDO_SEG = 0.35
