"""Pruebas del servicio de puntajes."""

import unittest

from juego_lleva.servicios.puntaje import PuntajeService


class TestPuntajeService(unittest.TestCase):

    def setUp(self):
        self.puntaje = PuntajeService()

    def test_registrar_lleva_acumula_tiempos(self):
        self.puntaje.registrar_lleva(0, 10.5)
        self.puntaje.registrar_lleva(0, 5.5)
        self.puntaje.registrar_lleva(1, 2.0)
        self.assertEqual(self.puntaje.tiempos_lleva[0], 16.0)
        self.assertEqual(self.puntaje.tiempos_lleva[1], 2.0)

    def test_obtener_ganador_con_menor_tiempo(self):
        self.puntaje.registrar_lleva(0, 10)
        self.puntaje.registrar_lleva(1, 50)
        self.assertEqual(self.puntaje.obtener_ganador(), 0)

    def test_obtener_ganador_sin_datos_devuelve_none(self):
        self.assertIsNone(self.puntaje.obtener_ganador())

    def test_obtener_ganador_desempata_con_primero(self):
        self.puntaje.registrar_lleva(0, 10)
        self.puntaje.registrar_lleva(1, 10)
        self.assertEqual(self.puntaje.obtener_ganador(), 0)

    def test_reiniciar_limpia_tiempos(self):
        self.puntaje.registrar_lleva(0, 10)
        self.puntaje.reiniciar()
        self.assertEqual(self.puntaje.tiempos_lleva, {})
        self.assertIsNone(self.puntaje.obtener_ganador())


if __name__ == '__main__':
    unittest.main()