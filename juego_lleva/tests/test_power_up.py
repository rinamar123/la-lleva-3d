"""Pruebas del modelo y servicio de power-ups."""

import unittest

from juego_lleva.core.config import Config
from juego_lleva.models.jugador_humano import JugadorHumano
from juego_lleva.models.power_up import PowerUp
from juego_lleva.servicios.power_up_service import PowerUpService


def _teclas_minimas():
    return {'arriba': 0, 'abajo': 0, 'izquierda': 0, 'derecha': 0}


class TestPowerUpModel(unittest.TestCase):

    def test_rectangulo_centrado(self):
        pu = PowerUp(500, 400, "velocidad")
        rect = pu.obtener_rectangulo()
        self.assertEqual(rect.center, (500, 400))
        self.assertEqual(rect.width, Config.POWER_UP_TAMAÑO)

    def test_tipo_invalido(self):
        with self.assertRaises(ValueError):
            PowerUp(100, 100, "invisible")

    def test_expirado(self):
        pu = PowerUp(100, 100, "escudo")
        self.assertFalse(pu.expirado())
        pu.vida = 0
        self.assertTrue(pu.expirado())


class TestPowerUpService(unittest.TestCase):

    def setUp(self):
        self.config = Config()
        self.servicio = PowerUpService(self.config)

    def test_efecto_velocidad(self):
        colector = JugadorHumano(100, 100, 0, _teclas_minimas())
        rival = JugadorHumano(500, 500, 1, _teclas_minimas())
        resultado = self.servicio.efecto(colector, rival, "velocidad")
        self.assertEqual(resultado, (0, "velocidad", self.config.POWER_UP_EFECTO_VELOCIDAD_SEG))

    def test_efecto_congelar_victima(self):
        colector = JugadorHumano(100, 100, 0, _teclas_minimas())
        rival = JugadorHumano(500, 500, 1, _teclas_minimas())
        resultado = self.servicio.efecto(colector, rival, "congelar")
        self.assertEqual(resultado, (1, "congelar", self.config.POWER_UP_CONGELAR_SEG))

    def test_efecto_escudo(self):
        colector = JugadorHumano(100, 100, 0, _teclas_minimas())
        rival = JugadorHumano(500, 500, 1, _teclas_minimas())
        resultado = self.servicio.efecto(colector, rival, "escudo")
        self.assertEqual(resultado, (0, "escudo", None))

    def test_crear_respeta_cupo_maximo(self):
        jugadores = [
            JugadorHumano(50, 50, 0, _teclas_minimas()),
            JugadorHumano(700, 700, 1, _teclas_minimas()),
        ]
        self.assertIsNotNone(self.servicio.crear(jugadores, []))
        llenos = [PowerUp(100, 100, "velocidad"), PowerUp(300, 300, "escudo")]
        self.assertIsNone(self.servicio.crear(jugadores, llenos))

    def test_crear_no_se_solapa_con_jugadores(self):
        jugador = JugadorHumano(Config.ANCHO_PANTALLA // 2, Config.ALTO_PANTALLA // 2, 0, _teclas_minimas())
        pu = self.servicio.crear([jugador], [])
        if pu is not None:
            self.assertFalse(jugador.obtener_rectangulo().inflate(200, 200).colliderect(pu.obtener_rectangulo()))


if __name__ == '__main__':
    unittest.main()