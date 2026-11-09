"""Servicio de audio que genera efectos de sonido y música de forma procedural."""

import array
import math

import pygame


class ServicioAudio:
    """Clase que sintetiza y reproduce sonidos y música del juego."""

    FRECUENCIA_MUESTREO = 22050

    def __init__(self):
        """Inicializa el mezclador y genera los sonidos del juego."""
        self.activo = True
        self.canal_musica = None
        try:
            pygame.mixer.pre_init(self.FRECUENCIA_MUESTREO, -16, 1, 512)
            pygame.mixer.init()
        except pygame.error:
            self.activo = False
            return

        try:
            self.sonido_toque = self._crear_toque()
            self.sonido_clic = self._crear_clic()
            self.sonido_countdown = self._crear_beep()
            self.sonido_inicio = self._crear_inicio()
            self.sonido_fin = self._crear_fin_ronda()
            self.sonido_paso = self._crear_paso()
            self.musica = self._generar_musica()
            self.canal_musica = pygame.mixer.Channel(1)
        except (pygame.error, OSError, ValueError):
            self.activo = False
            self.sonido_toque = self.sonido_clic = None
            self.sonido_countdown = self.sonido_inicio = self.sonido_fin = None
            self.sonido_paso = None
            self.musica = None
            self.canal_musica = None
            return
        self.volumen_sfx = 1.0
        self.volumen_musica = 1.0

    def _a_muestras(self, muestras):
        """Convierte una lista de muestras en un objeto pygame.mixer.Sound.

        Args:
            muestras (list): Lista de valores de muestra en el rango [-32768, 32767].

        Returns:
            pygame.mixer.Sound: Sonido listo para reproducir.
        """
        arr = array.array('h', (int(max(-32767, min(32767, m))) for m in muestras))
        return pygame.mixer.Sound(buffer=arr.tobytes())

    def _nota(self, frecuencia, duracion, volumen):
        """Genera las muestras de una nota con ataque y decaimiento suaves.

        Args:
            frecuencia (float): Frecuencia de la nota en hercios.
            duracion (float): Duración de la nota en segundos.
            volumen (float): Amplitud de la nota (0-1).

        Returns:
            list: Lista de muestras de la nota.
        """
        n = int(self.FRECUENCIA_MUESTREO * duracion)
        muestras = []
        for i in range(n):
            t = i / self.FRECUENCIA_MUESTREO
            ataque = min(1.0, t / 0.02)
            decaimiento = math.exp(-t * 4)
            desvanecimiento = 1 - i / n
            envolvente = ataque * decaimiento * desvanecimiento
            muestra = 32767 * volumen * envolvente * math.sin(2 * math.pi * frecuencia * t)
            muestras.append(muestra)
        return muestras

    def _silenzio(self, duracion):
        """Genera muestras de silencio.

        Args:
            duracion (float): Duración del silencio en segundos.

        Returns:
            list: Lista de muestras de silencio.
        """
        n = int(self.FRECUENCIA_MUESTREO * duracion)
        return [0.0] * n

    def _crear_toque(self):
        """Crea el sonido que se reproduce al tocar al otro jugador.

        Returns:
            pygame.mixer.Sound o None: Sonido generado.
        """
        if not self.activo:
            return None
        muestras = self._nota(880, 0.09, 0.5)
        muestras += self._nota(1174.66, 0.12, 0.45)
        return self._a_muestras(muestras)

    def _crear_clic(self):
        """Crea el sonido de los botones del menú.

        Returns:
            pygame.mixer.Sound o None: Sonido generado.
        """
        if not self.activo:
            return None
        return self._a_muestras(self._nota(960, 0.06, 0.35))

    def _crear_beep(self):
        """Crea el sonido del countdown.

        Returns:
            pygame.mixer.Sound o None: Sonido generado.
        """
        if not self.activo:
            return None
        return self._a_muestras(self._nota(620, 0.12, 0.4))

    def _crear_inicio(self):
        """Crea el sonido de arranque de la ronda.

        Returns:
            pygame.mixer.Sound o None: Sonido generado.
        """
        if not self.activo:
            return None
        muestras = self._nota(880, 0.12, 0.4)
        muestras += self._silenzio(0.04)
        muestras += self._nota(1174.66, 0.16, 0.4)
        return self._a_muestras(muestras)

    def _crear_paso(self):
        """Crea el sonido sordo de una pisada.

        Returns:
            pygame.mixer.Sound o None: Sonido generado.
        """
        if not self.activo:
            return None
        muestras = self._nota(110, 0.06, 0.45)
        muestras += self._nota(55, 0.06, 0.30)
        return self._a_muestras(muestras)

    def _crear_fin_ronda(self):
        """Crea la fanfarria de fin de ronda.

        Returns:
            pygame.mixer.Sound o None: Sonido generado.
        """
        if not self.activo:
            return None
        muestras = self._nota(523.25, 0.12, 0.4)
        muestras += self._nota(659.26, 0.12, 0.4)
        muestras += self._nota(783.99, 0.24, 0.45)
        return self._a_muestras(muestras)

    def _generar_musica(self):
        """Genera un bucle musical suave para el menú y la partida.

        Returns:
            pygame.mixer.Sound o None: Bucle musical generado.
        """
        if not self.activo:
            return None
        notas = [220.0, 261.63, 293.66, 329.63, 293.66, 261.63, 329.63, 392.0,
                 329.63, 293.66, 261.63, 220.0, 196.0, 220.0, 261.63, 293.66]
        muestras = []
        for f in notas:
            muestras += self._nota(f * 0.5, 0.55, 0.16)
            muestras += self._silenzio(0.05)
        return self._a_muestras(muestras)

    def reproducir_musica(self):
        """Reproduce la música en bucle."""
        if not self.activo or not self.musica:
            return
        if self.canal_musica and not self.canal_musica.get_busy():
            self.canal_musica.play(self.musica, loops=-1)

    def detener_musica(self):
        """Detiene la reproducción de música."""
        if not self.activo or not self.canal_musica:
            return
        self.canal_musica.stop()

    def musica_suena(self):
        """Indica si la música se está reproduciendo.

        Returns:
            bool: True si la música está sonando, False en caso contrario.
        """
        return bool(self.activo and self.canal_musica and self.canal_musica.get_busy())

    def tocar(self):
        """Reproduce el sonido de tocar a otro jugador."""
        self._reproducir(self.sonido_toque)

    def paso(self):
        """Reproduce el sonido de una pisada."""
        self._reproducir(self.sonido_paso, volumen=0.40)

    def clic(self):
        """Reproduce el sonido de clic de los botones."""
        self._reproducir(self.sonido_clic)

    def beep(self):
        """Reproduce el sonido del countdown."""
        self._reproducir(self.sonido_countdown)

    def inicio(self):
        """Reproduce el sonido de inicio de ronda."""
        self._reproducir(self.sonido_inicio)

    def fin_ronda(self):
        """Reproduce la fanfarria de fin de ronda."""
        self._reproducir(self.sonido_fin)

    def _reproducir(self, sonido, volumen=None):
        """Reproduce un sonido si está disponible, sin interrumpir otros.

        Args:
            sonido: Sonido a reproducir o None.
            volumen (float, optional): Volumen puntual (0-1) para este sonido.
        """
        if not self.activo or sonido is None:
            return
        canal = pygame.mixer.Channel(0)
        canal.set_volume(self.volumen_sfx if volumen is None else volumen)
        canal.play(sonido)

    def set_volumen_sfx(self, volumen):
        """Establece el volumen de los efectos de sonido.

        Args:
            volumen (float): Volumen en el rango 0-1.
        """
        self.volumen_sfx = max(0.0, min(1.0, float(volumen)))

    def set_volumen_musica(self, volumen):
        """Establece el volumen de la música.

        Args:
            volumen (float): Volumen en el rango 0-1.
        """
        self.volumen_musica = max(0.0, min(1.0, float(volumen)))
        if self.activo and self.canal_musica:
            self.canal_musica.set_volume(self.volumen_musica)