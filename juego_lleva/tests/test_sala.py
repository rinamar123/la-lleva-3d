"""Pruebas de la sala en línea y la simulación headless de la ronda."""

import contextlib
import io
import time
import unittest

from juego_lleva.core.config import Config
from juego_lleva.models.power_up import PowerUp
from juego_lleva.red.sala import (
    FASE_COUNTDOWN,
    FASE_ESPERANDO,
    FASE_FIN,
    FASE_JUGANDO,
    TIMEOUT_DESCONEXION,
    SalaEnLinea,
)
from juego_lleva.red import simulacion
from juego_lleva.red.simulacion import (
    SimulacionRonda,
    WEB_ALTO,
    WEB_ANCHO,
    aplicar_resolucion_web,
    restaurar_resolucion,
)

DT = 1.0 / 30


class TestSimulacionRonda(unittest.TestCase):
    """Pruebas deterministas de la simulación (sin entorno aleatorio)."""

    def setUp(self):
        aplicar_resolucion_web()
        self.nombres = {0: "Ana", 1: "Beto"}

    def tearDown(self):
        restaurar_resolucion()

    def _simulacion(self, dt=1.0 / 30):
        sim = SimulacionRonda(dict(self.nombres), semilla=7)
        sim.entorno.obstaculos = []
        return sim

    def test_aplica_resolucion_web(self):
        self.assertEqual(Config.ANCHO_PANTALLA, WEB_ANCHO)
        self.assertEqual(Config.ALTO_PANTALLA, WEB_ALTO)

    def test_crea_un_jugador_por_nombre(self):
        sim = SimulacionRonda(dict(self.nombres), semilla=1)
        self.assertEqual([j.id for j in sim.jugadores], [0, 1])
        self.assertEqual([j.nombre for j in sim.jugadores], ["Ana", "Beto"])
        self.assertEqual(sum(1 for j in sim.jugadores if j.es_lleva), 1)

    def test_mover_aplicado_segun_entrada(self):
        sim = self._simulacion()
        inicial = sim.jugadores[0].x
        sim.set_entrada(0, {"derecha": True})
        sim.paso(0.5)
        self.assertGreater(sim.jugadores[0].x, inicial)

    def test_entrada_no_booleana_se_ignora(self):
        sim = self._simulacion()
        sim.set_entrada(0, {"derecha": "si", "arriba": True})
        self.assertTrue(sim.entradas[0]["arriba"])
        self.assertFalse(sim.entradas[0]["derecha"])

    def test_toque_transfiere_lleva_y_acumula_tiempo(self):
        sim = self._simulacion()
        if sim.jugadores[1].es_lleva:
            sim.jugadores[0], sim.jugadores[1] = sim.jugadores[1], sim.jugadores[0]
        llevador = next(j for j in sim.jugadores if j.es_lleva)
        victima = next(j for j in sim.jugadores if not j.es_lleva)
        victima.x = llevador.x + 50
        victima.y = llevador.y
        sim.tiempo_ronda = 2.0
        sim.paso(DT)
        self.assertTrue(victima.es_lleva)
        self.assertFalse(llevador.es_lleva)
        self.assertGreater(sim.puntaje.tiempos_lleva[llevador.id], 0)
        self.assertTrue(any(e["tipo"] == "toque" for e in sim.eventos))

    def test_escudo_bloquea_toque(self):
        sim = self._simulacion()
        if sim.jugadores[1].es_lleva:
            sim.jugadores[0], sim.jugadores[1] = sim.jugadores[1], sim.jugadores[0]
        llevador = next(j for j in sim.jugadores if j.es_lleva)
        victima = next(j for j in sim.jugadores if not j.es_lleva)
        victima.escudo = True
        victima.x = llevador.x + 50
        victima.y = llevador.y
        sim.paso(DT)
        self.assertTrue(llevador.es_lleva)
        self.assertFalse(victima.escudo)
        self.assertTrue(any(e["tipo"] == "escudo" for e in sim.eventos))

    def test_power_up_congelar_elige_rival_aleatorio(self):
        sim = SimulacionRonda({0: "A", 1: "B", 2: "C", 3: "D"}, semilla=3)
        sim.entorno.obstaculos = []
        recolector = sim.jugadores[0]
        recolector.escudo = False
        sim.power_ups.append(PowerUp(
            recolector.x + 1, recolector.y + 1, "congelar", sim.config))
        sim.paso(DT)
        self.assertTrue(any(e["tipo"] == "power_up" for e in sim.eventos))
        objetivo = sim.obtener_jugador(sim.eventos[-1]["objetivo"])
        self.assertEqual(objetivo.id, sim.eventos[-1]["objetivo"])
        self.assertNotEqual(objetivo.id, recolector.id)
        self.assertGreater(objetivo.congelado, 0)

    def test_velocidad_power_up_afecta_al_recolector(self):
        sim = self._simulacion()
        recolector = sim.jugadores[0]
        sim.power_ups.append(PowerUp(
            recolector.x + 1, recolector.y + 1, "velocidad", sim.config))
        sim.paso(DT)
        self.assertEqual(recolector.factor_velocidad, Config.FACTOR_VELOCIDAD_POWER)
        self.assertIn("velocidad", sim.efectos_activos[recolector.id])

    def test_fin_de_ronda_con_ganador(self):
        sim = self._simulacion()
        sim.tiempo_ronda = sim.duracion_ronda - 0.1
        sim.paso(0.2)
        self.assertTrue(sim.terminada)
        self.assertIsNotNone(sim.ganador)
        self.assertTrue(any(e["tipo"] == "fin" for e in sim.eventos))

    def test_snapshot_estado_red_contiene_claves(self):
        sim = self._simulacion()
        estado = sim.estado_red()
        for clave in ("jugadores", "obstaculos", "power_ups", "tiempos_lleva",
                      "efectos_activos", "eventos", "ganador"):
            self.assertIn(clave, estado)
        for clave in ("id", "nombre", "x", "y", "es_lleva", "direccion_cara",
                      "velocidad_abs", "escudo", "congelado", "tropezando",
                      "factor_velocidad"):
            self.assertIn(clave, estado["jugadores"][0])

    def test_reiniciar_borra_el_estado_de_la_ronda(self):
        sim = self._simulacion()
        sim.puntaje.registrar_lleva(0, 5)
        sim.power_ups.append(PowerUp(200, 200, "escudo", sim.config))
        sim.efectos_activos[0] = {"velocidad": 1.0}
        sim.reiniciar()
        self.assertEqual(sim.puntaje.tiempos_lleva, {})
        self.assertEqual(sim.power_ups, [])
        self.assertEqual(sim.efectos_activos, {})
        self.assertFalse(sim.terminada)


class TestSalaEnLinea(unittest.TestCase):
    """Pruebas de la sala garantizando transiciones de fase deterministas."""

    def setUp(self):
        self.sala = SalaEnLinea(max_jugadores=3, duracion_ronda=10,
                                iniciar_hilo=False)
        self.addCleanup(self.sala.cerrar)

    def _unirse(self, nombre, listo=False):
        respuesta = self.sala.unirse(nombre)
        self.assertTrue(respuesta.get("ok"), respuesta)
        if listo:
            self.sala.sincronizar(respuesta["token"], listo=True)
        return respuesta["token"]

    def _pasar_a_jugando(self):
        tokens = [self._unirse("Ana", listo=True),
                  self._unirse("Beto", listo=True)]
        self.sala._tick(DT)
        self.assertEqual(self.sala.fase, FASE_COUNTDOWN)
        self.sala._tick(3.1)
        self.assertEqual(self.sala.fase, FASE_JUGANDO)
        return tokens

    def test_unirse_devuelve_token_y_estado(self):
        respuesta = self.sala.unirse("Ana")
        self.assertEqual(respuesta["fase"], FASE_ESPERANDO)
        self.assertEqual(respuesta["id"], 0)
        self.assertEqual(respuesta["jugadores_online"], 1)

    def test_token_de_128_bits(self):
        respuesta = self.sala.unirse("Ana")
        self.assertEqual(len(respuesta["token"]), 32)

    def test_limite_de_jugadores(self):
        for nombre in ("A", "B", "C"):
            self.assertTrue(self.sala.unirse(nombre)["ok"])
        respuesta = self.sala.unirse("D")
        self.assertEqual(respuesta, {"error": "sala_llena"})

    def test_nombres_duplicados_reciben_sufijo(self):
        self._unirse("Ana")
        respuesta = self.sala.unirse("Ana")
        self.assertEqual(respuesta["nombre"], "Ana2")

    def test_sala_llena_no_unirse_en_juego(self):
        self._pasar_a_jugando()
        self.assertEqual(self.sala.unirse("Caro"), {"error": "partida_en_curso"})

    def test_requiere_minimo_dos_y_todos_listos_para_countdown(self):
        self._unirse("Ana")
        self.sala._tick(DT)
        self.sala._tick(DT)
        self.assertEqual(self.sala.fase, FASE_ESPERANDO)

    def test_countdown_luego_jugando_cuando_todos_listos(self):
        tokens = self._pasar_a_jugando()
        self.assertIsNotNone(self.sala.sim)
        self.assertEqual(len(self.sala.sim.jugadores), 2)

    def test_sync_devuelve_snapshot_de_la_partida(self):
        token = self._pasar_a_jugando()[0]
        snapshot = self.sala.sincronizar(token, entrada={"derecha": True})
        self.assertEqual(snapshot["tipo"], "estado_partida")
        self.assertEqual(snapshot["fase"], FASE_JUGANDO)
        self.assertEqual(snapshot["max_jugadores"], 3)
        self.assertEqual(snapshot["mi_id"], 0)
        self.assertEqual(len(snapshot["jugadores"]), 2)

    def test_entrada_ilegal_o_token_invalido(self):
        token = self._pasar_a_jugando()[0]
        self.assertEqual(self.sala.sincronizar("inexistente"), {"error": "token_invalido"})
        self.sala.sincronizar(token, listo=False)
        snapshot = self.sala.sincronizar(token, entrada="no-dict", listo="si")
        self.assertEqual(snapshot["fase"], FASE_JUGANDO)
        self.assertFalse(snapshot["listos"][str(snapshot["mi_id"])],
                         "listo='si' no debía aceptarse")

    def test_seq_de_eventos_no_vuelve_a_cero_en_la_siguiente_ronda(self):
        self._pasar_a_jugando()
        self.sala.sim.tiempo_ronda = self.sala.sim.duracion_ronda - 0.1
        self.sala._tick(0.2)
        fin_ronda_1 = self.sala._seq_evento
        self.assertGreater(fin_ronda_1, 0)

        self.sala.tiempo_fin -= 60
        self.sala._tick(DT)
        self.sala._tick(3.1)
        self.assertEqual(self.sala.fase, FASE_JUGANDO)
        self.assertEqual(self.sala.sim.seq_evento, fin_ronda_1)

        victima = next(j for j in self.sala.sim.jugadores if not j.es_lleva)
        llevador = next(j for j in self.sala.sim.jugadores if j.es_lleva)
        victima.x, victima.y = llevador.x + 50, llevador.y
        self.sala._tick(DT)
        self.assertEqual(self.sala.sim.eventos[-1]["seq"], fin_ronda_1 + 1)

    def test_snapshot_incluye_al_que_entra_en_la_fase_de_fin(self):
        self._pasar_a_jugando()
        self.sala.sim.tiempo_ronda = self.sala.sim.duracion_ronda - 0.1
        self.sala._tick(0.2)
        self.assertEqual(self.sala.fase, FASE_FIN)

        nuevo = self.sala.unirse("Caro")
        self.assertTrue(nuevo.get("ok"), nuevo)
        snapshot = self.sala.sincronizar(nuevo["token"])
        self.assertEqual(len(snapshot["jugadores"]), 3)
        self.assertEqual([j["id"] for j in snapshot["jugadores"]], [0, 1, 2])
        for jugador in snapshot["jugadores"]:
            self.assertIn("listo", jugador)
        self.assertFalse(snapshot["listos"][str(nuevo["id"])])

    def test_victorias_no_acumula_ids_de_jugadores_fuera(self):
        self._pasar_a_jugando()
        self.sala.sim.tiempo_ronda = self.sala.sim.duracion_ronda - 0.1
        self.sala._tick(0.2)
        ganador = str(self.sala.sim.ganador)
        self.assertEqual(self.sala.victorias[ganador], 1)
        self.sala._eliminar_jugador(int(ganador))
        self.assertNotIn(ganador, self.sala.victorias)

    def test_estado_publico_se_lee_bajo_lock(self):
        self._unirse("Ana")
        estado = self.sala.estado_publico()
        self.assertEqual(estado["jugadores_online"], 1)
        self.assertEqual(estado["nombres"], ["Ana"])

    def test_el_hilo_sobrevive_a_un_error_de_tick(self):
        salida = io.StringIO()
        with contextlib.redirect_stderr(salida):
            sala = SalaEnLinea(max_jugadores=2, iniciar_hilo=True)
            self.addCleanup(sala.cerrar)
            original = sala._tick
            fallos = []

            def tick_fallido(delta_tiempo):
                if not fallos:
                    fallos.append(delta_tiempo)
                    raise RuntimeError("fallo simulado")
                return original(delta_tiempo)

            sala._tick = tick_fallido
            limite = time.monotonic() + 2.0
            while time.monotonic() < limite and "fallo simulado" not in salida.getvalue():
                time.sleep(0.01)
            self.assertTrue(fallos, "el tick con error nunca llegó a ejecutarse")
            self.assertIn("fallo simulado", salida.getvalue())
            self.assertTrue(sala._hilo.is_alive(), "el hilo de simulación murió")
            self.assertIn("fase", sala.estado_publico())

    def test_fin_de_ronda_incrementa_victorias(self):
        token = self._pasar_a_jugando()[0]
        self.sala.sim.tiempo_ronda = self.sala.sim.duracion_ronda - 0.1
        self.sala._tick(0.2)
        self.assertEqual(self.sala.fase, FASE_FIN)
        ganador = self.sala.sim.ganador
        self.assertEqual(self.sala.victorias[str(ganador)], 1)

    def test_desconexion_aborta_la_ronda(self):
        token = self._pasar_a_jugando()[0]
        self.sala._eliminar_jugador(0)
        self.sala._tick(DT)
        self.assertEqual(self.sala.fase, FASE_ESPERANDO)
        self.assertIsNone(self.sala.sim)

    def test_expulsion_por_inactividad(self):
        self._unirse("Ana")
        token = self._unirse("Beto", listo=True)
        self.sala.jugadores[0].listo = True
        self.sala.jugadores[0].ultima_actividad -= TIMEOUT_DESCONEXION + 1
        self.sala._tick(DT)
        self.assertEqual(len(self.sala.jugadores), 1)
        self.assertEqual(self.sala.sincronizar(token)["jugadores_online"], 1)

    def test_salir_elimina_y_token_queda_invalido(self):
        token = self._unirse("Ana")
        self.assertEqual(self.sala.salir(token), {"ok": True})
        self.assertEqual(self.sala.sincronizar(token), {"error": "token_invalido"})

    def test_reinicio_automatico_tras_fin(self):
        self._pasar_a_jugando()
        self.sala.sim.tiempo_ronda = self.sala.sim.duracion_ronda - 0.1
        self.sala._tick(0.2)
        self.assertEqual(self.sala.fase, FASE_FIN)
        self.sala.tiempo_fin -= 60
        self.sala._tick(DT)
        self.assertEqual(self.sala.fase, FASE_COUNTDOWN)


class TestResolucionWeb(unittest.TestCase):
    """Las salas comparten el contador de aplicaciones de la resolución web."""

    def setUp(self):
        self.usos_previos = simulacion._usos_resolucion
        self.originales_previos = simulacion._originales_resolucion
        self.config_antes = (Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA)
        if self.originales_previos is not None:
            Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA = self.originales_previos
        simulacion._usos_resolucion = 0
        simulacion._originales_resolucion = None
        self.config_limpia = (Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA)

    def tearDown(self):
        simulacion._usos_resolucion = self.usos_previos
        simulacion._originales_resolucion = self.originales_previos
        Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA = self.config_antes

    def test_una_sola_aplicacion_restaura_lo_original(self):
        aplicar_resolucion_web()
        self.assertEqual((Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA),
                         (WEB_ANCHO, WEB_ALTO))
        restaurar_resolucion()
        self.assertEqual(simulacion._usos_resolucion, 0)
        self.assertEqual((Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA),
                         self.config_limpia)

    def test_dos_salas_solapadas_solo_la_ultima_restaura(self):
        aplicar_resolucion_web()
        aplicar_resolucion_web()
        restaurar_resolucion()
        self.assertEqual(simulacion._usos_resolucion, 1)
        self.assertEqual((Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA),
                         (WEB_ANCHO, WEB_ALTO))
        restaurar_resolucion()
        self.assertEqual(simulacion._usos_resolucion, 0)
        self.assertEqual((Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA),
                         self.config_limpia)

    def test_restaurar_sin_aplicar_no_deja_negativo(self):
        restaurar_resolucion()
        restaurar_resolucion()
        self.assertEqual(simulacion._usos_resolucion, 0)
        self.assertEqual((Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA),
                         self.config_limpia)

    def test_dos_salas_en_linea_no_se_pisan(self):
        sala_a = SalaEnLinea(iniciar_hilo=False)
        self.addCleanup(sala_a.cerrar)
        sala_b = SalaEnLinea(iniciar_hilo=False)
        self.addCleanup(sala_b.cerrar)
        sala_a.cerrar()
        self.assertEqual((Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA),
                         (WEB_ANCHO, WEB_ALTO))
        sala_b.cerrar()
        self.assertEqual((Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA),
                         self.config_limpia)
        sala_a.cerrar()

    def test_cerrar_de_una_sala_con_hilo_restaura(self):
        sala = SalaEnLinea(iniciar_hilo=True)
        self.addCleanup(sala.cerrar)
        sala.cerrar()
        self.assertFalse(sala._hilo.is_alive())
        self.assertEqual((Config.ANCHO_PANTALLA, Config.ALTO_PANTALLA),
                         self.config_limpia)


if __name__ == '__main__':
    unittest.main()