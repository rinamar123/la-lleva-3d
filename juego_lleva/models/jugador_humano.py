"""Modelo que representa a un jugador controlado por un humano."""

from juego_lleva.models.jugador import Jugador


class JugadorHumano(Jugador):
    """Clase que representa a un jugador controlado por teclado."""

    def __init__(self, x, y, id_jugador, teclas, nombre=None):
        """Inicializa un jugador humano con configuración de teclas.

        Args:
            x (int): Coordenada horizontal inicial.
            y (int): Coordenada vertical inicial.
            id_jugador (int): Identificador único del jugador.
            teclas (dict): Diccionario que mapea acciones a teclas del teclado.
            nombre (str, optional): Nombre del jugador. Por defecto "J{id+1}".
        """
        super().__init__(x, y, id_jugador, nombre)
        self.teclas = teclas

    def mover(self, teclas_presionadas=None, en_zona_lenta=False, delta_tiempo=None, obstaculos=None):
        """Mueve el jugador según las teclas presionadas.

        Args:
            teclas_presionadas: Estado de las teclas del teclado.
            en_zona_lenta (bool): True si el jugador está en una zona que ralentiza.
            delta_tiempo (float, optional): Tiempo transcurrido en segundos.
                Por defecto equivale a un frame (1/FPS).
            obstaculos: Se ignora (el jugador humano choca y desliza).
        """
        if teclas_presionadas is None:
            return

        dt = delta_tiempo if delta_tiempo is not None else 1.0 / self.config.FPS

        dir_x = 0
        dir_y = 0
        if teclas_presionadas[self.teclas['izquierda']]:
            dir_x -= 1
        if teclas_presionadas[self.teclas['derecha']]:
            dir_x += 1
        if teclas_presionadas[self.teclas['arriba']]:
            dir_y -= 1
        if teclas_presionadas[self.teclas['abajo']]:
            dir_y += 1

        velocidad_max = self.config.VELOCIDAD_JUGADOR * self.factor_velocidad
        if en_zona_lenta:
            velocidad_max *= self.config.FACTOR_RALENTIZACION

        self.mover_con_fisica(dir_x, dir_y, velocidad_max, dt)