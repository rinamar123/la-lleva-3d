"""Servicio que maneja el ranking de mejores tiempos con persistencia."""

import json
import os
from datetime import datetime


class RankingService:
    """Clase que gestiona el ranking de partidas jugadas."""

    def __init__(self, ruta_archivo):
        """Inicializa el servicio de ranking.

        Args:
            ruta_archivo (str): Ruta al archivo JSON de ranking.
        """
        self.ruta = ruta_archivo
        self.entradas = self._cargar()

    def _cargar(self):
        """Carga las entradas del ranking desde el archivo JSON.

        Returns:
            list: Lista de entradas del ranking.
        """
        if not os.path.exists(self.ruta):
            return []
        try:
            with open(self.ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _guardar(self):
        """Guarda las entradas del ranking en el archivo JSON."""
        try:
            os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
            with open(self.ruta, 'w', encoding='utf-8') as f:
                json.dump(self.entradas, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def registrar_partida(self, ganador_nombre, tiempo_ganador, jugadores_tiempos):
        """Registra una partida en el ranking.

        Args:
            ganador_nombre (str): Nombre del jugador ganador.
            tiempo_ganador (float): Tiempo que el ganador fue "la lleva".
            jugadores_tiempos (dict): Diccionario {nombre: tiempo} de todos los jugadores.
        """
        entrada = {
            "ganador": ganador_nombre,
            "tiempo": round(tiempo_ganador, 2),
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "jugadores": {k: round(v, 2) for k, v in jugadores_tiempos.items()}
        }
        self.entradas.append(entrada)
        self._guardar()

    def obtener_top(self, n=10):
        """Obtiene las mejores entradas del ranking ordenadas por menor tiempo.

        Args:
            n (int): Cantidad máxima de entradas a retornar.

        Returns:
            list: Lista de las mejores N entradas ordenadas por tiempo ascendente.
        """
        ordenadas = sorted(self.entradas, key=lambda e: e["tiempo"])
        return ordenadas[:n]
