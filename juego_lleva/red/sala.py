"""Sala en línea: registro de jugadores, fases de la ronda y hilo de simulación.

La sala es el corazón autoritativo del multijugador HTTP. Un único hilo
avanza las fases (esperando -> countdown -> jugando -> fin) a ~30 Hz y un
``threading.RLock`` protege todo el estado compartido. Los clientes solo
envían su entrada y leen el snapshot que construye ``sincronizar``.
"""

import secrets
import threading
import time
import traceback

from juego_lleva.core.config import Config
from juego_lleva.red.simulacion import (
    SimulacionRonda,
    aplicar_resolucion_web,
    restaurar_resolucion,
)

FPS_SIMULACION = 30
DURACION_COUNTDOWN = 3.0
DURACION_FIN = 10.0
TIMEOUT_DESCONEXION = 8.0
MAX_SYNC_POR_SEGUNDO = 60
NOMBRE_MAX = 12

FASE_ESPERANDO = "esperando"
FASE_COUNTDOWN = "countdown"
FASE_JUGANDO = "jugando"
FASE_FIN = "fin"


class JugadorEnLinea:
    """Estado de un jugador conectado a la sala."""

    def __init__(self, id_jugador, nombre, token, color="azul", accesorio="ninguno"):
        """Inicializa un jugador conectado."""
        self.id = id_jugador
        self.nombre = nombre
        self.color = color
        self.accesorio = accesorio
        self.token = token
        self.listo = False
        self.ultima_actividad = time.monotonic()
        self.entrada = {"arriba": False, "abajo": False,
                        "izquierda": False, "derecha": False}
        self._marcas_tasa = []


class SalaEnLinea:
    """Sala multijugador con fases de ronda y simulación en hilo propio."""

    def __init__(self, max_jugadores=3, duracion_ronda=None, iniciar_hilo=True):
        """Inicializa la sala, aplica la resolución web y arranca el hilo.

        Args:
            max_jugadores (int): Capacidad de la sala (2 a 16).
            duracion_ronda (float, optional): Duración de la ronda en segundos.
            iniciar_hilo (bool): False arranca la sala sin hilo propio, para
                que los tests controlen ``_tick`` manualmente.
        """
        if not (2 <= max_jugadores <= 16):
            raise ValueError("max_jugadores debe estar entre 2 y 16")
        self.max_jugadores = max_jugadores
        self.duracion_ronda = duracion_ronda or Config().DURACION_RONDA
        aplicar_resolucion_web()
        self._lock = threading.RLock()
        self.jugadores = []
        self._por_token = {}
        self._siguiente_id = 0
        self.fase = FASE_ESPERANDO
        self.cuenta_regresiva = 0.0
        self.victorias = {}
        self.sim = None
        self.tiempo_fin = 0.0
        self.cerrado = False
        self._seq_evento = 0
        self._hilo = None
        if iniciar_hilo:
            self._hilo = threading.Thread(target=self._bucle, daemon=True)
            self._hilo.start()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def unirse(self, nombre, color="azul", accesorio="ninguno"):
        """Registra un nuevo jugador y devuelve su token.

        Returns:
            dict: Datos de entrada a la sala, o un mensaje de error.
        """
        with self._lock:
            if self.cerrado:
                return {"error": "sala_cerrada"}
            if self.fase in (FASE_COUNTDOWN, FASE_JUGANDO):
                return {"error": "partida_en_curso"}
            if len(self.jugadores) >= self.max_jugadores:
                return {"error": "sala_llena"}
            nombre_libre = self._nombre_valido(nombre)
            token = secrets.token_hex(16)
            colores = {"azul", "rojo", "verde", "morado", "amarillo", "rosa", "negro", "blanco"}
            accesorios = {"ninguno", "gorra", "gafas", "mochila"}
            color = color if color in colores else "azul"
            accesorio = accesorio if accesorio in accesorios else "ninguno"
            jugador = JugadorEnLinea(self._siguiente_id, nombre_libre, token, color, accesorio)
            self._siguiente_id += 1
            self.jugadores.append(jugador)
            self._por_token[token] = jugador
            return {
                "ok": True,
                "token": token,
                "id": jugador.id,
                "nombre": jugador.nombre,
                "color": jugador.color,
                "accesorio": jugador.accesorio,
                "fase": self.fase,
                "max_jugadores": self.max_jugadores,
                "jugadores_online": len(self.jugadores),
            }

    def sincronizar(self, token, entrada=None, listo=None):
        """Procesa la entrada de un jugador y devuelve el snapshot.

        Args:
            token (str): Token del jugador.
            entrada (dict, optional): Mapa de teclas presionadas.
            listo (bool, optional): True si el jugador marca "Listo".

        Returns:
            dict: Snapshot de la sala, o {"error": ...} si el token no existe.
        """
        with self._lock:
            jugador = self._por_token.get(token)
            if jugador is None:
                return {"error": "token_invalido"}
            jugador.ultima_actividad = time.monotonic()
            if self._admitir_entrada(jugador):
                if isinstance(entrada, dict):
                    jugador.entrada.update({
                        accion: bool(entrada[accion])
                        for accion in ("arriba", "abajo", "izquierda", "derecha")
                        if isinstance(entrada.get(accion), bool)
                    })
                if isinstance(listo, bool):
                    jugador.listo = listo
            if self.sim is not None:
                self.sim.set_entrada(jugador.id, jugador.entrada)
            return self._snapshot(jugador)

    def salir(self, token):
        """Desconecta a un jugador.

        Returns:
            dict: {"ok": True} o {"error": ...} si el token no existe.
        """
        with self._lock:
            jugador = self._por_token.get(token)
            if jugador is None:
                return {"error": "token_invalido"}
            self._eliminar_jugador(jugador.id)
            return {"ok": True}

    def estado_publico(self):
        """Resumen de la sala para ``GET /api/sala`` (lectura bajo lock)."""
        with self._lock:
            return {
                "fase": self.fase,
                "jugadores_online": len(self.jugadores),
                "max_jugadores": self.max_jugadores,
                "nombres": [j.nombre for j in self.jugadores],
            }

    def cerrar(self):
        """Detiene el hilo de simulación y restaura la resolución original."""
        with self._lock:
            if self.cerrado:
                return
            self.cerrado = True
        if self._hilo is not None:
            self._hilo.join(timeout=2.0)
            if self._hilo.is_alive():
                print("aviso: el hilo de la sala no terminó; "
                      "se conserva la resolución web para no corromper la simulación")
                return
        restaurar_resolucion()

    # ------------------------------------------------------------------
    # Bucle de simulación
    # ------------------------------------------------------------------

    def _bucle(self):
        """Hilo principal: avanza la sala a ~30 Hz sin bloquear a los clientes.

        Cualquier error de la simulación se registra y el hilo sigue vivo:
        morir en silencio dejaría la sala sirviendo snapshots congelados.
        """
        ultimo_tick = time.monotonic()
        paso = 1.0 / FPS_SIMULACION
        while not self.cerrado:
            ahora = time.monotonic()
            dt = min(ahora - ultimo_tick, 0.25)
            ultimo_tick = ahora
            with self._lock:
                try:
                    self._tick(dt)
                except Exception:
                    traceback.print_exc()
                    time.sleep(0.05)
            espera = paso - (time.monotonic() - ahora)
            if espera > 0:
                time.sleep(min(espera, paso / 2))

    def _tick(self, delta_tiempo):
        """Avanza un paso de la sala según la fase actual.

        Se ejecuta en el hilo propio o de forma manual en los tests
        (debe llamarse siempre bajo el mismo lock).
        """
        self._expulsar_inactivos()

        if self.fase == FASE_ESPERANDO:
            self._iniciar_countdown_si_aplica()
        elif self.fase == FASE_COUNTDOWN:
            if len(self.jugadores) < 2:
                self._a_esperando()
            else:
                self.cuenta_regresiva -= delta_tiempo
                if self.cuenta_regresiva <= 0:
                    self._nueva_ronda()
        elif self.fase == FASE_JUGANDO:
            if self.sim is None:
                self._a_esperando()
                return
            try:
                self.sim.paso(delta_tiempo)
            finally:
                self._seq_evento = self.sim.seq_evento
            if self.sim.terminada:
                if self.sim.ganador is not None:
                    clave = str(self.sim.ganador)
                    self.victorias[clave] = self.victorias.get(clave, 0) + 1
                self.fase = FASE_FIN
                self.tiempo_fin = time.monotonic()
        elif self.fase == FASE_FIN:
            if len(self.jugadores) < 2:
                self._a_esperando()
            elif time.monotonic() - self.tiempo_fin >= DURACION_FIN:
                self._reiniciar_despues_de_fin()

    def _iniciar_countdown_si_aplica(self):
        """Inicia el countdown cuando hay al menos 2 jugadores y todos listos."""
        if self.fase != FASE_ESPERANDO:
            return
        if len(self.jugadores) >= 2 and all(j.listo for j in self.jugadores):
            self.fase = FASE_COUNTDOWN
            self.cuenta_regresiva = DURACION_COUNTDOWN

    def _nueva_ronda(self):
        """Crea una nueva simulación y pasa a la fase de juego."""
        nombres = {j.id: j.nombre for j in self.jugadores}
        self.sim = SimulacionRonda(nombres, duracion_ronda=self.duracion_ronda,
                                   seq_inicial=self._seq_evento)
        for jugador in self.jugadores:
            self.sim.set_entrada(jugador.id, jugador.entrada)
        self.fase = FASE_JUGANDO
        self.cuenta_regresiva = 0.0

    def _reiniciar_despues_de_fin(self):
        """Tras el fin, vuelve al countdown o a esperando según el cupo."""
        self.sim = None
        if len(self.jugadores) >= 2:
            self.fase = FASE_COUNTDOWN
            self.cuenta_regresiva = DURACION_COUNTDOWN
        else:
            self._a_esperando()

    def _a_esperando(self):
        """Vuelve a la sala, limpiando la ronda y los marcos de 'Listo'."""
        self.fase = FASE_ESPERANDO
        self.cuenta_regresiva = 0.0
        self.sim = None
        for jugador in self.jugadores:
            jugador.listo = False

    def _expulsar_inactivos(self):
        """Expulsa a los jugadores sin actividad reciente."""
        ahora = time.monotonic()
        for jugador in list(self.jugadores):
            if ahora - jugador.ultima_actividad > TIMEOUT_DESCONEXION:
                self._eliminar_jugador(jugador.id)

    def _eliminar_jugador(self, id_jugador):
        """Quita un jugador de la sala y reconcilia la simulación."""
        jugador = None
        for candidato in self.jugadores:
            if candidato.id == id_jugador:
                jugador = candidato
                break
        if jugador is None:
            return
        self.jugadores.remove(jugador)
        self._por_token.pop(jugador.token, None)
        self.victorias.pop(str(id_jugador), None)
        if self.sim is not None:
            self.sim.eliminar_jugador_id(id_jugador)
        if self.fase == FASE_COUNTDOWN and len(self.jugadores) < 2:
            self._a_esperando()
        elif self.fase == FASE_JUGANDO and len(self.jugadores) < 2:
            self._a_esperando()

    def _admitir_entrada(self, jugador):
        """Limita la tasa de sincronización por jugador.

        Returns:
            bool: True si debe aplicarse la entrada.
        """
        ahora = time.monotonic()
        jugador._marcas_tasa = [t for t in jugador._marcas_tasa if ahora - t < 1.0]
        if len(jugador._marcas_tasa) >= MAX_SYNC_POR_SEGUNDO:
            return False
        jugador._marcas_tasa.append(ahora)
        return True

    def _nombre_valido(self, nombre):
        """Limpia el nombre y evita duplicados añadiendo un sufijo."""
        nombre = (nombre or "").strip()[:NOMBRE_MAX]
        if not nombre:
            nombre = f"J{self._siguiente_id + 1}"
        existentes = {j.nombre for j in self.jugadores}
        if nombre not in existentes:
            return nombre
        base = nombre
        sufijo = 2
        while f"{base}{sufijo}" in existentes:
            sufijo += 1
        return f"{base}{sufijo}"

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def _snapshot(self, jugador):
        """Construye el snapshot completo para un cliente."""
        estado = {
            "tipo": "estado_partida",
            "fase": self.fase,
            "cuenta_regresiva": max(0.0, round(self.cuenta_regresiva, 2))
            if self.fase == FASE_COUNTDOWN else 0.0,
            "mi_id": jugador.id,
            "jugadores_online": len(self.jugadores),
            "max_jugadores": self.max_jugadores,
            "listos": {str(j.id): j.listo for j in self.jugadores},
            "victorias": dict(self.victorias),
            "duracion_ronda": self.duracion_ronda,
            "tiempo_ronda": 0.0,
            "jugadores": [self._datos_jugador(j) for j in self.jugadores],
            "obstaculos": [],
            "power_ups": [],
            "tiempos_lleva": {},
            "efectos_activos": {},
            "eventos": [],
            "ganador": None,
        }
        if self.sim is not None:
            estado.update(self.sim.estado_red())
            # La simulación no conoce a quien entró en la fase de fin, así que
            # la lista de conectados (con su "listo") manda sobre la suya.
            estado["jugadores"] = [self._datos_jugador(j) for j in self.jugadores]
        return estado

    def _datos_jugador(self, conectado):
        """Serializa un jugador conectado, tomando la posición de la simulación."""
        sim_jugador = self.sim.obtener_jugador(conectado.id) if self.sim else None
        if sim_jugador is not None:
            datos = self.sim.serializar_jugador(sim_jugador)
        else:
            datos = {
                "id": conectado.id,
                "nombre": conectado.nombre,
                "x": 0, "y": 0, "vx": 0, "vy": 0,
                "es_lleva": False, "direccion_cara": 1, "velocidad_abs": 0.0,
                "escudo": False, "congelado": 0.0, "tropezando": 0.0,
                "factor_velocidad": 1.0,
            }
        datos["nombre"] = conectado.nombre
        datos["color"] = conectado.color
        datos["accesorio"] = conectado.accesorio
        datos["listo"] = conectado.listo
        return datos