"""Pruebas del jugador controlado por IA."""

import os
import random
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from juego_lleva.core.config import Config
from juego_lleva.models.jugador_humano import JugadorHumano
from juego_lleva.models.jugador_ia import JugadorIA


class TestJugadorIA(unittest.TestCase):

    def setUp(self):
        random.seed(1)
        self.config = Config()
        self.humano = JugadorHumano(0, 100, 0, {})
        self.ia = JugadorIA(300, 100, 1)
        self.ia.jugadores = [self.humano, self.ia]

    def test_persigue_cuando_no_lleva(self):
        self.humano.x = 500
        self.ia.x = 300
        self.ia.es_lleva = False
        self.ia.variacion_ia = 0
        self.ia.mover(delta_tiempo=1.0)
        self.assertLess(self.ia.x, 300)

    def test_huye_cuando_lleva(self):
        self.humano.x = 500
        self.ia.x = 300
        self.ia.es_lleva = True
        self.ia.variacion_ia = 0
        self.ia.mover(delta_tiempo=1.0)
        self.assertGreater(self.ia.x, 300)

    def test_se_mantiene_dentro_de_la_pantalla_al_huir(self):
        self.humano.x = 1000
        self.ia.x = 0
        self.ia.es_lleva = True
        self.ia.mover()
        self.assertGreaterEqual(self.ia.x, 0)

    def test_limita_en_el_borde_derecho(self):
        self.humano.x = 0
        self.ia.x = self.config.ANCHO_PANTALLA - self.config.TAMAÑO_JUGADOR
        self.ia.es_lleva = True
        self.ia.mover()
        self.assertLessEqual(self.ia.x, self.config.ANCHO_PANTALLA - self.config.TAMAÑO_JUGADOR)

    def test_no_se_mueve_sin_objetivo(self):
        self.ia.jugadores = [self.ia]
        x, y = self.ia.x, self.ia.y
        self.ia.mover()
        self.assertEqual((self.ia.x, self.ia.y), (x, y))

    def test_delta_escala_el_desplazamiento(self):
        self.humano.x = 500
        self.ia.x = 300
        self.ia.es_lleva = False
        self.ia.mover(delta_tiempo=2.0)
        self.assertLess(self.ia.x, 300 - self.config.VELOCIDAD_IA)
        self.ia.x = 300
        self.ia.mover(delta_tiempo=1.0)
        self.assertGreater(self.ia.x, 300 - self.config.VELOCIDAD_IA - 5)

    def test_huye_mas_lento_que_persigue(self):
        self.humano.x = 500
        self.ia.x = 300
        self.ia.es_lleva = False
        self.ia.mover(delta_tiempo=1.0)
        avance_persiguiendo = 300 - self.ia.x

        self.ia.x = 300
        self.ia.es_lleva = True
        self.ia.mover(delta_tiempo=1.0)
        avance_huyendo = self.ia.x - 300
        self.assertLess(avance_huyendo, avance_persiguiendo)


if __name__ == '__main__':
    unittest.main()