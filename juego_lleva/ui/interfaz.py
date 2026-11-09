"""Módulo de interfaz de usuario que maneja todos los elementos visuales del juego."""

import pygame
from juego_lleva.fuentes import fuente
import math
import random
from juego_lleva.core.config import Config
from juego_lleva.ui.acciones import ALTO_BOTON_MENU, rects_sala


class Interfaz:
    """Clase que gestiona toda la interfaz de usuario del juego."""

    acciones_menu = ["un_jugador", "jugar", "en_linea", "ayuda", "ranking", "opciones", "salir"]
    BOTONES_MENU = [
        ("Un Jugador", "un_jugador", 260),
        ("Multijugador", "jugar", 308),
        ("En Linea", "en_linea", 356),
        ("Como Jugar", "ayuda", 404),
        ("Ranking", "ranking", 452),
        ("Opciones", "opciones", 500),
        ("Salir", "salir", 548),
    ]

    def __init__(self):
        """Inicializa la interfaz con fuentes y partículas decorativas."""
        self.config = Config()
        if not self.config.PLATAFORMA_WEB:
            # En escritorio el botón lleva al navegador, no a la sala local.
            self.BOTONES_MENU = [
                ("En Linea (web)" if accion == "en_linea" else texto, accion, y)
                for texto, accion, y in self.BOTONES_MENU
            ]
        self.fuente_titulo = fuente(72)
        self.fuente_subtitulo = fuente(36)
        self.fuente_boton = fuente(32)
        self.fuente_pequena = fuente(24)
        self.fuente_hud = fuente(28)
        self.fuente_grande = fuente(56)
        self.fuente_countdown = fuente(120)
        self.tiempo_animacion = 0
        self.particulas = []
        self._particulas_cache = {}
        self._fondo_menu = None
        self.escala_ui = self.config.ALTO_PANTALLA / 1080.0
        self.en_linea = False
        self._generar_particulas_menu()

    def _u(self, valor):
        """Escala un valor de layout 1080p a la resolución activa.

        Args:
            valor (float): Medida original diseñada para 1080p.

        Returns:
            int: Valor escalado para la pantalla actual.
        """
        return int(valor * self.escala_ui)

    def _generar_particulas_menu(self):
        """Genera partículas decorativas para el menú."""
        for _ in range(40):
            self.particulas.append({
                'x': random.randint(0, self.config.ANCHO_PANTALLA),
                'y': random.randint(0, self.config.ALTO_PANTALLA),
                'tamaño': random.randint(2, 5),
                'velocidad_x': random.uniform(-0.5, 0.5),
                'velocidad_y': random.uniform(-0.3, 0.3),
                'alpha': random.randint(20, 60),
                'fase': random.uniform(0, math.pi * 2)
            })

    def actualizar(self, delta_tiempo):
        """Actualiza las animaciones de la interfaz.

        Args:
            delta_tiempo (float): Tiempo transcurrido desde la última actualización.
        """
        self.tiempo_animacion += delta_tiempo
        for p in self.particulas:
            p['x'] += p['velocidad_x']
            p['y'] += p['velocidad_y']
            p['fase'] += 0.02
            p['alpha'] = int(30 + 20 * math.sin(p['fase']))

            if p['x'] < 0:
                p['x'] = self.config.ANCHO_PANTALLA
            elif p['x'] > self.config.ANCHO_PANTALLA:
                p['x'] = 0
            if p['y'] < 0:
                p['y'] = self.config.ALTO_PANTALLA
            elif p['y'] > self.config.ALTO_PANTALLA:
                p['y'] = 0

    def dibujar_particulas_menu(self, pantalla):
        """Dibuja las partículas decorativas del menú.

        Args:
            pantalla: Superficie de pygame donde dibujar.
        """
        for p in self.particulas:
            color = (80 + int(40 * math.sin(p['fase'])),
                    80 + int(40 * math.sin(p['fase'] + 1)),
                    120 + int(30 * math.sin(p['fase'] + 2)))
            superficie = self._superficie_particula(p['tamaño'], color, p['alpha'])
            pantalla.blit(superficie, (int(p['x']) - p['tamaño'], int(p['y']) - p['tamaño']))

    def _superficie_particula(self, tamano, color, alpha):
        """Devuelve (cacheando) la superficie de una partícula del menú.

        Args:
            tamano (int): Radio de la partícula.
            color (tuple): Color RGB.
            alpha (int): Opacidad (0-255).

        Returns:
            pygame.Surface: Partícula pre-renderizada reutilizable.
        """
        if len(self._particulas_cache) >= 512:
            self._particulas_cache.clear()
        clave = (tamano, color, alpha)
        if clave not in self._particulas_cache:
            surface = pygame.Surface((tamano * 2, tamano * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*color, alpha), (tamano, tamano), tamano)
            self._particulas_cache[clave] = surface
        return self._particulas_cache[clave]

    def dibujar_boton(self, pantalla, texto, x, y, ancho, alto, hover=False):
        """Dibuja un botón con efecto hover.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            texto (str): Texto del botón.
            x (int): Posición horizontal.
            y (int): Posición vertical.
            ancho (int): Ancho del botón.
            alto (int): Alto del botón.
            hover (bool): True si el mouse está sobre el botón.
        """
        if hover:
            escala = 1.05
            nuevo_ancho = int(ancho * escala)
            nuevo_alto = int(alto * escala)
            nuevo_x = x - (nuevo_ancho - ancho) // 2
            nuevo_y = y - (nuevo_alto - alto) // 2
        else:
            nuevo_ancho, nuevo_alto, nuevo_x, nuevo_y = ancho, alto, x, y

        sombra_surface = pygame.Surface((nuevo_ancho, nuevo_alto), pygame.SRCALPHA)
        sombra_surface.fill((0, 0, 0, 50))
        pygame.draw.rect(sombra_surface, (0, 0, 0, 50), (0, 0, nuevo_ancho, nuevo_alto), border_radius=14)
        pantalla.blit(sombra_surface, (nuevo_x + 4, nuevo_y + 4))

        color = self.config.COLOR_BOTON_HOVER if hover else self.config.COLOR_BOTON
        gradiente = pygame.Surface((nuevo_ancho, nuevo_alto), pygame.SRCALPHA)
        superior = tuple(min(255, c + 45) for c in color)
        inferior = tuple(int(c * 0.82) for c in color)
        for yy in range(nuevo_alto):
            t_grad = yy / max(1, nuevo_alto - 1)
            color_linea = tuple(int(superior[i] + (inferior[i] - superior[i]) * t_grad)
                                for i in range(3))
            pygame.draw.line(gradiente, color_linea, (0, yy), (nuevo_ancho, yy))
        pantalla.blit(gradiente, (nuevo_x, nuevo_y))

        if hover:
            brillo = pygame.Surface((nuevo_ancho - 4, nuevo_alto - 4), pygame.SRCALPHA)
            brillo.fill((255, 255, 255, 25))
            pygame.draw.rect(brillo, (255, 255, 255, 25), (0, 0, nuevo_ancho - 4, nuevo_alto - 4), border_radius=10)
            pantalla.blit(brillo, (nuevo_x + 2, nuevo_y + 2))

        pygame.draw.rect(pantalla, self.config.COLOR_BORDE, (nuevo_x, nuevo_y, nuevo_ancho, nuevo_alto), 2, border_radius=12)

        texto_render = self.fuente_boton.render(texto, True, (255, 255, 255))
        pantalla.blit(texto_render, (nuevo_x + nuevo_ancho // 2 - texto_render.get_width() // 2,
                                     nuevo_y + nuevo_alto // 2 - texto_render.get_height() // 2))

    def dibujar_panel(self, pantalla, x, y, ancho, alto, alpha=180):
        """Dibuja un panel semitransparente.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            x (int): Posición horizontal.
            y (int): Posición vertical.
            ancho (int): Ancho del panel.
            alto (int): Alto del panel.
            alpha (int): Nivel de transparencia (0-255).
        """
        sombra = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        sombra.fill((0, 0, 0, 30))
        pygame.draw.rect(sombra, (0, 0, 0, 30), (0, 0, ancho, alto), border_radius=10)
        pantalla.blit(sombra, (x + 5, y + 5))

        surface = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        surface.fill((30, 30, 50, alpha))
        pygame.draw.rect(surface, self.config.COLOR_BORDE, (0, 0, ancho, alto), 2, border_radius=10)
        pantalla.blit(surface, (x, y))

    def _dentro_boton(self, pos, x, y, ancho, alto):
        """Verifica si una posición está dentro de un botón.

        Args:
            pos (tuple): Posición (x, y) a verificar.
            x (int): Posición horizontal del botón.
            y (int): Posición vertical del botón.
            ancho (int): Ancho del botón.
            alto (int): Alto del botón.

        Returns:
            bool: True si la posición está dentro del botón (el borde derecho
                e inferior quedan fuera, para no solapar botones contiguos).
        """
        return x <= pos[0] < x + ancho and y <= pos[1] < y + alto

    def _describir_efectos(self, tipos, jugador):
        """Convierte los efectos activos de un jugador en un texto corto.

        Args:
            tipos (list): Efectos activos (tipos).
            jugador: Jugador al que pertenecen los efectos.

        Returns:
            str: Descripción de los efectos, o cadena vacía si no hay ninguno.
        """
        nombres = []
        if "velocidad" in tipos:
            nombres.append("VELOCIDAD")
        if getattr(jugador, "escudo", False):
            nombres.append("ESCUDO")
        if "congelar" in tipos:
            nombres.append("CONGELADO")
        return " + ".join(nombres)

    def actualizar_toasts(self, toasts, delta_tiempo):
        """Actualiza el tiempo de vida de las notificaciones en pantalla.

        Args:
            toasts (list): Lista de notificaciones activas.
            delta_tiempo (float): Tiempo transcurrido desde la última actualización.

        Returns:
            list: Notificaciones que siguen visibles.
        """
        vivos = []
        for t in toasts:
            t['tiempo'] += delta_tiempo
            if t['tiempo'] < t['duracion']:
                vivos.append(t)
        return vivos

    def dibujar_toasts(self, pantalla, toasts):
        """Dibuja las notificaciones de eventos (toasts) sobre el campo.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            toasts (list): Lista de notificaciones activas.
        """
        y = 90
        for t in toasts:
            progreso = t['tiempo'] / t['duracion']
            if progreso < 0.2:
                alpha = int(255 * progreso / 0.2)
            elif progreso > 0.75:
                alpha = int(255 * (1 - progreso) / 0.25)
            else:
                alpha = 255

            texto = self.fuente_boton.render(t['texto'], True, t.get('color', (255, 255, 255)))
            ancho_panel = texto.get_width() + 36
            alto_panel = texto.get_height() + 18
            panel = pygame.Surface((ancho_panel, alto_panel), pygame.SRCALPHA)
            pygame.draw.rect(panel, (30, 30, 50, 200), (0, 0, ancho_panel, alto_panel), border_radius=8)
            pygame.draw.rect(panel, (255, 255, 255, 120), (0, 0, ancho_panel, alto_panel), 1, border_radius=8)
            panel.set_alpha(alpha)
            x = self.config.ANCHO_PANTALLA // 2 - ancho_panel // 2
            pantalla.blit(panel, (x, y))

            texto_alpha = texto.copy()
            texto_alpha.set_alpha(alpha)
            pantalla.blit(texto_alpha, (x + 18, y + 9))
            y += alto_panel + 14

    def dibujar_hud(self, pantalla, tiempo, puntajes, jugadores, duracion=None, efectos=None):
        """Dibuja el heads-up display con información del juego.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            tiempo (float): Tiempo transcurrido de la ronda.
            puntajes (dict): Diccionario con tiempos de cada jugador.
            jugadores (list): Lista de jugadores activos.
            duracion (float, optional): Duración de la ronda. Por defecto la configurada.
            efectos (dict, optional): Efectos activos por jugador (id -> lista de tipos).
        """
        u = self.escala_ui
        self.dibujar_panel(pantalla, 0, 0, self.config.ANCHO_PANTALLA, self._u(70), 220)

        duracion_total = duracion if duracion is not None else self.config.DURACION_RONDA
        tiempo_restante = max(0, duracion_total - tiempo)
        porcentaje_tiempo = min(1.0, tiempo_restante / duracion_total) if duracion_total else 0

        barra_x = self._u(20)
        barra_y = self._u(12)
        barra_ancho = self._u(150)
        barra_alto = self._u(16)
        pygame.draw.rect(pantalla, (40, 40, 60), (barra_x, barra_y, barra_ancho, barra_alto), border_radius=8)
        if porcentaje_tiempo > 0.3:
            color_barra = self.config.COLOR_LIBRE
        elif porcentaje_tiempo > 0.1:
            color_barra = self.config.COLOR_DORADO
        else:
            color_barra = self.config.COLOR_LLEVA
        ancho_barra = int(barra_ancho * porcentaje_tiempo)
        pygame.draw.rect(pantalla, color_barra, (barra_x, barra_y, ancho_barra, barra_alto), border_radius=8)
        pygame.draw.rect(pantalla, (255, 255, 255, 60), (barra_x, barra_y, ancho_barra, barra_alto // 2), border_radius=6)

        texto_tiempo = self.fuente_hud.render(f"{int(tiempo_restante)}s", True, (255, 255, 255))
        pantalla.blit(texto_tiempo, (barra_x + barra_ancho + self._u(10), barra_y - 2))

        x_jugador = self._u(280)
        for jugador in jugadores:
            if jugador.es_lleva:
                color = self.config.COLOR_LLEVA
                indicador = "LA LLEVA"
                pulso = abs(math.sin(self.tiempo_animacion * 6)) * 0.3 + 0.7
                color_texto = (int(255 * pulso), int(100 * pulso), int(100 * pulso))
            else:
                color = self.config.color_jugador(jugador.id)
                indicador = "Libre"
                color_texto = (255, 255, 255)

            casilla = self._u(18)
            pygame.draw.rect(pantalla, color, (x_jugador, self._u(20), casilla, casilla), border_radius=4)
            pygame.draw.rect(pantalla, (255, 255, 255), (x_jugador, self._u(20), casilla, casilla), 1, border_radius=4)

            texto_j = self.fuente_hud.render(f"{jugador.nombre}: {indicador}", True, color_texto)
            pantalla.blit(texto_j, (x_jugador + self._u(24), self._u(18)))

            tiempo_j = puntajes.get(jugador.id, 0)
            texto_t = self.fuente_pequena.render(f"({int(tiempo_j)}s)", True, self.config.COLOR_PLATA)
            pantalla.blit(texto_t, (x_jugador + self._u(24) + texto_j.get_width() + 5, self._u(22)))

            if efectos and efectos.get(jugador.id):
                etiqueta_efectos = self._describir_efectos(efectos.get(jugador.id), jugador)
                if etiqueta_efectos:
                    texto_efecto = self.fuente_pequena.render(etiqueta_efectos, True, self.config.COLOR_DORADO)
                    pantalla.blit(texto_efecto, (x_jugador + self._u(24), self._u(42)))

            x_jugador += self._u(240)

        texto_control = "ESC: Salir" if self.en_linea else "P: Pausa"
        texto_salir = self.fuente_pequena.render(texto_control, True, self.config.COLOR_PLATA)
        pantalla.blit(texto_salir, (self.config.ANCHO_PANTALLA - self._u(90), self._u(28)))

    def _cargar_fondo_menu(self):
        """Carga y escala el fondo del menú la primera vez que se dibuja."""
        if self._fondo_menu is None:
            try:
                fondo_menu = pygame.image.load(self.config.FONDO_MENU).convert()
                self._fondo_menu = pygame.transform.scale(
                    fondo_menu, (self.config.ANCHO_PANTALLA, self.config.ALTO_PANTALLA))
            except (pygame.error, OSError):
                self._fondo_menu = False
        return self._fondo_menu

    def dibujar_menu_principal(self, pantalla, mouse_pos=None, seleccion=None):
        """Dibuja el menú principal del juego.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            mouse_pos (tuple, optional): Posición del mouse para efectos hover.
            seleccion (int, optional): Índice de la opción seleccionada con teclado.
        """
        fondo_menu = self._cargar_fondo_menu()
        if fondo_menu:
            pantalla.blit(fondo_menu, (0, 0))
            overlay = pygame.Surface((self.config.ANCHO_PANTALLA, self.config.ALTO_PANTALLA), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            pantalla.blit(overlay, (0, 0))
        else:
            pantalla.fill(self.config.COLOR_FONDO)

        for i in range(0, self.config.ALTO_PANTALLA, 3):
            offset = math.sin(i * 0.015 + self.tiempo_animacion * 1.5) * 8
            alpha = int(25 + 15 * math.sin(i * 0.02 + self.tiempo_animacion * 2))
            color_linea = (35 + alpha // 8, 35 + alpha // 8, 55 + alpha // 4)
            pygame.draw.line(pantalla, color_linea, (int(offset), i), (self.config.ANCHO_PANTALLA + int(offset), i))

        self.dibujar_particulas_menu(pantalla)

        u = self.escala_ui
        titulo_y = self._u(100) + int(math.sin(self.tiempo_animacion * 1.5) * 8 * u)

        for desplazamiento in range(6, 0, -1):
            alpha = int(40 - desplazamiento * 6)
            sombra_surface = self.fuente_titulo.render("LA LLEVA", True, (0, 0, 0))
            pantalla.blit(sombra_surface, (self.config.ANCHO_PANTALLA // 2 - sombra_surface.get_width() // 2 + desplazamiento,
                                          titulo_y + desplazamiento))

        texto_titulo = self.fuente_titulo.render("LA LLEVA", True, self.config.COLOR_DORADO)
        brillo_titulo = pygame.Surface((texto_titulo.get_width(), texto_titulo.get_height() // 2), pygame.SRCALPHA)
        brillo_titulo.fill((255, 255, 255, 30))
        pantalla.blit(texto_titulo, (self.config.ANCHO_PANTALLA // 2 - texto_titulo.get_width() // 2, titulo_y))
        pantalla.blit(brillo_titulo, (self.config.ANCHO_PANTALLA // 2 - texto_titulo.get_width() // 2, titulo_y))

        texto_sub = self.fuente_subtitulo.render("Juego Tradicional Colombiano", True, self.config.COLOR_PLATA)
        pantalla.blit(texto_sub, (self.config.ANCHO_PANTALLA // 2 - texto_sub.get_width() // 2, self._u(195)))

        ancho_panel = self._u(380)
        alto_panel = self._u(385)
        x_panel = self.config.ANCHO_PANTALLA // 2 - ancho_panel // 2
        self.dibujar_panel(pantalla, x_panel, self._u(240), ancho_panel, alto_panel, 160)

        ancho_boton = self._u(280)
        alto_boton = self._u(ALTO_BOTON_MENU)
        x_boton = self.config.ANCHO_PANTALLA // 2 - ancho_boton // 2
        for i, (texto_boton, _accion, y) in enumerate(self.BOTONES_MENU):
            y_btn = self._u(y)
            hover = mouse_pos and self._dentro_boton(mouse_pos, x_boton, y_btn, ancho_boton, alto_boton)
            self.dibujar_boton(pantalla, texto_boton, x_boton, y_btn, ancho_boton, alto_boton, hover)
            if seleccion == i:
                pygame.draw.rect(pantalla, self.config.COLOR_DORADO,
                                 (x_boton, y_btn, ancho_boton, alto_boton), 2, border_radius=12)

        self.dibujar_panel(pantalla, self.config.ANCHO_PANTALLA // 2 - 195, 665, 390, 75, 130)
        controles = "Flechas + Enter: navegar   |   1, 2, 3: atajos"
        texto_ctrl = self.fuente_pequena.render(controles, True, self.config.COLOR_PLATA)
        pantalla.blit(texto_ctrl, (self.config.ANCHO_PANTALLA // 2 - texto_ctrl.get_width() // 2, 690))

    def dibujar_pantalla_nombres(self, pantalla, nombres, nombre_activo, mouse_pos=None, cantidad=None):
        """Dibuja la pantalla de ingreso de nombres.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            nombres (list): Lista de nombres de jugadores.
            nombre_activo (int): Índice del nombre que se está editando.
            mouse_pos (tuple, optional): Posición del mouse para efectos hover.
            cantidad (int, optional): Número de jugadores a mostrar. Por defecto 2.
        """
        total_campos = cantidad if cantidad is not None else len(nombres)
        pantalla.fill(self.config.COLOR_FONDO)
        self.dibujar_particulas_menu(pantalla)

        titulo = self.fuente_grande.render("Nombres de Jugadores", True, self.config.COLOR_DORADO)
        pantalla.blit(titulo, (self.config.ANCHO_PANTALLA // 2 - titulo.get_width() // 2, 80))

        self.dibujar_panel(pantalla, self.config.ANCHO_PANTALLA // 2 - 220, 160, 440, 340, 180)

        for i in range(total_campos):
            y_campo = 200 + i * 120
            color_label = self.config.color_jugador(i)
            label = self.fuente_boton.render(f"Jugador {i + 1}:", True, color_label)
            pantalla.blit(label, (self.config.ANCHO_PANTALLA // 2 - 180, y_campo))

            campo_x = self.config.ANCHO_PANTALLA // 2 - 180
            campo_y = y_campo + 35
            campo_ancho = 360
            campo_alto = 40

            if nombre_activo == i:
                pygame.draw.rect(pantalla, self.config.COLOR_BORDE,
                               (campo_x - 2, campo_y - 2, campo_ancho + 4, campo_alto + 4),
                               border_radius=8)
            pygame.draw.rect(pantalla, (40, 40, 60), (campo_x, campo_y, campo_ancho, campo_alto),
                           border_radius=6)

            texto_render = self.fuente_boton.render(nombres[i], True, (255, 255, 255))
            pantalla.blit(texto_render, (campo_x + 10, campo_y + campo_alto // 2 - texto_render.get_height() // 2))

            if nombre_activo == i and int(self.tiempo_animacion * 2) % 2 == 0:
                cursor_x = campo_x + 10 + texto_render.get_width() + 2
                pygame.draw.line(pantalla, (255, 255, 255), (cursor_x, campo_y + 8),
                               (cursor_x, campo_y + campo_alto - 8), 2)

        if total_campos > 1:
            texto_hint = self.fuente_pequena.render("TAB: cambiar campo  |  ENTER: jugar", True, self.config.COLOR_PLATA)
        else:
            texto_hint = self.fuente_pequena.render("ENTER: jugar", True, self.config.COLOR_PLATA)
        pantalla.blit(texto_hint, (self.config.ANCHO_PANTALLA // 2 - texto_hint.get_width() // 2, 470))

        hover = mouse_pos and self._dentro_boton(mouse_pos, self.config.ANCHO_PANTALLA // 2 - 140, 520, 280, 50)
        self.dibujar_boton(pantalla, "Jugar", self.config.ANCHO_PANTALLA // 2 - 140, 520, 280, 50, hover)

    def dibujar_opciones(self, pantalla, configuraciones, opcion_activa=None, mouse_pos=None):
        """Dibuja la pantalla de opciones configurables del juego.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            configuraciones: Objeto con claves/valores configurables.
            opcion_activa (int, optional): Índice de la fila seleccionada con teclado.
            mouse_pos (tuple, optional): Posición del mouse para efectos hover.
        """
        pantalla.fill(self.config.COLOR_FONDO)
        self.dibujar_particulas_menu(pantalla)

        titulo = self.fuente_grande.render("Opciones", True, self.config.COLOR_DORADO)
        pantalla.blit(titulo, (self.config.ANCHO_PANTALLA // 2 - titulo.get_width() // 2, 30))

        texto_hint = self.fuente_pequena.render(
            "Flechas: cambiar seleccion y valor   |   ESC: volver", True, self.config.COLOR_PLATA)
        pantalla.blit(texto_hint, (self.config.ANCHO_PANTALLA // 2 - texto_hint.get_width() // 2, 95))

        filas = [
            ("duracion_ronda", "Duracion"),
            ("dificultad_ia", "Dificultad"),
            ("volumen_musica", "Musica"),
            ("volumen_sfx", "Efectos"),
            ("pantalla_completa", "Pantalla completa"),
        ]

        cx = self.config.ANCHO_PANTALLA // 2
        self.dibujar_panel(pantalla, cx - 310, 130, 620, 430, 180)

        for i, (clave, etiqueta) in enumerate(filas):
            y = 155 + i * 80
            activa = (opcion_activa == i)
            sobre_fila = mouse_pos and 155 + i * 80 <= mouse_pos[1] <= 155 + i * 80 + 70 and abs(mouse_pos[0] - cx) < 270

            pygame.draw.rect(pantalla, (*self.config.COLOR_BOTON, 200),
                           ((cx - 260, y, 520, 70)), border_radius=10)
            if activa or sobre_fila:
                pygame.draw.rect(pantalla, self.config.COLOR_DORADO, (cx - 260, y, 520, 70), 2, border_radius=10)

            texto_label = self.fuente_boton.render(etiqueta, True, (255, 255, 255))
            pantalla.blit(texto_label, (cx - 240, y + 20))

            self.dibujar_boton(pantalla, "-", cx - 90, y + 15, 40, 40)
            valor = self._formatear_valor_opcion(clave, configuraciones.obtener(clave))
            texto_valor = self.fuente_boton.render(valor, True, self.config.COLOR_DORADO)
            pantalla.blit(texto_valor, (cx + 5 - texto_valor.get_width() // 2, y + 22))

            self.dibujar_boton(pantalla, "+", cx + 50, y + 15, 40, 40)

        hover_volver = mouse_pos and self._dentro_boton(mouse_pos, cx - 100, 610, 200, 50)
        self.dibujar_boton(pantalla, "Volver", cx - 100, 610, 200, 50, hover_volver)

    def _formatear_valor_opcion(self, clave, valor):
        """Formatea el valor de una opción para mostrarlo en pantalla.

        Args:
            clave (str): Nombre de la clave de configuración.
            valor: Valor actual.

        Returns:
            str: Texto legible del valor.
        """
        if clave == "duracion_ronda":
            return f"{valor}s"
        if clave == "dificultad_ia":
            return {"facil": "Facil", "normal": "Normal", "dificil": "Dificil"}.get(valor, str(valor))
        if clave in ("volumen_musica", "volumen_sfx"):
            return f"{int(round(valor * 100))}%"
        if clave == "pantalla_completa":
            return "SI" if valor else "NO"
        return str(valor)

    def dibujar_ayuda(self, pantalla, mouse_pos=None):
        """Dibuja la pantalla de ayuda con instrucciones del juego.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            mouse_pos (tuple, optional): Posición del mouse para efectos hover.
        """
        pantalla.fill(self.config.COLOR_FONDO)
        self.dibujar_particulas_menu(pantalla)

        titulo = self.fuente_grande.render("Como Jugar", True, self.config.COLOR_DORADO)
        pantalla.blit(titulo, (self.config.ANCHO_PANTALLA // 2 - titulo.get_width() // 2, 20))

        self.dibujar_panel(pantalla, 60, 80, 904, 580, 190)

        secciones = [
            ("Objetivo:", self.config.COLOR_DORADO, 100),
            ("Ser el ultimo en ser tocado cuando expira el tiempo.", (255, 255, 255), 130),
            ("", None, 152),
            ("Reglas:", self.config.COLOR_DORADO, 162),
            ("- La lleva inicial se elige al azar.", (255, 255, 255), 192),
            ("- Al tocar, el tocado pasa a ser 'La Lleva'.", (255, 255, 255), 217),
            ("- Gana quien menos tiempo sea 'La Lleva'.", (255, 255, 255), 242),
            ("", None, 264),
            ("Controles:", self.config.COLOR_DORADO, 274),
            ("J1: W (arriba), A (izq), S (abajo), D (der)", self.config.COLOR_JUGADOR_1, 304),
            ("J2: Flechas del teclado", self.config.COLOR_JUGADOR_2, 329),
            ("P o ESC: Pausa | F11: Pantalla | M: Musica", self.config.COLOR_PLATA, 354),
            ("Q: Menu (en pausa) | 1, 2 y 3: Modos y opciones", self.config.COLOR_PLATA, 379),
            ("", None, 406),
            ("Obstaculos y Power-ups:", self.config.COLOR_DORADO, 416),
            ("- Cajas (marrones): rebote al chocar.", (255, 255, 255), 446),
            ("- Zonas (azules): ralentizan el movimiento.", (255, 255, 255), 471),
            ("- Verde: velocidad | Azul: escudo | Cian: congelar", (255, 255, 255), 496),
            ("", None, 521),
            ("Ranking:", self.config.COLOR_DORADO, 531),
            ("- Tu tiempo se registra al finalizar la ronda.", (255, 255, 255), 561),
            ("- Consulta los mejores tiempos desde el menu.", (255, 255, 255), 586),
        ]

        for texto, color, y in secciones:
            if texto and color:
                render = self.fuente_pequena.render(texto, True, color)
                pantalla.blit(render, (100, y))

        x, y, ancho, alto = self._rect_ayuda_volver()
        hover = mouse_pos and self._dentro_boton(mouse_pos, x, y, ancho, alto)
        self.dibujar_boton(pantalla, "Volver", x, y, ancho, alto, hover)

    def _rect_ayuda_volver(self):
        """Devuelve el rectángulo del botón Volver de la pantalla de ayuda.

        Limita la posición vertical para que el botón quede visible en
        resoluciones reducidas (por ejemplo la versión web a 720p).

        Returns:
            tuple: (x, y, ancho, alto) en píxeles de la pantalla actual.
        """
        ancho, alto = 200, 50
        x = self.config.ANCHO_PANTALLA // 2 - ancho // 2
        y = min(680, self.config.ALTO_PANTALLA - alto - 10)
        return x, y, ancho, alto

    def dibujar_countdown(self, pantalla, numero):
        """Dibuja el countdown antes de iniciar la partida.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            numero (int): Número del countdown a mostrar.
        """
        pantalla.fill(self.config.COLOR_FONDO)
        self.dibujar_particulas_menu(pantalla)

        centro = (self.config.ANCHO_PANTALLA // 2, self.config.ALTO_PANTALLA // 2)
        radio = self._u(112)
        anillo = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
        pygame.draw.circle(anillo, (*self.config.COLOR_DORADO, 40), (radio, radio), radio, self._u(8))
        giro = (self.tiempo_animacion % 1.0) * math.pi * 2
        pygame.draw.arc(anillo, (*self.config.COLOR_DORADO, 235),
                        (self._u(4), self._u(4), radio * 2 - self._u(8), radio * 2 - self._u(8)),
                        giro, giro + 2.2, max(5, self._u(9)))
        pantalla.blit(anillo, (centro[0] - radio, centro[1] - radio))

        escala = 1.0 + abs(math.sin(self.tiempo_animacion * 4)) * 0.1
        texto = self.fuente_countdown.render(str(numero), True, self.config.COLOR_DORADO)
        texto_escalado = pygame.transform.rotozoom(texto, 0, escala)

        sombra = self.fuente_countdown.render(str(numero), True, (0, 0, 0))
        sombra_escalada = pygame.transform.rotozoom(sombra, 0, escala)
        pantalla.blit(sombra_escalada, (centro[0] - sombra_escalada.get_width() // 2 + 4,
                                        centro[1] - sombra_escalada.get_height() // 2 + 4))
        pantalla.blit(texto_escalado, (centro[0] - texto_escalado.get_width() // 2,
                                       centro[1] - texto_escalado.get_height() // 2))

        texto_preparado = self.fuente_subtitulo.render("Preparate...", True, self.config.COLOR_PLATA)
        pantalla.blit(texto_preparado, (centro[0] - texto_preparado.get_width() // 2,
                                        centro[1] + self._u(80)))

    def dibujar_pausa(self, pantalla, mouse_pos=None):
        """Dibuja la pantalla de pausa sobre la partida.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            mouse_pos (tuple, optional): Posición del mouse para efectos hover.
        """
        overlay = pygame.Surface((self.config.ANCHO_PANTALLA, self.config.ALTO_PANTALLA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        pantalla.blit(overlay, (0, 0))

        self.dibujar_panel(pantalla, self.config.ANCHO_PANTALLA // 2 - 220, 300, 440, 260, 220)

        texto_titulo = self.fuente_grande.render("PAUSA", True, self.config.COLOR_DORADO)
        pantalla.blit(texto_titulo, (self.config.ANCHO_PANTALLA // 2 - texto_titulo.get_width() // 2, 330))

        texto_pista = self.fuente_subtitulo.render("Pulsa P o ESC para continuar", True, (255, 255, 255))
        pantalla.blit(texto_pista, (self.config.ANCHO_PANTALLA // 2 - texto_pista.get_width() // 2, 410))

        texto_musica = self.fuente_pequena.render("M: Musica  |  F11: Pantalla completa", True, self.config.COLOR_PLATA)
        pantalla.blit(texto_musica, (self.config.ANCHO_PANTALLA // 2 - texto_musica.get_width() // 2, 460))

        texto_salir = self.fuente_pequena.render("ESC: continuar |  Q: volver al menu", True, self.config.COLOR_PLATA)
        pantalla.blit(texto_salir, (self.config.ANCHO_PANTALLA // 2 - texto_salir.get_width() // 2, 500))

    def dibujar_fin_ronda(self, pantalla, ganador, puntajes, mouse_pos=None, jugadores=None,
                          mostrar_botones=True,
                          texto_hint="ENTER/R: Revancha   |   ESC: Menu"):
        """Dibuja la pantalla de fin de ronda con resultados.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            ganador (int): ID del jugador ganador.
            puntajes (dict): Diccionario con tiempos de cada jugador.
            mouse_pos (tuple, optional): Posición del mouse para efectos hover.
            jugadores (list, optional): Lista de jugadores.
            mostrar_botones (bool): True dibuja los botones de revancha/menú
                (False en la versión en línea, donde la ronda sigue desde el
                servidor).
            texto_hint (str): Texto de atajos que se muestra al pie.
        """
        overlay = pygame.Surface((self.config.ANCHO_PANTALLA, self.config.ALTO_PANTALLA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        pantalla.blit(overlay, (0, 0))

        panel_ancho = self._u(520)
        panel_alto = self._u(450)
        self.dibujar_panel(pantalla, self.config.ANCHO_PANTALLA // 2 - panel_ancho // 2,
                           self._u(130), panel_ancho, panel_alto, 230)

        texto_titulo = self.fuente_grande.render("Fin de Ronda", True, self.config.COLOR_DORADO)
        pantalla.blit(texto_titulo, (self.config.ANCHO_PANTALLA // 2 - texto_titulo.get_width() // 2, self._u(160)))

        if ganador is not None and jugadores:
            ganador_nombre = next((j.nombre for j in jugadores if j.id == ganador), f"Jugador {ganador + 1}")
            texto_ganador = self.fuente_grande.render(f"{ganador_nombre} Gana!", True, (255, 255, 255))
        else:
            texto_ganador = self.fuente_grande.render("Empate!", True, (255, 255, 255))
        pantalla.blit(texto_ganador, (self.config.ANCHO_PANTALLA // 2 - texto_ganador.get_width() // 2, self._u(250)))

        tabla_ancho = self._u(380)
        self.dibujar_panel(pantalla, self.config.ANCHO_PANTALLA // 2 - tabla_ancho // 2,
                           self._u(320), tabla_ancho, self._u(130), 160)
        texto_titulo_tabla = self.fuente_boton.render("Tabla de Tiempos", True, self.config.COLOR_PLATA)
        pantalla.blit(texto_titulo_tabla, (self.config.ANCHO_PANTALLA // 2 - texto_titulo_tabla.get_width() // 2, self._u(330)))

        colores_medalla = {1: (255, 215, 0), 2: (192, 192, 192), 3: (205, 127, 50)}
        y = self._u(370)
        for posicion, (id_j, tiempo) in enumerate(sorted(puntajes.items(), key=lambda x: x[1]), start=1):
            nombre = next((j.nombre for j in jugadores if j.id == id_j), f"J{id_j + 1}") if jugadores else f"J{id_j + 1}"
            color = self.config.COLOR_DORADO if id_j == ganador else (255, 255, 255)
            texto = self.fuente_boton.render(f"{nombre}: {int(tiempo)}s", True, color)

            if posicion <= 3 and colores_medalla.get(posicion):
                radio_medalla = self._u(11)
                mx = self.config.ANCHO_PANTALLA // 2 - texto.get_width() // 2 - radio_medalla - self._u(12)
                my = y + texto.get_height() // 2
                pygame.draw.circle(pantalla, colores_medalla[posicion], (mx, my), radio_medalla)
                pygame.draw.circle(pantalla, (255, 255, 255), (mx, my), radio_medalla, 1)
                texto_pos = self.fuente_pequena.render(str(posicion), True, (20, 20, 30))
                pantalla.blit(texto_pos, (mx - texto_pos.get_width() // 2, my - texto_pos.get_height() // 2))

            pantalla.blit(texto, (self.config.ANCHO_PANTALLA // 2 - texto.get_width() // 2, y))
            y += self._u(35)

        btn_ancho = self._u(190)
        btn_alto = self._u(50)
        y_btn = self._u(510)
        x_revancha = self.config.ANCHO_PANTALLA // 2 - btn_ancho - self._u(20)
        x_menu = self.config.ANCHO_PANTALLA // 2 + self._u(20)
        if mostrar_botones:
            hover_revancha = mouse_pos and self._dentro_boton(mouse_pos, x_revancha, y_btn, btn_ancho, btn_alto)
            hover_menu = mouse_pos and self._dentro_boton(mouse_pos, x_menu, y_btn, btn_ancho, btn_alto)
            self.dibujar_boton(pantalla, "Revancha", x_revancha, y_btn, btn_ancho, btn_alto, hover_revancha)
            self.dibujar_boton(pantalla, "Menu", x_menu, y_btn, btn_ancho, btn_alto, hover_menu)

        texto_atajos = self.fuente_pequena.render(texto_hint, True, self.config.COLOR_PLATA)
        pantalla.blit(texto_atajos, (self.config.ANCHO_PANTALLA // 2 - texto_atajos.get_width() // 2, self._u(600)))

    def dibujar_ranking(self, pantalla, entradas, mouse_pos=None):
        """Dibuja la pantalla de ranking con las mejores partidas.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            entradas (list): Lista de entradas del ranking ordenadas por tiempo.
            mouse_pos (tuple, optional): Posición del mouse para efectos hover.
        """
        pantalla.fill(self.config.COLOR_FONDO)
        self.dibujar_particulas_menu(pantalla)

        titulo = self.fuente_grande.render("Ranking", True, self.config.COLOR_DORADO)
        pantalla.blit(titulo, (self.config.ANCHO_PANTALLA // 2 - titulo.get_width() // 2, 40))

        subtitulo = self.fuente_subtitulo.render("Mejores Tiempos", True, self.config.COLOR_PLATA)
        pantalla.blit(subtitulo, (self.config.ANCHO_PANTALLA // 2 - subtitulo.get_width() // 2, 100))

        panel_y = 150
        panel_alto = 400
        self.dibujar_panel(pantalla, self.config.ANCHO_PANTALLA // 2 - 280, panel_y, 560, panel_alto, 180)

        if not entradas:
            texto_vacio = self.fuente_boton.render("No hay partidas registradas", True, self.config.COLOR_PLATA)
            pantalla.blit(texto_vacio, (self.config.ANCHO_PANTALLA // 2 - texto_vacio.get_width() // 2, panel_y + 180))
        else:
            encabezado_y = panel_y + 15
            col_pos_x = self.config.ANCHO_PANTALLA // 2 - 250
            col_nom_x = self.config.ANCHO_PANTALLA // 2 - 180
            col_tiempo_x = self.config.ANCHO_PANTALLA // 2 + 120

            texto_pos_h = self.fuente_pequena.render("#", True, self.config.COLOR_DORADO)
            texto_nom_h = self.fuente_pequena.render("Jugador", True, self.config.COLOR_DORADO)
            texto_tiem_h = self.fuente_pequena.render("Tiempo", True, self.config.COLOR_DORADO)
            pantalla.blit(texto_pos_h, (col_pos_x, encabezado_y))
            pantalla.blit(texto_nom_h, (col_nom_x, encabezado_y))
            pantalla.blit(texto_tiem_h, (col_tiempo_x, encabezado_y))

            pygame.draw.line(pantalla, self.config.COLOR_BORDE,
                           (col_pos_x, encabezado_y + 22),
                           (col_tiempo_x + 100, encabezado_y + 22), 1)

            for i, entrada in enumerate(entradas):
                y = encabezado_y + 35 + i * 34
                if y > panel_y + panel_alto - 40:
                    break

                if i == 0:
                    color_pos = self.config.COLOR_DORADO
                elif i == 1:
                    color_pos = (192, 192, 192)
                elif i == 2:
                    color_pos = (205, 127, 50)
                else:
                    color_pos = (255, 255, 255)

                texto_pos = self.fuente_boton.render(f"{i + 1}", True, color_pos)
                texto_nom = self.fuente_boton.render(entrada["ganador"], True, (255, 255, 255))
                texto_tiem = self.fuente_boton.render(f'{entrada["tiempo"]:.1f}s', True, color_pos)

                pantalla.blit(texto_pos, (col_pos_x + 10, y))
                pantalla.blit(texto_nom, (col_nom_x, y))
                pantalla.blit(texto_tiem, (col_tiempo_x + 20, y))

        hover_volver = mouse_pos and self._dentro_boton(mouse_pos, self.config.ANCHO_PANTALLA // 2 - 100, 580, 200, 50)
        self.dibujar_boton(pantalla, "Volver", self.config.ANCHO_PANTALLA // 2 - 100, 580, 200, 50, hover_volver)

    def dibujar_sala(self, pantalla, snapshot, mi_id=None, listo=False, mouse_pos=None):
        """Dibuja la sala de espera del modo en línea.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            snapshot (dict, optional): Último snapshot de la sala, o None.
            mi_id (int, optional): Id del jugador local.
            listo (bool): True si el jugador local está marcado como listo.
            mouse_pos (tuple, optional): Posición del mouse para efectos hover.
        """
        pantalla.fill(self.config.COLOR_FONDO)
        self.dibujar_particulas_menu(pantalla)

        titulo = self.fuente_grande.render("Sala en Linea", True, self.config.COLOR_DORADO)
        pantalla.blit(titulo, (self.config.ANCHO_PANTALLA // 2 - titulo.get_width() // 2, 30))

        if snapshot is None:
            espera = self.fuente_subtitulo.render("Conectando con la sala...", True, (255, 255, 255))
            pantalla.blit(espera, (self.config.ANCHO_PANTALLA // 2 - espera.get_width() // 2,
                                   self.config.ALTO_PANTALLA // 2))
            self.dibujar_panel(pantalla, self.config.ANCHO_PANTALLA // 2 - 280, 150, 560, 360, 180)
            return

        subtitulo = self.fuente_pequena.render(
            "Abre esta misma pagina en cada dispositivo para unirte", True, self.config.COLOR_PLATA)
        pantalla.blit(subtitulo, (self.config.ANCHO_PANTALLA // 2 - subtitulo.get_width() // 2, 90))

        cx = self.config.ANCHO_PANTALLA // 2
        self.dibujar_panel(pantalla, cx - 280, 140, 560, 350, 190)

        conectados = snapshot.get("jugadores_online", 0)
        maximo = snapshot.get("max_jugadores", 0)
        cabecera = self.fuente_boton.render(
            f"Jugadores conectados ({conectados}/{maximo})", True, self.config.COLOR_PLATA)
        pantalla.blit(cabecera, (cx - 245, 160))

        listos = snapshot.get("listos", {})
        victorias = snapshot.get("victorias", {})

        for jugador in snapshot.get("jugadores", []):
            id_j = jugador.get("id")
            nombre = jugador.get("nombre", f"J{id_j + 1}")
            color = self.config.color_jugador(id_j)
            y_fila = 210 + id_j * 55
            if y_fila > 400:
                break

            pygame.draw.circle(pantalla, color, (cx - 245, y_fila + 12), 11)
            pygame.draw.circle(pantalla, (255, 255, 255), (cx - 245, y_fila + 12), 11, 1)

            texto_nombre = self.fuente_boton.render(nombre, True, (255, 255, 255))
            pantalla.blit(texto_nombre, (cx - 215, y_fila))

            etiqueta_yo = " (tu)" if id_j == mi_id else ""
            if etiqueta_yo:
                texto_yo = self.fuente_pequena.render(etiqueta_yo, True, self.config.COLOR_DORADO)
                pantalla.blit(texto_yo, (cx - 215 + texto_nombre.get_width() + 4, y_fila + 6))

            esta_listo = bool(listos.get(str(id_j), jugador.get("listo", False)))
            color_estado = self.config.COLOR_LIBRE if esta_listo else self.config.COLOR_PLATA
            texto_estado = self.fuente_pequena.render(
                "Listo" if esta_listo else "Esperando", True, color_estado)
            pantalla.blit(texto_estado, (cx + 20, y_fila))

            texto_victorias = self.fuente_pequena.render(
                f"Victorias: {victorias.get(str(id_j), 0)}", True, self.config.COLOR_DORADO)
            pantalla.blit(texto_victorias, (cx + 100, y_fila))

        todos = snapshot.get("jugadores", [])
        if len(todos) >= 2 and listos and all(listos.get(str(j.get("id")), False) for j in todos):
            estado_sala = "¡Todos listos!"
        elif len(todos) < 2:
            estado_sala = "Esperando a otro jugador..."
        else:
            estado_sala = "Aun faltan jugadores por marcar 'Listo'"
        texto_estado_sala = self.fuente_pequena.render(estado_sala, True, self.config.COLOR_LIBRE)
        pantalla.blit(texto_estado_sala, (cx - texto_estado_sala.get_width() // 2, 440))

        x_listo, x_salir, y_btn, btn_ancho, btn_alto = rects_sala(
            self.config.ANCHO_PANTALLA)
        hover_listo = mouse_pos and self._dentro_boton(mouse_pos, x_listo, y_btn, btn_ancho, btn_alto)
        hover_salir = mouse_pos and self._dentro_boton(mouse_pos, x_salir, y_btn, btn_ancho, btn_alto)

        self.dibujar_boton(pantalla, "Listo", x_listo, y_btn, btn_ancho, btn_alto, hover_listo)
        self.dibujar_boton(pantalla, "Salir", x_salir, y_btn, btn_ancho, btn_alto, hover_salir)
        if listo:
            pygame.draw.rect(pantalla, self.config.COLOR_DORADO,
                             (x_listo, y_btn, btn_ancho, btn_alto), 2, border_radius=12)

        texto_atajos = self.fuente_pequena.render(
            "R/ESPACIO: Listo   |   ESC: Salir", True, self.config.COLOR_PLATA)
        pantalla.blit(texto_atajos, (self.config.ANCHO_PANTALLA // 2 - texto_atajos.get_width() // 2, 625))


