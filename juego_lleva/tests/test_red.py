"""Pruebas del multijugador en red: protocolo e integración cliente-servidor."""

import threading
import time
import unittest

from juego_lleva.red.protocolo import (
    TIPO_ESTADO,
    TIPO_POSICION,
    codificar_mensaje,
    extraer_linea,
)
from juego_lleva.red.servidor import ServidorMultijugador
from juego_lleva.red.cliente import ClienteMultijugador


def esperar(condicion, intentos=100, pausa=0.01):
    """Espera hasta que la condición sea verdadera o se acaben los intentos."""
    for _ in range(intentos):
        if condicion():
            return True
        time.sleep(pausa)
    return condicion()


class TestProtocolo(unittest.TestCase):

    def test_codificar_termina_en_nueva_linea(self):
        datos = codificar_mensaje({"tipo": TIPO_POSICION, "x": 1, "y": 2})
        self.assertTrue(datos.endswith(b"\n"))
        self.assertEqual(datos, b'{"tipo": "posicion", "x": 1, "y": 2}\n')

    def test_extraer_linea_completa(self):
        mensaje, resto = extraer_linea('{"tipo": "posicion", "x": 1, "y": 2}\n{"tipo": "estado"}')
        self.assertEqual(mensaje, {"tipo": TIPO_POSICION, "x": 1, "y": 2})
        self.assertEqual(resto, '{"tipo": "estado"}')

    def test_extraer_linea_incompleta(self):
        mensaje, resto = extraer_linea('{"tipo": "posicion", "x": 1')
        self.assertIsNone(mensaje)
        self.assertEqual(resto, '{"tipo": "posicion", "x": 1')

    def test_extraer_linea_vacia_se_omite(self):
        mensaje, resto = extraer_linea("\nrestante")
        self.assertIsNone(mensaje)
        self.assertEqual(resto, "restante")

    def test_redondear_protocolo(self):
        original = {"tipo": TIPO_ESTADO, "jugadores": {"1": {"x": 10, "y": 20}}}
        mensaje, resto = extraer_linea(codificar_mensaje(original).decode("utf-8"))
        self.assertEqual(mensaje, original)
        self.assertEqual(resto, "")

    def test_procesar_buffer_consume_y_devuelve_restante(self):
        cliente = ClienteMultijugador(silencioso=True)
        resto = cliente._procesar_buffer(
            '{"tipo": "estado", "jugadores": {"1": {"x": 10, "y": 20}}}\n'
            '{"tipo": "estado"'
        )
        self.assertEqual(resto, '{"tipo": "estado"')
        self.assertIn("1", cliente.jugadores)


class TestServidorCliente(unittest.TestCase):
    """Integración: un servidor real en un hilo y un cliente conectado."""

    def setUp(self):
        self.servidor = ServidorMultijugador("127.0.0.1", 0, silencioso=True)
        self.hilo_servidor = threading.Thread(target=self.servidor.iniciar, daemon=True)
        self.hilo_servidor.start()
        self.assertTrue(
            esperar(lambda: self.servidor.puerto_real is not None),
            "El servidor no llegó a abrir el puerto",
        )
        self.cliente = ClienteMultijugador(
            "127.0.0.1", self.servidor.puerto_real, silencioso=True
        )

    def tearDown(self):
        self.cliente.cerrar()
        self.servidor.detener()

    def test_conexion_asigna_id_y_recibe_estado(self):
        self.cliente.conectar()
        self.assertTrue(esperar(lambda: self.cliente.mi_id is not None))
        self.assertEqual(self.cliente.mi_id, "1")
        self.assertTrue(esperar(lambda: "1" in self.cliente.obtener_jugadores()))

    def test_enviar_posicion_actualiza_estado(self):
        self.cliente.conectar()
        self.assertTrue(esperar(lambda: self.cliente.mi_id is not None))

        self.assertTrue(self.cliente.enviar_posicion(150, 200))
        self.assertTrue(
            esperar(
                lambda: self.cliente.obtener_jugadores().get("1", {}).get("x") == 150
            )
        )
        estado = self.cliente.obtener_jugadores()["1"]
        self.assertEqual(estado["y"], 200)
        self.assertEqual(estado["color"], [50, 150, 255])

    def test_no_envia_sin_conexion(self):
        self.assertFalse(self.cliente.enviar_posicion(0, 0))

    def test_multiples_posiciones_consecutivas(self):
        self.cliente.conectar()
        self.assertTrue(esperar(lambda: self.cliente.mi_id is not None))

        for x, y in ((10, 20), (30, 40), (50, 60)):
            self.assertTrue(self.cliente.enviar_posicion(x, y))

        self.assertTrue(
            esperar(
                lambda: self.cliente.obtener_jugadores().get("1", {}).get("x") == 50
            )
        )
        estado = self.cliente.obtener_jugadores()["1"]
        self.assertEqual((estado["x"], estado["y"]), (50, 60))


if __name__ == "__main__":
    unittest.main()