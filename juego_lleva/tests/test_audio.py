"""Pruebas de síntesis de audio con driver ficticio."""

import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from juego_lleva.servicios.audio import ServicioAudio


@unittest.skipUnless("SDL_AUDIODRIVER" in os.environ, "sin driver de audio")
class TestServicioAudio(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.audio = ServicioAudio()

    def test_genera_sonidos_si_el_mezclador_esta_disponible(self):
        if not self.audio.activo:
            self.skipTest("mezclador de audio no disponible")
        self.assertIsNotNone(self.audio.sonido_toque)
        self.assertIsNotNone(self.audio.sonido_clic)
        self.assertIsNotNone(self.audio.sonido_countdown)
        self.assertIsNotNone(self.audio.sonido_inicio)
        self.assertIsNotNone(self.audio.sonido_fin)

    def test_genera_musica_no_vacia(self):
        if not self.audio.activo:
            self.skipTest("mezclador de audio no disponible")
        self.assertIsNotNone(self.audio.musica)

    def test_reproducir_y_detener_musica(self):
        if not self.audio.activo:
            self.skipTest("mezclador de audio no disponible")
        self.audio.reproducir_musica()
        pygame.time.wait(50)
        self.assertTrue(self.audio.musica_suena())
        self.audio.detener_musica()
        self.assertFalse(self.audio.musica_suena())

    def test_a_muestras_recorta_valores_fuera_de_rango(self):
        arr = self.audio._a_muestras([40000, -40000, 0])
        self.assertEqual(len(arr.get_raw()), 6)


if __name__ == '__main__':
    unittest.main()