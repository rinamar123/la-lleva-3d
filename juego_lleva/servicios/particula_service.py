"""Servicio que gestiona las partículas de rastro de los jugadores."""

import random


class ParticulaService:
    """Maneja el ciclo de vida de las partículas de rastro."""

    def __init__(self):
        self._trail_timers = {}

    def actualizar(self, particulas, delta_tiempo):
        """Actualiza el estado de las partículas de rastro.

        Args:
            particulas (list): Lista de partículas activas.
            delta_tiempo (float): Tiempo transcurrido desde la última actualización.

        Returns:
            list: Partículas que siguen vivas.
        """
        nuevas = []
        for p in particulas:
            p['vida'] -= delta_tiempo * 2
            p['x'] += p['velocidad_x'] * delta_tiempo
            p['y'] += p['velocidad_y'] * delta_tiempo
            p['tamaño'] *= 0.95
            if p['vida'] > 0:
                nuevas.append(p)
        return nuevas

    def agregar_rastro(self, jugador, config):
        """Agrega una nueva partícula de rastro al jugador.

        Args:
            jugador: Objeto jugador para obtener posición y color.
            config: Instancia de Config con colores y tamaños.

        Returns:
            dict or None: Partícula creada, o None si el jugador va muy lento.
        """
        velocidad = jugador.velocidad_abs
        potenciado = getattr(jugador, "factor_velocidad", 1.0) > 1.0

        if velocidad <= 60:
            return None

        color = config.COLOR_LLEVA if jugador.es_lleva else (
            config.color_jugador(jugador.id)
        )
        if potenciado:
            color = (255, 235, 120)
        tamaño = random.randint(2, 4) if not jugador.es_lleva else random.randint(3, 6)
        if potenciado:
            tamaño = random.randint(4, 7)
        return {
            'x': jugador.x + config.TAMAÑO_JUGADOR // 2,
            'y': jugador.y + config.TAMAÑO_JUGADOR,
            'velocidad_x': random.uniform(-30, 30),
            'velocidad_y': -jugador.vy * 0.15 + random.uniform(-10, 10),
            'tamaño': tamaño,
            'color': color,
            'vida': 1.0
        }

    def actualizar_rastro(self, jugador_id, particulas_rastro, jugador, config, delta_tiempo):
        """Gestiona el timer de rastro, agrega nuevas partículas y actualiza las existentes.

        Args:
            jugador_id: Identificador único del jugador.
            particulas_rastro (list): Lista mutable de partículas de rastro.
            jugador: Objeto jugador para posición y velocidad.
            config: Instancia de Config.
            delta_tiempo (float): Tiempo transcurrido desde la última actualización.

        Returns:
            list: Partículas actualizadas (misma referencia que la entrada).
        """
        timer = self._trail_timers.get(jugador_id, 0.0)
        timer += delta_tiempo
        if timer > 0.05:
            nueva = self.agregar_rastro(jugador, config)
            if nueva is not None:
                particulas_rastro.append(nueva)
            timer = 0
        self._trail_timers[jugador_id] = timer
        particulas_rastro[:] = self.actualizar(particulas_rastro, delta_tiempo)
        return particulas_rastro
