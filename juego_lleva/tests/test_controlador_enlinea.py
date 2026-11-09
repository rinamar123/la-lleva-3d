"""Pruebas del modo en línea (ControladorEnLinea) con un cliente simulado."""

import asyncio
import builtins
import copy
import os
import tempfile
import types
import unittest
from unittest import mock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from juego_lleva.core.config import Config
from juego_lleva.core.controlador_enlinea import ControladorEnLinea
from juego_lleva.core.juego import Juego
from juego_lleva.models.obstaculo import Obstaculo
from juego_lleva.red import cliente_web
from juego_lleva.red.cliente_web import ClienteEnLinea
from juego_lleva.red.sala import FASE_ESPERANDO, FASE_FIN, FASE_JUGANDO
from juego_lleva.ui.acciones import ALTO_BOTON_MENU, rects_sala


def _jugador(id_j, x, y, es_lleva=False, nombre=None):
    """Construye un jugador como lo envía el servidor."""
    return {
        "id": id_j,
        "nombre": nombre or f"J{id_j + 1}",
        "x": x,
        "y": y,
        "vx": 0.0,
        "vy": 0.0,
        "es_lleva": es_lleva,
        "direccion_cara": 1,
        "velocidad_abs": 0.0,
        "escudo": False,
        "congelado": 0.0,
        "tropezando": 0.0,
        "factor_velocidad": 1.0,
        "listo": True,
    }


def snapshot_sala():
    """Snapshot mínimo de la sala de espera."""
    return {
        "ok": True,
        "tipo": "sala",
        "fase": FASE_ESPERANDO,
        "mi_id": 2,
        "jugadores_online": 2,
        "max_jugadores": 3,
        "jugadores": [
            _jugador(0, 100.0, 200.0, True, "Ana"),
            _jugador(1, 400.0, 200.0, False, "Beto"),
            _jugador(2, 700.0, 500.0, False, "Yo"),
        ],
        "obstaculos": [],
        "power_ups": [],
        "eventos": [],
        "tiempos_lleva": {"0": 5.0},
        "efectos_activos": {},
    }


def snapshot_jugando(mi_id=2, eventos=None):
    """Snapshot de la partida en curso."""
    return {
        "ok": True,
        "tipo": "partida",
        "fase": FASE_JUGANDO,
        "mi_id": mi_id,
        "jugadores_online": 3,
        "max_jugadores": 3,
        "jugadores": [
            _jugador(0, 100.0, 200.0, True, "Ana"),
            _jugador(1, 400.0, 200.0, False, "Beto"),
            _jugador(2, 700.0, 500.0, False, "Yo"),
        ],
        "obstaculos": [{"x": 300.0, "y": 300.0, "tipo": "libro"}],
        "power_ups": [{"x": 500.0, "y": 400.0, "tipo": "velocidad"}],
        "eventos": eventos or [],
        "tiempos_lleva": {"0": 5.0},
        "efectos_activos": {"1": {"congelar": 1.0}},
        "tiempo_ronda": 30.0,
        "duracion_ronda": 60.0,
    }


def snapshot_fin(ganador=0):
    """Snapshot de la fase de fin de ronda."""
    return {
        "ok": True,
        "tipo": "fin",
        "fase": FASE_FIN,
        "mi_id": 2,
        "jugadores_online": 3,
        "max_jugadores": 3,
        "jugadores": [
            _jugador(0, 100.0, 200.0, True, "Ana"),
            _jugador(1, 400.0, 200.0, False, "Beto"),
            _jugador(2, 700.0, 500.0, False, "Yo"),
        ],
        "obstaculos": [],
        "power_ups": [],
        "eventos": [],
        "tiempos_lleva": {"0": 10.0, "1": 50.0, "2": 0.0},
        "efectos_activos": {},
        "tiempo_ronda": 60.0,
        "duracion_ronda": 60.0,
        "ganador": ganador,
    }


class ClienteSimulado:
    """Cliente de sala mutable para pruebas, sin red.

    Conserva la última respuesta y la repite cuando se agotan las
    respuestas programadas (como hace el servidor real, que mantiene la
    misma fase entre snapshots).
    """

    PERIODO_SYNC = 1.0 / 30
    SALA_LLENA = "sala_llena"
    PARTIDA_EN_CURSO = "partida_en_curso"
    TOKEN_INVALIDO = "token_invalido"

    def __init__(self, respuestas=None, fallar_unirse=False):
        self.token = "t1"
        self.mi_id = 2
        self.nombre = "Yo"
        self._respuestas = list(respuestas or [])
        self.fallar_unirse = fallar_unirse
        self.envios = []
        self.salidas = 0
        self._ultima = snapshot_sala()

    @property
    def conectado(self):
        return self.token is not None

    async def unirse(self, nombre):
        if self.fallar_unirse:
            return {"error": "sin_conexion"}
        return {
            "ok": True,
            "token": "t1",
            "id": 2,
            "nombre": nombre,
            "fase": FASE_ESPERANDO,
        }

    async def sincronizar(self, entrada=None, listo=None):
        self.envios.append({"entrada": entrada, "listo": listo})
        if self._respuestas:
            self._ultima = self._respuestas.pop(0)
        return self._ultima

    async def salir(self):
        if self.token is None:
            return {"error": "token_invalido"}
        self.salidas += 1
        self.token = None
        return {"ok": True}


class TestControladorEnLinea(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.juego = Juego(Config())
        self.dir_tmp = tempfile.TemporaryDirectory()
        self.juego.configuracion.ruta = os.path.join(self.dir_tmp.name, "settings.json")
        self.juego.ranking_service.ruta = os.path.join(
            self.dir_tmp.name, "ranking.json"
        )
        self.juego.config.PLATAFORMA_WEB = True

    def tearDown(self):
        self.dir_tmp.cleanup()

    def _crear_ctrl(self, cliente):
        """Arranca el modo en línea como lo haría el menú e inyecta el cliente."""
        self.juego.modo = "en_linea"
        self.juego.nombres = ["Yo"]
        self.juego._iniciar_partida_en_linea()
        ctrl = self.juego.ctrl_enlinea
        ctrl.cliente = cliente
        return ctrl

    def _bombear(self, ctrl, veces=8):
        """Ejecuta frames del controlador dejando avanzar el bucle de sync."""

        async def escenario():
            for _ in range(veces):
                await ctrl.actualizar(0.03)
                await asyncio.sleep(0)
            ctrl.detener()

        asyncio.run(escenario())

    def test_unirse_muestra_sala_y_crea_jugadores(self):
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_sala()]))
        self._bombear(ctrl)
        self.assertEqual(ctrl.mi_id, 2)
        self.assertEqual(ctrl.fase, FASE_ESPERANDO)
        self.assertEqual(self.juego.estado, "en_linea")
        self.assertEqual([j.id for j in self.juego.jugadores], [0, 1, 2])
        self.assertEqual(len(self.juego.jugadores_views), 3)
        self.assertTrue(self.juego.jugadores[0].es_lleva)
        self.assertEqual(self.juego.jugadores[2].nombre, "Yo")

    def test_entrada_se_envia_a_la_sala(self):
        cliente = ClienteSimulado()
        ctrl = self._crear_ctrl(cliente)
        self._bombear(ctrl)
        self.assertGreaterEqual(len(cliente.envios), 1)
        entrada = cliente.envios[-1]["entrada"]
        self.assertEqual(set(entrada), {"arriba", "abajo", "izquierda", "derecha"})

    def test_snapshot_jugando_aplica_entorno_y_efectos(self):
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_jugando()]))
        self._bombear(ctrl, veces=10)
        self.assertEqual(ctrl.fase, FASE_JUGANDO)
        obstaculos = self.juego.gestor_modos.entorno.obstaculos
        self.assertEqual(len(obstaculos), 1)
        self.assertIsInstance(obstaculos[0], Obstaculo)
        self.assertEqual(obstaculos[0].tipo, "libro")
        self.assertEqual(len(self.juego.power_ups), 1)
        self.assertIn("congelar", self.juego.efectos_activos.get(1, {}))
        self.assertEqual(self.juego.tiempo_ronda, 30.0)

    def test_eventos_de_toque_escudo_powerup_y_fin_generan_toasts(self):
        eventos = [
            {"seq": 1, "tipo": "escudo", "objetivo": 1, "x": 400.0, "y": 200.0},
            {"seq": 2, "tipo": "toque", "a": 0, "b": 1, "x": 300.0, "y": 300.0},
            {
                "seq": 3,
                "tipo": "power_up",
                "objetivo": 2,
                "efecto": "congelar",
                "x": 500.0,
                "y": 200.0,
            },
            {"seq": 4, "tipo": "fin", "ganador": 0},
        ]
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_jugando(eventos=eventos)]))
        self._bombear(ctrl, veces=12)
        textos = [t["texto"] for t in self.juego.toasts]
        self.assertTrue(any("bloqueo" in t for t in textos), textos)
        self.assertTrue(any("toco a" in t for t in textos), textos)
        self.assertTrue(any("congelado" in t for t in textos), textos)
        self.assertTrue(any("Fin de ronda" in t for t in textos), textos)

    def test_flash_de_toque_desaparece_durante_frames_online(self):
        ctrl = self._crear_ctrl(ClienteSimulado())
        self.juego.toque_flash = 0.12

        ctrl._gestionar_juego(0.05)
        self.assertAlmostEqual(self.juego.toque_flash, 0.07, places=6)
        ctrl._gestionar_juego(0.05)
        self.assertAlmostEqual(self.juego.toque_flash, 0.02, places=6)
        ctrl._gestionar_juego(0.05)
        self.assertEqual(self.juego.toque_flash, 0.0)

    def test_fin_ronda_aplica_puntajes(self):
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_fin()]))
        self._bombear(ctrl, veces=10)
        self.assertEqual(ctrl.fase, FASE_FIN)
        self.assertEqual(self.juego.puntaje_service.tiempos_lleva[0], 10.0)
        self.assertEqual(self.juego.puntaje_service.tiempos_lleva[1], 50.0)

    def test_power_up_objetivo_muestra_toast(self):
        eventos = [
            {
                "seq": 1,
                "tipo": "power_up",
                "objetivo": 1,
                "efecto": "congelar",
                "x": 500.0,
                "y": 200.0,
            },
        ]
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_jugando(eventos=eventos)]))
        self._bombear(ctrl, veces=10)
        textos = [t["texto"] for t in self.juego.toasts]
        self.assertTrue(any("congelado" in t for t in textos), textos)

    def test_salir_vuelve_al_menu_y_notifica_la_sala(self):
        cliente = ClienteSimulado([snapshot_sala()])
        self._crear_ctrl(cliente)

        async def escenario():
            await self.juego.ctrl_enlinea.actualizar(0.03)
            await asyncio.sleep(0)
            self.juego._salir_en_linea()
            await asyncio.sleep(0)

        asyncio.run(escenario())
        self.assertEqual(self.juego.estado, "menu")
        self.assertIsNone(self.juego.ctrl_enlinea)
        self.assertFalse(self.juego.interfaz.en_linea)
        self.assertEqual(cliente.salidas, 1)

    def test_detener_envia_la_salida_con_el_token_intacto(self):
        cliente = ClienteSimulado([snapshot_sala()])
        ctrl = self._crear_ctrl(cliente)

        async def escenario():
            await ctrl.actualizar(0.03)
            await asyncio.sleep(0)
            ctrl.detener()
            self.assertIsNotNone(
                cliente.token, "el token se borró antes de enviar salir"
            )
            await asyncio.sleep(0)
            self.assertEqual(cliente.salidas, 1)
            await asyncio.sleep(0)

        asyncio.run(escenario())
        self.assertIsNone(cliente.token)
        self.assertIsNone(cliente.mi_id)

    def test_unirse_reintenta_hasta_conectar(self):
        cliente = ClienteSimulado()
        ctrl = self._crear_ctrl(cliente)
        cliente.fallar_unirse = True

        async def escenario():
            await ctrl._intentar_unirse(0.0)
            self.assertEqual(ctrl.fase, ControladorEnLinea.FASE_CONECTANDO)
            cliente.fallar_unirse = False
            await ctrl._intentar_unirse(1.0)
            ctrl.detener()

        asyncio.run(escenario())
        self.assertEqual(ctrl.fase, FASE_ESPERANDO)

    def test_sala_llena_aborta_y_vuelve_al_menu(self):
        cliente = ClienteSimulado()

        async def unirse_llena(nombre):
            return {"error": cliente.SALA_LLENA}

        cliente.unirse = unirse_llena
        self._crear_ctrl(cliente)

        async def escenario():
            await self.juego.ctrl_enlinea.actualizar(0.03)
            await asyncio.sleep(0)

        asyncio.run(escenario())
        self.assertEqual(self.juego.estado, "menu")
        self.assertIsNone(self.juego.ctrl_enlinea)

    def test_snapshot_sin_mi_id_no_reemplaza(self):
        ctrl = self._crear_ctrl(ClienteSimulado())
        ctrl.mi_id = 5
        snap = snapshot_jugando()
        snap.pop("mi_id", None)
        ctrl._aplicar_snapshot(snap)
        self.assertEqual(ctrl.mi_id, 5)

    def test_jugador_local_responde_a_la_entrada_entre_snapshots(self):
        """La predicción local debe mover al jugador propio al instante."""
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_jugando()]))
        self._bombear(ctrl)
        self.assertIsNotNone(ctrl._sim_local)
        local = self.juego.jugadores[2]
        self.assertEqual((local.x, local.y), (700.0, 500.0))
        ctrl.entrada["derecha"] = True
        ctrl._predecir_jugador_local(local, ctrl._t_pred + 1.0)
        self.assertGreater(local.x, 700.0)
        self.assertGreater(local.vx, 0.0)
        self.assertAlmostEqual(local.y, 500.0, delta=0.5)

        rival = self.juego.jugadores[0]
        self.assertEqual(rival.x, 100.0)

    def test_prediccion_local_integra_solo_el_delta_desde_el_frame_anterior(self):
        """La predicción por frame no debe volver a integrar todo el RTT."""
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_jugando()]))
        self._bombear(ctrl)
        ctrl.entrada["derecha"] = True
        ctrl._t_pred = 100.0
        ctrl._sim_local.x = 700.0
        ctrl._sim_local.y = 500.0
        ctrl._sim_local.vx = 0.0
        ctrl._sim_local.vy = 0.0

        esperado = copy.deepcopy(ctrl._sim_local)
        teclas = {
            pygame.K_w: False,
            pygame.K_s: False,
            pygame.K_a: False,
            pygame.K_d: True,
        }
        esperado.mover(teclas, False, 0.1)
        esperado.mover(teclas, False, 0.1)

        local = self.juego.jugadores[2]
        ctrl._predecir_jugador_local(local, 100.1)
        primera_x = local.x
        ctrl._predecir_jugador_local(local, 100.2)

        self.assertEqual(ctrl._t_pred, 100.2)
        self.assertAlmostEqual(local.x, esperado.x, places=5)
        self.assertAlmostEqual(local.vx, esperado.vx, places=5)
        self.assertGreater(local.x, primera_x)

    def test_correccion_autoritativa_local_se_aplica_suavemente(self):
        """Una diferencia pequeña del servidor no debe teletransportar el sprite."""
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_jugando()]))
        self._bombear(ctrl)
        local = self.juego.jugadores[2]
        posicion_anterior = local.x

        nueva = snapshot_jugando()
        nueva["jugadores"][2]["x"] += 20.0
        with mock.patch(
            "juego_lleva.core.controlador_enlinea.time.monotonic", return_value=100.0
        ):
            ctrl._aplicar_snapshot(nueva)
            ctrl._predecir_jugador_local(local, 100.06)
            posicion_intermedia = local.x
            ctrl._predecir_jugador_local(local, 100.12)

        self.assertGreater(posicion_intermedia, posicion_anterior)
        self.assertLess(posicion_intermedia, posicion_anterior + 20.0)
        self.assertGreater(local.x, posicion_intermedia)

    def test_prediccion_local_congelada_no_avanza(self):
        """La predicción respeta el bloqueo de movimiento del servidor."""
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_jugando()]))
        self._bombear(ctrl)
        local = self.juego.jugadores[2]
        ctrl._sim_local.congelado = 1.0
        ctrl.entrada["derecha"] = True
        ctrl.juego.gestor_modos.entorno.obstaculos = []
        x_inicial = ctrl._sim_local.x

        ctrl._predecir_jugador_local(local, ctrl._t_pred + 0.1)

        self.assertAlmostEqual(ctrl._sim_local.x, x_inicial)
        self.assertAlmostEqual(local.x, x_inicial)

    def test_reloj_prediccion_avanza_sin_obstaculos(self):
        """Un escenario sin cajas no debe volver a integrar el tiempo anterior."""
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_jugando()]))
        self._bombear(ctrl)
        local = self.juego.jugadores[2]
        ctrl.juego.gestor_modos.entorno.obstaculos = []
        ctrl.entrada["derecha"] = True
        ctrl._t_pred = 100.0

        ctrl._predecir_jugador_local(local, 100.1)

        self.assertEqual(ctrl._t_pred, 100.1)

    def test_rivales_se_interpolan_entre_snapshots_con_buffer(self):
        """Renderiza el punto a 80 ms antes del tiempo actual, entre muestras."""
        ctrl = self._crear_ctrl(ClienteSimulado())
        primera = snapshot_jugando()
        segunda = snapshot_jugando()
        primera["jugadores"][0]["x"] = 0.0
        segunda["jugadores"][0]["x"] = 100.0

        with mock.patch(
            "juego_lleva.core.controlador_enlinea.time.monotonic",
            side_effect=(9.99, 10.0, 10.09, 10.1, 10.14),
        ):
            ctrl._aplicar_snapshot(primera)
            ctrl._aplicar_snapshot(segunda)
            ctrl._aplicar_posicion_mostrada()

        self.assertAlmostEqual(self.juego.jugadores[0].x, 60.0, places=5)

    def test_prediccion_respeto_limite_de_pantalla(self):
        """La predicción no debe sacar al jugador local de la pantalla."""
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_jugando()]))
        self._bombear(ctrl)
        local = self.juego.jugadores[2]
        ctrl.entrada["izquierda"] = True
        for _ in range(200):
            ctrl._predecir_jugador_local(local, ctrl._t_pred + 0.3)
            ctrl._predecir_jugador_local(local, ctrl._t_pred + 0.6)
        self.assertGreaterEqual(local.x, 0.0)
        self.assertLessEqual(
            local.x, ctrl._config().ANCHO_PANTALLA - ctrl._config().TAMAÑO_JUGADOR
        )

    def test_cliente_web_constantes_y_atributos(self):
        cliente = ClienteEnLinea()
        self.assertIsNone(cliente.token)
        self.assertIsNone(cliente.mi_id)
        self.assertIsNone(cliente.nombre)
        self.assertFalse(cliente.conectado)
        self.assertGreater(cliente.PERIODO_SYNC, 0)

    def test_post_wasm_cede_el_control_al_navegador(self):
        """El sondeo del POST debe ceder al navegador (si no, SDL no bombea input).

        Con ``asyncio.sleep(0)`` el bucle solo rota dentro de wasm, la cola de
        tareas del navegador se congela y los clics llegan segundos tarde.
        """

        class Ubicacion:
            origin = "http://localhost:8000"

        class PlataformaFalsa:
            class Ventana:
                lallevaFetchOk = True
                location = Ubicacion()

                def __init__(self):
                    self.leidas = 0
                    self.url = None

                def lallevaPost(self, url, datos):
                    self.url = url
                    self.datos = datos

                @property
                def pglalleva(self):
                    self.leidas += 1
                    return types.SimpleNamespace(
                        done=self.leidas > 2, error="", text='{"ok": true}'
                    )

            window = Ventana()

        class AsyncioFalso:
            """Registra los retardos pedidos y no bloquea la prueba."""

            def __init__(self):
                self.esperas = []

            async def sleep(self, retardo, *args, **kwargs):
                self.esperas.append(retardo)
                await asyncio.sleep(0)

        ventana = PlataformaFalsa.window
        plataforma = PlataformaFalsa()
        asyncio_falso = AsyncioFalso()
        anterior = getattr(builtins, "__EMSCRIPTEN__", None)
        builtins.__EMSCRIPTEN__ = plataforma
        try:
            with mock.patch.object(cliente_web, "asyncio", asyncio_falso):
                texto = asyncio.run(
                    ClienteEnLinea()._post_wasm("/api/sala/sync", {"a": 1})
                )
        finally:
            if anterior is None:
                del builtins.__EMSCRIPTEN__
            else:
                builtins.__EMSCRIPTEN__ = anterior

        self.assertEqual(texto, '{"ok": true}')
        self.assertEqual(ventana.url, "http://localhost:8000/api/sala/sync")
        self.assertTrue(asyncio_falso.esperas, "el sondeo no llegó a esperar")
        self.assertTrue(
            all(retardo > 0 for retardo in asyncio_falso.esperas),
            f"el sondeo gira sin ceder: {asyncio_falso.esperas}",
        )

    def test_snapshot_sala_maneja_mouse_pos(self):
        ctrl = self._crear_ctrl(ClienteSimulado([snapshot_sala()]))
        x_listo, x_salir, y_btn, btn_ancho, btn_alto = rects_sala(
            self.juego.config.ANCHO_PANTALLA
        )
        centro_listo = (x_listo + btn_ancho // 2, y_btn + btn_alto // 2)
        centro_salir = (x_salir + btn_ancho // 2, y_btn + btn_alto // 2)

        async def escenario():
            for _ in range(8):
                self.juego.mouse_pos = centro_listo
                await ctrl.actualizar(0.03)
                await asyncio.sleep(0)
            ctrl.detener()

        asyncio.run(escenario())
        self.assertEqual(ctrl.fase, FASE_ESPERANDO)
        self.assertIsNotNone(ctrl.snapshot)
        self.assertNotEqual(
            self.juego.pantalla.get_at((x_listo + 20, y_btn + 8))[:3],
            Config.COLOR_FONDO,
        )
        self.assertEqual(
            self.juego.acciones_ui.detectar_sala(centro_listo, True), "listo"
        )
        self.assertEqual(
            self.juego.acciones_ui.detectar_sala(centro_salir, True), "salir"
        )
        self.assertIsNone(
            self.juego.acciones_ui.detectar_sala((centro_listo[0], y_btn - 1), True)
        )

    def test_procesar_frame_async_flujo_completo(self):
        """Recorre captura -> dispatch online -> fundido como en la web."""
        fake = ClienteSimulado([snapshot_jugando()])
        self._crear_ctrl(fake)

        async def escenario():
            for _ in range(10):
                await self.juego.procesar_frame_async()
                await asyncio.sleep(0)
            self.juego._salir_en_linea()

        asyncio.run(escenario())
        self.assertEqual(self.juego.estado, "menu")
        self.assertEqual([getattr(j, "id", None) for j in self.juego.jugadores], [])


class TestGeometriaBotones(unittest.TestCase):
    """El dibujo y la hitbox de los botones comparten la misma geometría."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_botones_del_menu_no_comparten_pixel(self):
        juego = Juego(Config())
        escala = juego.interfaz.escala_ui
        botones = juego.interfaz.BOTONES_MENU
        x = juego.config.ANCHO_PANTALLA // 2
        alto = int(ALTO_BOTON_MENU * escala)
        y_primero = int(botones[0][2] * escala)
        y_segundo = int(botones[1][2] * escala)
        acciones = juego.acciones_ui

        self.assertEqual(
            acciones.detectar_menu((x, y_primero + alto - 1), True, botones, escala),
            botones[0][1],
        )
        self.assertIsNone(
            acciones.detectar_menu((x, y_primero + alto), True, botones, escala)
        )
        self.assertEqual(
            acciones.detectar_menu((x, y_segundo), True, botones, escala), botones[1][1]
        )
        self.assertIsNone(
            acciones.detectar_menu((x, y_primero + 1), False, botones, escala)
        )

    def test_sala_con_cuatro_jugadores_dibuja_donde_se_detecta(self):
        juego = Juego(Config())
        ancho = juego.config.ANCHO_PANTALLA
        snapshot = snapshot_sala()
        snapshot["jugadores"] = [
            _jugador(i, 100.0 + i * 50, 200.0, i == 0) for i in range(4)
        ]
        snapshot["jugadores_online"] = 4
        snapshot["max_jugadores"] = 4
        pantalla = pygame.Surface((ancho, juego.config.ALTO_PANTALLA))
        juego.interfaz.dibujar_sala(
            pantalla, snapshot, mi_id=2, listo=True, mouse_pos=None
        )

        x_listo, x_salir, y_btn, btn_ancho, btn_alto = rects_sala(ancho)
        self.assertNotEqual(
            pantalla.get_at((x_listo + 20, y_btn + 8))[:3], Config.COLOR_FONDO
        )
        self.assertNotEqual(
            pantalla.get_at((x_salir + 20, y_btn + 8))[:3], Config.COLOR_FONDO
        )

        centro_listo = (x_listo + btn_ancho // 2, y_btn + btn_alto // 2)
        self.assertEqual(juego.acciones_ui.detectar_sala(centro_listo, True), "listo")
        self.assertEqual(
            juego.acciones_ui.detectar_sala(
                (x_salir + btn_ancho // 2, y_btn + btn_alto // 2), True
            ),
            "salir",
        )
        self.assertIsNone(
            juego.acciones_ui.detectar_sala((centro_listo[0], y_btn - 1), True)
        )


if __name__ == "__main__":
    unittest.main()
