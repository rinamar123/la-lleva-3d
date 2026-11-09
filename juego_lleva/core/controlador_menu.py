"""Controlador que maneja las pantallas de menú, nombres, ayuda, ranking y opciones."""

import sys

import pygame
from juego_lleva.constantes_entrada import K_1, K_2, K_3, K_UP, K_DOWN, K_RETURN, K_ESCAPE, K_TAB, K_BACKSPACE, K_LEFT, K_RIGHT, KEYDOWN

from juego_lleva.core.estado import EstadoJuego


class ControladorMenu:
    """Gestiona las pantallas de navegación: menú, nombres, ayuda, ranking, opciones, countdown."""

    def __init__(self, juego):
        self.j = juego

    def menu_principal(self):
        """Maneja la pantalla del menú principal con mouse y teclado."""
        accion = self.j.acciones_ui.detectar_menu(
            self.j.mouse_pos, self.j.click_realizado,
            self.j.interfaz.BOTONES_MENU, self.j.interfaz.escala_ui)

        if accion:
            self._ejecutar_accion_menu(accion)
            return

        for evento in self.j.eventos_pendientes:
            if evento.type == KEYDOWN:
                if evento.key == K_1:
                    self._ejecutar_accion_menu("un_jugador")
                    return
                elif evento.key == K_2:
                    self._ejecutar_accion_menu("jugar")
                    return
                elif evento.key == K_3:
                    self._ejecutar_accion_menu("opciones")
                    return
                elif evento.key == K_UP:
                    self.j.opcion_menu = (self.j.opcion_menu - 1) % self.j.config.BOTONES_MENU
                    self.j.audio.clic()
                elif evento.key == K_DOWN:
                    self.j.opcion_menu = (self.j.opcion_menu + 1) % self.j.config.BOTONES_MENU
                    self.j.audio.clic()
                elif evento.key == K_RETURN:
                    self._ejecutar_accion_menu(self.j.interfaz.acciones_menu[self.j.opcion_menu])
                    return

        self.j.renderer.menu_principal()
        self.j.renderer.flip()

    def _ejecutar_accion_menu(self, accion):
        if accion == "un_jugador":
            self.j.modo = "un_jugador"
            self.j.nombres = ["J1"]
            self.j.nombre_activo = 0
            self.j.estado = EstadoJuego.NOMBRES
        elif accion == "jugar":
            self.j.modo = "dos_jugadores"
            self.j.nombres = ["J1", "J2"]
            self.j.nombre_activo = 0
            self.j.estado = EstadoJuego.NOMBRES
        elif accion == "en_linea":
            if self.j.config.PLATAFORMA_WEB:
                self.j.modo = "en_linea"
                # campo vacio: si arrancaba con "J1" el texto escrito quedaba
                # pegado (J1TEST). _iniciar_partida_en_linea normaliza a J1.
                self.j.nombres = [""]
                self.j.nombre_activo = 0
                self.j.estado = EstadoJuego.NOMBRES
            else:
                self._abrir_en_linea_en_navegador()
        elif accion == "ayuda":
            self.j.estado = EstadoJuego.AYUDA
        elif accion == "ranking":
            self.j.estado = EstadoJuego.RANKING
        elif accion == "opciones":
            self.j.estado = EstadoJuego.OPCIONES
            self.j.opcion_activa = 0
        elif accion == "salir":
            pygame.quit()
            sys.exit()
        self.j.audio.clic()
        if accion not in ("salir",):
            self.j.opcion_menu = self.j.interfaz.acciones_menu.index(accion)

    def _abrir_en_linea_en_navegador(self):
        """Redirige a la versión web, que es donde sí funciona la sala en línea.

        La sala se sincroniza por HTTP desde el navegador, así que la ventana de
        pygame no puede alojarla. Si el servidor no está levantado se avisa en
        lugar de abrir una página que no carga.
        """
        from juego_lleva.red.url_sala import servidor_responde, url_sala

        url = url_sala()
        if not servidor_responde(url):
            self.j._mostrar_toast(
                f"Sin servidor en {url}: ejecuta ./jugar.py",
                self.j.config.COLOR_DORADO)
            return
        import webbrowser
        try:
            abierto = webbrowser.open(url)
        except webbrowser.Error:
            abierto = False
        if not abierto:
            # sin navegador por defecto: que quede la url a abrir a mano
            self.j._mostrar_toast(
                f"Abre {url} en el navegador para jugar en linea",
                self.j.config.COLOR_DORADO)
            return
        self.j._mostrar_toast(
            "Modo en linea abierto en el navegador",
            self.j.config.COLOR_LIBRE)

    def pantalla_nombres(self):
        """Maneja la pantalla de ingreso de nombres."""
        cantidad_jugadores = len(self.j.nombres)
        for evento in self.j.eventos_pendientes:
            if evento.type == KEYDOWN:
                if evento.key == K_ESCAPE:
                    self.j._volver_al_menu()
                    return
                elif evento.key == K_TAB and cantidad_jugadores > 1:
                    self.j.nombre_activo = (self.j.nombre_activo + 1) % cantidad_jugadores
                elif evento.key == K_RETURN:
                    self.j._iniciar_partida()
                    return
                elif evento.key == K_BACKSPACE:
                    self.j.nombres[self.j.nombre_activo] = self.j.nombres[self.j.nombre_activo][:-1]
                elif evento.unicode.isprintable() and len(self.j.nombres[self.j.nombre_activo]) < 12:
                    self.j.nombres[self.j.nombre_activo] += evento.unicode

        if self.j.click_realizado and self.j.mouse_pos:
            x, y = self.j.mouse_pos
            if (self.j.config.ANCHO_PANTALLA // 2 - 140 <= x <= self.j.config.ANCHO_PANTALLA // 2 + 140 and
                520 <= y <= 570):
                self.j._iniciar_partida()
                return

        self.j.renderer.pantalla_nombres()
        self.j.renderer.flip()

    def pantalla_ayuda(self):
        """Maneja la pantalla de ayuda."""
        for evento in self.j.eventos_pendientes:
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                self.j._volver_al_menu()
                return

        accion = self.j.acciones_ui.detectar_ayuda(
            self.j.mouse_pos, self.j.click_realizado,
            self.j.config.ANCHO_PANTALLA, self.j.config.ALTO_PANTALLA)
        if accion == "volver":
            self.j._volver_al_menu()
            return

        self.j.renderer.pantalla_ayuda()
        self.j.renderer.flip()

    def pantalla_ranking(self):
        """Maneja la pantalla de ranking."""
        for evento in self.j.eventos_pendientes:
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                self.j._volver_al_menu()
                return

        accion = self.j.acciones_ui.detectar_ranking(self.j.mouse_pos, self.j.click_realizado)
        if accion == "volver":
            self.j._volver_al_menu()
            return

        self.j.renderer.pantalla_ranking()
        self.j.renderer.flip()

    def pantalla_opciones(self):
        """Maneja la pantalla de opciones configurables."""
        for evento in self.j.eventos_pendientes:
            if evento.type == KEYDOWN:
                if evento.key == K_ESCAPE:
                    self.j._volver_al_menu()
                    return
                elif evento.key == K_UP:
                    self.j.opcion_activa = (self.j.opcion_activa - 1) % 5
                elif evento.key == K_DOWN:
                    self.j.opcion_activa = (self.j.opcion_activa + 1) % 5
                elif evento.key in (K_LEFT, K_RIGHT):
                    self._cambiar_opcion(self.j.opcion_activa, evento.key == K_RIGHT)
                elif evento.key == K_RETURN:
                    self._cambiar_opcion(self.j.opcion_activa, True)

        accion = self.j.acciones_ui.detectar_opciones(self.j.mouse_pos, self.j.click_realizado)
        if accion:
            if accion[0] == "volver":
                self.j._volver_al_menu()
                return
            if accion[0] == "cambiar":
                _, clave, direccion = accion
                self._aplicar_opcion(clave, direccion)

        self.j.renderer.pantalla_opciones()
        self.j.renderer.flip()

    def _cambiar_opcion(self, indice, aumentar):
        claves = ["duracion_ronda", "dificultad_ia", "volumen_musica", "volumen_sfx", "pantalla_completa"]
        if 0 <= indice < len(claves):
            self._aplicar_opcion(claves[indice], 1 if aumentar else -1)

    def _aplicar_opcion(self, clave, direccion):
        self.j.configuracion.siguiente(clave, direccion)
        if clave == "duracion_ronda":
            self.j.duracion_ronda = self.j.configuracion.obtener("duracion_ronda")
        elif clave == "volumen_musica":
            self.j.audio.set_volumen_musica(self.j.configuracion.obtener("volumen_musica"))
        elif clave == "volumen_sfx":
            self.j.audio.set_volumen_sfx(self.j.configuracion.obtener("volumen_sfx"))
        elif clave == "pantalla_completa":
            self.j._alternar_pantalla_completa()
        self.j.audio.clic()

    def pantalla_countdown(self, delta_tiempo):
        """Maneja la pantalla de countdown antes de iniciar la partida."""
        for evento in self.j.eventos_pendientes:
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                self.j._volver_al_menu()
                return

        self.j.countdown_timer += delta_tiempo

        if self.j.countdown_timer >= 1.0:
            self.j.countdown_timer = 0
            self.j.countdown_valor -= 1
            if self.j.countdown_valor <= 0:
                self.j.audio.inicio()
                self.j._mostrar_toast("¡A jugar!", self.j.config.COLOR_LIBRE)
                self.j.estado = EstadoJuego.JUGANDO
                return
            self.j.audio.beep()

        self.j.renderer.pantalla_countdown()
        self.j.renderer.flip()
