"""Simulación autoritativa y sin pygame de una ronda de La Lleva.

El servidor ejecuta aquí las reglas exactas del modo local (ver
``juego_lleva.core.controlador_partida``), pero sin depender de pygame:
los inputs llegan como mapas ``{arriba, abajo, izquierda, derecha: bool}``
por jugador y el resto de servicios se reutiliza tal cual.

Resolución: el servidor corre en un sistema de escritorio donde ``Config``
por defecto usa 1908x1080, pero los navegadores (pygbag) juegan a
1280x720. ``SalaEnLinea`` sobreescribe las constantes de clase
``Config.ANCHO_PANTALLA``/``ALTO_PANTALLA`` a ``WEB_ANCHO``/``WEB_ALTO``
antes de crear cualquier modelo, de modo que la simulación coincida con lo
que renderizan los clientes.
"""

import random

from juego_lleva.core.config import Config
from juego_lleva.models.entorno import Entorno
from juego_lleva.models.jugador_humano import JugadorHumano
from juego_lleva.servicios.colision import ColisionService
from juego_lleva.servicios.power_up_service import PowerUpService
from juego_lleva.servicios.puntaje import PuntajeService
from juego_lleva.servicios.ronda import RondaService

WEB_ANCHO = 1280
WEB_ALTO = 720

_TECLAS = {"arriba": 119, "abajo": 115, "izquierda": 97, "derecha": 100}

_SPAWNS = {
    2: [(300, 360), (980, 360)],
    3: [(300, 200), (640, 560), (980, 200)],
    4: [(300, 200), (980, 200), (300, 580), (980, 580)],
    5: [(220, 150), (500, 150), (780, 150), (1060, 150), (640, 570)],
    6: [(220, 150), (640, 150), (1060, 150), (220, 570), (640, 570), (1060, 570)],
    7: [(180, 150), (485, 150), (795, 150), (1100, 150), (180, 570), (640, 570), (1100, 570)],
    8: [(180, 150), (485, 150), (795, 150), (1100, 150), (180, 570), (485, 570), (795, 570), (1100, 570)],
    9: [(180, 130), (485, 130), (795, 130), (1100, 130), (180, 360), (485, 360), (795, 360), (1100, 360), (640, 590)],
    10: [(180, 130), (485, 130), (795, 130), (1100, 130), (180, 360), (485, 360), (795, 360), (1100, 360), (350, 590), (930, 590)],
    11: [(180, 130), (485, 130), (795, 130), (1100, 130), (180, 360), (485, 360), (795, 360), (1100, 360), (180, 590), (640, 590), (1100, 590)],
    12: [(180, 130), (485, 130), (795, 130), (1100, 130), (180, 360), (485, 360), (795, 360), (1100, 360), (180, 590), (485, 590), (795, 590), (1100, 590)],
    13: [(140, 130), (390, 130), (640, 130), (890, 130), (1140, 130), (140, 360), (390, 360), (640, 360), (890, 360), (1140, 360), (265, 590), (640, 590), (1015, 590)],
    14: [(140, 130), (390, 130), (640, 130), (890, 130), (1140, 130), (140, 360), (390, 360), (640, 360), (890, 360), (1140, 360), (140, 590), (390, 590), (890, 590), (1140, 590)],
    15: [(140, 130), (390, 130), (640, 130), (890, 130), (1140, 130), (140, 360), (390, 360), (640, 360), (890, 360), (1140, 360), (140, 590), (390, 590), (640, 590), (890, 590), (1140, 590)],
    16: [(140, 130), (390, 130), (640, 130), (890, 130), (1140, 130), (140, 360), (390, 360), (640, 360), (890, 360), (1140, 360), (140, 590), (390, 590), (640, 590), (890, 590), (1140, 590), (640, 490)],
}


_originales_resolucion = None
_usos_resolucion = 0


def aplicar_resolucion_web():
    """Fija la resolución de clase de ``Config`` a la versión web.

    Lleva un contador de usos: con varias salas solapadas solo la última en
    cerrar restaura, para no dejar ``Config`` a medias.

    Returns:
        tuple: (ancho_original, alto_original) capturados en la primera
            aplicación.
    """
    global _originales_resolucion, _usos_resolucion
    if _usos_resolucion == 0:
        _originales_resolucion = (Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA)
        Config.ANCHO_PANTALLA = WEB_ANCHO
        Config.ALTO_PANTALLA = WEB_ALTO
    _usos_resolucion += 1
    return _originales_resolucion


def restaurar_resolucion():
    """Restaura la resolución previa de clase de ``Config``.

    Cada ``aplicar_resolucion_web`` debe emparejarse con una llamada; solo la
    que deja el contador a 0 restaura de verdad.
    """
    global _originales_resolucion, _usos_resolucion
    if _usos_resolucion == 0:
        return
    _usos_resolucion -= 1
    if _usos_resolucion > 0:
        return
    Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA = _originales_resolucion
    _originales_resolucion = None


def entradas_vacias():
    """Devuelve un mapa de entrada por defecto (sin teclas presionadas)."""
    return {"arriba": False, "abajo": False, "izquierda": False, "derecha": False}


class SimulacionRonda:
    """Replica headless de la lógica de una ronda para N jugadores."""

    def __init__(self, nombres, duracion_ronda=None, semilla=None,
                 seq_inicial=0):
        """Inicializa la simulación con los jugadores indicados.

        Args:
            nombres (dict): Mapeo id (int) -> nombre (str).
            duracion_ronda (float, optional): Duración en segundos. Por
                defecto usa ``Config.DURACION_RONDA``.
            semilla (int, optional): Semilla aleatoria para que los tests
                sean deterministas.
            seq_inicial (int, optional): Última ``seq`` usada por la ronda
                anterior, para que la secuencia no vuelva a empezar en 0.
        """
        if semilla is not None:
            random.seed(semilla)
        self.config = Config()
        self.duracion_ronda = duracion_ronda or self.config.DURACION_RONDA
        self.entradas = {id_: entradas_vacias() for id_ in nombres}
        self.jugadores = []

        id_ordenados = sorted(nombres)
        posiciones = _SPAWNS.get(len(id_ordenados), _SPAWNS[4])
        for indice, id_ in enumerate(id_ordenados):
            x, y = posiciones[indice % len(posiciones)]
            self.jugadores.append(JugadorHumano(x, y, id_, dict(_TECLAS), nombres[id_]))

        self.entorno = Entorno()
        self.entorno.generar_obstaculos(self.jugadores)
        self.puntaje = PuntajeService()
        self.ronda = RondaService(self.puntaje)
        self.colision = ColisionService()
        self.power_up_service = PowerUpService(self.config)
        self.power_ups = []
        self.power_up_timer = 0.0
        self.efectos_activos = {}
        self.tiempo_ronda = 0.0
        self.tiempo_inicio_lleva = 0.0
        self.terminada = False
        self.ganador = None
        self.eventos = []
        self._seq_evento = seq_inicial
        self.ronda.asignar_lleva_inicial(self.jugadores, random.choice(id_ordenados))

    @property
    def seq_evento(self):
        """Última secuencia emitida por esta simulación."""
        return self._seq_evento

    def obtener_jugador(self, id_jugador):
        """Devuelve el jugador con el id dado o None si no está."""
        for jugador in self.jugadores:
            if jugador.id == id_jugador:
                return jugador
        return None

    def set_entrada(self, id_jugador, entrada):
        """Almacena la entrada más reciente de un jugador.

        Args:
            id_jugador (int): Identificador del jugador.
            entrada (dict): Mapa con teclas opcionales (bool).
        """
        if id_jugador not in self.entradas:
            return
        for accion in ("arriba", "abajo", "izquierda", "derecha"):
            valor = entrada.get(accion)
            if isinstance(valor, bool):
                self.entradas[id_jugador][accion] = valor

    def _presionadas(self, id_jugador):
        """Traduce la entrada de un jugador a un mapa código -> bool."""
        entrada = self.entradas.get(id_jugador, entradas_vacias())
        return {_TECLAS[accion]: bool(entrada[accion]) for accion in _TECLAS}

    def pasos(self, segundos):
        """Avanza la simulación en pasos fijos de un frame."""
        dt = 1.0 / 30
        restante = segundos
        while restante > 0 and not self.terminada:
            self.paso(min(dt, restante))
            restante -= dt

    def paso(self, delta_tiempo):
        """Ejecuta un paso completo de la ronda (un frame)."""
        if self.terminada:
            return

        obstaculos = self.entorno.obstaculos
        self._actualizar_power_ups(delta_tiempo)
        self._actualizar_efectos_activos(delta_tiempo)

        for jugador in self.jugadores:
            if self.efectos_activos.get(jugador.id, {}).get("congelar", 0) > 0:
                continue
            en_zona = self.colision.jugador_en_zona_lenta(jugador, obstaculos)
            jugador.mover(self._presionadas(jugador.id), en_zona,
                          delta_tiempo, obstaculos=obstaculos)

        for jugador in self.jugadores:
            for obs in obstaculos:
                if obs.tipo == "caja" and self.colision.detectar_colision_jugador_obstaculo(jugador, obs):
                    self.colision.resolver_obstaculo(jugador, obs)

        colisiones = self.colision.detectar_colisiones(self.jugadores, delta_tiempo)
        for j1, j2 in colisiones:
            self._procesar_colision(j1, j2)
            self.colision.separar_jugadores(j1, j2, self.config.TAMAÑO_JUGADOR)

        self.tiempo_ronda += delta_tiempo
        if self.tiempo_ronda >= self.duracion_ronda:
            self._finalizar()

    def _actualizar_efectos_activos(self, delta_tiempo):
        """Decrementa los temporizadores de efectos y revierte los vencidos."""
        vencidos = []
        for id_jugador, timers in list(self.efectos_activos.items()):
            for tipo in list(timers):
                timers[tipo] -= delta_tiempo
                if timers[tipo] <= 0:
                    vencidos.append((id_jugador, tipo))
                    del timers[tipo]
            if not timers:
                del self.efectos_activos[id_jugador]

        for id_jugador, tipo in vencidos:
            jugador = self.obtener_jugador(id_jugador)
            if jugador is None:
                continue
            if tipo == "velocidad":
                jugador.factor_velocidad = 1.0
            elif tipo == "congelar":
                jugador.congelado = 0.0

    def _actualizar_power_ups(self, delta_tiempo):
        """Genera, envejece y recolecta power-ups durante la ronda."""
        self.power_up_timer += delta_tiempo
        if self.power_up_timer >= self.config.POWER_UP_FRECUENCIA_SEG:
            self.power_up_timer = 0
            nuevo = self.power_up_service.crear(self.jugadores, self.power_ups)
            if nuevo:
                self.power_ups.append(nuevo)

        for pu in self.power_ups:
            pu.vida -= delta_tiempo

        for jugador in self.jugadores:
            rect_jugador = jugador.obtener_rectangulo()
            for pu in list(self.power_ups):
                if rect_jugador.colliderect(pu.obtener_rectangulo()):
                    self._recoger_power_up(jugador, pu)
                    self.power_ups.remove(pu)

        self.power_ups = [pu for pu in self.power_ups if not pu.expirado()]

    def _recoger_power_up(self, jugador, power_up):
        """Aplica el efecto de un power-up recogido, eligiendo un rival."""
        rivales = [j for j in self.jugadores if j.id != jugador.id]
        rival = random.choice(rivales) if rivales else None
        efecto = self.power_up_service.efecto(jugador, rival, power_up.tipo)
        if not efecto:
            return
        id_objetivo, tipo, duracion = efecto
        objetivo = self.obtener_jugador(id_objetivo) or jugador

        if tipo == "velocidad":
            objetivo.factor_velocidad = self.config.FACTOR_VELOCIDAD_POWER
            self.efectos_activos.setdefault(id_objetivo, {})["velocidad"] = duracion
        elif tipo == "congelar":
            self.efectos_activos.setdefault(id_objetivo, {})["congelar"] = duracion
            objetivo.congelado = duracion
        elif tipo == "escudo":
            objetivo.escudo = True

        self._agregar_evento("power_up", x=power_up.x, y=power_up.y,
                             objetivo=id_objetivo, efecto=tipo)

    def _procesar_colision(self, j1, j2):
        """Procesa la colisión entre dos jugadores."""
        if j1.es_lleva:
            if getattr(j2, "escudo", False):
                self._romper_escudo(j2, j1)
            else:
                self._transferir_lleva(j1, j2)
        elif j2.es_lleva:
            if getattr(j1, "escudo", False):
                self._romper_escudo(j1, j2)
            else:
                self._transferir_lleva(j2, j1)

    def _romper_escudo(self, protegido, llevador):
        """Consume el escudo de un jugador y bloquea el toque."""
        protegido.escudo = False
        x1, y1 = llevador.obtener_posicion()
        x2, y2 = protegido.obtener_posicion()
        self._agregar_evento("escudo", x=(x1 + x2) / 2, y=(y1 + y2) / 2,
                             objetivo=protegido.id)

    def _transferir_lleva(self, quien_tiene, quien_recibe):
        """Transfiere el rol de 'La Lleva' al jugador tocado."""
        self.tiempo_inicio_lleva = self.ronda.transferir_lleva(
            quien_tiene, quien_recibe, self.tiempo_ronda, self.tiempo_inicio_lleva)
        quien_recibe.tropezando = self.config.DURACION_TROPIEZO
        self._agregar_evento("toque", x=(quien_tiene.x + quien_recibe.x) / 2,
                             y=(quien_tiene.y + quien_recibe.y) / 2,
                             a=quien_tiene.id, b=quien_recibe.id)

    def _agregar_evento(self, tipo, **campos):
        """Registra un evento con su número de secuencia global."""
        self._seq_evento += 1
        self.eventos.append({"seq": self._seq_evento, "tipo": tipo, **campos})
        if len(self.eventos) > 30:
            self.eventos = self.eventos[-30:]

    def _finalizar(self):
        """Finaliza la ronda actual y determina el ganador."""
        self.ronda.cerrar_lleva_actual(
            self.jugadores, self.tiempo_ronda, self.tiempo_inicio_lleva)
        self.ganador = self.puntaje.obtener_ganador()
        self.terminada = True
        self._agregar_evento("fin", ganador=self.ganador)

    def reiniciar(self):
        """Prepara una nueva ronda en la misma sala."""
        self.puntaje.reiniciar()
        self.power_ups.clear()
        self.power_up_timer = 0.0
        self.efectos_activos.clear()
        self.entradas = {j.id: entradas_vacias() for j in self.jugadores}
        id_ordenados = sorted(j.id for j in self.jugadores)
        posiciones = _SPAWNS.get(len(id_ordenados), _SPAWNS[4])
        for indice, id_ in enumerate(id_ordenados):
            jugador = self.obtener_jugador(id_)
            x, y = posiciones[indice % len(posiciones)]
            jugador.x, jugador.y = x, y
            jugador.vx = jugador.vy = 0.0
            jugador.escudo = False
            jugador.factor_velocidad = 1.0
            jugador.congelado = 0.0
            jugador.tropezando = 0.0
        self.entorno.generar_obstaculos(self.jugadores)
        self.ronda.asignar_lleva_inicial(self.jugadores, random.choice(id_ordenados))
        self.tiempo_ronda = 0.0
        self.tiempo_inicio_lleva = 0.0
        self.terminada = False
        self.ganador = None
        self.eventos = []
        self.colision.limpiar_cooldown()

    def eliminar_jugador_id(self, id_jugador):
        """Quita un jugador de la simulación, transfiriendo la lleva si la tenía."""
        jugador = self.obtener_jugador(id_jugador)
        if jugador is None:
            return
        if jugador.es_lleva:
            restantes = [j for j in self.jugadores if j.id != id_jugador]
            if restantes:
                receptor = random.choice(restantes)
                self.tiempo_inicio_lleva = self.ronda.transferir_lleva(
                    jugador, receptor, self.tiempo_ronda, self.tiempo_inicio_lleva)
        self.jugadores.remove(jugador)
        self.entradas.pop(id_jugador, None)

    def serializar_jugador(self, jugador):
        """Convierte un jugador en un dict serializable para el snapshot."""
        return {
            "id": jugador.id,
            "nombre": jugador.nombre,
            "x": round(jugador.x, 1),
            "y": round(jugador.y, 1),
            "vx": round(jugador.vx, 1),
            "vy": round(jugador.vy, 1),
            "es_lleva": jugador.es_lleva,
            "direccion_cara": jugador.direccion_cara,
            "velocidad_abs": round(jugador.velocidad_abs, 1),
            "escudo": jugador.escudo,
            "congelado": round(jugador.congelado, 2),
            "tropezando": round(jugador.tropezando, 2),
            "factor_velocidad": jugador.factor_velocidad,
        }

    def estado_red(self):
        """Devuelve el estado actual de la partida como dict JSON-serializable."""
        return {
            "tiempo_ronda": round(self.tiempo_ronda, 2),
            "duracion_ronda": self.duracion_ronda,
            "jugadores": [self.serializar_jugador(j)
                          for j in sorted(self.jugadores, key=lambda j: j.id)],
            "obstaculos": [{"x": o.x, "y": o.y, "tipo": o.tipo}
                           for o in self.entorno.obstaculos],
            "power_ups": [{"x": pu.x, "y": pu.y, "tipo": pu.tipo,
                           "vida": round(pu.vida, 2)} for pu in self.power_ups],
            "tiempos_lleva": {str(k): round(v, 1)
                              for k, v in self.puntaje.tiempos_lleva.items()},
            "efectos_activos": {str(k): {t: round(v, 2) for t, v in timers.items()}
                                for k, timers in self.efectos_activos.items()},
            "eventos": self.eventos[-12:],
            "ganador": self.ganador,
        }