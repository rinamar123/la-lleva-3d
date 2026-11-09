"""Controlador que maneja las pantallas de pausa y fin de ronda."""

import pygame
from juego_lleva.constantes_entrada import K_p, K_ESCAPE, K_q, K_RETURN, K_r, KEYDOWN

from juego_lleva.core.estado import EstadoJuego


class ControladorPantallas:
    """Gestiona las pantallas de pausa y fin de ronda."""

    def __init__(self, juego):
        self.j = juego

    def pantalla_pausa(self):
        """Maneja la pantalla de pausa durante la partida."""
        if self.j.tactil.consumir_pausa():
            self.j.estado = EstadoJuego.JUGANDO
            return
        for evento in self.j.eventos_pendientes:
            if evento.type == KEYDOWN:
                if evento.key in (K_p, K_ESCAPE):
                    self.j.estado = EstadoJuego.JUGANDO
                    return
                if evento.key == K_q:
                    self.j._volver_al_menu()
                    return

        self.j.renderer.pantalla_pausa()
        self.j.renderer.flip()

    def pantalla_fin_ronda(self):
        """Maneja la pantalla de fin de ronda mostrando resultados."""
        ganador = self.j.puntaje_service.obtener_ganador()

        if not self.j._ranking_registrado:
            self._registrar_en_ranking(ganador)
            self.j._ranking_registrado = True

        accion = self.j.acciones_ui.detectar_fin_ronda(
            self.j.mouse_pos, self.j.click_realizado, self.j.interfaz.escala_ui)

        if accion == "revancha":
            self.j._iniciar_partida()
            return
        elif accion == "menu":
            self.j._volver_al_menu()
            return

        for evento in self.j.eventos_pendientes:
            if evento.type == KEYDOWN and evento.key in (K_RETURN, K_r):
                self.j._iniciar_partida()
                return
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                self.j._volver_al_menu()
                return

        self.j.renderer.pantalla_fin_ronda()
        self.j.renderer.flip()

    def _registrar_en_ranking(self, ganador_id):
        """Registra la partida actual en el ranking."""
        if ganador_id is None:
            return
        ganador_nombre = next(
            (j.nombre for j in self.j.jugadores if j.id == ganador_id), f"J{ganador_id + 1}")
        tiempo_ganador = self.j.puntaje_service.tiempos_lleva.get(ganador_id, 0)
        jugadores_tiempos = {}
        for j in self.j.jugadores:
            jugadores_tiempos[j.nombre] = self.j.puntaje_service.tiempos_lleva.get(j.id, 0)
        self.j.ranking_service.registrar_partida(ganador_nombre, tiempo_ganador, jugadores_tiempos)
