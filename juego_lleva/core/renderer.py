"""Modulo centralizado de renderizado. Unico punto que toca la pantalla y flip()."""

import pygame


class Renderer:
    """Centraliza todo el renderizado del juego en un solo lugar."""

    def __init__(self, juego):
        self.j = juego

    def flip(self):
        """Ejecuta el unico pygame.display.flip() del juego y limita FPS.

        Los avisos (toasts) se pintan aqui mismo, justo antes de presentar el
        buffer, para que se vean en todas las pantallas sin flip extra.
        """
        if self.j.toasts:
            self.j.interfaz.dibujar_toasts(self.j.pantalla, self.j.toasts)
        pygame.display.flip()
        if not self.j.config.PLATAFORMA_WEB:
            self.j.reloj.tick(self.j.config.FPS)

    def fade(self):
        """Renderiza la transicion de fundido si esta activa."""
        if self.j.fade_alpha <= 0:
            return
        fundido = pygame.Surface(
            (self.j.config.ANCHO_PANTALLA, self.j.config.ALTO_PANTALLA), pygame.SRCALPHA)
        fundido.fill((0, 0, 0, int(self.j.fade_alpha)))
        self.j.pantalla.blit(fundido, (0, 0))

    def frame_juego(self, delta_tiempo):
        """Renderiza el frame completo de una partida en curso."""
        if self.j.fondo:
            self.j.pantalla.blit(self.j.fondo, (0, 0))
        else:
            self.j.pantalla.fill(self.j.config.COLOR_FONDO)

        self.j.entorno_view.renderizar(
            self.j.pantalla, self.j.gestor_modos.entorno, self.j.tiempo_ronda)
        self.j.power_up_view.renderizar(
            self.j.pantalla, self.j.power_ups, self.j.tiempo_ronda)

        for i, jugador in enumerate(self.j.jugadores):
            if i < len(self.j.jugadores_views):
                self.j.jugadores_views[i].renderizar(
                    self.j.pantalla, jugador, delta_tiempo)

        self.j.efecto_view.renderizar(self.j.pantalla, self.j.efectos)

        self.j.interfaz.dibujar_hud(
            self.j.pantalla, self.j.tiempo_ronda,
            self.j.puntaje_service.tiempos_lleva, self.j.jugadores,
            self.j.duracion_ronda, self.j.efectos_activos)
        self.j.tactil_view.dibujar(self.j.pantalla, self.j.tactil)

        if self.j.toque_flash > 0:
            capa = pygame.Surface(
                (self.j.config.ANCHO_PANTALLA, self.j.config.ALTO_PANTALLA), pygame.SRCALPHA)
            capa.fill((255, 255, 255, int(140 * max(0.0, self.j.toque_flash / 0.12))))
            self.j.pantalla.blit(capa, (0, 0))

    def menu_principal(self):
        """Renderiza el menu principal."""
        self.j.interfaz.dibujar_menu_principal(
            self.j.pantalla, self.j.mouse_pos, self.j.opcion_menu)

    def pantalla_nombres(self):
        """Renderiza la pantalla de nombres."""
        cantidad = len(self.j.nombres)
        self.j.interfaz.dibujar_pantalla_nombres(
            self.j.pantalla, self.j.nombres, self.j.nombre_activo,
            self.j.mouse_pos, cantidad)

    def pantalla_ayuda(self):
        """Renderiza la pantalla de ayuda."""
        self.j.interfaz.dibujar_ayuda(self.j.pantalla, self.j.mouse_pos)

    def pantalla_ranking(self):
        """Renderiza la pantalla de ranking."""
        entradas = self.j.ranking_service.obtener_top(10)
        self.j.interfaz.dibujar_ranking(self.j.pantalla, entradas, self.j.mouse_pos)

    def pantalla_opciones(self):
        """Renderiza la pantalla de opciones."""
        self.j.interfaz.dibujar_opciones(
            self.j.pantalla, self.j.configuracion,
            self.j.opcion_activa, self.j.mouse_pos)

    def pantalla_countdown(self):
        """Renderiza la pantalla de countdown."""
        self.j.interfaz.dibujar_countdown(self.j.pantalla, self.j.countdown_valor)

    def pantalla_pausa(self):
        """Renderiza la pantalla de pausa."""
        self.j.interfaz.dibujar_pausa(self.j.pantalla)

    def pantalla_fin_ronda(self):
        """Renderiza la pantalla de fin de ronda."""
        ganador = self.j.puntaje_service.obtener_ganador()
        self.j.pantalla.fill(self.j.config.COLOR_FONDO)
        self.j.interfaz.dibujar_fin_ronda(
            self.j.pantalla, ganador, self.j.puntaje_service.tiempos_lleva,
            self.j.mouse_pos, self.j.jugadores)
