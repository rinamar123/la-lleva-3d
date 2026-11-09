"""Pruebas del servicio de configuración persistente."""

import json
import os
import tempfile
import unittest

from juego_lleva.servicios.configuracion import ConfiguracionService


class TestConfiguracionService(unittest.TestCase):

    def setUp(self):
        self.dir_tmp = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.dir_tmp.name, "settings.json")
        self.servicio = ConfiguracionService(self.ruta)

    def tearDown(self):
        self.dir_tmp.cleanup()

    def test_valores_por_defecto(self):
        self.assertEqual(self.servicio.obtener("duracion_ronda"), 60)
        self.assertEqual(self.servicio.obtener("dificultad_ia"), "normal")
        self.assertEqual(self.servicio.obtener("volumen_musica"), 0.8)
        self.assertEqual(self.servicio.obtener("volumen_sfx"), 0.8)
        self.assertFalse(self.servicio.obtener("pantalla_completa"))

    def test_establecer_y_recargar(self):
        self.servicio.establecer("duracion_ronda", 90)
        self.servicio.establecer("dificultad_ia", "dificil")
        self.servicio.establecer("volumen_sfx", 0.3)

        recargado = ConfiguracionService(self.ruta)
        self.assertEqual(recargado.obtener("duracion_ronda"), 90)
        self.assertEqual(recargado.obtener("dificultad_ia"), "dificil")
        self.assertEqual(recargado.obtener("volumen_sfx"), 0.3)

    def test_normaliza_valores_invalidos(self):
        self.assertEqual(self.servicio.establecer("duracion_ronda", 999), 60)
        self.assertEqual(self.servicio.establecer("dificultad_ia", "imposible"), "normal")
        self.assertEqual(self.servicio.establecer("volumen_musica", 5.0), 1.0)
        self.assertEqual(self.servicio.establecer("volumen_sfx", -1.0), 0.0)

    def test_siguiente_cicla_opciones(self):
        self.assertEqual(self.servicio.siguiente("duracion_ronda", 1), 90)
        self.assertEqual(self.servicio.siguiente("duracion_ronda", 1), 30)
        self.assertEqual(self.servicio.siguiente("duracion_ronda", -1), 90)

        self.assertEqual(self.servicio.siguiente("dificultad_ia", 1), "dificil")
        self.assertEqual(self.servicio.siguiente("dificultad_ia", 1), "facil")

        self.servicio.establecer("volumen_sfx", 0.95)
        self.assertEqual(self.servicio.siguiente("volumen_sfx", 1), 1.0)
        self.assertEqual(self.servicio.siguiente("volumen_sfx", 1), 1.0)

        self.assertTrue(self.servicio.siguiente("pantalla_completa", 1))
        self.assertFalse(self.servicio.siguiente("pantalla_completa", -1))

    def test_archivo_corrupto_usa_defaults(self):
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            archivo.write("no soy json")
        servicio = ConfiguracionService(self.ruta)
        self.assertEqual(servicio.obtener("duracion_ronda"), 60)
        self.assertEqual(servicio.obtener("volumen_musica"), 0.8)

    def test_archivo_con_json_valido(self):
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            json.dump({"duracion_ronda": 30, "desconocida": 1}, archivo)
        servicio = ConfiguracionService(self.ruta)
        self.assertEqual(servicio.obtener("duracion_ronda"), 30)
        self.assertEqual(servicio.obtener("dificultad_ia"), "normal")


if __name__ == '__main__':
    unittest.main()