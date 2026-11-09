"""Pruebas de la vista de efectos visuales y el servicio de efectos."""

import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from juego_lleva.views.efecto_view import EfectoView
from juego_lleva.servicios.efecto_service import EfectoService


class TestEfectoService(unittest.TestCase):

    def setUp(self):
        self.servicio = EfectoService()

    def test_crear_toque_genera_anillo_y_particulas(self):
        efecto = self.servicio.crear_toque(400, 300)
        self.assertEqual(efecto['tiempo'], 0)
        self.assertGreater(len(efecto['particulas']), 0)

    def test_actualizar_elimina_efectos_vencidos(self):
        efecto = self.servicio.crear_toque(400, 300)
        efecto['tiempo'] = self.servicio.DURACION - 0.1
        vivos = self.servicio.actualizar([efecto], 0.2)
        self.assertEqual(vivos, [])

    def test_actualizar_conserva_efectos_nuevos(self):
        efecto = self.servicio.crear_toque(400, 300)
        vivos = self.servicio.actualizar([efecto], 0.1)
        self.assertEqual(len(vivos), 1)


class TestEfectoView(unittest.TestCase):

    def setUp(self):
        pygame.init()
        self.vista = EfectoView()
        self.servicio = EfectoService()
        self.pantalla = pygame.Surface((800, 600))

    def test_renderizar_no_lanza_errores(self):
        efecto = self.servicio.crear_toque(400, 300)
        self.vista.renderizar(self.pantalla, [efecto])
        efectos = self.servicio.actualizar([efecto], 0.3)
        self.vista.renderizar(self.pantalla, efectos)


if __name__ == '__main__':
    unittest.main()
