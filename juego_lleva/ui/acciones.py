"""Detección de acciones de usuario en las distintas pantallas del juego."""

from juego_lleva.core.config import Config

ALTO_BOTON_MENU = 44
ALTO_BOTON_SALA = 50


def rects_sala(ancho_pantalla):
    """Geometría de los botones de la sala, compartida con ``dibujar_sala``.

    La pantalla de sala usa coordenadas absolutas (su texto tiene tamaño fijo
    y el panel no escala), así dibujo e hitbox salen del mismo sitio.

    Args:
        ancho_pantalla (int): Ancho lógico de la pantalla.

    Returns:
        tuple: (x_listo, x_salir, y, ancho, alto).
    """
    ancho = 200
    alto = ALTO_BOTON_SALA
    y = 560
    x_listo = ancho_pantalla // 2 - ancho - 20
    x_salir = ancho_pantalla // 2 + 20
    return x_listo, x_salir, y, ancho, alto


class AccionesUI:
    """Detecta qué acción seleccionó el usuario según mouse y click."""

    def __init__(self):
        self.config = Config()

    def _dentro_boton(self, pos, x, y, ancho, alto):
        """Verifica si una posición está dentro de un rectángulo de botón.

        El borde derecho e inferior quedan fuera para que dos botones
        contiguos no compartan la misma fila/columna de píxeles.
        """
        return x <= pos[0] < x + ancho and y <= pos[1] < y + alto

    def detectar_menu(self, mouse_pos, click, botones_menu, escala_ui):
        """Obtiene la acción del menú según la posición del mouse y el click.

        Args:
            mouse_pos (tuple): Posición del mouse.
            click (bool): True si se hizo click.
            botones_menu (list): Lista de tuplas (texto, accion, y).
            escala_ui (float): Factor de escala de la UI.

        Returns:
            str: Acción seleccionada o None.
        """
        if not click:
            return None
        ancho = int(280 * escala_ui)
        alto = int(ALTO_BOTON_MENU * escala_ui)
        x = self.config.ANCHO_PANTALLA // 2 - ancho // 2
        for _texto, accion, y in botones_menu:
            if self._dentro_boton(mouse_pos, x, int(y * escala_ui), ancho, alto):
                return accion
        return None

    def detectar_fin_ronda(self, mouse_pos, click, escala_ui):
        """Obtiene la acción de fin de ronda según el mouse.

        Args:
            mouse_pos (tuple): Posición del mouse.
            click (bool): True si se hizo click.
            escala_ui (float): Factor de escala de la UI.

        Returns:
            str: Acción seleccionada ("revancha", "menu") o None.
        """
        if not click:
            return None
        btn_ancho = int(190 * escala_ui)
        btn_alto = int(50 * escala_ui)
        y_btn = int(510 * escala_ui)
        x_revancha = self.config.ANCHO_PANTALLA // 2 - btn_ancho - int(20 * escala_ui)
        x_menu = self.config.ANCHO_PANTALLA // 2 + int(20 * escala_ui)
        if self._dentro_boton(mouse_pos, x_revancha, y_btn, btn_ancho, btn_alto):
            return "revancha"
        if self._dentro_boton(mouse_pos, x_menu, y_btn, btn_ancho, btn_alto):
            return "menu"
        return None

    def detectar_ranking(self, mouse_pos, click):
        """Obtiene la acción de la pantalla de ranking.

        Args:
            mouse_pos (tuple): Posición del mouse.
            click (bool): True si se hizo click.

        Returns:
            str: Acción seleccionada ("volver") o None.
        """
        if not click:
            return None
        if self._dentro_boton(mouse_pos, self.config.ANCHO_PANTALLA // 2 - 100, 580, 200, 50):
            return "volver"
        return None

    def detectar_opciones(self, mouse_pos, click):
        """Obtiene la acción de la pantalla de opciones según el mouse.

        Args:
            mouse_pos (tuple): Posición del mouse.
            click (bool): True si se hizo click.

        Returns:
            tuple: ("cambiar", clave, direccion), ("volver",) o None.
        """
        if not click:
            return None
        cx = self.config.ANCHO_PANTALLA // 2
        if self._dentro_boton(mouse_pos, cx - 100, 610, 200, 50):
            return ("volver",)
        filas = ["duracion_ronda", "dificultad_ia", "volumen_musica", "volumen_sfx", "pantalla_completa"]
        for i, clave in enumerate(filas):
            y = 155 + i * 80
            if self._dentro_boton(mouse_pos, cx - 90, y + 15, 40, 40):
                return ("cambiar", clave, -1)
            if self._dentro_boton(mouse_pos, cx + 50, y + 15, 40, 40):
                return ("cambiar", clave, 1)
        return None

    def detectar_sala(self, mouse_pos, click):
        """Obtiene la acción de la sala de espera según el mouse.

        Args:
            mouse_pos (tuple): Posición del mouse.
            click (bool): True si se hizo click.

        Returns:
            str: Acción seleccionada ("listo", "salir") o None.
        """
        if not click:
            return None
        x_listo, x_salir, y_btn, ancho, alto = rects_sala(
            self.config.ANCHO_PANTALLA)
        if self._dentro_boton(mouse_pos, x_listo, y_btn, ancho, alto):
            return "listo"
        if self._dentro_boton(mouse_pos, x_salir, y_btn, ancho, alto):
            return "salir"
        return None

    def detectar_ayuda(self, mouse_pos, click, ancho_pantalla, alto_pantalla):
        """Obtiene la acción de la pantalla de ayuda según el mouse.

        Args:
            mouse_pos (tuple): Posición del mouse.
            click (bool): True si se hizo click.
            ancho_pantalla (int): Ancho de la pantalla.
            alto_pantalla (int): Alto de la pantalla.

        Returns:
            str: "volver" si se pulsó el botón, o None.
        """
        if not click:
            return None
        ancho, alto = 200, 50
        x = ancho_pantalla // 2 - ancho // 2
        y = min(680, alto_pantalla - alto - 10)
        if self._dentro_boton(mouse_pos, x, y, ancho, alto):
            return "volver"
        return None
