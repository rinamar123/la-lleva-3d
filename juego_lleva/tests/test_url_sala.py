"""Pruebas de la URL de la sala y del redireccionamiento al navegador."""

import os
import socket
import threading
import unittest
from unittest import mock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from juego_lleva.core.controlador_menu import ControladorMenu
from juego_lleva.core.estado import EstadoJuego
from juego_lleva.core.juego import Juego
from juego_lleva.core.config import Config
from juego_lleva.red.url_sala import URL_DEFECTO, VARIABLE_URL, url_sala


def _puerto_libre():
    """Reserva un puerto libre y devuelve el número."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestUrlSala(unittest.TestCase):
    """Resolución de la URL del juego web."""

    def setUp(self):
        self._url_previo = os.environ.pop(VARIABLE_URL, None)

    def tearDown(self):
        if self._url_previo is None:
            os.environ.pop(VARIABLE_URL, None)
        else:
            os.environ[VARIABLE_URL] = self._url_previo

    def test_sin_variable_usa_el_puerto_por_defecto(self):
        self.assertEqual(url_sala(), URL_DEFECTO)

    def test_variable_de_entorno_tiene_prioridad(self):
        os.environ[VARIABLE_URL] = "http://localhost:9321/"
        self.assertEqual(url_sala(), "http://localhost:9321/")

    def test_variable_sin_barra_final_se_normaliza(self):
        os.environ[VARIABLE_URL] = "http://localhost:9321"
        self.assertEqual(url_sala(), "http://localhost:9321/")

    def test_variable_vacia_usa_el_defecto(self):
        os.environ[VARIABLE_URL] = "   "
        self.assertEqual(url_sala(), URL_DEFECTO)


class TestServidorResponde(unittest.TestCase):
    """Comprobación de que el servidor de la sala está levantado."""

    def test_puerto_sin_escuchar_devuelve_false(self):
        url = f"http://127.0.0.1:{_puerto_libre()}/"
        self.assertFalse(_servidor_responde(url))

    def test_puerto_escuchando_devuelve_true(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind(("127.0.0.1", 0))
        servidor.listen(1)
        puerto = servidor.getsockname()[1]
        try:
            self.assertTrue(_servidor_responde(f"http://127.0.0.1:{puerto}/"))
        finally:
            servidor.close()


def _servidor_responde(url):
    """Llama al módulo recién importado (evitaShadowing en la clase)."""
    from juego_lleva.red import url_sala as modulo
    return modulo.servidor_responde(url, timeout=0.2)


class TestMenuEnLineaEscritorio(unittest.TestCase):
    """El menú de escritorio lleva al navegador en vez de a la sala local."""

    def setUp(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((320, 240))
        self.juego = Juego(Config())
        self.menu = ControladorMenu(self.juego)
        self._url_previo = os.environ.pop(VARIABLE_URL, None)

    def tearDown(self):
        if self._url_previo is not None:
            os.environ[VARIABLE_URL] = self._url_previo
        else:
            os.environ.pop(VARIABLE_URL, None)
        pygame.quit()

    def _pulsar_en_linea(self):
        """Ejecuta la acción 'en_linea' como si el menú la enviara."""
        self.menu._ejecutar_accion_menu("en_linea")

    def test_sin_servidor_no_abre_navegador_y_avisa(self):
        os.environ[VARIABLE_URL] = f"http://127.0.0.1:{_puerto_libre()}/"
        with mock.patch("webbrowser.open") as abrir:
            self._pulsar_en_linea()
        abrir.assert_not_called()
        self.assertEqual(len(self.juego.toasts), 1)
        self.assertIn("jugar.py", self.juego.toasts[0]["texto"])
        self.assertEqual(self.juego.estado, EstadoJuego.MENU)

    def test_con_servidor_abre_el_navegador_en_la_url_de_la_sala(self):
        os.environ[VARIABLE_URL] = f"http://127.0.0.1:{_puerto_libre()}/"
        with mock.patch("juego_lleva.red.url_sala.servidor_responde",
                        return_value=True) as responde, \
                mock.patch("webbrowser.open") as abrir:
            self._pulsar_en_linea()
        responde.assert_called_once()
        abrir.assert_called_once_with(os.environ[VARIABLE_URL])
        self.assertEqual(len(self.juego.toasts), 1)
        self.assertIn("navegador", self.juego.toasts[0]["texto"])
        self.assertEqual(self.juego.estado, EstadoJuego.MENU)

    def test_navegador_no_abre_muestra_la_url(self):
        os.environ[VARIABLE_URL] = f"http://127.0.0.1:{_puerto_libre()}/"
        with mock.patch("juego_lleva.red.url_sala.servidor_responde",
                        return_value=True), \
                mock.patch("webbrowser.open", return_value=False) as abrir:
            self._pulsar_en_linea()
        abrir.assert_called_once()
        self.assertEqual(len(self.juego.toasts), 1)
        self.assertIn(os.environ[VARIABLE_URL], self.juego.toasts[0]["texto"])
        self.assertEqual(self.juego.estado, EstadoJuego.MENU)

    def test_el_boton_muestra_que_va_al_navegador(self):
        textos = {accion: texto for texto, accion, _y in self.juego.interfaz.BOTONES_MENU}
        self.assertEqual(textos["en_linea"], "En Linea (web)")

    def test_el_estado_en_linea_sin_controlador_vuelve_al_menu(self):
        self.juego.estado = EstadoJuego.EN_LINEA
        self.juego.ctrl_enlinea = None
        self.juego._dispatch_estado(0.016)
        self.assertEqual(self.juego.estado, EstadoJuego.MENU)
        self.assertEqual(len(self.juego.toasts), 1)


class TestMenuEnLineaWeb(unittest.TestCase):
    """En la web el campo de nombre arranca vacio (si no quedaba J1TEST)."""

    def setUp(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((320, 240))
        self.juego = Juego(Config())
        self.juego.config.PLATAFORMA_WEB = True
        self.menu = ControladorMenu(self.juego)

    def tearDown(self):
        if self.juego.ctrl_enlinea is not None:
            self.juego._salir_en_linea()
        pygame.quit()

    def _iniciar(self, nombre):
        self.menu._ejecutar_accion_menu("en_linea")
        self.juego.nombres[0] = nombre
        self.juego._iniciar_partida()

    def test_el_campo_arranca_vacio(self):
        self.menu._ejecutar_accion_menu("en_linea")
        self.assertEqual(self.juego.modo, "en_linea")
        self.assertEqual(self.juego.nombres, [""])
        self.assertEqual(self.juego.estado, EstadoJuego.NOMBRES)

    def test_el_nombre_escrito_se_usa_completo(self):
        self._iniciar("TEST")
        self.assertEqual(self.juego.nombres, ["TEST"])
        self.assertEqual(self.juego.estado, EstadoJuego.EN_LINEA)

    def test_sin_nombre_queda_j1(self):
        self._iniciar("   ")
        self.assertEqual(self.juego.nombres, ["J1"])


class TestToastsVisiblesEnMenu(unittest.TestCase):
    """Los avisos deben verse también fuera de una partida en curso."""

    def setUp(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((320, 240))
        self.juego = Juego(Config())

    def tearDown(self):
        pygame.quit()

    def test_flip_dibuja_los_toasts_antes_de_presentar(self):
        """El aviso debe pintarse en el mismo frame, justo antes del flip."""
        self.juego.toasts = []
        self.juego._mostrar_toast("Hola", (255, 255, 255))
        orden = []
        with mock.patch.object(self.juego.interfaz, "dibujar_toasts",
                               side_effect=lambda pantalla, toasts: orden.append("toast")), \
                mock.patch.object(pygame.display, "flip",
                                  side_effect=lambda: orden.append("flip")):
            self.juego.renderer.flip()
        self.assertEqual(orden, ["toast", "flip"])

    def test_finalizar_frame_no_deja_toasts_sin_presentar(self):
        """_finalizar_frame ya no pinta toasts (los toma flip)."""
        self.juego.toasts = []
        self.juego._mostrar_toast("Hola", (255, 255, 255))
        with mock.patch.object(self.juego.interfaz, "dibujar_toasts") as dibujar:
            self.juego._finalizar_frame(0.016)
        dibujar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
