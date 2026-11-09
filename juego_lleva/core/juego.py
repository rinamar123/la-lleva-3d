"""Módulo principal del juego que orquesta todos los componentes MVC."""

import pygame
from juego_lleva.constantes_entrada import (
    QUIT, MOUSEBUTTONDOWN, KEYDOWN, K_F11, K_m,
    FINGERDOWN, FINGERMOTION, FINGERUP,
)
from juego_lleva.controles.tactil import ControladorTactil
from juego_lleva.models.jugador_humano import JugadorHumano
from juego_lleva.models.jugador_ia import JugadorIA
from juego_lleva.servicios.audio import ServicioAudio
from juego_lleva.servicios.colision import ColisionService
from juego_lleva.servicios.configuracion import ConfiguracionService
from juego_lleva.servicios.power_up_service import PowerUpService
from juego_lleva.servicios.puntaje import PuntajeService
from juego_lleva.servicios.ranking import RankingService
from juego_lleva.servicios.ronda import RondaService
from juego_lleva.servicios.efecto_service import EfectoService
from juego_lleva.servicios.particula_service import ParticulaService
from juego_lleva.ui.interfaz import Interfaz
from juego_lleva.ui.acciones import AccionesUI

from juego_lleva.core.config import Config
from juego_lleva.core.estado import EstadoJuego
from juego_lleva.core.gestor_modos import GestorModos
from juego_lleva.core.controlador_menu import ControladorMenu
from juego_lleva.core.controlador_partida import ControladorPartida
from juego_lleva.core.controlador_enlinea import ControladorEnLinea
from juego_lleva.core.controlador_pantallas import ControladorPantallas
from juego_lleva.core.renderer import Renderer

from juego_lleva.views.jugador_view import JugadorView
from juego_lleva.views.entorno_view import EntornoView
from juego_lleva.views.efecto_view import EfectoView
from juego_lleva.views.power_up_view import PowerUpView
from juego_lleva.views.tactil_view import TactilView


class Juego:
    """Clase principal que orquesta el juego completo."""

    def __init__(self, config):
        """Inicializa el juego con la configuración especificada."""
        self.config = config
        self.pantalla = pygame.display.set_mode(
            (config.ANCHO_PANTALLA, config.ALTO_PANTALLA))
        pygame.display.set_caption("La Lleva - Juego Tradicional Colombiano")
        self.reloj = pygame.time.Clock()
        self.interfaz = Interfaz()
        self.acciones_ui = AccionesUI()
        self.tactil = ControladorTactil(
            config.ANCHO_PANTALLA, config.ALTO_PANTALLA,
            visible=config.PLATAFORMA_WEB)
        self.tactil_view = TactilView()
        self.configuracion = ConfiguracionService(config.SETTINGS_PATH)
        self.duracion_ronda = self.configuracion.obtener("duracion_ronda")
        self.puntaje_service = PuntajeService()
        self.servicio_colision = ColisionService()
        self.ranking_service = RankingService(config.RANKING_PATH)
        self.ronda_service = RondaService(self.puntaje_service)
        self.power_up_service = PowerUpService(config)
        self.efecto_service = EfectoService()
        self.particula_service = ParticulaService()
        self.particulas_rastro = {}
        self.audio = ServicioAudio()
        self.audio.set_volumen_sfx(self.configuracion.obtener("volumen_sfx"))
        self.audio.set_volumen_musica(self.configuracion.obtener("volumen_musica"))
        self.musica_activa = True
        if self.configuracion.obtener("pantalla_completa"):
            self._alternar_pantalla_completa()
        self.modo = "dos_jugadores"
        self.gestor_modos = GestorModos()
        self.jugadores = []
        self.jugadores_views = []
        self.entorno_view = EntornoView()
        self.efecto_view = EfectoView()
        self.efectos = []
        self.power_up_view = PowerUpView()
        self.power_ups = []
        self.power_up_timer = 0
        self.efectos_activos = {}
        self.tiempo_ronda = 0
        self.estado = EstadoJuego.MENU
        self.opcion_activa = 0
        self.opcion_menu = 0
        self.toasts = []
        self.tiempo_inicio_lleva = 0
        self.fade_alpha = 0
        self.mouse_pos = None
        self.click_realizado = False
        self.tiempo_anterior = 0
        self.eventos_pendientes = []
        self.countdown_valor = 3
        self.countdown_timer = 0
        self.nombres = ["J1", "J2"]
        self.nombre_activo = 0
        self.fondo = self._cargar_fondo()
        self._ranking_registrado = False
        self.toque_flash = 0.0
        self.tiempo_pasos = 0.0

        # Controladores y renderer delegados
        self.renderer = Renderer(self)
        self.ctrl_menu = ControladorMenu(self)
        self.ctrl_partida = ControladorPartida(self)
        self.ctrl_pantallas = ControladorPantallas(self)
        self.ctrl_enlinea = None

    def _cargar_fondo(self):
        """Carga la imagen de fondo del juego."""
        try:
            imagen = pygame.image.load(self.config.FONDO).convert()
            return pygame.transform.scale(imagen, (self.config.ANCHO_PANTALLA, self.config.ALTO_PANTALLA))
        except (pygame.error, OSError):
            return None

    def _alternar_pantalla_completa(self):
        """Alterna entre modo ventana y pantalla completa."""
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

    def _gestionar_musica(self):
        """Inicia o detiene la música según la preferencia del jugador."""
        if not self.audio.activo:
            return
        if self.musica_activa and not self.audio.musica_suena():
            self.audio.reproducir_musica()
        elif not self.musica_activa and self.audio.musica_suena():
            self.audio.detener_musica()

    def ejecutar(self):
        """Ejecuta el bucle principal del juego."""
        self.tiempo_anterior = pygame.time.get_ticks() / 1000.0
        while True:
            self._procesar_frame()

    def _capturar_entrada(self):
        """Lee eventos, mouse y audio del frame y devuelve el delta de tiempo."""
        tiempo_actual = pygame.time.get_ticks() / 1000.0
        delta_tiempo = tiempo_actual - self.tiempo_anterior
        self.tiempo_anterior = tiempo_actual

        self.mouse_pos = pygame.mouse.get_pos()
        self.click_realizado = False
        self.eventos_pendientes = []

        for evento in pygame.event.get():
            if evento.type == QUIT:
                pygame.quit()
                import sys
                sys.exit()
            if evento.type == MOUSEBUTTONDOWN and evento.button == 1:
                self.click_realizado = True
            if evento.type in (FINGERDOWN, FINGERMOTION, FINGERUP):
                if self.config.PLATAFORMA_WEB and evento.type == FINGERDOWN:
                    self.click_realizado = True
                    self.mouse_pos = (int(evento.x * self.config.ANCHO_PANTALLA),
                                      int(evento.y * self.config.ALTO_PANTALLA))
                self.tactil.procesar_evento(evento)
            if evento.type == KEYDOWN:
                if evento.key == K_F11:
                    self._alternar_pantalla_completa()
                    self.configuracion.establecer(
                        "pantalla_completa", bool(pygame.display.is_fullscreen()))
                elif evento.key == K_m and self.estado != EstadoJuego.NOMBRES:
                    self.musica_activa = not self.musica_activa
            self.eventos_pendientes.append(evento)

        self.interfaz.actualizar(delta_tiempo)
        self._gestionar_musica()
        if self.toasts:
            self.toasts = self.interfaz.actualizar_toasts(self.toasts, delta_tiempo)
        return delta_tiempo

    def _dispatch_estado(self, delta_tiempo):
        """Delega el frame según el estado actual del juego."""
        if self.estado == EstadoJuego.MENU:
            self.ctrl_menu.menu_principal()
        elif self.estado == EstadoJuego.NOMBRES:
            self.ctrl_menu.pantalla_nombres()
        elif self.estado == EstadoJuego.JUGANDO:
            self._bucle_juego(delta_tiempo)
        elif self.estado == EstadoJuego.PAUSA:
            self.ctrl_pantallas.pantalla_pausa()
        elif self.estado == EstadoJuego.FIN_RONDA:
            self.ctrl_pantallas.pantalla_fin_ronda()
        elif self.estado == EstadoJuego.AYUDA:
            self.ctrl_menu.pantalla_ayuda()
        elif self.estado == EstadoJuego.COUNTDOWN:
            self.ctrl_menu.pantalla_countdown(delta_tiempo)
        elif self.estado == EstadoJuego.RANKING:
            self.ctrl_menu.pantalla_ranking()
        elif self.estado == EstadoJuego.OPCIONES:
            self.ctrl_menu.pantalla_opciones()
        elif self.estado == EstadoJuego.EN_LINEA:
            # La sala en línea es solo de la versión web; el escritorio redirige
            # al navegador. Esta red evita que el bucle síncrono se quede mudo.
            self._volver_al_menu()
            self._mostrar_toast(
                "El modo en linea se juega en el navegador", self.config.COLOR_DORADO)

    def _finalizar_frame(self, delta_tiempo):
        """Aplica el fundido si está activo; los toasts los pinta Renderer.flip."""
        if self.fade_alpha > 0:
            self.fade_alpha = max(
                0, self.fade_alpha - delta_tiempo * 255 / self.config.DURACION_FUNDIDO_SEG)
            self.renderer.fade()
            self.renderer.flip()

    def _procesar_frame(self):
        """Procesa un frame completo del juego (escritorio)."""
        delta_tiempo = self._capturar_entrada()
        self._dispatch_estado(delta_tiempo)
        self._finalizar_frame(delta_tiempo)

    async def procesar_frame_async(self):
        """Procesa un frame completo del juego (web, con soporte asíncrono)."""
        delta_tiempo = self._capturar_entrada()
        if self.estado == EstadoJuego.EN_LINEA:
            if self.ctrl_enlinea is not None:
                await self.ctrl_enlinea.actualizar(delta_tiempo)
            else:
                self._salir_en_linea()
        else:
            self._dispatch_estado(delta_tiempo)
        self._finalizar_frame(delta_tiempo)

    def _mostrar_toast(self, texto, color=None):
        """Muestra una notificación breve en pantalla."""
        if len(self.toasts) >= 4:
            self.toasts.pop(0)
        self.toasts.append({
            'texto': texto,
            'color': color or (255, 255, 255),
            'tiempo': 0.0,
            'duracion': 2.5,
        })

    def _bucle_juego(self, delta_tiempo):
        """Ejecuta el bucle principal de juego delegando lógica y renderizado."""
        termino_ronda = self.ctrl_partida.actualizar(delta_tiempo)
        if termino_ronda:
            return
        self.renderer.frame_juego(delta_tiempo)
        self.renderer.flip()

    def _iniciar_partida(self):
        """Prepara y arranca una partida."""
        if self.modo == "en_linea":
            self._iniciar_partida_en_linea()
            return
        self._normalizar_nombres()
        self.toasts.clear()
        if self.modo == "un_jugador":
            self.gestor_modos.iniciar_un_jugador(self, self.nombres[0] if self.nombres else "J1")
        else:
            self.gestor_modos.iniciar_multijugador(self, self.nombres)
        self._aplicar_dificultad_ia()
        self._ranking_registrado = False
        self.efectos.clear()
        self.power_ups.clear()
        self.power_up_timer = 0
        self.efectos_activos.clear()
        self.particulas_rastro.clear()
        for jugador in self.jugadores:
            jugador.escudo = False
            jugador.factor_velocidad = 1.0
            jugador.congelado = 0.0
        self.estado = EstadoJuego.COUNTDOWN
        self.countdown_valor = 3
        self.countdown_timer = 0
        self.fade_alpha = 255
        self.audio.beep()

    def _normalizar_nombres(self):
        """Ajusta los nombres de los jugadores antes de iniciar."""
        cantidad = len(self.nombres)
        for i in range(cantidad):
            nombre = (self.nombres[i] or "").strip()
            if not nombre:
                nombre = f"J{i + 1}"
            self.nombres[i] = nombre[:12]

    def _iniciar_partida_en_linea(self):
        """Prepara el modo en línea con el nombre escrito."""
        nombre = (self.nombres[0] if self.nombres else "").strip() or "J1"
        self.nombres = [nombre[:12]]
        self.jugadores.clear()
        self.jugadores_views.clear()
        self.efectos.clear()
        self.power_ups.clear()
        self.power_up_timer = 0
        self.efectos_activos.clear()
        self.particulas_rastro.clear()
        self.toasts.clear()
        self.tiempo_ronda = 0
        self.tiempo_inicio_lleva = 0
        self.ctrl_enlinea = ControladorEnLinea(self)
        self.estado = EstadoJuego.EN_LINEA
        self.interfaz.en_linea = True
        self.fade_alpha = 255

    def _salir_en_linea(self):
        """Abandona la sala en línea y vuelve al menú."""
        if self.ctrl_enlinea is not None:
            self.ctrl_enlinea.detener()
            self.ctrl_enlinea = None
        self._volver_al_menu()

    def _aplicar_dificultad_ia(self):
        """Aplica la dificultad seleccionada al jugador controlado por IA."""
        nivel = self.configuracion.obtener("dificultad_ia")
        parametros = self.config.DIFICULTADES.get(nivel, self.config.DIFICULTADES["normal"])
        for jugador in self.jugadores:
            if isinstance(jugador, JugadorIA):
                jugador.velocidad_ia = parametros["VELOCIDAD_IA"]
                jugador.variacion_ia = parametros["VARIACION_IA"]
                jugador.factor_ia_huyendo = parametros["FACTOR_IA_HUYENDO"]
                jugador.tiempo_reaccion = parametros.get("TIEMPO_REACCION", 0.2)

    def _volver_al_menu(self):
        """Vuelve al menú principal limpiando el estado de la partida."""
        self.estado = EstadoJuego.MENU
        self.jugadores.clear()
        self.jugadores_views.clear()
        self.tiempo_ronda = 0
        self.tiempo_inicio_lleva = 0
        self.efectos.clear()
        self.power_ups.clear()
        self.efectos_activos.clear()
        self.particulas_rastro.clear()
        self.toasts.clear()
        self.interfaz.en_linea = False
        self.fade_alpha = 255
        self._ranking_registrado = False

    def crear_jugador(self, x, y, id_jugador, teclas=None, nombre=None):
        """Crea un nuevo jugador y su vista correspondiente."""
        jugador = JugadorHumano(x, y, id_jugador, teclas, nombre)
        jugador_view = JugadorView()
        self.jugadores.append(jugador)
        self.jugadores_views.append(jugador_view)
        return jugador

    def crear_jugador_ia(self, x, y, id_jugador, nombre="IA"):
        """Crea un jugador controlado por IA y su vista correspondiente."""
        jugador = JugadorIA(x, y, id_jugador, nombre)
        jugador.jugadores = self.jugadores
        jugador_view = JugadorView()
        self.jugadores.append(jugador)
        self.jugadores_views.append(jugador_view)
        return jugador

    def set_lleva_inicial(self, id_jugador):
        """Establece qué jugador tiene la pelota inicialmente."""
        self.ronda_service.asignar_lleva_inicial(self.jugadores, id_jugador)
        self.tiempo_inicio_lleva = 0
        self.servicio_colision.limpiar_cooldown()
