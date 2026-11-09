"""Pruebas del servicio de colisiones con modelos reales."""

import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from juego_lleva.models.jugador_humano import JugadorHumano
from juego_lleva.models.obstaculo import Obstaculo
from juego_lleva.servicios.colision import ColisionService


class TestColisionService(unittest.TestCase):

    def setUp(self):
        self.servicio = ColisionService()

    def test_separar_jugadores_aleja_posiciones(self):
        j1 = JugadorHumano(0, 0, 0, {})
        j2 = JugadorHumano(10, 0, 1, {})
        x1, x2 = j1.x, j2.x
        self.servicio.separar_jugadores(j1, j2, 95)
        self.assertLess(j1.x, x1)
        self.assertGreater(j2.x, x2)

    def test_detectar_toque_por_alcance(self):
        j1 = JugadorHumano(0, 0, 0, {})
        j2 = JugadorHumano(89, 0, 1, {})
        self.assertTrue(self.servicio.detectar_toque(j1, j2))

    def test_no_hay_toque_mas_alla_del_alcance(self):
        j1 = JugadorHumano(0, 0, 0, {})
        j2 = JugadorHumano(500, 0, 1, {})
        self.assertFalse(self.servicio.detectar_toque(j1, j2))

    def test_jugador_en_zona_lenta(self):
        jugador = JugadorHumano(100, 100, 0, {})
        zona = Obstaculo(100, 100, "zona")
        caja = Obstaculo(500, 500, "caja")
        self.assertTrue(self.servicio.jugador_en_zona_lenta(jugador, [zona, caja]))
        self.assertFalse(self.servicio.jugador_en_zona_lenta(jugador, [caja]))

    def test_desliza_sin_penetrar(self):
        jugador = JugadorHumano(350, 350, 0, {})
        jugador.mover_con_fisica(0, 1, 100, 0.5)
        caja = Obstaculo(300, 400, "caja")
        self.servicio.resolver_obstaculo(jugador, caja)
        self.assertFalse(self.servicio.detectar_colision_jugador_obstaculo(jugador, caja))

    def test_rebote_a_alta_velocidad(self):
        jugador = JugadorHumano(260, 402.5, 0, {})
        jugador.vx = -400
        jugador.vy = 0
        caja = Obstaculo(300, 400, "caja")
        self.servicio.resolver_obstaculo(jugador, caja)
        self.assertGreater(jugador.vx, 0)

    def test_velocidad_lenta_no_invierte_direccion(self):
        jugador = JugadorHumano(260, 402.5, 0, {})
        jugador.vx = -50
        jugador.vy = 0
        caja = Obstaculo(300, 400, "caja")
        self.servicio.resolver_obstaculo(jugador, caja)
        self.assertLessEqual(jugador.vx, 0)

    def test_cooldown_evita_colisiones_seguidas(self):
        j1 = JugadorHumano(0, 0, 0, {})
        j2 = JugadorHumano(10, 0, 1, {})
        pares = self.servicio.detectar_colisiones([j1, j2])
        self.assertEqual(len(pares), 1)
        self.assertEqual(self.servicio.detectar_colisiones([j1, j2]), [])

    def test_limpiar_cooldown_reanuda_deteccion(self):
        j1 = JugadorHumano(0, 0, 0, {})
        j2 = JugadorHumano(10, 0, 1, {})
        self.servicio.detectar_colisiones([j1, j2])
        self.servicio.limpiar_cooldown()
        self.assertEqual(len(self.servicio.detectar_colisiones([j1, j2])), 1)

    def test_cooldown_se_agota(self):
        j1 = JugadorHumano(0, 0, 0, {})
        j2 = JugadorHumano(10, 0, 1, {})
        self.servicio.detectar_colisiones([j1, j2])
        self.servicio.detectar_colisiones([j1, j2], self.servicio.COOLDOWN_SEG + 0.01)
        self.assertEqual(len(self.servicio.detectar_colisiones([j1, j2])), 1)

    def test_cooldown_parcial_sigue_bloqueando(self):
        j1 = JugadorHumano(0, 0, 0, {})
        j2 = JugadorHumano(10, 0, 1, {})
        self.servicio.detectar_colisiones([j1, j2])
        self.servicio.detectar_colisiones([j1, j2], self.servicio.COOLDOWN_SEG / 2)
        self.assertEqual(self.servicio.detectar_colisiones([j1, j2]), [])


if __name__ == '__main__':
    unittest.main()