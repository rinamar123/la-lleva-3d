"""Estados de la máquina de estados del juego."""

from enum import Enum


class EstadoJuego(str, Enum):
    """Estados posibles del bucle principal del juego.

    Hereda de ``str`` para que pueda compararse tanto con miembros del enum
    como con sus cadenas equivalentes (compatibilidad con código y pruebas
    existentes).
    """

    MENU = "menu"
    NOMBRES = "nombres"
    JUGANDO = "jugando"
    PAUSA = "pausa"
    FIN_RONDA = "fin_ronda"
    AYUDA = "ayuda"
    COUNTDOWN = "countdown"
    RANKING = "ranking"
    OPCIONES = "opciones"
    EN_LINEA = "en_linea"
