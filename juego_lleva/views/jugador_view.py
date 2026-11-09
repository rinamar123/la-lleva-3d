"""Vista responsable del renderizado de jugadores en pantalla.

Dibuja personajes procedimentales con identidad propia por jugador (peinado,
tono de piel y accesorio), anatomía con codos y rodillas, postura animada
(bobbing, inclinación, squash al tropezar, contorno) y estados claros:
escudo giratorio, congelamiento, estelas de velocidad y expresión de "la lleva".
"""

import math

import pygame
from juego_lleva.fuentes import fuente
from juego_lleva.core.config import Config


class JugadorView:
    """Clase que maneja la presentación visual de un jugador."""

    PIEL = (238, 203, 168)
    CONTORNO = (16, 14, 22)

    ESTILOS = {
        0: {
            "pelo": "flequillo",
            "color_pelo": (70, 50, 34),
            "piel": PIEL,
            "accesorio": "gorra",
            "color_accesorio": (210, 45, 45),
        },
        1: {
            "pelo": "largo",
            "color_pelo": (166, 78, 28),
            "piel": (214, 152, 104),
            "accesorio": "vincha",
            "color_accesorio": (120, 190, 255),
        },
        2: {
            "pelo": "mohicano",
            "color_pelo": (22, 22, 30),
            "piel": (222, 184, 146),
            "accesorio": "banda",
            "color_accesorio": (90, 210, 120),
        },
        3: {
            "pelo": "largo",
            "color_pelo": (230, 190, 60),
            "piel": (140, 92, 58),
            "accesorio": "vincha",
            "color_accesorio": (230, 120, 220),
        },
    }

    def __init__(self):
        """Inicializa la vista del jugador con configuración por defecto."""
        self.config = Config()
        self.tiempo_animacion = 0
        self.fase_caminar = 0
        self.s = self.config.TAMAÑO_JUGADOR / 95.0
        self._fuente_nombre = fuente(24)

    def _color_oscuro(self, color):
        """Devuelve una versión oscurecida de un color.

        Args:
            color (tuple): Color RGB.

        Returns:
            tuple: Color oscurecido.
        """
        return (int(color[0] * 0.55), int(color[1] * 0.55), int(color[2] * 0.55))

    def _tinte_congelado(self, color):
        """Tiñe un color hacia un azul helado.

        Args:
            color (tuple): Color RGB original.

        Returns:
            tuple: Color congelado.
        """
        return (int(min(255, color[0] * 0.72 + 30)),
                int(min(255, color[1] * 0.72 + 75)),
                int(min(255, color[2] * 0.72 + 120)))

    def _estilo_para(self, jugador):
        """Devuelve el estilo visual correspondiente a un jugador.

        Args:
            jugador: Jugador objetivo.

        Returns:
            dict: Estilo (peinado, color de pelo, piel y accesorio).
        """
        if getattr(jugador, "es_ia", False):
            return self.ESTILOS[2]
        return self.ESTILOS[jugador.id % 4]

    def _esta_congelado(self, jugador):
        """Indica si el jugador está bajo el efecto de congelamiento.

        Args:
            jugador: Jugador objetivo.

        Returns:
            bool: True si está congelado.
        """
        return getattr(jugador, "congelado", 0) > 0

    def renderizar(self, pantalla, jugador, tiempo_delta=0):
        """Renderiza el jugador en la pantalla.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            jugador: Objeto jugador a renderizar.
            tiempo_delta (float): Tiempo transcurrido desde la última actualización.
        """
        self.tiempo_animacion += tiempo_delta
        self.fase_caminar += jugador.velocidad_abs * tiempo_delta * 0.022

        cx = jugador.x + self.config.TAMAÑO_JUGADOR // 2
        pie_y = jugador.y + self.config.TAMAÑO_JUGADOR

        self._dibujar_aura_lleva(pantalla, jugador, cx, pie_y)
        self._dibujar_sombra(pantalla, cx, pie_y, jugador)

        sprite = self._componer_personaje(jugador)
        if jugador.direccion_cara < 0:
            sprite = pygame.transform.flip(sprite, True, False)

        agachado = 0
        if jugador.tropezando > 0:
            agachado = int(10 * self.s)
        temblor = int(math.sin(self.tiempo_animacion * 38) * 1.5) if self._esta_congelado(jugador) else 0
        pantalla.blit(sprite, (int(cx - sprite.get_width() // 2 + temblor),
                               int(pie_y - sprite.get_height() + agachado)))

        if jugador.escudo:
            self._dibujar_escudo(pantalla, jugador, cx, pie_y)

        self._dibujar_nombre(pantalla, jugador)

    def _trazar_extremidad(self, superficie, contorno, color, p1, p2, p3, grosor):
        """Traza un miembro articulado (dos segmentos) con contorno y articulación.

        Args:
            superficie: Superficie de pygame donde dibujar.
            contorno: Color del contorno.
            color: Color del miembro.
            p1: Origen (torso).
            p2: Articulación (rodilla/codo).
            p3: Extremo (pie/mano).
            grosor: Grosor de trazo del miembro.
        """
        ancho_contorno = grosor + int(4 * self.s)
        for inicio, fin in ((p1, p2), (p2, p3)):
            pygame.draw.line(superficie, contorno, inicio, fin, ancho_contorno)
        for inicio, fin in ((p1, p2), (p2, p3)):
            pygame.draw.line(superficie, color, inicio, fin, grosor)
        pygame.draw.circle(superficie, contorno, (int(p2[0]), int(p2[1])), grosor // 2 + 1)
        pygame.draw.circle(superficie, color, (int(p2[0]), int(p2[1])), grosor // 2)
        pygame.draw.circle(superficie, self._color_oscuro(color), (int(p3[0]), int(p3[1])), max(2, grosor // 2 + 2))

    def _componer_personaje(self, jugador):
        """Compone el muñeco procedural en una superficie independiente.

        Args:
            jugador: Objeto jugador del que se toman estado y colores.

        Returns:
            pygame.Surface: Muñeco dibujado mirando a la derecha.
        """
        s = self.s
        ancho = int(150 * s)
        alto = int(160 * s)
        superficie = pygame.Surface((ancho, alto), pygame.SRCALPHA)

        estilo = self._estilo_para(jugador)
        congelado = self._esta_congelado(jugador)

        color = self.config.color_jugador(jugador.id)
        if congelado:
            color = self._tinte_congelado(color)
        if jugador.es_lleva:
            color = (min(color[0] + 45, 255), max(color[1] - 25, 0), max(color[2] - 25, 0))
        oscuro = self._color_oscuro(color)
        contorno = self.CONTORNO

        fx = ancho // 2
        velocidad = jugador.velocidad_abs

        bobbing = abs(math.sin(self.fase_caminar)) * 4 * s if velocidad > 40 * s else 0
        aplanado = int(3 * s) if jugador.tropezando > 0 else 0

        hip_y = alto - 48 * s - bobbing - aplanado
        hombro_y = hip_y - 34 * s - aplanado
        inclina = int(6 * s) if velocidad > 120 * s else 0

        paso = math.sin(self.fase_caminar)
        paso2 = math.sin(self.fase_caminar + math.pi)
        alto_pie = alto - 8 * s

        pie_izq = (fx + paso * 13 * s, alto_pie - max(0.0, math.cos(self.fase_caminar)) * 5 * s)
        pie_der = (fx + paso2 * 13 * s, alto_pie - max(0.0, math.cos(self.fase_caminar + math.pi)) * 5 * s)

        grosor = max(4, int(9 * s))
        for pie, fase in ((pie_izq, paso), (pie_der, paso2)):
            rodilla = (fx + fase * 8 * s, (hip_y + pie[1]) / 2)
            self._trazar_extremidad(superficie, contorno, oscuro,
                                    (fx, hip_y), rodilla, pie, grosor)

        torso = pygame.Rect(int(fx - 21 * s), int(hombro_y - inclina),
                            int(42 * s), int(hip_y - hombro_y + 5 * s))
        pygame.draw.rect(superficie, contorno, torso.inflate(int(4 * s), int(4 * s)), border_radius=int(13 * s))
        pygame.draw.rect(superficie, oscuro, torso.move(0, int(2 * s)), border_radius=int(13 * s))
        pygame.draw.rect(superficie, color, torso, border_radius=int(13 * s))
        cintura = pygame.Rect(int(fx - 15 * s), int(hip_y - 6 * s), int(30 * s), int(10 * s))
        pygame.draw.rect(superficie, oscuro, cintura, border_radius=int(5 * s))
        brillo = pygame.Rect(torso.x + 4, torso.y + 4, int(torso.w * 0.45), int(torso.h * 0.35))
        pygame.draw.rect(superficie, (255, 255, 255, 26), brillo, border_radius=int(8 * s))

        piel = estilo["piel"]
        if congelado:
            piel = self._tinte_congelado(piel)

        hombro_y_torso = hombro_y - inclina
        hombro_izq = (fx - int(16 * s), hombro_y_torso + int(2 * s))
        hombro_der = (fx + int(16 * s), hombro_y_torso + int(2 * s))
        mano_izq = (hombro_izq[0] - paso2 * 10 * s, hombro_y_torso + int(32 * s))
        mano_der = (hombro_der[0] + paso * 10 * s, hombro_y_torso + int(32 * s))
        grosor_brazo = max(4, int(8 * s))
        for hombro_b, mano in ((hombro_izq, mano_izq), (hombro_der, mano_der)):
            lado_codo = -1 if hombro_b[0] < fx else 1
            codo = ((hombro_b[0] + mano[0]) // 2 + lado_codo * int(7 * s),
                    (hombro_b[1] + mano[1]) // 2 + int(8 * s))
            self._trazar_extremidad(superficie, contorno, piel, hombro_b, codo, mano, grosor_brazo)

        cabeza_y = hombro_y - inclina - int(30 * s)
        radio = int(21 * s)

        # Cuello: une la cabeza con el torso sin dejar hueco.
        cuello_alto = int(hombro_y_torso - (cabeza_y + radio) + 2 * s)
        pygame.draw.rect(superficie, contorno,
                         (int(fx - 7 * s), int(cabeza_y + radio - 2 * s),
                          int(14 * s), cuello_alto))
        pygame.draw.rect(superficie, piel,
                         (int(fx - 5.5 * s), int(cabeza_y + radio - 2 * s),
                          int(11 * s), cuello_alto))

        pygame.draw.circle(superficie, contorno, (fx, cabeza_y), radio + int(2 * s))
        pygame.draw.circle(superficie, piel, (fx, cabeza_y), radio)
        self._dibujar_pelo(superficie, estilo, fx, cabeza_y, radio, s, ancho)
        self._dibujar_cara(superficie, jugador, fx, cabeza_y, s, congelado)
        self._dibujar_accesorio(superficie, estilo, fx, cabeza_y, radio, s)

        if jugador.es_lleva:
            self._dibujar_panuelo(superficie, fx, hombro_y, s)

        if congelado:
            for i in range(4):
                px = fx + ((i * 37) % int(58 * s)) - int(29 * s)
                py = hip_y - ((i * 29) % int(90 * s)) - int(6 * s)
                pygame.draw.circle(superficie, (225, 245, 255, 170),
                                   (px, py), max(1, int(1.5 * s)))

        return superficie

    def _dibujar_pelo(self, superficie, estilo, fx, cabeza_y, radio, s, ancho):
        """Dibuja el peinado según el estilo del jugador.

        Args:
            superficie: Superficie de pygame donde dibujar.
            estilo: Estilo del jugador.
            fx (int): Centro horizontal de la cabeza.
            cabeza_y (float): Centro vertical de la cabeza.
            radio (int): Radio de la cabeza.
            s (float): Escala base.
            ancho (int): Ancho de la superficie.
        """
        color = estilo["color_pelo"]
        tipo = estilo["pelo"]

        if tipo == "mohicano":
            pygame.draw.rect(superficie, color,
                             (int(fx - 3 * s), int(cabeza_y - radio - 7 * s),
                              int(6 * s), int(radio + 16 * s)),
                             border_radius=int(3 * s))
            return

        rect_pelo = pygame.Rect(0, 0, ancho, int(cabeza_y - 5 * s))
        superficie.set_clip(rect_pelo)
        pygame.draw.circle(superficie, color, (fx, int(cabeza_y + 6 * s)), radio + int(7 * s))
        superficie.set_clip(None)

        if tipo == "largo":
            for lado in (-1, 1):
                x = int(fx + lado * radio * 0.9)
                pygame.draw.rect(superficie, color,
                                 (x - int(2.5 * s), int(cabeza_y - 4 * s),
                                  int(5 * s), int(20 * s)),
                                 border_radius=int(2 * s))

    def _dibujar_cara(self, superficie, jugador, fx, cabeza_y, s, congelado):
        """Dibuja ojos, boca y expresión según el estado del jugador.

        Args:
            superficie: Superficie de pygame donde dibujar.
            jugador: Jugador objetivo.
            fx (int): Centro horizontal de la cabeza.
            cabeza_y (float): Centro vertical de la cabeza.
            s (float): Escala base.
            congelado (bool): True si el jugador está congelado.
        """
        ojo_dx = int(7 * s)
        ojo_y = int(cabeza_y + 2 * s)

        if jugador.tropezando > 0:
            for lado in (-1, 1):
                ox = fx + lado * ojo_dx
                pygame.draw.circle(superficie, (255, 255, 255), (ox, ojo_y), int(4.5 * s))
                pygame.draw.line(superficie, (30, 25, 20),
                                 (ox - int(3 * s), ojo_y - int(3 * s)),
                                 (ox + int(3 * s), ojo_y + int(3 * s)), 2)
                pygame.draw.line(superficie, (30, 25, 20),
                                 (ox - int(3 * s), ojo_y + int(3 * s)),
                                 (ox + int(3 * s), ojo_y - int(3 * s)), 2)
        else:
            for lado in (-1, 1):
                ox = fx + lado * ojo_dx
                pygame.draw.circle(superficie, (255, 255, 255), (ox, ojo_y), int(4.5 * s))
                pygame.draw.circle(superficie, (30, 25, 20),
                                   (ox + int(1.5 * s), ojo_y), int(2.2 * s))
            if jugador.es_lleva:
                for lado in (-1, 1):
                    x1 = fx + lado * int(2 * s)
                    x2 = fx + lado * int(11 * s)
                    pygame.draw.line(superficie, (50, 30, 25),
                                     (x1, ojo_y - int(5 * s)),
                                     (x2, ojo_y - int(2 * s)), max(2, int(2 * s)))

        boca = pygame.Rect(int(fx - 2 * s), int(cabeza_y + 8 * s), int(12 * s), int(6 * s))
        if congelado:
            pygame.draw.circle(superficie, (95, 125, 185),
                               (fx, int(cabeza_y + 10 * s)), int(2.5 * s))
        elif jugador.tropezando > 0:
            pygame.draw.ellipse(superficie, (70, 45, 40), boca)
        elif jugador.es_lleva:
            pygame.draw.arc(superficie, (70, 40, 30), boca, math.pi + 0.4, 2 * math.pi - 0.4, 2)
        else:
            pygame.draw.arc(superficie, (80, 50, 40), boca, 0.2, math.pi - 0.2, 2)

        if jugador.tropezando > 0:
            for i in range(3):
                pygame.draw.circle(superficie, (255, 255, 60, 150),
                                   (fx - int(14 * s), int(cabeza_y - 22 * s - i * 6 * s)),
                                   max(2, int(2 * s)))

    def _dibujar_accesorio(self, superficie, estilo, fx, cabeza_y, radio, s):
        """Dibuja el accesorio de cabeza (gorra, vincha o banda).

        Args:
            superficie: Superficie de pygame donde dibujar.
            estilo: Estilo del jugador.
            fx (int): Centro horizontal de la cabeza.
            cabeza_y (float): Centro vertical de la cabeza.
            radio (int): Radio de la cabeza.
            s (float): Escala base.
        """
        color = estilo["color_accesorio"]
        tipo = estilo["accesorio"]
        arco = pygame.Rect(fx - radio, cabeza_y - radio, radio * 2, radio * 2)
        if tipo == "gorra":
            pygame.draw.arc(superficie, color, arco, 0.15, math.pi - 0.15, int(6 * s))
            pygame.draw.polygon(superficie, color, [
                (fx + int(8 * s), int(cabeza_y - radio * 0.6)),
                (fx + int(26 * s), int(cabeza_y - radio * 0.35)),
                (fx + int(8 * s), int(cabeza_y - radio * 0.05))])
        elif tipo == "vincha":
            pygame.draw.arc(superficie, color, arco, 0.15, math.pi - 0.15, int(4 * s))
        elif tipo == "banda":
            pygame.draw.arc(superficie, color, arco, 0.9, math.pi - 0.15, int(5 * s))

    def _dibujar_panuelo(self, superficie, fx, hombro_y, s):
        """Dibuja el pañuelo rojo característico de "la lleva".

        Args:
            superficie: Superficie de pygame donde dibujar.
            fx (int): Centro horizontal del torso.
            hombro_y (float): Posición vertical de los hombros.
            s (float): Escala base.
        """
        cuello_y = hombro_y - int(4 * s)
        for i, lado in enumerate((-1, 1)):
            ondeo = math.sin(self.tiempo_animacion * 9 + i) * 6 * s
            pygame.draw.polygon(superficie, (232, 40, 40), [
                (fx + lado * 10 * s, cuello_y),
                (fx + lado * (34 * s) + ondeo, cuello_y - 8 * s),
                (fx + lado * (46 * s), cuello_y + 4 * s),
                (fx + lado * (30 * s), cuello_y - 6 * s)])
        pygame.draw.polygon(superficie, (255, 255, 255), [
            (fx - 4 * s, cuello_y), (fx + 4 * s, cuello_y),
            (fx + 4 * s, cuello_y + 16 * s), (fx - 4 * s, cuello_y + 16 * s)])

    def _dibujar_aura_lleva(self, pantalla, jugador, cx, pie_y):
        """Dibuja el aura roja pulsante alrededor del jugador que lleva.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            jugador: Jugador objetivo.
            cx (int): Centro horizontal del jugador.
            pie_y (int): Posición vertical de los pies.
        """
        if not jugador.es_lleva:
            return
        centro = (cx, pie_y - int(self.config.TAMAÑO_JUGADOR * 0.55))
        for i in range(3):
            radio = int((22 + i * 9) * self.s + math.sin(self.tiempo_animacion * 6 + i) * (4 + i * 2) * self.s)
            alpha = max(12, int(45 - i * 13))
            capa = pygame.Surface((radio * 2 + 8, radio * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(capa, (255, 45, 45, alpha), (radio + 4, radio + 4), radio)
            pantalla.blit(capa, (centro[0] - radio - 4, centro[1] - radio - 4))

    def _dibujar_sombra(self, pantalla, cx, pie_y, jugador):
        """Dibuja la sombra elíptica bajo los pies del jugador.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            cx (int): Centro horizontal del jugador.
            pie_y (int): Posición vertical de los pies.
            jugador: Jugador al que pertenece la sombra.
        """
        encogido = 0.82 if jugador.tropezando > 0 else 1.0
        ancho_s = int(54 * self.s * encogido)
        sombra = pygame.Surface((ancho_s + 10, 26), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (0, 0, 0, 70), (5, 4, ancho_s, 18))
        pantalla.blit(sombra, (cx - sombra.get_width() // 2, pie_y - 6))

    def _dibujar_escudo(self, pantalla, jugador, cx, pie_y):
        """Dibuja el anillo de escudo giratorio alrededor del jugador.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            jugador: Jugador con escudo.
            cx (int): Centro horizontal del jugador.
            pie_y (int): Posición vertical de los pies.
        """
        radio = int(46 * self.s)
        centro = (cx, pie_y - int(self.config.TAMAÑO_JUGADOR * 0.55))
        capa = pygame.Surface((radio * 2 + 12, radio * 2 + 12), pygame.SRCALPHA)
        pygame.draw.circle(capa, (110, 155, 255, 75), (radio + 6, radio + 6), radio, 5)
        pantalla.blit(capa, (centro[0] - radio - 6, centro[1] - radio - 6))
        t = self.tiempo_animacion
        for i in range(2):
            ang = t * 2.6 + i * math.pi
            arco = pygame.Surface((radio * 2 + 20, radio * 2 + 20), pygame.SRCALPHA)
            pygame.draw.arc(arco, (190, 225, 255, 210),
                            (10, 10, radio * 2, radio * 2),
                            ang, ang + 1.1, max(4, int(5 * self.s)))
            pantalla.blit(arco, (centro[0] - radio - 10, centro[1] - radio - 10))

    def _dibujar_nombre(self, pantalla, jugador):
        """Dibuja el nombre del jugador con contorno legible.

        Args:
            pantalla: Superficie de pygame donde dibujar.
            jugador: Jugador al que pertenece el nombre.
        """
        fuente = self._fuente_nombre
        texto = fuente.render(jugador.nombre, True, (255, 255, 255))
        contorno = fuente.render(jugador.nombre, True, (15, 15, 25))
        cx = jugador.x + self.config.TAMAÑO_JUGADOR // 2
        ty = jugador.y - 8
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    pantalla.blit(contorno, (cx - texto.get_width() // 2 + dx, ty + dy))
        pantalla.blit(texto, (cx - texto.get_width() // 2, ty))