"""Versión 3D de escritorio de La Lleva usando Ursina.

La versión Pygame original permanece intacta. Este módulo reutiliza la
simulación autoritativa existente (SimulacionRonda) y solo sustituye la capa
visual por una escena 3D con cámara en primera persona.
"""

from __future__ import annotations

import math
from ursina.shaders import unlit_shader

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
        self.cantidad_ia = 3
        self.dificultad = "normal"
        self.duracion_ronda = 180
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
        # Cielo azul visible y materiales sin depender de la intensidad de luz.
        Sky(color=color.rgb(105, 175, 225))
        self.luz = DirectionalLight()
        self.luz.look_at((1, -2, -1))
        AmbientLight(color=color.rgba(190, 195, 205, 0.65))

        Entity(
            model="plane", scale=(13.0, 1, 8.0), position=(0, -0.06, 0),
            texture="white_cube", texture_scale=(13, 8),
            color=color.rgb(48, 135, 72), collider="box", shader=unlit_shader,
        )
        # Detalles de parque alrededor de la zona de juego: senderos, árboles
        # bajos, jardineras y bancas. Se mantienen fuera del área central.
        Entity(model="cube", position=(0, -0.025, 0), scale=(1.15, 0.025, 7.7),
               color=color.rgb(218, 190, 130), shader=unlit_shader)
        Entity(model="cube", position=(0, -0.02, 0), scale=(12.8, 0.025, 0.75),
               color=color.rgb(218, 190, 130), shader=unlit_shader)
        for tx, tz in [(-5.7, -3.2), (-5.7, 3.2), (5.7, -3.2), (5.7, 3.2)]:
            Entity(model="cylinder", position=(tx, 0.55, tz), scale=(0.28, 1.1, 0.28),
                   color=color.rgb(105, 69, 42), collider="box")
            Entity(model="sphere", position=(tx, 1.55, tz), scale=(1.25, 1.45, 1.25),
                   color=color.rgb(42, 130, 58))
        for bx, bz in [(-3.6, 2.9), (3.6, -2.9)]:
            Entity(model="cube", position=(bx, 0.42, bz), scale=(1.15, 0.12, 0.38),
                   color=color.rgb(135, 78, 42))
            for leg in (-0.42, 0.42):
                Entity(model="cube", position=(bx + leg, 0.2, bz), scale=(0.09, 0.42, 0.1),
                       color=color.rgb(70, 55, 42))
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
            color=color.rgb(255, 225, 95), background=True,
        )
        self.estado = Text(
            "Pulsa COMENZAR para jugar", position=(-0.86, 0.39),
            scale=0.85, color=color.rgb(255, 255, 255), background=True,
        )
        self.instrucciones = Text(
            "WASD: moverse   |   Mouse: mirar   |   ESC: pausar",
            position=(-0.86, -0.46), scale=0.75, color=color.white, background=True,
        )
        self.cruz = Text("+", origin=(0, 0), scale=1.2, color=color.white)
        self.cruz.enabled = False
        self.panel_mapa = Entity(
            parent=camera.ui, model="quad", position=(0.34, 0.31),
            scale=(0.31, 0.23), color=color.rgba(5, 12, 22, 245),
        )
        self.mapa_borde = Entity(
            parent=self.panel_mapa, model="quad", z=-0.01,
            scale=(0.97, 0.94), color=color.rgb(235, 195, 75),
        )
        self.mapa_campo = Entity(
            parent=self.panel_mapa, model="quad", z=-0.02,
            scale=(0.94, 0.91), color=color.rgb(32, 105, 58),
        )
        self.mapa_titulo = Text(
            "MINIMAPA", parent=self.panel_mapa, position=(-0.42, 0.39, -0.03),
            scale=0.75, color=color.rgb(255, 230, 130), background=True,
        )
        self.minimapa_activo = False
        self.panel_menu = Entity(
            parent=camera.ui, model="quad", position=(0, 0.02, -0.1),
            scale=(0.78, 0.78), color=color.rgba(7, 16, 29, 250),
        )
        self.titulo_menu = Text(
            "CONFIGURA TU PARTIDA", parent=self.panel_menu,
            position=(0, 0.38, -0.02), origin=(0, 0), scale=1.15,
            color=color.rgb(255, 225, 95), background=True,
        )
        self.etiqueta_ia = Text(
            "Rivales controlados por IA", parent=self.panel_menu,
            position=(0, 0.20, -0.02), origin=(0, 0), scale=0.85,
            color=color.rgb(245, 248, 255), background=True,
        )
        self.valor_ia = Text(
            str(self.cantidad_ia), parent=self.panel_menu,
            position=(0, 0.04, -0.02), origin=(0, 0), scale=1.35,
            color=color.rgb(255, 235, 100), background=True,
        )
        self.boton_ia_menos = Button(
            text="−", parent=self.panel_menu, scale=(0.16, 0.11),
            position=(-0.23, 0.04), color=color.rgb(20, 95, 150),
            highlight_color=color.rgb(35, 135, 195),
            on_click=lambda: self._cambiar_ia(-1),
        )
        self.boton_ia_mas = Button(
            text="+", parent=self.panel_menu, scale=(0.16, 0.11),
            position=(0.23, 0.04), color=color.rgb(20, 95, 150),
            highlight_color=color.rgb(35, 135, 195),
            on_click=lambda: self._cambiar_ia(1),
        )
        self.etiqueta_dificultad = Text(
            "Dificultad", parent=self.panel_menu, position=(0, -0.12, -0.02),
            origin=(0, 0), scale=0.8, color=color.white, background=True,
        )
        self.boton_dificultad = Button(
            text=self.dificultad.upper(), parent=self.panel_menu,
            scale=(0.38, 0.09), position=(0, -0.23),
            color=color.rgb(18, 105, 165),
            text_color=color.white, highlight_color=color.rgb(35, 145, 205),
            on_click=self._cambiar_dificultad,
        )
        self.boton_inicio = Button(
            text="COMENZAR PARTIDA", parent=self.panel_menu,
            scale=(0.48, 0.105), position=(0, -0.39),
            color=color.rgb(15, 135, 75),
            text_color=color.white, highlight_color=color.rgb(30, 175, 100),
            on_click=self._accion_inicio,
        )
        self.panel_menu.enabled = True
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
        self.panel_menu.enabled = True
        self.titulo_menu.text = "CONFIGURA TU PARTIDA"
        self.boton_inicio.text = "COMENZAR PARTIDA"
        self._actualizar_controles_menu()
        self.estado.text = "Elige cuántas IA quieres y pulsa COMENZAR."

    def _actualizar_controles_menu(self):
        self.valor_ia.text = str(self.cantidad_ia)
        self.boton_dificultad.text = self.dificultad.upper()

    def _cambiar_ia(self, delta):
        self.cantidad_ia = max(1, min(8, self.cantidad_ia + delta))
        self._actualizar_controles_menu()

    def _cambiar_dificultad(self):
        opciones = ("facil", "normal", "dificil")
        self.dificultad = opciones[(opciones.index(self.dificultad) + 1) % len(opciones)]
        self._actualizar_controles_menu()

    def _crear_simulacion(self):
        nombres = {0: "Jugador"}
        nombres.update({i: f"IA {i}" for i in range(1, self.cantidad_ia + 1)})
        self.sim = SimulacionRonda(nombres, duracion_ronda=self.duracion_ronda)
        from juego_lleva.models.jugador_ia import JugadorIA
        for indice in range(1, self.cantidad_ia + 1):
            original = self.sim.obtener_jugador(indice)
            ia = JugadorIA(original.x, original.y, indice, f"IA {indice}")
            self.sim.jugadores[indice] = ia
        for jugador in self.sim.jugadores:
            if isinstance(jugador, JugadorIA):
                jugador.jugadores = self.sim.jugadores
                jugador.tiempo_reaccion = {"facil": 0.55, "normal": 0.28, "dificil": 0.12}[self.dificultad]
                jugador.velocidad_ia *= {"facil": 0.78, "normal": 1.0, "dificil": 1.18}[self.dificultad]
        self._construir_jugadores()
        self._construir_obstaculos()

    def _accion_inicio(self):
        if self.sim is not None and not self.terminado:
            self.activo = True
            self.boton_inicio.enabled = False
            self.panel_menu.enabled = False
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
        self.panel_menu.enabled = False
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
            torso = Entity(parent=root, model="cube", position=(0, 0.92, 0),
                           scale=(0.52, 0.78, 0.34), color=color_jugador,
                           shader=unlit_shader)
            cabeza = Entity(parent=root, model="sphere", position=(0, 1.58, 0),
                            scale=(0.38, 0.38, 0.38), color=color.rgb(244, 190, 145),
                            shader=unlit_shader)
            # Solo el jugador que lleva la lleva tendrá una banda roja.
            banda = Entity(parent=root, model="cube", position=(0, 1.12, -0.19),
                           scale=(0.56, 0.15, 0.07), color=color.rgb(255, 45, 45),
                           shader=unlit_shader)
            banda.enabled = jugador.es_lleva
            Entity(parent=root, model="cube", position=(-0.15, 0.32, 0),
                   scale=(0.17, 0.58, 0.19), color=color.rgb(28, 42, 68),
                   shader=unlit_shader)
            Entity(parent=root, model="cube", position=(0.15, 0.32, 0),
                   scale=(0.17, 0.58, 0.19), color=color.rgb(28, 42, 68),
                   shader=unlit_shader)
            aura = Entity(parent=root, model="sphere", position=(0, 1.75, 0),
                          scale=(0.72, 0.10, 0.72), color=color.rgba(255, 45, 45, 90))
            aura.enabled = False
            self.entidades_jugadores[jugador.id] = {
                "root": root, "torso": torso, "aura": aura, "banda": banda,
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
        # Al iniciar, orientar la cámara hacia el centro del parque. El jugador
        # aparece desplazado del centro; mirar en yaw=0 lo deja mirando paralelo
        # al campo y puede dar la impresión de que la escena está vacía.
        jugador = self.sim.obtener_jugador(0)
        wx, wz = _mundo(jugador.x + self.sim.config.TAMAÑO_JUGADOR / 2,
                        jugador.y + self.sim.config.TAMAÑO_JUGADOR / 2)
        self.yaw = math.degrees(math.atan2(-wx, -wz))
        self.pitch = 12.0
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
            self.entidades_jugadores[jugador.id]["banda"].enabled = jugador.es_lleva

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
            self.estado.text = "Partida pausada. Pulsa CONTINUAR para seguir."
            self.titulo_menu.text = "PARTIDA PAUSADA"
            self.boton_inicio.text = "CONTINUAR"
            self.boton_inicio.enabled = True
            self.panel_menu.enabled = True
        elif key == "enter" and not self.activo and not self.terminado:
            self._accion_inicio()


def main():
    LaLlevaUrsina()


if __name__ == "__main__":
    main()
