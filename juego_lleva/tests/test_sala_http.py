"""Pruebas de la API HTTP de la sala en línea (sin navegador)."""

import asyncio
import json
import os
import socket
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from juego_lleva.red.cliente_web import ClienteEnLinea
from juego_lleva.red.sala import FASE_JUGANDO, SalaEnLinea
from juego_lleva.red.url_sala import VARIABLE_URL
from servidor_web import MAX_CUERPO, crear_manejador


def _peticion(metodo, url, datos=None, content_type="application/json"):
    cuerpo = None
    cabeceras = {}
    if datos is not None:
        if content_type == "application/json":
            cuerpo = json.dumps(datos).encode("utf-8")
        else:
            cuerpo = urlencode(datos).encode("utf-8")
        cabeceras["Content-Type"] = content_type
    solicitud = Request(url, data=cuerpo, headers=cabeceras, method=metodo)
    try:
        with urlopen(solicitud) as respuesta:
            contenido = respuesta.read().decode("utf-8")
            return respuesta.status, (json.loads(contenido) if contenido else {})
    except HTTPError as error:
        contenido = error.read().decode("utf-8")
        return error.code, (json.loads(contenido) if contenido else {})


def _post_crudo(puerto, ruta, cabeceras, cuerpo=b""):
    """POST con cabeceras escritas a mano (para casos que urllib no permite)."""
    solicitud = f"POST {ruta} HTTP/1.1\r\nHost: localhost\r\n"
    for clave, valor in cabeceras:
        solicitud += f"{clave}: {valor}\r\n"
    solicitud += "Connection: close\r\n\r\n"
    with socket.create_connection(("127.0.0.1", puerto), timeout=2) as conexion:
        conexion.sendall(solicitud.encode("utf-8") + cuerpo)
        respuesta = b""
        while True:
            bloque = conexion.recv(4096)
            if not bloque:
                return respuesta.decode("utf-8", "replace")
            respuesta += bloque


class TestApiSalaHttp(unittest.TestCase):

    def setUp(self):
        self.sala = SalaEnLinea(max_jugadores=3, duracion_ronda=10,
                                iniciar_hilo=False)
        self.addCleanup(self.sala.cerrar)
        manejador = crear_manejador(".", self.sala)
        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), manejador)
        self.puerto = self.servidor.server_address[1]
        self.base = f"http://127.0.0.1:{self.puerto}"
        self.hilo = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.hilo.start()
        self.addCleanup(self._detener_servidor)

    def _detener_servidor(self):
        self.servidor.shutdown()
        self.servidor.server_close()

    def test_unirse_devuelve_token(self):
        estado, datos = _peticion("POST", f"{self.base}/api/sala/unirse",
                                  {"nombre": "Ana"})
        self.assertEqual(estado, 200)
        self.assertTrue(datos["ok"])
        self.assertEqual(datos["nombre"], "Ana")

    def test_body_urlencoded_tambien_funciona(self):
        estado, datos = _peticion("POST", f"{self.base}/api/sala/unirse",
                                  {"nombre": "Beto"},
                                  content_type="application/x-www-form-urlencoded")
        self.assertEqual(estado, 200)
        self.assertTrue(datos["ok"])

    def test_sync_con_token_invalido_devuelve_401(self):
        estado, datos = _peticion("POST", f"{self.base}/api/sala/sync",
                                  {"token": "no-existe"})
        self.assertEqual(estado, 401)
        self.assertEqual(datos, {"error": "token_invalido"})

    def test_flujo_completo_hasta_jugando(self):
        _, a = _peticion("POST", f"{self.base}/api/sala/unirse", {"nombre": "Ana"})
        _, b = _peticion("POST", f"{self.base}/api/sala/unirse", {"nombre": "Beto"})

        estado, _ = _peticion("POST", f"{self.base}/api/sala/sync",
                              {"token": a["token"], "listo": True})
        self.assertEqual(estado, 200)
        _peticion("POST", f"{self.base}/api/sala/sync",
                  {"token": b["token"], "listo": True})
        self.sala._tick(1.0 / 30)
        self.sala._tick(3.1)

        estado, snapshot = _peticion(
            "POST", f"{self.base}/api/sala/sync",
            {"token": a["token"], "entrada": {"derecha": True}})
        self.assertEqual(snapshot["fase"], FASE_JUGANDO)
        self.assertEqual(estado, 200)
        self.assertEqual(len(snapshot["jugadores"]), 2)
        self.assertEqual(snapshot["mi_id"], a["id"])

    def test_salir_y_token_queda_invalido(self):
        _, a = _peticion("POST", f"{self.base}/api/sala/unirse", {"nombre": "Ana"})
        estado, datos = _peticion("POST", f"{self.base}/api/sala/salir",
                                  {"token": a["token"]})
        self.assertEqual(estado, 200)
        self.assertEqual(datos, {"ok": True})
        estado, _ = _peticion("POST", f"{self.base}/api/sala/sync",
                              {"token": a["token"]})
        self.assertEqual(estado, 401)

    def test_estado_publico_de_la_sala(self):
        _peticion("POST", f"{self.base}/api/sala/unirse", {"nombre": "Ana"})
        estado, datos = _peticion("GET", f"{self.base}/api/sala")
        self.assertEqual(estado, 200)
        self.assertEqual(datos["jugadores_online"], 1)
        self.assertEqual(datos["nombres"], ["Ana"])

    def test_ruta_api_desconocida_devuelve_404(self):
        estado, datos = _peticion("POST", f"{self.base}/api/sala/otra",
                                  {"a": 1})
        self.assertEqual(estado, 404)
        self.assertEqual(datos, {"error": "ruta_desconocida"})

    def test_content_length_no_numerico_devuelve_400(self):
        respuesta = _post_crudo(self.puerto, "/api/sala/unirse",
                                [("Content-Length", "abc"),
                                 ("Content-Type", "application/json")])
        self.assertIn("400", respuesta.splitlines()[0])
        self.assertIn("content_length_invalido", respuesta)

    def test_cuerpo_demasiado_grande_devuelve_413(self):
        respuesta = _post_crudo(
            self.puerto, "/api/sala/sync",
            [("Content-Length", str(MAX_CUERPO + 1)),
             ("Content-Type", "application/json")])
        self.assertIn("413", respuesta.splitlines()[0])
        self.assertIn("cuerpo_demasiado_grande", respuesta)

    def test_campo_repetido_urlencoded_devuelve_400(self):
        cuerpo = b"nombre=Ana&nombre=Beto"
        respuesta = _post_crudo(
            self.puerto, "/api/sala/unirse",
            [("Content-Length", str(len(cuerpo))),
             ("Content-Type", "application/x-www-form-urlencoded")], cuerpo)
        self.assertIn("400", respuesta.splitlines()[0])
        self.assertIn("campo_nombre_invalido", respuesta)

    def test_token_repetido_urlencoded_devuelve_400(self):
        cuerpo = b"token=a&token=b"
        respuesta = _post_crudo(
            self.puerto, "/api/sala/sync",
            [("Content-Length", str(len(cuerpo))),
             ("Content-Type", "application/x-www-form-urlencoded")], cuerpo)
        self.assertIn("400", respuesta.splitlines()[0])
        self.assertIn("campo_token_invalido", respuesta)

    def test_unirse_con_sala_llena_devuelve_409(self):
        for nombre in ("Ana", "Beto", "Caro"):
            estado, datos = _peticion("POST", f"{self.base}/api/sala/unirse",
                                      {"nombre": nombre})
            self.assertEqual(estado, 200, datos)
        estado, datos = _peticion("POST", f"{self.base}/api/sala/unirse",
                                  {"nombre": "Dana"})
        self.assertEqual(estado, 409)
        self.assertEqual(datos, {"error": "sala_llena"})


class TestClienteEnLineaHttp(unittest.TestCase):
    """El cliente de escritorio debe entenderse con la sala real por HTTP."""

    def setUp(self):
        self.sala = SalaEnLinea(max_jugadores=3, duracion_ronda=10,
                                iniciar_hilo=False)
        self.addCleanup(self.sala.cerrar)
        manejador = crear_manejador(".", self.sala)
        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), manejador)
        self.puerto = self.servidor.server_address[1]
        self.hilo = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.hilo.start()
        self.addCleanup(self._detener_servidor)
        anterior = os.environ.get(VARIABLE_URL)
        os.environ[VARIABLE_URL] = f"http://127.0.0.1:{self.puerto}/"
        self.addCleanup(self._restaurar_url, anterior)

    def _restaurar_url(self, anterior):
        if anterior is None:
            os.environ.pop(VARIABLE_URL, None)
        else:
            os.environ[VARIABLE_URL] = anterior

    def _detener_servidor(self):
        self.servidor.shutdown()
        self.servidor.server_close()

    def test_unirse_y_sincronizar_mandan_json(self):
        """``listo`` y ``entrada`` deben llegar a la sala como bool y dict.

        Si el cuerpo se mandara url-encoded, la sala los descartaría y la
        ronda nunca empezaría: este test falla si el cliente deja de enviar
        JSON de verdad.
        """
        a = ClienteEnLinea()
        b = ClienteEnLinea()
        respuesta = asyncio.run(a.unirse("Ana"))
        self.assertTrue(respuesta["ok"], respuesta)
        asyncio.run(b.unirse("Beto"))

        for _ in range(2):
            asyncio.run(a.sincronizar({"derecha": True}, True))
            estado = asyncio.run(b.sincronizar({"izquierda": True}, True))
        self.assertEqual(estado["listos"], {"0": True, "1": True})

        self.sala._tick(1.0 / 30)
        self.sala._tick(3.1)
        inicio = asyncio.run(a.sincronizar({"derecha": True}, True))
        self.assertEqual(inicio["fase"], FASE_JUGANDO)
        for _ in range(30):
            self.sala._tick(1.0 / 30)
        final = asyncio.run(a.sincronizar({"derecha": True}, True))

        mi_id = inicio["mi_id"]
        x_inicial = next(j["x"] for j in inicio["jugadores"] if j["id"] == mi_id)
        x_final = next(j["x"] for j in final["jugadores"] if j["id"] == mi_id)
        self.assertGreater(x_final, x_inicial,
                           f"la entrada no movió al jugador: {final['jugadores']}")

    def test_token_invalido_llega_como_error(self):
        """Un 401 debe traducirse en ``token_invalido``, no en una excepción."""
        respuesta = asyncio.run(ClienteEnLinea().sincronizar())
        self.assertEqual(respuesta, {"error": "token_invalido"})


if __name__ == '__main__':
    unittest.main()