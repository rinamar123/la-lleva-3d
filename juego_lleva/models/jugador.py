"""Modelo que representa a un jugador en el juego."""

from juego_lleva.core.config import Config
from juego_lleva.interfaces.movible import Movible
from juego_lleva.models.rect import Rect


class Jugador(Movible):
    """Clase que representa a un jugador con posición, estado y comportamiento de movimiento."""

    def __init__(self, x, y, id_jugador, nombre=None):
        """Inicializa un jugador con posición y identificación.

        Args:
            x (int): Coordenada horizontal inicial.
            y (int): Coordenada vertical inicial.
            id_jugador (int): Identificador único del jugador.
            nombre (str, optional): Nombre del jugador. Por defecto "J{id+1}".
        """
        self.x = x
        self.y = y
        self.id = id_jugador
        self.nombre = nombre or f"J{id_jugador + 1}"
        self._es_lleva = False
        self.config = Config()
        self.factor_velocidad = 1.0
        self.escudo = False
        self.congelado = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.tropezando = 0.0
        self.direccion_cara = 1
        self.velocidad_abs = 0.0

    def obtener_posicion(self):
        """Obtiene la posición actual del jugador.

        Returns:
            tuple: Coordenadas (x, y) de la posición actual.
        """
        return (self.x, self.y)

    def _limitar_pantalla(self):
        """Limita la posición del jugador a los bordes de la pantalla."""
        if self.x < 0:
            self.x = 0
            self.vx = max(self.vx, 0)
        elif self.x > self.config.ANCHO_PANTALLA - self.config.TAMAÑO_JUGADOR:
            self.x = self.config.ANCHO_PANTALLA - self.config.TAMAÑO_JUGADOR
            self.vx = min(self.vx, 0)
        if self.y < 0:
            self.y = 0
            self.vy = max(self.vy, 0)
        elif self.y > self.config.ALTO_PANTALLA - self.config.TAMAÑO_JUGADOR:
            self.y = self.config.ALTO_PANTALLA - self.config.TAMAÑO_JUGADOR
            self.vy = min(self.vy, 0)

    def obtener_rectangulo(self):
        """Obtiene el rectángulo de colisión del jugador.

        Returns:
            Rect: Rectángulo que define los límites del jugador para colisiones.
        """
        margen = int(self.config.TAMAÑO_JUGADOR * 0.2)
        return Rect(
            self.x + margen, self.y + margen,
            self.config.TAMAÑO_JUGADOR - margen * 2,
            self.config.TAMAÑO_JUGADOR - margen * 2
        )

    @property
    def es_lleva(self):
        """Indica si el jugador tiene la pelota (la lleva).

        Returns:
            bool: True si el jugador tiene la pelota, False en caso contrario.
        """
        return self._es_lleva

    @es_lleva.setter
    def es_lleva(self, valor):
        """Establece si el jugador tiene la pelota.

        Args:
            valor (bool): True si el jugador tiene la pelota, False en caso contrario.
        """
        self._es_lleva = valor

    def _impulso(self, dir_x, dir_y, velocidad_max, delta_tiempo):
        """Acelera hacia la velocidad objetivo con inercia y normaliza la diagonal.

        Args:
            dir_x (float): Dirección horizontal deseada (-1, 0 o 1).
            dir_y (float): Dirección vertical deseada (-1, 0 o 1).
            velocidad_max (float): Velocidad máxima (px/s) en esta circunstancia.
            delta_tiempo (float): Tiempo transcurrido en segundos.
        """
        if self.tropezando > 0 or self.congelado > 0:
            self._aplicar_friccion(delta_tiempo, 0.85)
            return

        distancia = (dir_x * dir_x + dir_y * dir_y) ** 0.5
        if distancia > 0:
            dir_x, dir_y = dir_x / distancia, dir_y / distancia

        objetivo_x = dir_x * velocidad_max
        objetivo_y = dir_y * velocidad_max

        paso = self.config.ACELERACION * delta_tiempo
        if abs(objetivo_x - self.vx) <= paso:
            self.vx = objetivo_x
        else:
            self.vx += paso if objetivo_x > self.vx else -paso
        if abs(objetivo_y - self.vy) <= paso:
            self.vy = objetivo_y
        else:
            self.vy += paso if objetivo_y > self.vy else -paso

        if dir_x == 0 and dir_y == 0:
            self._aplicar_friccion(delta_tiempo, self.config.ROZAMIENTO)

    def _aplicar_friccion(self, delta_tiempo, factor):
        """Reduce la velocidad actual hacia cero.

        Args:
            delta_tiempo (float): Tiempo transcurrido en segundos.
            factor (float): Coeficiente de fricción (intensidad).
        """
        decaimiento = max(0.0, 1.0 - factor * delta_tiempo)
        self.vx *= decaimiento
        self.vy *= decaimiento
        if abs(self.vx) < 1:
            self.vx = 0.0
        if abs(self.vy) < 1:
            self.vy = 0.0

    def _desplazar(self, delta_tiempo):
        """Mueve al jugador según su velocidad actual en el tiempo dado.

        Args:
            delta_tiempo (float): Tiempo transcurrido en segundos.
        """
        if self.tropezando > 0:
            self.tropezando -= delta_tiempo
            self._aplicar_friccion(delta_tiempo, 10.0)

        self.x += self.vx * delta_tiempo
        self.y += self.vy * delta_tiempo
        self._limitar_pantalla()

        if abs(self.vx) > 10:
            self.direccion_cara = 1 if self.vx > 0 else -1

        self.velocidad_abs = (self.vx * self.vx + self.vy * self.vy) ** 0.5

    def mover_con_fisica(self, dir_x, dir_y, velocidad_max, delta_tiempo):
        """Combina el impulso (aceleración/inercia) con el desplazamiento.

        Args:
            dir_x (float): Dirección horizontal deseada.
            dir_y (float): Dirección vertical deseada.
            velocidad_max (float): Velocidad máxima en px/s.
            delta_tiempo (float): Tiempo transcurrido en segundos.
        """
        self._impulso(dir_x, dir_y, velocidad_max, delta_tiempo)
        self._desplazar(delta_tiempo)