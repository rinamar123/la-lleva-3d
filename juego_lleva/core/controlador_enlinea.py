"""Controlador del modo en línea: conecta, sincroniza y renderiza la sala.

El controlador mantiene el estado local de la partida en línea. Un bucle
de fondo (``_bucle_sync``) intercambia snapshots con la sala a ~30 Hz y
aplica cada estado al ``juego``; el bucle de frames solo lee ese estado y
lo renderiza (predicción local del propio jugador e interpolación de los
rivales). Los eventos con ``seq`` del servidor se convierten en toasts.
"""

import asyncio
import math
import time
from collections import defaultdict, deque

import pygame
from juego_lleva.constantes_entrada import (
    K_a,
    K_d,
    K_DOWN,
    K_LEFT,
    K_RIGHT,
    K_s,
    K_SPACE,
    K_UP,
    K_w,
    K_ESCAPE,
    K_r,
    KEYDOWN,
)

from juego_lleva.models.jugador_humano import JugadorHumano
from juego_lleva.models.obstaculo import Obstaculo
from juego_lleva.models.power_up import PowerUp
from juego_lleva.views.jugador_view import JugadorView

from juego_lleva.red.sala import (
    FASE_COUNTDOWN,
    FASE_ESPERANDO,
    FASE_FIN,
    FASE_JUGANDO,
)

_MAX_EVENTOS_SALTO = 6
_ERRORES_MAX = 5
_MAX_DT_PREDICCION = 0.3
_RETARDO_INTERPOLACION = 0.08
_MUESTRAS_INTERPOLACION = 12
_DURACION_CORRECCION_LOCAL = 0.12
_MAX_CORRECCION_LOCAL = 120.0

_TECLAS_JUGADOR = {
    "arriba": K_w,
    "abajo": K_s,
    "izquierda": K_a,
    "derecha": K_d,
}

_CODIGOS_A_ACCION = {
    K_w: "arriba",
    K_s: "abajo",
    K_a: "izquierda",
    K_d: "derecha",
    K_UP: "arriba",
    K_DOWN: "abajo",
    K_LEFT: "izquierda",
    K_RIGHT: "derecha",
}


class ControladorEnLinea:
    """Maneja el flujo completo de una partida en línea."""

    FASE_CONECTANDO = "conectando"

    def __init__(self, juego, cliente=None):
        """Inicializa el controlador.

        Args:
            juego: Instancia principal del juego.
            cliente (optional): Cliente de sala inyectable (tests).
        """
        self.juego = juego
        if cliente is None:
            from juego_lleva.red.cliente_web import ClienteEnLinea

            cliente = ClienteEnLinea()
        self.cliente = cliente
        self.fase = self.FASE_CONECTANDO
        self.mi_id = None
        self.listo = False
        self.entrada = {
            "arriba": False,
            "abajo": False,
            "izquierda": False,
            "derecha": False,
        }
        self.snapshot = None
        self._tarea_sync = None
        self._detenido = False
        self._pedir_salir = False
        self._errores = 0
        self._intentos_unirse = 0
        self._proximo_intento = 0.0
        self._ultima_snapshot = 0.0
        self._ultima_seq_evento = 0
        self._prev = {}
        self._cur = {}
        self._t_prev = 0.0
        self._t_cur = 0.0
        self._sim_local = None
        self._t_pred = 0.0
        self._correccion_local = (0.0, 0.0)
        self._t_correccion_local = 0.0
        self._historial_posiciones = defaultdict(
            lambda: deque(maxlen=_MUESTRAS_INTERPOLACION)
        )

    def _config(self):
        """Devuelve la configuración del juego."""
        return self.juego.config

    # ------------------------------------------------------------------
    # Bucle de frames (invocado desde juego.procesar_frame_async)
    # ------------------------------------------------------------------

    async def actualizar(self, delta_tiempo):
        """Procesa un frame del modo en línea.

        Args:
            delta_tiempo (float): Tiempo transcurrido desde el último frame.
        """
        j = self.juego
        ahora = time.monotonic()

        if self._pedir_salir:
            j._salir_en_linea()
            return

        if self.fase == self.FASE_CONECTANDO:
            await self._intentar_unirse(ahora)
            return

        self.entrada = self._leer_entrada()

        if self.fase == FASE_ESPERANDO:
            self._gestionar_sala()
        elif self.fase == FASE_COUNTDOWN:
            self._gestionar_countdown()
        elif self.fase == FASE_JUGANDO:
            self._gestionar_juego(delta_tiempo)
        elif self.fase == FASE_FIN:
            self._gestionar_fin(delta_tiempo)

    def detener(self):
        """Detiene la sincronización y pide abandono a la sala."""
        self._detenido = True
        if self._tarea_sync is not None:
            self._tarea_sync.cancel()
            self._tarea_sync = None
        if not self.cliente.conectado:
            return
        try:
            tarea = asyncio.get_running_loop().create_task(self.cliente.salir())
        except RuntimeError:
            return
        tarea.add_done_callback(self._olvidar_credenciales)

    def _olvidar_credenciales(self, tarea):
        """Descarta el token cuando la petición de salida termina (o falla).

        Si se limpiara antes, ``salir()`` vería el token en ``None`` y la sala
        conservaría al jugador hasta el timeout de desconexión.
        """
        if not tarea.cancelled():
            tarea.exception()
        self.cliente.token = None
        self.cliente.mi_id = None

    # ------------------------------------------------------------------
    # Conexión
    # ------------------------------------------------------------------

    async def _intentar_unirse(self, ahora):
        """Pide un token a la sala y arranca el bucle de sincronización."""
        j = self.juego
        if ahora < self._proximo_intento:
            self._render_conectando("Conectando con la sala...")
            return
        try:
            respuesta = await self.cliente.unirse(j.nombres[0] if j.nombres else "J1")
        except Exception:
            respuesta = {"error": "sin_conexion"}

        if respuesta.get("ok"):
            self.mi_id = respuesta.get("id")
            self.fase = respuesta.get("fase", FASE_ESPERANDO)
            self.snapshot = None
            self._intentos_unirse = 0
            j.audio.clic()
            self._tarea_sync = asyncio.create_task(self._bucle_sync())
            return

        codigo = respuesta.get("error")
        if codigo == self.cliente.SALA_LLENA:
            j._mostrar_toast("La sala está llena", self._config().COLOR_DORADO)
            j._salir_en_linea()
            return
        if codigo == self.cliente.PARTIDA_EN_CURSO:
            j._mostrar_toast(
                "La partida ya comenzó, vuelve luego", self._config().COLOR_DORADO
            )
            j._salir_en_linea()
            return

        self._intentos_unirse += 1
        self._proximo_intento = ahora + (1.0 if self._intentos_unirse < 5 else 3.0)
        self._render_conectando(
            "Reintentando conexion..."
            if self._intentos_unirse > 1
            else "Conectando con la sala..."
        )

    # ------------------------------------------------------------------
    # Sincronización (bucle de fondo)
    # ------------------------------------------------------------------

    async def _bucle_sync(self):
        """Envía entrada y recibe snapshots a la frecuencia del cliente."""
        periodo = self.cliente.PERIODO_SYNC
        while not self._detenido:
            inicio = time.monotonic()
            try:
                respuesta = await self.cliente.sincronizar(self.entrada, self.listo)
            except Exception:
                respuesta = None
            if self._detenido:
                break
            if respuesta is None:
                self._registrar_error()
            elif "error" in respuesta:
                if respuesta["error"] == self.cliente.TOKEN_INVALIDO:
                    self._interrumpir("Conexion perdida con la sala")
                    break
                self._registrar_error()
            else:
                self._aplicar_snapshot(respuesta)
                self._errores = 0
            transcurrido = time.monotonic() - inicio
            espera = periodo - transcurrido
            if espera > 0:
                await asyncio.sleep(espera)

    def _registrar_error(self):
        """Acumula errores de red y aborta si son demasiados seguidos."""
        self._errores += 1
        self.juego._mostrar_toast("Reconectando...", self._config().COLOR_PLATA)
        if self._errores >= _ERRORES_MAX:
            self._interrumpir("Conexion perdida con la sala")

    def _interrumpir(self, mensaje):
        """Cancela la sincronización y pide volver al menú."""
        self.juego._mostrar_toast(mensaje, self._config().COLOR_LLEVA)
        if (
            self._tarea_sync is not None
            and self._tarea_sync is not asyncio.current_task()
        ):
            self._tarea_sync.cancel()
        self._tarea_sync = None
        self._detenido = True
        self._pedir_salir = True

    # ------------------------------------------------------------------
    # Aplicación del snapshot
    # ------------------------------------------------------------------

    def _aplicar_snapshot(self, respuesta):
        """Refleja un snapshot del servidor en el estado local del juego."""
        j = self.juego
        self.snapshot = respuesta
        self.fase = respuesta.get("fase", self.fase)
        self._ultima_snapshot = time.monotonic()
        if respuesta.get("mi_id") is not None:
            self.mi_id = respuesta["mi_id"]

        self._sincronizar_jugadores(respuesta.get("jugadores", []))
        self._sincronizar_entorno(respuesta)
        self._procesar_eventos(respuesta.get("eventos", []))

    def _sincronizar_jugadores(self, datos):
        """Crea/reutiliza los jugadores locales desde el snapshot."""
        j = self.juego
        existentes = {}
        for jugador, vista in zip(j.jugadores, j.jugadores_views):
            existentes[jugador.id] = (jugador, vista)

        instante = time.monotonic()
        self._t_prev = self._t_cur
        self._t_cur = instante

        jugadores = []
        vistas = []
        for dato in sorted(datos, key=lambda d: d["id"]):
            id_j = dato["id"]
            posicion_mostrada = None
            if id_j in existentes:
                jugador, vista = existentes[id_j]
                if id_j == self.mi_id:
                    posicion_mostrada = (jugador.x, jugador.y)
            else:
                jugador = JugadorHumano(
                    dato["x"],
                    dato["y"],
                    id_j,
                    dict(_TECLAS_JUGADOR),
                    dato.get("nombre"),
                )
                vista = JugadorView()
            self._aplicar_datos_jugador(jugador, dato)
            self._prev[id_j] = self._cur.get(id_j, (dato["x"], dato["y"]))
            self._cur[id_j] = (dato["x"], dato["y"])
            self._historial_posiciones[id_j].append(
                (instante, float(dato["x"]), float(dato["y"]))
            )
            if id_j == self.mi_id:
                if self._sim_local is None:
                    self._sim_local = JugadorHumano(
                        dato["x"],
                        dato["y"],
                        id_j,
                        dict(_TECLAS_JUGADOR),
                        dato.get("nombre"),
                    )
                self._aplicar_datos_jugador(self._sim_local, dato)
                if posicion_mostrada is not None:
                    dx = posicion_mostrada[0] - self._sim_local.x
                    dy = posicion_mostrada[1] - self._sim_local.y
                    if math.hypot(dx, dy) <= _MAX_CORRECCION_LOCAL:
                        self._correccion_local = (dx, dy)
                    else:
                        self._correccion_local = (0.0, 0.0)
                    self._t_correccion_local = instante
                else:
                    self._correccion_local = (0.0, 0.0)
                    self._t_correccion_local = instante
            jugadores.append(jugador)
            vistas.append(vista)

        self._t_pred = self._t_cur
        j.jugadores = jugadores
        j.jugadores_views = vistas
        presentes = {jugador.id for jugador in jugadores}
        for id_j in list(self._prev):
            if id_j not in presentes:
                self._prev.pop(id_j, None)
                self._cur.pop(id_j, None)
                self._historial_posiciones.pop(id_j, None)

    @staticmethod
    def _aplicar_datos_jugador(jugador, dato):
        """Copia el estado de un jugador del snapshot al objeto local."""
        jugador.nombre = dato.get("nombre", jugador.nombre)
        jugador.x = float(dato.get("x", jugador.x))
        jugador.y = float(dato.get("y", jugador.y))
        jugador.vx = float(dato.get("vx", 0.0))
        jugador.vy = float(dato.get("vy", 0.0))
        jugador.es_lleva = bool(dato.get("es_lleva", False))
        jugador.direccion_cara = int(dato.get("direccion_cara", jugador.direccion_cara))
        jugador.velocidad_abs = float(dato.get("velocidad_abs", 0.0))
        jugador.escudo = bool(dato.get("escudo", False))
        jugador.congelado = float(dato.get("congelado", 0.0))
        jugador.tropezando = float(dato.get("tropezando", 0.0))
        jugador.factor_velocidad = float(dato.get("factor_velocidad", 1.0))

    def _sincronizar_entorno(self, respuesta):
        """Copia obstáculos, power-ups, tiempos y efectos del snapshot."""
        j = self.juego
        j.gestor_modos.entorno.obstaculos = [
            self._a_obstaculo(o) for o in respuesta.get("obstaculos", [])
        ]
        j.power_ups = [
            PowerUp(p["x"], p["y"], p["tipo"]) for p in respuesta.get("power_ups", [])
        ]
        j.tiempo_ronda = float(respuesta.get("tiempo_ronda", 0.0))
        j.duracion_ronda = float(respuesta.get("duracion_ronda", j.duracion_ronda))
        j.puntaje_service.tiempos_lleva = {
            int(k): float(v) for k, v in respuesta.get("tiempos_lleva", {}).items()
        }
        j.efectos_activos = {
            int(k): {t: float(v) for t, v in timers.items()}
            for k, timers in respuesta.get("efectos_activos", {}).items()
        }

    @staticmethod
    def _a_obstaculo(dato):
        """Convierte un obstáculo del snapshot (dict u objeto) en Obstaculo."""
        if isinstance(dato, Obstaculo):
            return dato
        return Obstaculo(dato["x"], dato["y"], dato["tipo"])

    def _procesar_eventos(self, eventos):
        """Convierte eventos nuevos del servidor en feedback visual."""
        pendientes = [e for e in eventos if e.get("seq", 0) > self._ultima_seq_evento]
        if not pendientes:
            return
        pendientes.sort(key=lambda e: e.get("seq", 0))
        if pendientes[-1]["seq"] - self._ultima_seq_evento > _MAX_EVENTOS_SALTO:
            self._ultima_seq_evento = pendientes[-1]["seq"]
            return
        nombres = {jj.id: jj.nombre for jj in self.juego.jugadores}
        for evento in pendientes:
            self._ultima_seq_evento = evento["seq"]
            self._aplicar_evento(evento, nombres)

    def _aplicar_evento(self, evento, nombres):
        """Muestra un toast/efecto según el tipo de evento recibido."""
        j = self.juego
        tipo = evento.get("tipo")
        if tipo == "toque":
            a = nombres.get(evento.get("a"), f"J{evento.get('a', 0) + 1}")
            b = nombres.get(evento.get("b"), f"J{evento.get('b', 0) + 1}")
            j._mostrar_toast(f"{a} toco a {b}!", self._config().COLOR_LLEVA)
            j.toque_flash = 0.12
            j.audio.clic()
        elif tipo == "escudo":
            objetivo = nombres.get(evento.get("objetivo"), "Un jugador")
            j._mostrar_toast(
                f"¡{objetivo} bloqueo el toque!", self._config().COLOR_LIBRE
            )
            j.audio.beep()
        elif tipo == "power_up":
            etiquetas = {
                "velocidad": "¡velocidad!",
                "escudo": "¡escudo!",
                "congelar": "¡congelado!",
            }
            efecto = evento.get("efecto")
            objetivo = nombres.get(evento.get("objetivo"), "Un jugador")
            j._mostrar_toast(
                f"{objetivo} {etiquetas.get(efecto, 'power-up')}",
                self._config().COLOR_DORADO,
            )
            j.audio.beep()
        elif tipo == "fin":
            j._mostrar_toast("¡Fin de ronda!", self._config().COLOR_DORADO)
            j.audio.inicio()

    # ------------------------------------------------------------------
    # Entrada local
    # ------------------------------------------------------------------

    def _leer_entrada(self):
        """Combina teclado y táctil en el mapa de entrada del jugador."""
        teclas = pygame.key.get_pressed()
        activas = set()
        for codigo, accion in _CODIGOS_A_ACCION.items():
            if teclas[codigo]:
                activas.add(accion)
        for codigo in self.juego.tactil.teclas_activas():
            accion = _CODIGOS_A_ACCION.get(codigo)
            if accion:
                activas.add(accion)
        return {
            accion: accion in activas
            for accion in ("arriba", "abajo", "izquierda", "derecha")
        }

    # ------------------------------------------------------------------
    # Gestión por fase
    # ------------------------------------------------------------------

    def _gestionar_sala(self):
        """Maneja la sala de espera (fase esperando)."""
        j = self.juego
        accion = j.acciones_ui.detectar_sala(j.mouse_pos, j.click_realizado)
        if accion == "listo":
            self.listo = not self.listo
            j.audio.clic()
        elif accion == "salir":
            j._salir_en_linea()
            return

        for evento in j.eventos_pendientes:
            if evento.type == KEYDOWN:
                if evento.key in (K_r, K_SPACE):
                    self.listo = not self.listo
                    j.audio.clic()
                elif evento.key == K_ESCAPE:
                    j._salir_en_linea()
                    return

        j.interfaz.dibujar_sala(
            j.pantalla, self.snapshot, self.mi_id, self.listo, j.mouse_pos
        )
        j.renderer.flip()

    def _gestionar_countdown(self):
        """Muestra el countdown que envía el servidor."""
        j = self.juego
        if self.snapshot:
            valor = int(math.ceil(self.snapshot.get("cuenta_regresiva", 3)))
            j.countdown_valor = max(1, min(valor, 3))
        for evento in j.eventos_pendientes:
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                j._salir_en_linea()
                return
        j.renderer.pantalla_countdown()
        j.renderer.flip()

    def _gestionar_juego(self, delta_tiempo):
        """Renderiza la ronda en curso."""
        j = self.juego
        for evento in j.eventos_pendientes:
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                j._salir_en_linea()
                return
        self._actualizar_flash_toque(delta_tiempo)
        self._aplicar_posicion_mostrada()
        j.renderer.frame_juego(delta_tiempo)
        self._dibujar_indicador_red()
        j.renderer.flip()

    def _gestionar_fin(self, delta_tiempo):
        """Muestra el marcador de fin de ronda hasta la siguiente ronda."""
        j = self.juego
        for evento in j.eventos_pendientes:
            if evento.type == KEYDOWN and evento.key == K_ESCAPE:
                j._salir_en_linea()
                return
        self._actualizar_flash_toque(delta_tiempo)
        self._aplicar_posicion_mostrada()
        j.renderer.frame_juego(delta_tiempo)
        ganador = self.snapshot.get("ganador") if self.snapshot else None
        puntajes = {
            int(k): float(v)
            for k, v in (self.snapshot or {}).get("tiempos_lleva", {}).items()
        }
        j.interfaz.dibujar_fin_ronda(
            j.pantalla,
            ganador,
            puntajes,
            j.mouse_pos,
            j.jugadores,
            mostrar_botones=False,
            texto_hint="La siguiente ronda comienza pronto...   (ESC: salir)",
        )
        self._dibujar_indicador_red()
        j.renderer.flip()

    def _actualizar_flash_toque(self, delta_tiempo):
        """Decrementa el destello de toque y lo limita a cero en modo online."""
        self.juego.toque_flash = max(0.0, self.juego.toque_flash - delta_tiempo)

    # ------------------------------------------------------------------
    # Interpolación / predicción
    # ------------------------------------------------------------------

    def _aplicar_posicion_mostrada(self):
        """Predice al jugador local y suaviza el movimiento de los rivales."""
        j = self.juego
        ahora = time.monotonic()
        for jugador in j.jugadores:
            id_j = jugador.id
            actual = self._cur.get(id_j)
            if actual is None:
                continue
            anterior = self._prev.get(id_j)
            if id_j == self.mi_id:
                self._predecir_jugador_local(jugador, ahora)
            elif self._historial_posiciones.get(id_j):
                jugador.x, jugador.y = self._interpolar_posicion_remota(id_j, ahora)
            elif anterior is not None:
                jugador.x, jugador.y = actual
            else:
                jugador.x, jugador.y = actual

    def _interpolar_posicion_remota(self, id_j, ahora):
        """Interpola snapshots remotos en un instante ligeramente retrasado."""
        muestras = self._historial_posiciones[id_j]
        objetivo = ahora - _RETARDO_INTERPOLACION
        anterior = muestras[0]
        for actual in tuple(muestras)[1:]:
            if objetivo <= actual[0]:
                intervalo = actual[0] - anterior[0]
                if intervalo <= 1e-6:
                    return actual[1], actual[2]
                proporcion = min(1.0, max(0.0, (objetivo - anterior[0]) / intervalo))
                return (
                    anterior[1] + (actual[1] - anterior[1]) * proporcion,
                    anterior[2] + (actual[2] - anterior[2]) * proporcion,
                )
            anterior = actual
        return anterior[1], anterior[2]

    def _predecir_jugador_local(self, jugador, ahora):
        """Simula la física del jugador local desde el último snapshot.

        Replica la simulación del servidor (impulso, fricción, zonas lentas y
        límites de pantalla) a partir del estado autoritativo recibido y la
        entrada local: el jugador responde al instante y se re-baseiza en cada
        snapshot.
        """
        j = self.juego
        sim = self._sim_local
        if sim is None:
            return
        dt = min(_MAX_DT_PREDICCION, max(0.0, ahora - self._t_pred))
        if dt <= 0:
            jugador.x, jugador.y = sim.x, sim.y
            return
        presionadas = {
            codigo: self.entrada[accion] for accion, codigo in _TECLAS_JUGADOR.items()
        }
        en_zona = j.servicio_colision.jugador_en_zona_lenta(
            sim, j.gestor_modos.entorno.obstaculos
        )
        if sim.congelado <= 0:
            sim.mover(presionadas, en_zona, dt)
        for obstaculo in j.gestor_modos.entorno.obstaculos:
            if (
                obstaculo.tipo == "caja"
                and j.servicio_colision.detectar_colision_jugador_obstaculo(
                    sim, obstaculo
                )
            ):
                j.servicio_colision.resolver_obstaculo(sim, obstaculo)
        self._t_pred = ahora

        transcurrido = max(0.0, ahora - self._t_correccion_local)
        factor = math.exp(-transcurrido / _DURACION_CORRECCION_LOCAL)
        dx, dy = self._correccion_local
        dx *= factor
        dy *= factor
        self._correccion_local = (dx, dy)
        self._t_correccion_local = ahora
        jugador.x = min(
            max(0.0, sim.x + dx),
            self._config().ANCHO_PANTALLA - self._config().TAMAÑO_JUGADOR,
        )
        jugador.y = min(
            max(0.0, sim.y + dy),
            self._config().ALTO_PANTALLA - self._config().TAMAÑO_JUGADOR,
        )
        jugador.vx, jugador.vy = sim.vx, sim.vy
        jugador.direccion_cara = sim.direccion_cara
        jugador.velocidad_abs = sim.velocidad_abs

    def _dibujar_indicador_red(self):
        """Dibuja un punto que indica la frescura de la conexión."""
        j = self.juego
        fresco = time.monotonic() - self._ultima_snapshot < 1.0
        color = self._config().COLOR_LIBRE if fresco else self._config().COLOR_LLEVA
        cx = self._config().ANCHO_PANTALLA - 22
        cy = 110
        pygame.draw.circle(j.pantalla, (20, 20, 35), (cx, cy), 11)
        pygame.draw.circle(j.pantalla, color, (cx, cy), 8)
        pygame.draw.circle(j.pantalla, (255, 255, 255), (cx, cy), 8, 1)

    def _render_conectando(self, texto):
        """Pantalla mínima mientras se establece la conexión."""
        j = self.juego
        j.pantalla.fill(self._config().COLOR_FONDO)
        render = j.interfaz.fuente_subtitulo.render(texto, True, (255, 255, 255))
        j.pantalla.blit(
            render,
            (
                self._config().ANCHO_PANTALLA // 2 - render.get_width() // 2,
                self._config().ALTO_PANTALLA // 2 - render.get_height() // 2,
            ),
        )
        j.renderer.flip()
