"""Versión 3D de escritorio de La Lleva usando Ursina.

La versión Pygame original permanece intacta. Este módulo reutiliza la
simulación autoritativa existente (SimulacionRonda) y solo sustituye la capa
visual por una escena 3D con cámara en primera persona.
"""

from __future__ import annotations

import math

try:
    from ursina import (
        Ursina, Entity, Text, Button, Sky, DirectionalLight, AmbientLight, held_keys,
        camera, color, mouse, window, time, application, destroy,
    )
except ImportError as exc:  # pragma: no cover - depende del entorno gráfico
    raise SystemExit(
        "No se encontró Ursina. Instálalo con:\n"
        "  python -m pip install -r requirements-3d.txt\n"
        "Después ejecuta: python -m juego_lleva.ursina3d"
    ) from exc

from juego_lleva.red.simulacion import SimulacionRonda
from juego_lleva.desktop3d_logic import (
    ANCHO_LOGICO, ALTO_LOGICO, ESCALA_MUNDO,
    mundo_desde_logico as _mundo, entrada_relativa as _entrada_relativa,
)

ALTURA_OJOS = 1.62


class LaLlevaUrsina:
    def __init__(self):
        self.app = Ursina(title="La Lleva 3D")
        window.color = color.rgb(12, 22, 34)
        window.borderless = False
        window.exit_button.visible = True
        window.fps_counter.enabled = True

        self.sim = None
        self.activo = False
        self.terminado = False
        self.yaw = 0.0
        self.pitch = 0.0
        self.ultima_lleva = None
        self.entidades_jugadores = {}
        self.entidades_obstaculos = []
        self.entidades_powerups = {}
        self.marcadores_minimapa = {}
        self.entidades_mapa_obstaculos = []

        self._crear_escena()
        self._crear_interfaz()
        self._mostrar_inicio()
        self.loop = Entity()
        self.loop.update = self.update
        self.loop.input = self.input
        self.app.run()

    def _crear_escena(self):
        Sky()
        self.luz = DirectionalLight()
        self.luz.look_at((1, -2, -1))
        AmbientLight(color=color.rgba(150, 160, 180, 0.55))

        Entity(
            model="plane", scale=(13.0, 1, 8.0), position=(0, -0.06, 0),
            texture="white_cube", texture_scale=(13, 8),
            color=color.rgb(54, 112, 74), collider="box",
        )
        # Límites físicos y visuales del campo.
        pared_color = color.rgb(46, 64, 76)
        for x in (-6.5, 6.5):
            Entity(model="cube", position=(x, 1.0, 0), scale=(0.16, 2, 7.8),
                   color=pared_color, collider="box")
        for z in (-3.9, 3.9):
            Entity(model="cube", position=(0, 1.0, z), scale=(13.0, 2, 0.16),
                   color=pared_color, collider="box")

        # Cuadrícula discreta para dar profundidad al campo.
        for x in range(-6, 7):
            Entity(model="cube", position=(x, 0.005, 0), scale=(0.012, 0.01, 7.7),
                   color=color.rgba(205, 225, 190, 35))
        for z in range(-3, 4):
            Entity(model="cube", position=(0, 0.006, z), scale=(12.8, 0.01, 0.012),
                   color=color.rgba(205, 225, 190, 35))

        camera.fov = 88
        camera.position = (0, ALTURA_OJOS, 0)
        camera.rotation = (0, 0, 0)

    def _crear_interfaz(self):
        self.titulo = Text(
            "LA LLEVA 3D", position=(-0.86, 0.45), scale=1.5,
            color=color.white, background=True,
        )
        self.estado = Text(
            "Pulsa COMENZAR para jugar", position=(-0.86, 0.39),
            scale=0.85, color=color.azure,
        )
        self.instrucciones = Text(
            "WASD: moverse   |   Mouse: mirar   |   ESC: pausar",
            position=(-0.86, -0.46), scale=0.75, color=color.white,
        )
        self.cruz = Text("+", origin=(0, 0), scale=1.2, color=color.white)
        self.cruz.enabled = False
        self.panel_mapa = Entity(
            parent=camera.ui, model="quad", position=(0.34, 0.31),
            scale=(0.28, 0.20), color=color.rgba(8, 16, 25, 220),
        )
        self.mapa_borde = Entity(
            parent=self.panel_mapa, model="quad", z=-0.01,
            scale=(0.97, 0.94), color=color.rgb(95, 125, 135),
        )
        self.mapa_campo = Entity(
            parent=self.panel_mapa, model="quad", z=-0.02,
            scale=(0.94, 0.91), color=color.rgb(48, 91, 65),
        )
        self.mapa_titulo = Text(
            "MINIMAPA", parent=self.panel_mapa, position=(-0.42, 0.39),
            scale=0.75, color=color.white,
        )
        self.minimapa_activo = False
        self.boton_inicio = Button(
            text="COMENZAR", scale=(0.24, 0.075), position=(0, -0.02),
            color=color.azure, on_click=self._accion_inicio,
        )
        self.boton_reiniciar = Button(
            text="JUGAR OTRA VEZ", scale=(0.25, 0.075), position=(0, -0.13),
            color=color.azure, on_click=self.reiniciar,
        )
        self.boton_reiniciar.enabled = False
        self.resultado = Text(
            "", origin=(0, 0), position=(0, 0.13), scale=1.5,
            color=color.white, background=True,
        )
        self.resultado.enabled = False

    def _mostrar_inicio(self):
        self.boton_inicio.enabled = True
        self.boton_reiniciar.enabled = False
        self.resultado.enabled = False
        self.panel_mapa.enabled = False
        self.estado.text = "Esquiva al rival o persíguelo si tienes la lleva."

    def _crear_simulacion(self):
        self.sim = SimulacionRonda({0: "Jugador", 1: "Rival IA"}, duracion_ronda=60)
        # Se conserva la simulación y la lógica de colisiones de la rama online.
        from juego_lleva.models.jugador_ia import JugadorIA
        x, y = self.sim.jugadores[1].x, self.sim.jugadores[1].y
        ia = JugadorIA(x, y, 1, "Rival IA")
        self.sim.jugadores[1] = ia
        ia.jugadores = self.sim.jugadores
        self._construir_jugadores()
        self._construir_obstaculos()

    def _accion_inicio(self):
        if self.sim is not None and not self.terminado:
            self.activo = True
            self.boton_inicio.enabled = False
            self.panel_mapa.enabled = True
            self.cruz.enabled = True
            mouse.locked = True
            mouse.visible = False
            return
        self.iniciar()

    def iniciar(self):
        self._crear_simulacion()
        self.activo = True
        self.terminado = False
        self.boton_inicio.enabled = False
        self.boton_reiniciar.enabled = False
        self.resultado.enabled = False
        self.panel_mapa.enabled = True
        self.cruz.enabled = True
        mouse.locked = True
        mouse.visible = False
        self._sincronizar_camara()

    def _construir_jugadores(self):
        for entidad in self.entidades_jugadores.values():
            destroy(entidad["root"])
        for marker in self.marcadores_minimapa.values():
            destroy(marker)
        self.entidades_jugadores.clear()
        self.marcadores_minimapa.clear()
        for jugador in self.sim.jugadores:
            root = Entity()
            # La cámara está en la cabeza del jugador local: ocultamos su malla
            # para que no tape la vista en primera persona.
            root.enabled = jugador.id != 0
            color_jugador = color.rgb(*self.sim.config.color_jugador(jugador.id))
            torso = Entity(parent=root, model="cube", position=(0, 0.88, 0),
                           scale=(0.43, 0.72, 0.27), color=color_jugador)
            cabeza = Entity(parent=root, model="sphere", position=(0, 1.48, 0),
                            scale=(0.34, 0.34, 0.34), color=color.rgb(232, 190, 150))
            Entity(parent=root, model="cube", position=(0, 1.12, -0.17),
                   scale=(0.47, 0.13, 0.08), color=color.red)
            Entity(parent=root, model="cube", position=(-0.13, 0.30, 0),
                   scale=(0.14, 0.55, 0.16), color=color.rgb(38, 48, 68))
            Entity(parent=root, model="cube", position=(0.13, 0.30, 0),
                   scale=(0.14, 0.55, 0.16), color=color.rgb(38, 48, 68))
            aura = Entity(parent=root, model="sphere", position=(0, 1.75, 0),
                          scale=(0.72, 0.10, 0.72), color=color.rgba(255, 45, 45, 90))
            aura.enabled = False
            self.entidades_jugadores[jugador.id] = {
                "root": root, "torso": torso, "aura": aura,
            }
            marker = Entity(
                parent=self.panel_mapa, model="circle", scale=(0.085, 0.085),
                color=color_jugador, z=-0.04,
            )
            self.marcadores_minimapa[jugador.id] = marker

    def _construir_obstaculos(self):
        for entidad in self.entidades_obstaculos:
            destroy(entidad)
        for marker in self.entidades_mapa_obstaculos:
            destroy(marker)
        self.entidades_obstaculos.clear()
        self.entidades_mapa_obstaculos.clear()
        for obstaculo in self.sim.entorno.obstaculos:
            wx, wz = _mundo(obstaculo.x + obstaculo.ancho / 2,
                            obstaculo.y + obstaculo.alto / 2)
            tam = obstaculo.ancho / ESCALA_MUNDO
            if obstaculo.tipo == "caja":
                entidad = Entity(
                    model="cube", position=(wx, 0.48, wz),
                    scale=(tam, 0.96, tam), color=color.rgb(132, 83, 47),
                    collider="box",
                )
                Entity(parent=entidad, model="cube", position=(0, 0.52, 0),
                       scale=(1.02, 0.04, 1.02), color=color.rgb(174, 123, 72))
            else:
                entidad = Entity(
                    model="cube", position=(wx, 0.015, wz),
                    scale=(tam, 0.025, tam), color=color.rgba(35, 145, 210, 155),
                )
            self.entidades_obstaculos.append(entidad)
            mx = (obstaculo.x / ANCHO_LOGICO - 0.5) * 0.84
            my = (0.5 - obstaculo.y / ALTO_LOGICO) * 0.72
            marker = Entity(
                parent=self.panel_mapa, model="quad", position=(mx, my, -0.035),
                scale=(obstaculo.ancho / ANCHO_LOGICO * 0.84,
                       obstaculo.alto / ALTO_LOGICO * 0.72),
                color=color.rgba(55, 175, 220, 180) if obstaculo.tipo == "zona"
                else color.rgb(155, 105, 65),
            )
            self.entidades_mapa_obstaculos.append(marker)

    def _actualizar_camara(self):
        jugador = self.sim.obtener_jugador(0)
        wx, wz = _mundo(jugador.x + self.sim.config.TAMAÑO_JUGADOR / 2,
                        jugador.y + self.sim.config.TAMAÑO_JUGADOR / 2)
        camera.position = (wx, ALTURA_OJOS, wz)
        camera.rotation = (self.pitch, self.yaw, 0)

    def _sincronizar_camara(self):
        self._actualizar_camara()

    def _actualizar_powerups(self):
        vivos = set()
        for indice, power in enumerate(self.sim.power_ups):
            vivos.add(id(power))
            entidad = self.entidades_powerups.get(id(power))
            if entidad is None:
                wx, wz = _mundo(power.x, power.y)
                color_power = {
                    "velocidad": color.lime,
                    "congelar": color.cyan,
                    "escudo": color.yellow,
                }.get(power.tipo, color.white)
                entidad = Entity(
                    model="sphere", position=(wx, 0.38, wz),
                    scale=0.36, color=color_power,
                    rotation=(0, 0, 0),
                )
                self.entidades_powerups[id(power)] = entidad
            entidad.rotation_y += 1.5
        for key in list(self.entidades_powerups):
            if key not in vivos:
                destroy(self.entidades_powerups.pop(key))

    def _actualizar_minimapa(self):
        for jugador in self.sim.jugadores:
            marker = self.marcadores_minimapa[jugador.id]
            nx = (jugador.x / ANCHO_LOGICO - 0.5) * 0.84
            ny = (0.5 - jugador.y / ALTO_LOGICO) * 0.72
            marker.position = (nx, ny, -0.05)
            marker.color = color.red if jugador.es_lleva else color.rgb(
                *self.sim.config.color_jugador(jugador.id))
            self.entidades_jugadores[jugador.id]["aura"].enabled = jugador.es_lleva

    def _actualizar_estado(self):
        restante = max(0, int(self.sim.duracion_ronda - self.sim.tiempo_ronda))
        quien = next((j.nombre for j in self.sim.jugadores if j.es_lleva), "—")
        self.estado.text = f"Tiempo: {restante:02d}s   |   La lleva: {quien}"

    def update(self):
        if not self.activo or self.sim is None or self.sim.terminada:
            return
        dt = min(time.dt, 0.05)
        self.yaw += mouse.velocity[0] * 95
        self.pitch = max(-75, min(75, self.pitch - mouse.velocity[1] * 95))

        teclas = {
            "w": bool(held_keys["w"]),
            "a": bool(held_keys["a"]),
            "s": bool(held_keys["s"]),
            "d": bool(held_keys["d"]),
        }
        entrada = _entrada_relativa(teclas, math.radians(self.yaw))
        self.sim.set_entrada(0, entrada)
        self.sim.paso(dt)

        for jugador in self.sim.jugadores:
            wx, wz = _mundo(jugador.x + self.sim.config.TAMAÑO_JUGADOR / 2,
                            jugador.y + self.sim.config.TAMAÑO_JUGADOR / 2)
            self.entidades_jugadores[jugador.id]["root"].position = (wx, 0, wz)
        self._actualizar_camara()
        self._actualizar_powerups()
        self._actualizar_minimapa()
        self._actualizar_estado()

        if self.sim.terminada:
            self._terminar()

    def _terminar(self):
        self.activo = False
        self.terminado = True
        mouse.locked = False
        mouse.visible = True
        self.cruz.enabled = False
        ganador = self.sim.ganador
        nombre = next((j.nombre for j in self.sim.jugadores if j.id == ganador), "Empate")
        self.resultado.text = f"¡{nombre} gana!"
        self.resultado.enabled = True
        self.boton_reiniciar.enabled = True
        self.estado.text = "Ronda terminada"

    def reiniciar(self):
        if self.sim is None:
            self.iniciar()
            return
        self.sim.reiniciar()
        # La simulación conserva la instancia de IA al reiniciar.
        rival = self.sim.obtener_jugador(1)
        rival.jugadores = self.sim.jugadores
        self._construir_obstaculos()
        self.activo = True
        self.terminado = False
        self.resultado.enabled = False
        self.boton_reiniciar.enabled = False
        self.panel_mapa.enabled = True
        mouse.locked = True
        mouse.visible = False
        self._actualizar_minimapa()

    def input(self, key):
        if key == "escape" and self.activo:
            self.activo = False
            mouse.locked = False
            mouse.visible = True
            self.cruz.enabled = False
            self.estado.text = "Partida pausada. Pulsa COMENZAR para continuar."
            self.boton_inicio.text = "CONTINUAR"
            self.boton_inicio.enabled = True
        elif key == "enter" and not self.activo and not self.terminado:
            self._accion_inicio()


def main():
    LaLlevaUrsina()


if __name__ == "__main__":
    main()
