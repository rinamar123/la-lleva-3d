"""Interfaz que define el contrato para objetos que pueden moverse en el espacio del juego."""

from abc import ABC, abstractmethod


class Movible(ABC):
    """Clase abstracta que define los métodos que debe implementar cualquier objeto móvil."""

    @abstractmethod
    def mover(self, teclas=None):
        """Mueve el objeto según las teclas presionadas.

        Args:
            teclas: Diccionario con el estado de las teclas del teclado.
        """
        pass

    @abstractmethod
    def obtener_posicion(self):
        """Obtiene la posición actual del objeto.

        Returns:
            tuple: Coordenadas (x, y) de la posición actual.
        """
        pass

    @abstractmethod
    def obtener_rectangulo(self):
        """Obtiene el rectángulo de colisión del objeto.

        Returns:
            models.rect.Rect: Rectángulo que define los límites del objeto.
        """
        pass
