"""Servicio que gestiona la lógica de los efectos visuales (crear, actualizar, eliminar)."""

import math
import random


class EfectoService:
    """Maneja el ciclo de vida de los efectos: creación, actualización y limpieza."""

    DURACION = 0.6

    def crear_toque(self, x, y, color=(255, 215, 0), cantidad=14):
        """Crea un efecto de toque en la posición indicada.

        Args:
            x (float): Coordenada horizontal del toque.
            y (float): Coordenada vertical del toque.
            color (tuple): Color RGB del efecto.
            cantidad (int): Número de partículas a generar.

        Returns:
            dict: Efecto listo para agregarse a la lista de activos.
        """
        particulas = []
        for _ in range(cantidad):
            angulo = random.uniform(0, math.pi * 2)
            velocidad = random.uniform(40, 140)
            particulas.append({
                'x': x,
                'y': y,
                'vx': math.cos(angulo) * velocidad,
                'vy': math.sin(angulo) * velocidad,
                'vida': random.uniform(0.5, 0.7)
            })
        return {
            'x': x,
            'y': y,
            'tiempo': 0.0,
            'color': color,
            'particulas': particulas
        }

    def crear_anillo(self, x, y, color=(255, 215, 0)):
        """Crea un efecto de solo anillo (sin partículas).

        Args:
            x (float): Coordenada horizontal.
            y (float): Coordenada vertical.
            color (tuple): Color del anillo.

        Returns:
            dict: Efecto listo para agregarse a la lista de activos.
        """
        return {
            'x': x,
            'y': y,
            'tiempo': 0.0,
            'color': color,
            'anillo_solo': True,
            'particulas': []
        }

    def actualizar(self, efectos, delta_tiempo):
        """Actualiza el tiempo de vida de los efectos y elimina los vencidos.

        Args:
            efectos (list): Lista de efectos activos.
            delta_tiempo (float): Tiempo transcurrido desde la última actualización.

        Returns:
            list: Lista de efectos que siguen vivos.
        """
        vivos = []
        for efecto in efectos:
            efecto['tiempo'] += delta_tiempo
            if efecto['tiempo'] >= self.DURACION:
                continue

            for particula in efecto['particulas']:
                particula['x'] += particula['vx'] * delta_tiempo
                particula['y'] += particula['vy'] * delta_tiempo
                particula['vida'] -= delta_tiempo
            efecto['particulas'] = [p for p in efecto['particulas'] if p['vida'] > 0]
            vivos.append(efecto)
        return vivos
