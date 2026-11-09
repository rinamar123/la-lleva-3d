import os
import unittest
from types import SimpleNamespace

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from juego_lleva.controles.tactil import ControladorTactil


class TestControladorTactil(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.ancho = 1908
        self.alto = 1080
        self.tactil = ControladorTactil(self.ancho, self.alto)

    def _dedo(self, tipo, x, y, id_dedo=0):
        return SimpleNamespace(type=tipo, x=x, y=y, finger_id=id_dedo)

    def test_toque_en_cruz_j1_activa_tecla(self):
        rect = self.tactil.zonas_j1["arriba"]
        cx, cy = rect.center
        evento = self._dedo(pygame.FINGERDOWN, cx / self.ancho, cy / self.alto)
        self.tactil.procesar_evento(evento)
        self.assertIn(pygame.K_w, self.tactil.teclas_activas())

    def test_teclas_j1_y_j2_independientes(self):
        self.tactil.procesar_evento(self._dedo(
            pygame.FINGERDOWN, self.tactil.zonas_j2["derecha"].centerx / self.ancho,
            self.tactil.zonas_j2["derecha"].centery / self.alto))
        self.assertIn(pygame.K_RIGHT, self.tactil.teclas_activas())
        self.assertNotIn(pygame.K_d, self.tactil.teclas_activas())

    def test_soltar_dedo_limpia_teclas(self):
        rect = self.tactil.zonas_j1["abajo"]
        cx, cy = rect.center
        self.tactil.procesar_evento(self._dedo(pygame.FINGERDOWN, cx / self.ancho, cy / self.alto, 1))
        self.assertTrue(self.tactil.teclas_activas())
        self.tactil.procesar_evento(self._dedo(pygame.FINGERUP, cx / self.ancho, cy / self.alto, 1))
        self.assertEqual(self.tactil.teclas_activas(), [])

    def test_pulso_de_pausa(self):
        cx, cy = self.tactil.zona_pausa.center
        self.tactil.procesar_evento(self._dedo(pygame.FINGERDOWN, cx / self.ancho, cy / self.alto))
        self.assertTrue(self.tactil.consumir_pausa())
        self.assertFalse(self.tactil.consumir_pausa())

    def test_inactivo_hasta_primer_toque(self):
        self.assertEqual(self.tactil.activo, False)
        rect = self.tactil.zonas_j1["izquierda"]
        cx, cy = rect.center
        self.tactil.procesar_evento(self._dedo(pygame.FINGERDOWN, cx / self.ancho, cy / self.alto))
        self.assertTrue(self.tactil.activo)


if __name__ == '__main__':
    unittest.main()