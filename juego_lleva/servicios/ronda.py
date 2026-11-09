"""Servicio que encapsula las reglas de la ronda (regla clásica de La Lleva)."""


class RondaService:
    """Gestiona la regla clásica: al tocar, la lleva se transfiere
    y gana quien menos tiempo fue la lleva."""

    def __init__(self, puntaje):
        """Inicializa el servicio con el registro de puntajes.

        Args:
            puntaje: Instancia de PuntajeService.
        """
        self.puntaje = puntaje

    def transferir_lleva(self, quien_tiene, quien_recibe, tiempo_ronda, tiempo_inicio_lleva):
        """Transfiere el rol de 'La Lleva' al jugador tocado.

        Args:
            quien_tiene: Jugador que tenía el rol de 'La Lleva'.
            quien_recibe: Jugador que fue tocado y pasa a ser 'La Lleva'.
            tiempo_ronda (float): Tiempo transcurrido de la ronda.
            tiempo_inicio_lleva (float): Momento en que comenzó la lleva actual.

        Returns:
            float: Nuevo momento de inicio de la lleva (tiempo_ronda).
        """
        tiempo_lleva = max(0, tiempo_ronda - tiempo_inicio_lleva)
        self.puntaje.registrar_lleva(quien_tiene.id, tiempo_lleva)
        quien_tiene.es_lleva = False
        quien_recibe.es_lleva = True
        return tiempo_ronda

    def cerrar_lleva_actual(self, jugadores, tiempo_ronda, tiempo_inicio_lleva):
        """Registra el tiempo final del jugador que lleva al terminar la ronda.

        Args:
            jugadores (list): Jugadores de la partida.
            tiempo_ronda (float): Tiempo transcurrido de la ronda.
            tiempo_inicio_lleva (float): Momento en que comenzó la lleva actual.
        """
        for jugador in jugadores:
            if jugador.es_lleva:
                tiempo_lleva = max(0, tiempo_ronda - tiempo_inicio_lleva)
                self.puntaje.registrar_lleva(jugador.id, tiempo_lleva)
                break

    def asignar_lleva_inicial(self, jugadores, id_jugador):
        """Establece qué jugador tiene la pelota inicialmente.

        Args:
            jugadores (list): Jugadores de la partida.
            id_jugador (int): ID del jugador que tendrá la pelota.
        """
        for jugador in jugadores:
            jugador.es_lleva = (jugador.id == id_jugador)