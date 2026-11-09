"""Pruebas del servicio de ranking con persistencia en archivo."""

import json
import os
import tempfile
import unittest

from juego_lleva.servicios.ranking import RankingService


class TestRankingService(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.tmpdir.name, "ranking.json")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_archivo_inexistente_carga_vacio(self):
        servicio = RankingService(self.ruta)
        self.assertEqual(servicio.entradas, [])

    def test_registrar_partida_redondea_y_persiste(self):
        servicio = RankingService(self.ruta)
        servicio.registrar_partida("Ana", 12.345, {"Ana": 12.345, "Beto": 40.678})

        con_redondeo = servicio.entradas[0]
        self.assertEqual(con_redondeo["ganador"], "Ana")
        self.assertEqual(con_redondeo["tiempo"], 12.35)
        self.assertEqual(con_redondeo["jugadores"]["Beto"], 40.68)

        recargado = RankingService(self.ruta)
        self.assertEqual(len(recargado.entradas), 1)
        self.assertEqual(recargado.entradas[0]["ganador"], "Ana")

    def test_obtener_top_ordena_por_menor_tiempo_y_limita(self):
        servicio = RankingService(self.ruta)
        servicio.registrar_partida("Slow", 50, {"Slow": 50})
        servicio.registrar_partida("Fast", 5, {"Fast": 5})
        servicio.registrar_partida("Mid", 25, {"Mid": 25})
        servicio.registrar_partida("Last", 60, {"Last": 60})

        top = servicio.obtener_top(3)
        self.assertEqual([e["ganador"] for e in top], ["Fast", "Mid", "Slow"])

    def test_archivo_corrupto_carga_vacio(self):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write("{esto no es json")
        servicio = RankingService(self.ruta)
        self.assertEqual(servicio.entradas, [])

    def test_entradas_sin_archivo_previo(self):
        servicio = RankingService(self.ruta)
        servicio.registrar_partida("Sola", 3, {"Sola": 3})

        with open(self.ruta, encoding="utf-8") as f:
            datos = json.load(f)
        self.assertEqual(len(datos), 1)
        self.assertIn("fecha", datos[0])


if __name__ == '__main__':
    unittest.main()