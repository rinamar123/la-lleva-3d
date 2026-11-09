"""Pruebas del movimiento por tiempo real del jugador humano."""

import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from juego_lleva.core.config import Config
from juego_lleva.models.jugador_humano import JugadorHumano


class TestJugadorHumanoRealTime(unittest.TestCase):

    def setUp(self):
        self.config = Config()
        self.teclas = {
            'arriba': 1, 'abajo': 2, 'izquierda': 3, 'derecha': 4
        }

    def _presionadas(self, *teclas):
        estado = {1: False, 2: False, 3: False, 4: False}
        for t in teclas:
            estado[t] = True
        return estado

    def test_mueve_velocidad_en_px_por_segundo(self):
        jugador = JugadorHumano(0, 0, 0, self.teclas)
        jugador.mover(self._presionadas(self.teclas['derecha']), delta_tiempo=1.0)
        self.assertAlmostEqual(jugador.x, self.config.VELOCIDAD_JUGADOR, delta=1)

    def test_delta_escala_el_desplazamiento(self):
        jugador = JugadorHumano(0, 0, 0, self.teclas)
        jugador.mover(self._presionadas(self.teclas['derecha']), delta_tiempo=0.5)
        self.assertAlmostEqual(jugador.x, self.config.VELOCIDAD_JUGADOR / 2, delta=1)

    def test_diagonal_mueve_en_ambos_ejes(self):
        jugador = JugadorHumano(100, 100, 0, self.teclas)
        jugador.mover(self._presionadas(self.teclas['arriba'], self.teclas['derecha']),
                      delta_tiempo=0.5)
        self.assertLess(jugador.y, 100)
        self.assertGreater(jugador.x, 100)

    def test_zona_lenta_reduce_velocidad(self):
        jugador = JugadorHumano(0, 0, 0, self.teclas)
        jugador.mover(self._presionadas(self.teclas['derecha']),
                      en_zona_lenta=True, delta_tiempo=1.0)
        esperado = self.config.VELOCIDAD_JUGADOR * self.config.FACTOR_RALENTIZACION
        self.assertAlmostEqual(jugador.x, esperado, delta=1)

    def test_factor_velocidad_multiplica(self):
        jugador = JugadorHumano(0, 0, 0, self.teclas)
        jugador.factor_velocidad = 2.0
        jugador.mover(self._presionadas(self.teclas['derecha']), delta_tiempo=1.0)
        self.assertAlmostEqual(jugador.x, self.config.VELOCIDAD_JUGADOR * 2, delta=1)

    def test_atributos_por_defecto_de_estado(self):
        jugador = JugadorHumano(0, 0, 0, self.teclas)
        self.assertEqual(jugador.factor_velocidad, 1.0)
        self.assertFalse(jugador.escudo)
        self.assertEqual(jugador.congelado, 0.0)

    def test_limita_en_los_bordes(self):
        jugador = JugadorHumano(0, 0, 0, self.teclas)
        jugador.mover(self._presionadas(self.teclas['arriba'], self.teclas['izquierda']),
                      delta_tiempo=10.0)
        self.assertEqual(jugador.x, 0)
        self.assertEqual(jugador.y, 0)

    def test_diagonal_no_supera_velocidad_maxima(self):
        jugador = JugadorHumano(800, 800, 0, self.teclas)
        jugador.mover(self._presionadas(self.teclas['arriba'], self.teclas['derecha']),
                      delta_tiempo=1.0)
        self.assertAlmostEqual(jugador.velocidad_abs, self.config.VELOCIDAD_JUGADOR, delta=1)

    def test_inercia_no_detiene_de_golpe(self):
        jugador = JugadorHumano(0, 0, 0, self.teclas)
        jugador.mover(self._presionadas(self.teclas['derecha']), delta_tiempo=2.0)
        tras_mover = jugador.x
        jugador.mover(self._presionadas(), delta_tiempo=0.05)
        self.assertGreater(jugador.x, tras_mover)

    def test_tropiezo_frena_movimiento(self):
        jugador = JugadorHumano(100, 100, 0, self.teclas)
        jugador.tropezando = self.config.DURACION_TROPIEZO
        jugador.mover(self._presionadas(self.teclas['derecha']), delta_tiempo=0.1)
        self.assertLess(jugador.x, 105)

    def test_direccion_cara_sigue_la_velocidad(self):
        jugador = JugadorHumano(1000, 800, 0, self.teclas)
        jugador.mover(self._presionadas(self.teclas['izquierda']), delta_tiempo=1.0)
        self.assertEqual(jugador.direccion_cara, -1)


if __name__ == '__main__':
    unittest.main()