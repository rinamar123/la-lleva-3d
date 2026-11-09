"""Prueba de integración de la regla clásica a través de Juego (headless)."""

import os
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from juego_lleva.core.config import Config
from juego_lleva.core.juego import Juego
from juego_lleva.models.power_up import PowerUp


class TestReglaClasicaIntegracion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.juego = Juego(Config())
        self.dir_tmp = tempfile.TemporaryDirectory()
        self.juego.configuracion.ruta = os.path.join(self.dir_tmp.name, "settings.json")
        # el ranking también va a un archivo temporal: si se usara el de
        # assets/, cada corrida de la suite añadiría una partida de mentira
        self.juego.ranking_service.ruta = os.path.join(self.dir_tmp.name, "ranking.json")

    def tearDown(self):
        self.dir_tmp.cleanup()

    def test_transferencia_y_ganador(self):
        juego = self.juego
        juego.gestor_modos.iniciar_multijugador(juego, ["Ana", "Beto"])
        juego.set_lleva_inicial(0)

        juego.tiempo_ronda = 10
        juego.tiempo_inicio_lleva = 0
        beto, ana = juego.jugadores[1], juego.jugadores[0]
        juego.ctrl_partida._transferir_lleva(ana, beto)

        self.assertFalse(ana.es_lleva)
        self.assertTrue(beto.es_lleva)
        self.assertEqual(juego.puntaje_service.tiempos_lleva[0], 10)
        self.assertEqual(len(juego.efectos), 1)
        self.assertGreater(len(juego.efectos[0]['particulas']), 0)

        juego.tiempo_ronda = 60
        juego.ctrl_partida.finalizar_ronda()

        self.assertEqual(juego.puntaje_service.tiempos_lleva[0], 10)
        self.assertEqual(juego.puntaje_service.tiempos_lleva[1], 50)
        self.assertEqual(juego.puntaje_service.obtener_ganador(), 0)
        self.assertEqual(juego.estado, "fin_ronda")

    def test_escudo_bloquea_el_toque(self):
        juego = self.juego
        juego.gestor_modos.iniciar_multijugador(juego, ["Ana", "Beto"])
        juego.set_lleva_inicial(0)
        ana, beto = juego.jugadores[0], juego.jugadores[1]

        beto.escudo = True
        juego.ctrl_partida.procesar_colision(ana, beto)

        self.assertTrue(ana.es_lleva)
        self.assertFalse(beto.escudo)
        self.assertEqual(juego.puntaje_service.tiempos_lleva.get(0, 0), 0)

    def test_recoger_power_up_aplica_efectos(self):
        juego = self.juego
        juego.gestor_modos.iniciar_multijugador(juego, ["Ana", "Beto"])
        juego.set_lleva_inicial(0)
        ana, beto = juego.jugadores[0], juego.jugadores[1]

        creado = PowerUp(0, 0, "velocidad")
        juego.ctrl_partida._recoger_power_up(ana, creado)
        self.assertEqual(ana.factor_velocidad, Config.FACTOR_VELOCIDAD_POWER)
        self.assertIn("velocidad", juego.efectos_activos.get(0, {}))

        juego.ctrl_partida._recoger_power_up(ana, PowerUp(0, 0, "congelar"))
        self.assertGreater(juego.efectos_activos.get(1, {}).get("congelar", 0), 0)

        juego.ctrl_partida._recoger_power_up(beto, PowerUp(0, 0, "escudo"))
        self.assertTrue(beto.escudo)

    def test_congelado_detiene_movimiento(self):
        juego = self.juego
        juego.gestor_modos.iniciar_multijugador(juego, ["Ana", "Beto"])
        juego.set_lleva_inicial(0)
        beto = juego.jugadores[1]
        juego.efectos_activos.setdefault(1, {})["congelar"] = 3.0

        x_antes, y_antes = beto.x, beto.y
        juego._bucle_juego(0.5)
        self.assertEqual(beto.x, x_antes)
        self.assertEqual(beto.y, y_antes)
        self.assertGreater(juego.efectos_activos.get(1, {}).get("congelar", 0), 0)

    def test_congelar_expira_y_se_limpia(self):
        juego = self.juego
        juego.gestor_modos.iniciar_multijugador(juego, ["Ana", "Beto"])
        juego.set_lleva_inicial(0)
        juego.efectos_activos.setdefault(1, {})["congelar"] = 0.4

        juego._bucle_juego(0.5)
        self.assertNotIn("congelar", juego.efectos_activos.get(1, {}))

    def test_dificultad_aplicada_a_ia(self):
        juego = self.juego
        juego.modo = "un_jugador"
        juego.nombres = ["Ana"]
        juego.gestor_modos.iniciar_un_jugador(juego, "Ana")
        juego.configuracion.establecer("dificultad_ia", "dificil")
        juego._aplicar_dificultad_ia()
        ia = juego.jugadores[1]
        self.assertEqual(ia.velocidad_ia, Config.DIFICULTADES["dificil"]["VELOCIDAD_IA"])

    def test_normalizar_nombres_vacios(self):
        juego = self.juego
        juego.nombres = ["   ", ""]
        juego._normalizar_nombres()
        self.assertEqual(juego.nombres, ["J1", "J2"])

    def test_normalizar_nombres_recorta_maximo(self):
        juego = self.juego
        juego.nombres = ["12345678901234"]
        juego._normalizar_nombres()
        self.assertEqual(len(juego.nombres[0]), 12)

    def test_toque_web_escala_las_coordenadas(self):
        juego = self.juego
        juego.config.PLATAFORMA_WEB = True
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(
            pygame.FINGERDOWN, x=0.25, y=0.5, finger_id=0))
        juego._capturar_entrada()
        self.assertTrue(juego.click_realizado)
        self.assertEqual(
            juego.mouse_pos,
            (int(0.25 * juego.config.ANCHO_PANTALLA),
             int(0.5 * juego.config.ALTO_PANTALLA)))

    def test_toast_se_agrega_y_expira(self):
        juego = self.juego
        juego._mostrar_toast("Hola", (255, 0, 0))
        self.assertEqual(len(juego.toasts), 1)
        self.assertEqual(juego.toasts[0]['texto'], "Hola")
        juego.toasts = juego.interfaz.actualizar_toasts(juego.toasts, 3.0)
        self.assertEqual(len(juego.toasts), 0)

    def test_menu_teclado_seleccion_y_enter(self):
        juego = self.juego
        self.assertEqual(juego.opcion_menu, 0)
        juego.eventos_pendientes = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)]
        juego.ctrl_menu.menu_principal()
        self.assertEqual(juego.opcion_menu, 1)
        juego.eventos_pendientes = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)]
        juego.ctrl_menu.menu_principal()
        self.assertEqual(juego.opcion_menu, 2)
        juego.eventos_pendientes = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)]
        juego.ctrl_menu.menu_principal()
        self.assertEqual(juego.opcion_menu, 3)
        juego.eventos_pendientes = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)]
        juego.ctrl_menu.menu_principal()
        self.assertEqual(juego.estado, "ayuda")

    def test_fin_ronda_tecla_r_revancha(self):
        juego = self.juego
        juego.gestor_modos.iniciar_multijugador(juego, ["Ana", "Beto"])
        juego.tiempo_ronda = 60
        juego.ctrl_partida.finalizar_ronda()
        self.assertEqual(juego.estado, "fin_ronda")
        juego.eventos_pendientes = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r)]
        juego.ctrl_pantallas.pantalla_fin_ronda()
        self.assertEqual(juego.estado, "countdown")


if __name__ == '__main__':
    unittest.main()
