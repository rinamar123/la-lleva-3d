"""Pruebas de las vistas gráficas mejoradas y del reflejo del congelado.

Cubre: identidad visual por jugador, estados (lleva, congelado, escudo,
potenciado/tropiezo), cacheo de superficies (puntos de fondo, halos, anillos),
fondo del menú cacheado y UI relativa a 720p, además del reflejo del efecto
congelar en el modelo Jugador.
"""

import os
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from juego_lleva.core.config import Config
from juego_lleva.core.juego import Juego
from juego_lleva.models.jugador_humano import JugadorHumano
from juego_lleva.models.jugador_ia import JugadorIA
from juego_lleva.models.power_up import PowerUp
from juego_lleva.ui.interfaz import Interfaz
from juego_lleva.views.efecto_view import EfectoView
from juego_lleva.views.entorno_view import EntornoView
from juego_lleva.views.jugador_view import JugadorView
from juego_lleva.views.power_up_view import PowerUpView


class TestJugadorView(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.vista = JugadorView()
        self.vista.fase_caminar = 1.2
        self.vista.tiempo_animacion = 0.5

    def _bytes(self, jugador):
        superficie = self.vista._componer_personaje(jugador)
        return pygame.image.tobytes(superficie, 'RGBA')

    def test_estilos_visuales_distintos(self):
        j1 = JugadorHumano(100, 100, 0, {})
        j2 = JugadorHumano(100, 100, 1, {})
        j3 = JugadorIA(100, 100, 2)
        self.assertNotEqual(self._bytes(j1), self._bytes(j2))
        self.assertNotEqual(self._bytes(j1), self._bytes(j3))

    def test_lleva_cambia_apariencia(self):
        normal = JugadorHumano(100, 100, 0, {})
        lleva = JugadorHumano(100, 100, 0, {})
        lleva.es_lleva = True
        self.assertNotEqual(self._bytes(normal), self._bytes(lleva))

    def test_congelado_cambia_apariencia(self):
        normal = JugadorHumano(100, 100, 0, {})
        helado = JugadorHumano(100, 100, 0, {})
        helado.congelado = 3.0
        self.assertNotEqual(self._bytes(normal), self._bytes(helado))

    def test_tropezando_cambia_apariencia(self):
        normal = JugadorHumano(100, 100, 0, {})
        caido = JugadorHumano(100, 100, 0, {})
        caido.tropezando = 0.2
        self.assertNotEqual(self._bytes(normal), self._bytes(caido))

    def test_renderizar_estados_no_lanza(self):
        pantalla = pygame.Surface((1280, 720))
        jugadores = []
        j1 = JugadorHumano(200, 300, 0, {})
        j1.vx, j1.vy, j1.velocidad_abs = -180, 20, 180.2
        j1.factor_velocidad = 1.6
        j1.direccion_cara = -1
        jugadores.append(j1)

        j2 = JugadorIA(600, 300, 1)
        j2.es_lleva = True
        j2.escudo = True
        j2.vx, j2.velocidad_abs = 160, 160.0
        jugadores.append(j2)

        j3 = JugadorIA(900, 300, 2)
        j3.congelado = 3.0
        j3.tropezando = 0.3
        j3.vy, j3.velocidad_abs = -140, 140.0
        jugadores.append(j3)

        for _ in range(10):
            for j in jugadores:
                self.vista.renderizar(pantalla, j, 0.016)

    def test_rastro_potenciado_es_dorado(self):
        from juego_lleva.servicios.particula_service import ParticulaService
        svc = ParticulaService()
        j = JugadorHumano(300, 300, 0, {})
        j.vx, j.velocidad_abs = 150, 150.0
        j.factor_velocidad = 1.6
        particula = svc.agregar_rastro(j, Config())
        self.assertIsNotNone(particula)
        self.assertEqual(particula['color'], (255, 235, 120))

    def test_rastro_normal_usa_color_jugador(self):
        from juego_lleva.servicios.particula_service import ParticulaService
        svc = ParticulaService()
        j = JugadorHumano(300, 300, 0, {})
        j.vx, j.velocidad_abs = 150, 150.0
        particula = svc.agregar_rastro(j, Config())
        self.assertIsNotNone(particula)
        self.assertEqual(particula['color'], Config.COLOR_JUGADOR_1)


class TestCacheSuperficies(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_puntos_de_fondo_cacheados(self):
        vista = EntornoView()
        superficie = vista._superficie_punto(3, 60)
        self.assertIs(superficie, vista._superficie_punto(3, 60))
        self.assertIsNot(superficie, vista._superficie_punto(4, 60))

    def test_halo_power_up_cacheado(self):
        vista = PowerUpView()
        halo = vista._superficie_halo((255, 215, 0), 28, 255)
        self.assertIs(halo, vista._superficie_halo((255, 215, 0), 28, 255))

    def test_anillos_efecto_cacheados(self):
        vista = EfectoView()
        anillo = vista._superficie_anillo((255, 215, 0), 30, 200)
        self.assertIs(anillo, vista._superficie_anillo((255, 215, 0), 30, 200))
        self.assertGreater(len(vista._anillos), 0)


class TestInterfazVisual(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.interfaz = Interfaz()
        self.pantalla = pygame.Surface((1280, 720))

    def test_fondo_menu_cacheado(self):
        self.assertIsNone(self.interfaz._fondo_menu)
        self.interfaz.dibujar_menu_principal(self.pantalla)
        self.interfaz.dibujar_menu_principal(self.pantalla)
        self.assertTrue(isinstance(self.interfaz._fondo_menu, pygame.Surface))

    def test_hud_720p_no_lanza(self):
        j1 = JugadorHumano(100, 100, 0, {})
        j2 = JugadorIA(300, 200, 1)
        j2.es_lleva = True
        self.interfaz.dibujar_hud(
            self.pantalla, 30.0, {0: 10, 1: 20}, [j1, j2],
            duracion=60, efectos={0: ['velocidad'], 1: ['congelar']})

    def test_fin_ronda_medallas_no_lanza(self):
        j1 = JugadorHumano(100, 100, 0, {})
        j2 = JugadorIA(300, 200, 1)
        self.interfaz.dibujar_fin_ronda(
            self.pantalla, 0, {0: 10, 1: 55}, mouse_pos=(640, 500), jugadores=[j1, j2])

    def test_countdown_anillo_no_lanza(self):
        self.interfaz.dibujar_countdown(self.pantalla, 3)

    def test_boton_gradiente_no_lanza(self):
        self.interfaz.dibujar_boton(self.pantalla, "Jugar", 480, 300, 320, 50, hover=True)


class TestCongeladoEnModelo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.juego = Juego(Config())
        self.dir_tmp = tempfile.TemporaryDirectory()
        self.juego.configuracion.ruta = os.path.join(self.dir_tmp.name, "settings.json")
        self.juego.ranking_service.ruta = os.path.join(self.dir_tmp.name, "ranking.json")

    def tearDown(self):
        self.dir_tmp.cleanup()

    def test_congelar_refleja_estado_en_el_rival(self):
        juego = self.juego
        juego.gestor_modos.iniciar_multijugador(juego, ["Ana", "Beto"])
        juego.set_lleva_inicial(0)
        ana = juego.jugadores[0]
        beto = juego.jugadores[1]

        juego.ctrl_partida._recoger_power_up(ana, PowerUp(0, 0, "congelar"))

        self.assertGreater(juego.efectos_activos.get(1, {}).get("congelar", 0), 0)
        self.assertGreater(beto.congelado, 0)

    def test_al_vencer_el_congelar_se_restablece(self):
        juego = self.juego
        juego.gestor_modos.iniciar_multijugador(juego, ["Ana", "Beto"])
        juego.set_lleva_inicial(0)
        ana = juego.jugadores[0]
        beto = juego.jugadores[1]

        juego.ctrl_partida._recoger_power_up(ana, PowerUp(0, 0, "congelar"))
        duracion = juego.efectos_activos[1]["congelar"]
        juego.ctrl_partida.actualizar_efectos_activos(duracion + 0.1)

        self.assertEqual(juego.efectos_activos.get(1, {}).get("congelar", 0), 0)
        self.assertEqual(beto.congelado, 0)


if __name__ == '__main__':
    unittest.main()