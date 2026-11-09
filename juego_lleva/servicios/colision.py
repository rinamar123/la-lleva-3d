"""Servicio que maneja la detección y resolución de colisiones."""

import math

from juego_lleva.core.config import Config


class ColisionService:
    """Clase que gestiona las colisiones entre jugadores y obstáculos."""

    def __init__(self):
        """Inicializa el servicio de colisiones con configuración por defecto."""
        self.config = Config()
        self.cooldown = 0.0
        self.COOLDOWN_SEG = 0.15

    def detectar_toque(self, j1, j2):
        """Detecta si dos jugadores se tocan a distancia de alcance real.

        Usa la distancia entre centros: si es menor que el alcance configurado
        (suma de mitades + margen), se considera contacto, aunque sus
        rectángulos de colisión aún no se solapen.

        Args:
            j1: Primer jugador.
            j2: Segundo jugador.

        Returns:
            bool: True si están a distancia de toque, False en caso contrario.
        """
        dx = j1.x - j2.x
        dy = j1.y - j2.y
        dist = math.hypot(dx, dy)
        return dist < self.config.ALCANCE_TOQUE

    def detectar_colisiones(self, jugadores, delta_tiempo=0.0):
        """Detecta todas las colisiones entre una lista de jugadores.

        El cooldown se mide en segundos (no en frames) para que el
        comportamiento sea independiente de la tasa de refresco, que en la
        versión web la marca el navegador.

        Args:
            jugadores (list): Lista de jugadores a verificar.
            delta_tiempo (float): Tiempo transcurrido desde el último frame.

        Returns:
            list: Lista de tuplas con pares de jugadores en colisión.
        """
        if self.cooldown > 0:
            self.cooldown = max(0.0, self.cooldown - delta_tiempo)
            return []

        colisiones = []
        for i, j1 in enumerate(jugadores):
            for j2 in jugadores[i + 1:]:
                if self.detectar_toque(j1, j2):
                    colisiones.append((j1, j2))

        if colisiones:
            self.cooldown = self.COOLDOWN_SEG

        return colisiones[:1]

    def separar_jugadores(self, j1, j2, tamano_jugador):
        """Separa dos jugadores que están colisionando.

        Args:
            j1: Primer jugador.
            j2: Segundo jugador.
            tamano_jugador (int): Tamaño del jugador para calcular separación.
        """
        dx = j1.x - j2.x
        dy = j1.y - j2.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist == 0:
            j1.x += tamano_jugador
            return

        overlap = tamano_jugador - dist
        if overlap > 0:
            separacion = overlap / 2 + 1
            j1.x += (dx / dist) * separacion
            j1.y += (dy / dist) * separacion
            j2.x -= (dx / dist) * separacion
            j2.y -= (dy / dist) * separacion

    def detectar_colision_jugador_obstaculo(self, jugador, obstaculo):
        """Detecta si un jugador está colisionando con un obstáculo.

        Args:
            jugador: Jugador a verificar.
            obstaculo: Obstáculo a verificar.

        Returns:
            bool: True si hay colisión, False en caso contrario.
        """
        rect_j = jugador.obtener_rectangulo()
        rect_o = obstaculo.obtener_rectangulo()
        return rect_j.colliderect(rect_o)

    def resolver_obstaculo(self, jugador, obstaculo):
        """Resuelve la colisión deslizando al jugador alrededor del obstáculo.

        Primero corrige el eje de menor penetración, de forma que al chocar
        de frente el jugador "se desliza" a lo largo de la pared. Si la
        velocidad de entrada es alta, aplica un rebote.

        Args:
            jugador: Jugador que colisiona.
            obstaculo: Obstáculo (caja) con el que colisiona.
        """
        rect_j = jugador.obtener_rectangulo()
        rect_o = obstaculo.obtener_rectangulo()

        centro_x = rect_j.centerx - rect_o.centerx
        centro_y = rect_j.centery - rect_o.centery
        over_x = (rect_j.width + rect_o.width) / 2 - abs(centro_x)
        over_y = (rect_j.height + rect_o.height) / 2 - abs(centro_y)

        if over_x <= 0 or over_y <= 0:
            return

        horizontal = over_x < over_y
        empuje = over_x if horizontal else over_y

        if horizontal:
            jugador.x += empuje if centro_x > 0 else -empuje
        else:
            jugador.y += empuje if centro_y > 0 else -empuje

        velocidad_entrada = math.hypot(jugador.vx, jugador.vy)
        if velocidad_entrada > self.config.FUERZA_REBOTE:
            choque = 0.6
            if horizontal and centro_x != 0:
                jugador.vx = -math.copysign(velocidad_entrada * choque, centro_x)
            elif not horizontal and centro_y != 0:
                jugador.vy = -math.copysign(velocidad_entrada * choque, centro_y)

    def jugador_en_zona_lenta(self, jugador, obstaculos):
        """Verifica si un jugador está en una zona que ralentiza.

        Args:
            jugador: Jugador a verificar.
            obstaculos (list): Lista de obstáculos del juego.

        Returns:
            bool: True si el jugador está en zona lenta, False en caso contrario.
        """
        rect_j = jugador.obtener_rectangulo()
        for obs in obstaculos:
            if obs.es_zona_lenta():
                rect_o = obs.obtener_rectangulo()
                if rect_j.colliderect(rect_o):
                    return True
        return False

    def limpiar_cooldown(self):
        """Limpia el cooldown de colisiones."""
        self.cooldown = 0