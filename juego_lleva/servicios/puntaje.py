"""Servicio que maneja el registro de puntajes y tiempos de juego."""


class PuntajeService:
    """Clase que gestiona los puntajes y tiempos de los jugadores."""

    def __init__(self):
        """Inicializa el servicio de puntajes."""
        self.tiempos_lleva = {}

    def registrar_lleva(self, id_jugador, tiempo):
        """Registra el tiempo que un jugador tuvo la pelota.

        Args:
            id_jugador (int): Identificador del jugador.
            tiempo (float): Tiempo en segundos que tuvo la pelota.
        """
        if id_jugador not in self.tiempos_lleva:
            self.tiempos_lleva[id_jugador] = 0
        self.tiempos_lleva[id_jugador] += tiempo

    def obtener_ganador(self):
        """Obtiene el ID del jugador con menos tiempo con la pelota.

        Returns:
            int: ID del ganador o None si no hay datos.
        """
        if not self.tiempos_lleva:
            return None
        return min(self.tiempos_lleva, key=self.tiempos_lleva.get)

    def reiniciar(self):
        """Reinicia todos los puntajes registrados."""
        self.tiempos_lleva.clear()
