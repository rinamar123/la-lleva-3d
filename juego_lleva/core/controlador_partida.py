"""Controlador que maneja la logica de la partida: movimiento, colisiones, power-ups."""

import random

import pygame
from juego_lleva.constantes_entrada import K_ESCAPE, K_p, KEYDOWN

from juego_lleva.core.estado import EstadoJuego

COLORES_POWER_UP = {
    "velocidad": (0, 220, 100),
    "escudo": (100, 150, 255),
    "congelar": (80, 200, 255),
}


class TeclasFusionadas:
    """Mapa de teclas que combina el teclado físico con teclas virtuales."""

    def __init__(self, base, extras):
        self.base = base
        self.extras = set(extras)

    def __getitem__(self, codigo):
        return bool(self.base[codigo]) or codigo in self.extras


class ControladorPartida:
    """Gestiona la lógica de la partida: input, movimiento, colisiones, power-ups."""

    def __init__(self, juego):
        self.j = juego

    def verificar_pausa(self):
        """Verifica si el jugador solicitó pausa. Retorna True si se pausó."""
        if self.j.tactil.consumir_pausa():
            self.j.estado = EstadoJuego.PAUSA
            return True
        for evento in self.j.eventos_pendientes:
            if evento.type == KEYDOWN and evento.key in (K_ESCAPE, K_p):
                self.j.estado = EstadoJuego.PAUSA
                return True
        return False

    def actualizar(self, delta_tiempo):
        """Ejecuta toda la lógica de la partida en un frame. Retorna True si la ronda terminó."""
        if self.verificar_pausa():
            return True

        teclas = self.teclas_fusionadas()
        obstaculos = self.j.gestor_modos.entorno.obstaculos
        self.j.gestor_modos.entorno.actualizar(delta_tiempo)

        self.actualizar_power_ups(delta_tiempo)
        self.actualizar_efectos_activos(delta_tiempo)

        for jugador in self.j.jugadores:
            if self.j.efectos_activos.get(jugador.id, {}).get("congelar", 0) > 0:
                continue
            en_zona = self.j.servicio_colision.jugador_en_zona_lenta(jugador, obstaculos)
            jugador.mover(teclas, en_zona, delta_tiempo, obstaculos=obstaculos)

        for jugador in self.j.jugadores:
            for obs in obstaculos:
                if obs.tipo == "caja" and self.j.servicio_colision.detectar_colision_jugador_obstaculo(jugador, obs):
                    self.j.servicio_colision.resolver_obstaculo(jugador, obs)

        self.j.tiempo_pasos += delta_tiempo
        if self.j.tiempo_pasos >= self.j.config.INTERVALO_PASOS:
            self.j.tiempo_pasos = 0
            if any(j.velocidad_abs > 80 for j in self.j.jugadores):
                self.j.audio.paso()

        colisiones = self.j.servicio_colision.detectar_colisiones(self.j.jugadores, delta_tiempo)
        for j1, j2 in colisiones:
            self.procesar_colision(j1, j2)
            self.j.servicio_colision.separar_jugadores(j1, j2, self.j.config.TAMAÑO_JUGADOR)

        self.j.tiempo_ronda += delta_tiempo
        if self.j.tiempo_ronda >= self.j.duracion_ronda:
            self.finalizar_ronda()
            return True

        self._actualizar_particulas_rastro(delta_tiempo)
        self.j.efectos = self.j.efecto_service.actualizar(self.j.efectos, delta_tiempo)
        if self.j.toque_flash > 0:
            self.j.toque_flash -= delta_tiempo

        return False

    def _actualizar_particulas_rastro(self, delta_tiempo):
        """Actualiza las particulas de rastro de todos los jugadores."""
        for jugador in self.j.jugadores:
            pid = jugador.id
            if pid not in self.j.particulas_rastro:
                self.j.particulas_rastro[pid] = []
            self.j.particula_service.actualizar_rastro(
                pid, self.j.particulas_rastro[pid], jugador,
                self.j.config, delta_tiempo)

    def teclas_fusionadas(self):
        """Combina las teclas físicas con las teclas virtuales táctiles."""
        return TeclasFusionadas(pygame.key.get_pressed(), self.j.tactil.teclas_activas())

    def actualizar_efectos_activos(self, delta_tiempo):
        """Decrementa los temporizadores de efectos y revierte los vencidos."""
        vencidos = []
        for id_jugador, timers in list(self.j.efectos_activos.items()):
            for tipo in list(timers):
                timers[tipo] -= delta_tiempo
                if timers[tipo] <= 0:
                    vencidos.append((id_jugador, tipo))
                    del timers[tipo]
            if not timers:
                del self.j.efectos_activos[id_jugador]

        for id_jugador, tipo in vencidos:
            jugador = next((j for j in self.j.jugadores if j.id == id_jugador), None)
            if jugador is None:
                continue
            if tipo == "velocidad":
                jugador.factor_velocidad = 1.0
            elif tipo == "congelar":
                jugador.congelado = 0.0

    def actualizar_power_ups(self, delta_tiempo):
        """Genera, envejece y recolecta power-ups durante la ronda."""
        self.j.power_up_timer += delta_tiempo
        if self.j.power_up_timer >= self.j.config.POWER_UP_FRECUENCIA_SEG:
            self.j.power_up_timer = 0
            nuevo = self.j.power_up_service.crear(self.j.jugadores, self.j.power_ups)
            if nuevo:
                self.j.power_ups.append(nuevo)

        for pu in self.j.power_ups:
            pu.vida -= delta_tiempo

        for jugador in self.j.jugadores:
            rect_jugador = jugador.obtener_rectangulo()
            for pu in list(self.j.power_ups):
                if rect_jugador.colliderect(pu.obtener_rectangulo()):
                    self._recoger_power_up(jugador, pu)
                    self.j.power_ups.remove(pu)

        self.j.power_ups = [pu for pu in self.j.power_ups if not pu.expirado()]

    def _recoger_power_up(self, jugador, power_up):
        """Aplica el efecto de un power-up recogido."""
        rival = next((j for j in self.j.jugadores if j.id != jugador.id), None)
        efecto = self.j.power_up_service.efecto(jugador, rival, power_up.tipo)
        if not efecto:
            return
        id_objetivo, tipo, duracion = efecto
        objetivo = next((j for j in self.j.jugadores if j.id == id_objetivo), None)
        if objetivo is None:
            return

        if tipo == "velocidad":
            objetivo.factor_velocidad = self.j.config.FACTOR_VELOCIDAD_POWER
            self.j.efectos_activos.setdefault(id_objetivo, {})["velocidad"] = duracion
        elif tipo == "congelar":
            self.j.efectos_activos.setdefault(id_objetivo, {})["congelar"] = duracion
            objetivo.congelado = duracion
        elif tipo == "escudo":
            objetivo.escudo = True

        color = COLORES_POWER_UP.get(power_up.tipo, (255, 215, 0))
        if len(self.j.efectos) < 6:
            self.j.efectos.append(self.j.efecto_service.crear_toque(power_up.x, power_up.y, color, 10))
        self.j.audio.clic()

        if tipo == "velocidad":
            self.j._mostrar_toast(f"¡{objetivo.nombre}: VELOCIDAD!", color)
        elif tipo == "congelar":
            self.j._mostrar_toast(f"¡{objetivo.nombre} CONGELADO!", color)
        elif tipo == "escudo":
            self.j._mostrar_toast(f"¡{objetivo.nombre}: ESCUDO!", color)

    def procesar_colision(self, j1, j2):
        """Procesa la colisión entre dos jugadores."""
        if j1.es_lleva:
            if getattr(j2, "escudo", False):
                self._romper_escudo(j2, j1)
            else:
                self._transferir_lleva(j1, j2)
        elif j2.es_lleva:
            if getattr(j1, "escudo", False):
                self._romper_escudo(j1, j2)
            else:
                self._transferir_lleva(j2, j1)

    def _romper_escudo(self, protegido, llevador):
        """Consume el escudo de un jugador y bloquea el toque."""
        protegido.escudo = False
        self.j.toque_flash = max(self.j.toque_flash, 0.06)
        self.j.audio.clic()
        self.j._mostrar_toast(f"¡Escudo de {protegido.nombre} bloqueado!", (100, 150, 255))
        x1, y1 = llevador.obtener_posicion()
        x2, y2 = protegido.obtener_posicion()
        if len(self.j.efectos) < 6:
            self.j.efectos.append(
                self.j.efecto_service.crear_anillo((x1 + x2) / 2, (y1 + y2) / 2, (100, 150, 255)))

    def _transferir_lleva(self, quien_tiene_lleva, quien_recibe):
        """Transfiere el rol de 'La Lleva' al jugador tocado."""
        self.j.tiempo_inicio_lleva = self.j.ronda_service.transferir_lleva(
            quien_tiene_lleva, quien_recibe, self.j.tiempo_ronda, self.j.tiempo_inicio_lleva)
        quien_recibe.tropezando = self.j.config.DURACION_TROPIEZO
        self.j.toque_flash = 0.12
        self._crear_efecto_toque(quien_tiene_lleva, quien_recibe)
        self.j.audio.tocar()
        self.j._mostrar_toast(f"¡{quien_recibe.nombre} es La Lleva!", self.j.config.COLOR_LLEVA)

    def _crear_efecto_toque(self, j1, j2):
        """Crea un efecto visual en el punto medio del toque."""
        x1, y1 = j1.obtener_posicion()
        x2, y2 = j2.obtener_posicion()
        if len(self.j.efectos) < 6:
            self.j.efectos.append(self.j.efecto_service.crear_toque((x1 + x2) / 2, (y1 + y2) / 2))

    def finalizar_ronda(self):
        """Finaliza la ronda actual y determina el ganador."""
        self.j.ronda_service.cerrar_lleva_actual(
            self.j.jugadores, self.j.tiempo_ronda, self.j.tiempo_inicio_lleva)
        ganador = self.j.puntaje_service.obtener_ganador()
        if ganador is not None:
            nombre = next((j.nombre for j in self.j.jugadores if j.id == ganador), "Jugador")
            self.j._mostrar_toast(f"¡{nombre} gana!", self.j.config.COLOR_DORADO)
            ganador_jugador = next((j for j in self.j.jugadores if j.id == ganador), None)
            if ganador_jugador:
                x, y = ganador_jugador.obtener_posicion()
                for _ in range(8):
                    if len(self.j.efectos) >= 10:
                        break
                    self.j.efectos.append(self.j.efecto_service.crear_toque(
                        x + random.uniform(-80, 80), y + random.uniform(-80, 80),
                        self.j.config.COLOR_DORADO, 6))
        self.j.audio.fin_ronda()
        self.j.estado = EstadoJuego.FIN_RONDA
