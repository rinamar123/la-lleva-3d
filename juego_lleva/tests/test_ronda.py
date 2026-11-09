"""Pruebas de las reglas de la ronda (regla clásica de La Lleva)."""

import unittest

from juego_lleva.servicios.puntaje import PuntajeService
from juego_lleva.servicios.ronda import RondaService


class JugadorFake:
    """Jugador mínimo para probar la lógica de la ronda."""

    def __init__(self, id_jugador):
        self.id = id_jugador
        self.es_lleva = False


class TestRondaService(unittest.TestCase):

    def setUp(self):
        self.puntaje = PuntajeService()
        self.ronda = RondaService(self.puntaje)
        self.p0 = JugadorFake(0)
        self.p1 = JugadorFake(1)

    def test_transferir_lleva_registra_cambia_roles_y_devuelve_nuevo_inicio(self):
        self.p0.es_lleva = True
        inicio = self.ronda.transferir_lleva(self.p0, self.p1, 10, 0)

        self.assertEqual(inicio, 10)
        self.assertFalse(self.p0.es_lleva)
        self.assertTrue(self.p1.es_lleva)
        self.assertEqual(self.puntaje.tiempos_lleva[0], 10)

    def test_transferir_lleva_acumula_tiempo_de_quien_la_tenia(self):
        self.p0.es_lleva = True
        self.ronda.transferir_lleva(self.p0, self.p1, 10, 2)

        self.assertEqual(self.puntaje.tiempos_lleva[0], 8)
        self.assertTrue(self.p1.es_lleva)

    def test_transferir_lleva_no_registra_negativos(self):
        self.p0.es_lleva = True
        self.ronda.transferir_lleva(self.p0, self.p1, 10, 15)

        self.assertEqual(self.puntaje.tiempos_lleva[0], 0)

    def test_cerrar_lleva_actual_registra_al_que_lleva_al_final(self):
        self.p1.es_lleva = True
        self.p0.es_lleva = False
        self.ronda.cerrar_lleva_actual([self.p0, self.p1], 60, 10)

        self.assertEqual(self.puntaje.tiempos_lleva[1], 50)
        self.assertNotIn(0, self.puntaje.tiempos_lleva)

    def test_cerrar_lleva_actual_sin_lleva_no_registra(self):
        self.ronda.cerrar_lleva_actual([self.p0, self.p1], 60, 0)
        self.assertEqual(self.puntaje.tiempos_lleva, {})

    def test_asignar_lleva_inicial_a_un_solo_jugador(self):
        self.ronda.asignar_lleva_inicial([self.p0, self.p1], 1)

        self.assertFalse(self.p0.es_lleva)
        self.assertTrue(self.p1.es_lleva)

    def test_regla_clasica_completa(self):
        self.ronda.asignar_lleva_inicial([self.p0, self.p1], 0)
        inicio = self.ronda.transferir_lleva(self.p0, self.p1, 10, 0)
        self.ronda.cerrar_lleva_actual([self.p0, self.p1], 60, inicio)

        self.assertEqual(self.puntaje.tiempos_lleva[0], 10)
        self.assertEqual(self.puntaje.tiempos_lleva[1], 50)
        self.assertEqual(self.puntaje.obtener_ganador(), 0)


if __name__ == '__main__':
    unittest.main()