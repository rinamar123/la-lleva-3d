"""Modelo que representa a un jugador controlado por la computadora."""

import math
import random

from juego_lleva.models.jugador import Jugador


class JugadorIA(Jugador):
    """Clase que representa a un jugador controlado por IA."""

    def __init__(self, x, y, id_jugador, nombre="IA"):
        """Inicializa una IA con posición e identificación.

        Args:
            x (int): Coordenada horizontal inicial.
            y (int): Coordenada vertical inicial.
            id_jugador (int): Identificador único del jugador.
            nombre (str, optional): Nombre del jugador. Por defecto "IA".
        """
        super().__init__(x, y, id_jugador, nombre)
        self.es_ia = True
        self.jugadores = []
        self.tiempo_reaccion = 0.2
        self.velocidad_ia = self.config.VELOCIDAD_IA
        self.variacion_ia = self.config.VARIACION_IA
        self.factor_ia_huyendo = self.config.FACTOR_IA_HUYENDO
        self._dir_x = 0.0
        self._dir_y = 0.0
        self._recalcular = 0.0

    def _objetivo(self):
        """Encuentra al otro jugador de la partida.

        Returns:
            Jugador: El jugador contrario o None si no hay oponente.
        """
        for j in self.jugadores:
            if j is not self:
                return j
        return None

    def _evitar_cajas(self, dir_x, dir_y, obstaculos):
        """Ajusta la dirección deseada para no estrellarse contra las cajas.

        Args:
            dir_x (float): Dirección horizontal deseada.
            dir_y (float): Dirección vertical deseada.
            obstaculos (list): Lista de obstáculos del entorno.

        Returns:
            tuple: Dirección corregida (x, y).
        """
        if not obstaculos:
            return (dir_x, dir_y)

        repulsion_x = 0.0
        repulsion_y = 0.0
        margen = self.config.TAMAÑO_JUGADOR // 2 + 45
        alcance = 240
        ax = self.x + self.config.TAMAÑO_JUGADOR // 2
        ay = self.y + self.config.TAMAÑO_JUGADOR // 2

        for obs in obstaculos:
            if obs.tipo != obs.TIPO_CAJA:
                continue
            rect = obs.obtener_rectangulo().inflate(margen * 2, margen * 2)
            if not rect.collidepoint((ax, ay)):
                continue
            dx = ax - (obs.x + obs.ancho / 2)
            dy = ay - (obs.y + obs.alto / 2)
            dist = math.hypot(dx, dy)
            if dist < 1:
                dist = 1
            fuerza = (1.0 - min(dist / alcance, 1.0)) * 2.5
            repulsion_x += (dx / dist) * fuerza
            repulsion_y += (dy / dist) * fuerza

        dir_x += repulsion_x
        dir_y += repulsion_y
        return (dir_x, dir_y)

    def _calcular_direccion(self, obstaculos):
        """Calcula la dirección de movimiento tras aplicar enemigos y paredes.

        Args:
            obstaculos (list): Lista de obstáculos del entorno.

        Returns:
            tuple: Dirección normalizada (x, y).
        """
        objetivo = self._objetivo()
        if objetivo is None:
            return (0.0, 0.0)

        dx = objetivo.x - self.x
        dy = objetivo.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return (self._dir_x, self._dir_y)

        direccion = 1 if self.es_lleva else -1
        dir_x = (dx / dist) * direccion
        dir_y = (dy / dist) * direccion

        variacion = random.uniform(-1, 1) * self.variacion_ia
        dir_x += variacion
        dir_y += variacion

        if obstaculos:
            dir_x, dir_y = self._evitar_cajas(dir_x, dir_y, obstaculos)

        margen = 90
        if self.x < margen:
            dir_x += 1.0
        elif self.x > self.config.ANCHO_PANTALLA - self.config.TAMAÑO_JUGADOR - margen:
            dir_x -= 1.0
        if self.y < margen:
            dir_y += 1.0
        elif self.y > self.config.ALTO_PANTALLA - self.config.TAMAÑO_JUGADOR - margen:
            dir_y -= 1.0

        return (dir_x, dir_y)

    def mover(self, teclas=None, en_zona_lenta=False, delta_tiempo=None, obstaculos=None):
        """Mueve la IA: persigue si es la lleva, huye si no lo es.

        La IA evita las cajas, se aleja de las paredes y reacciona con un
        pequeño retardo según la dificultad. Es ligeramente más lenta que
        el jugador humano y va aún más despacio al llevar "la lleva".

        Args:
            teclas: Se ignora (la IA no usa teclado).
            en_zona_lenta (bool): True si el jugador está en una zona que ralentiza.
            delta_tiempo (float, optional): Tiempo transcurrido en segundos.
                Por defecto equivale a un frame (1/FPS).
            obstaculos (list, optional): Obstáculos del entorno para evitarlos.
        """
        dt = delta_tiempo if delta_tiempo is not None else 1.0 / self.config.FPS

        if self._recalcular <= 0 or (self._dir_x == 0 and self._dir_y == 0):
            self._dir_x, self._dir_y = self._calcular_direccion(obstaculos)
            self._recalcular = self.tiempo_reaccion
        self._recalcular -= dt

        velocidad_max = self.velocidad_ia * self.factor_velocidad
        if en_zona_lenta:
            velocidad_max *= self.config.FACTOR_RALENTIZACION
        if self.es_lleva:
            velocidad_max *= self.factor_ia_huyendo

        self.mover_con_fisica(self._dir_x, self._dir_y, velocidad_max, dt)