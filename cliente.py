"""Launcher del cliente multijugador en red.

Levanta una ventana pygame, conecta con el servidor y sincroniza la posición
de los jugadores en tiempo real. La lógica de red vive en
``juego_lleva.red.cliente``; aquí solo queda la interfaz.

Uso:
    python cliente.py [--host 127.0.0.1] [--puerto 5555]
"""

import argparse

import pygame

from juego_lleva.red.cliente import ClienteMultijugador

ANCHO = 800
ALTO = 800
VELOCIDAD = 5
TAMAÑO_JUGADOR = 40

COLOR_FONDO = (30, 30, 30)
COLOR_TEXTO = (255, 255, 255)
COLOR_TEXTO_SUAVE = (200, 200, 200)
COLOR_YO = (50, 150, 255)
COLOR_RIVAL = (255, 80, 80)
COLOR_BORDE = (255, 255, 255)

FUENTE_DEFECTO = "Arial"


class ClienteJuego:
    """Aplicación pygame que muestra el estado compartido del multijugador."""

    def __init__(self, host, puerto):
        """Inicializa la pantalla, fuentes y el cliente de red.

        Args:
            host (str): Dirección del servidor.
            puerto (int): Puerto del servidor.
        """
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Juego Multijugador")
        self.reloj = pygame.time.Clock()
        self.red = ClienteMultijugador(host, puerto)

        self.x = 100
        self.y = 300

        self.fuente = pygame.font.SysFont(FUENTE_DEFECTO, 24)
        self.fuente_titulo = pygame.font.SysFont(FUENTE_DEFECTO, 32)

        self.ejecutando = True

    # ------------------------------------------------------------
    # Ciclo principal
    # ------------------------------------------------------------

    def iniciar(self):
        """Conecta al servidor y ejecuta el bucle del juego."""
        self.red.conectar()
        while self.ejecutando:
            self._procesar_eventos()
            self._actualizar()
            self._dibujar()
            self.reloj.tick(60)
        self._cerrar()

    def _procesar_eventos(self):
        """Maneja los eventos de pygame (salida de la ventana)."""
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.ejecutando = False

    def _actualizar(self):
        """Mueve al jugador con las flechas y envía su posición al servidor."""
        self._mover_con_teclas()
        self._limitar_a_pantalla()
        if self.red.mi_id is not None:
            self.red.enviar_posicion(self.x, self.y)

    def _mover_con_teclas(self):
        """Aplica el movimiento según las flechas presionadas."""
        teclas = pygame.key.get_pressed()
        if teclas[pygame.K_LEFT]:
            self.x -= VELOCIDAD
        if teclas[pygame.K_RIGHT]:
            self.x += VELOCIDAD
        if teclas[pygame.K_UP]:
            self.y -= VELOCIDAD
        if teclas[pygame.K_DOWN]:
            self.y += VELOCIDAD

    def _limitar_a_pantalla(self):
        """Mantiene la posición dentro de los límites de la ventana."""
        self.x = max(0, min(ANCHO - TAMAÑO_JUGADOR, self.x))
        self.y = max(0, min(ALTO - TAMAÑO_JUGADOR, self.y))

    # ------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------

    def _dibujar(self):
        """Renderiza la escena completa."""
        self.pantalla.fill(COLOR_FONDO)
        self._dibujar_titulo()
        self._dibujar_jugadores()
        self._dibujar_informacion()
        pygame.display.flip()

    def _dibujar_titulo(self):
        """Dibuja el título en la esquina superior izquierda."""
        titulo = self.fuente_titulo.render("JUEGO MULTIJUGADOR", True, COLOR_TEXTO)
        self.pantalla.blit(titulo, (20, 20))

    def _dibujar_jugadores(self):
        """Dibuja a todos los jugadores sincronizados por el servidor."""
        jugadores = self.red.obtener_jugadores()
        for jugador_id, jugador in jugadores.items():
            px = jugador["x"]
            py = jugador["y"]
            es_propio = self.red.mi_id is not None and jugador_id == self.red.mi_id

            color = COLOR_YO if es_propio else COLOR_RIVAL
            pygame.draw.rect(self.pantalla, color, (px, py, TAMAÑO_JUGADOR, TAMAÑO_JUGADOR))
            pygame.draw.rect(self.pantalla, COLOR_BORDE, (px, py, TAMAÑO_JUGADOR, TAMAÑO_JUGADOR), 2)

            texto = self.fuente.render(f"J{jugador_id}", True, COLOR_TEXTO)
            self.pantalla.blit(texto, (px, py - 25))

    def _dibujar_informacion(self):
        """Dibuja el id propio y la referencia de controles al pie."""
        if self.red.mi_id is not None:
            informacion = self.fuente.render(
                f"Tu jugador: J{self.red.mi_id}", True, COLOR_TEXTO
            )
            self.pantalla.blit(informacion, (20, ALTO - 50))

        controles = self.fuente.render("Flechas = Mover", True, COLOR_TEXTO_SUAVE)
        self.pantalla.blit(controles, (ANCHO - 220, ALTO - 50))

    def _cerrar(self):
        """Cierra la conexión y libera pygame."""
        self.red.cerrar()


def main():
    """Punto de entrada CLI del cliente: parsea argumentos y abre la app."""
    parser = argparse.ArgumentParser(description="Cliente del juego La Lleva en red")
    parser.add_argument("--host", default="127.0.0.1", help="Dirección del servidor")
    parser.add_argument("--puerto", type=int, default=5555, help="Puerto del servidor")
    args = parser.parse_args()

    pygame.init()
    try:
        ClienteJuego(args.host, args.puerto).iniciar()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()