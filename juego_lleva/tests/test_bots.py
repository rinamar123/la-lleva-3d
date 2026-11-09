"""Harness de bots: clientes virtuales que prueban el servidor sin navegador.

Simula N jugadores conectados que envían entrada aleatoria a través de la
API de la sala, verificando el flujo completo: esperando -> countdown ->
jugando -> fin -> siguiente ronda.
"""

import random
import unittest

from juego_lleva.red.sala import (
    FASE_COUNTDOWN,
    FASE_ESPERANDO,
    FASE_JUGANDO,
    FASE_FIN,
    SalaEnLinea,
)

ACCIONES = ("arriba", "abajo", "izquierda", "derecha")
DT = 1.0 / 30


class Bot:
    """Un cliente virtual: token + entrada aleatoria con inercia."""

    def __init__(self, sala, nombre, semilla):
        self.sala = sala
        self.respuesta = sala.unirse(nombre)
        self.token = self.respuesta["token"]
        self.rng = random.Random(semilla)
        self.entrada = {accion: False for accion in ACCIONES}
        self.listo = False

    def paso_aleatorio(self):
        if self.rng.random() < 0.3:
            accion = self.rng.choice(ACCIONES)
            self.entrada[accion] = not self.entrada[accion]
        return self.sala.sincronizar(self.token, entrada=self.entrada)

    def marcar_listo(self):
        self.listo = True
        return self.sala.sincronizar(self.token, listo=True)


class TestBots(unittest.TestCase):

    def setUp(self):
        self.sala = SalaEnLinea(max_jugadores=4, duracion_ronda=1.0,
                                iniciar_hilo=False)
        self.addCleanup(self.sala.cerrar)

    def test_primera_ronda_completa_con_cuatro_bots(self):
        bots = [Bot(self.sala, f"J{i}", 100 + i) for i in range(4)]
        self.assertEqual(self.sala.fase, FASE_ESPERANDO)
        for bot in bots:
            bot.marcar_listo()

        fases = []
        tope = 0
        while self.sala.fase != FASE_FIN and tope < 600:
            self.sala._tick(DT)
            fases.append(self.sala.fase)
            for bot in bots:
                bot.paso_aleatorio()
            tope += 1

        self.assertIn(FASE_COUNTDOWN, fases)
        self.assertIn(FASE_JUGANDO, fases)
        self.assertEqual(self.sala.fase, FASE_FIN)
        self.assertIsNotNone(self.sala.sim.ganador)
        self.assertEqual(sum(self.sala.victorias.values()), 1)

    def test_segunda_ronda_arranca_tras_el_fin(self):
        bots = [Bot(self.sala, f"J{i}", 10 + i) for i in range(3)]
        for bot in bots:
            bot.marcar_listo()
        for _ in range(200):
            self.sala._tick(DT)
            for bot in bots:
                bot.paso_aleatorio()
        self.assertEqual(self.sala.fase, FASE_FIN)

        self.sala.tiempo_fin -= 30
        self.sala._tick(DT)
        self.assertEqual(self.sala.fase, FASE_COUNTDOWN)
        snapshot = self.sala.sincronizar(bots[0].token, listo=False)
        self.assertEqual(snapshot["fase"], FASE_COUNTDOWN)
        self.assertIsNone(snapshot["ganador"])
        fases = []
        for _ in range(200):
            self.sala._tick(DT)
            for bot in bots:
                bot.paso_aleatorio()
            fases.append(self.sala.fase)

        self.assertIn(FASE_COUNTDOWN, fases)
        self.assertIn(FASE_JUGANDO, fases)
        ultimo = self.sala.sincronizar(bots[0].token)
        self.assertNotIn("error", ultimo)
        self.assertEqual(ultimo["fase"], self.sala.fase)
        self.assertGreaterEqual(sum(self.sala.victorias.values()), 1)


if __name__ == '__main__':
    unittest.main()