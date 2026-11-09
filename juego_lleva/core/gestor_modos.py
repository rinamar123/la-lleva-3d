"""Gestor de modos de juego que administra la inicialización de partidas."""

import random

from juego_lleva.controles.controlador import Controlador
from juego_lleva.models.entorno import Entorno


class GestorModos:
    """Clase que administra los diferentes modos de juego."""

    def __init__(self):
        """Inicializa el gestor con controlador y entorno."""
        self.controlador = Controlador()
        self.entorno = Entorno()

    def iniciar_multijugador(self, juego, nombres=None):
        """Inicia una partida multijugador con los jugadores especificados.

        Args:
            juego: Instancia del juego principal.
            nombres (list, optional): Lista de nombres para los jugadores.
        """
        juego.jugadores.clear()
        juego.jugadores_views.clear()

        positions = [(100, 100), (900, 100)]

        for i in range(2):
            teclas = self.controlador.obtener_teclas_jugador(i)
            nombre = nombres[i] if nombres and i < len(nombres) else f"J{i + 1}"
            juego.crear_jugador(positions[i][0], positions[i][1],
                                i, teclas=teclas, nombre=nombre)

        self.entorno.generar_obstaculos(juego.jugadores)

        juego.set_lleva_inicial(random.randint(0, len(juego.jugadores) - 1))
        juego.tiempo_ronda = 0
        juego.puntaje_service.reiniciar()

    def iniciar_un_jugador(self, juego, nombre=None):
        """Inicia una partida de un jugador contra la computadora.

        Args:
            juego: Instancia del juego principal.
            nombre (str, optional): Nombre del jugador humano.
        """
        juego.jugadores.clear()
        juego.jugadores_views.clear()

        teclas = self.controlador.obtener_teclas_jugador(0)
        juego.crear_jugador(100, 100, 0, teclas=teclas, nombre=nombre or "J1")
        juego.crear_jugador_ia(900, 100, 1, "IA")

        self.entorno.generar_obstaculos(juego.jugadores)

        juego.set_lleva_inicial(random.randint(0, len(juego.jugadores) - 1))
        juego.tiempo_ronda = 0
        juego.puntaje_service.reiniciar()
