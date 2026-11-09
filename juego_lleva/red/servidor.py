"""Servidor del multijugador en red.

Encapsula el socket, la administración de clientes y el estado compartido.
Cada cliente se atiende en un hilo propio y el estado se notifica a todos
los conectados mediante mensajes de tipo "estado".

Ejecución desde la raíz del proyecto:
    python servidor.py [--host 0.0.0.0] [--puerto 5555]
"""

import argparse
import socket
import threading

from .protocolo import (
    ANCHO_BUFFER,
    HOST_DEFECTO,
    PUERTO_DEFECTO,
    TIPO_CONEXION,
    TIPO_ESTADO,
    TIPO_POSICION,
    codificar_mensaje,
    extraer_linea,
)


class ServidorMultijugador:
    """Servidor que sincroniza la posición de los jugadores conectados."""

    def __init__(self, host=HOST_DEFECTO, puerto=PUERTO_DEFECTO, silencioso=False):
        """Inicializa el servidor sin abrir todavía el socket.

        Args:
            host (str): Dirección a la que se vincula el servidor.
            puerto (int): Puerto de escucha. Usar 0 para que el SO asigne uno.
            silencioso (bool): True para no imprimir mensajes (útil en tests).
        """
        self.host = host
        self.puerto = puerto
        self.puerto_real = None
        self.silencioso = silencioso
        self.jugadores = {}
        self._clientes = {}
        self._siguiente_id = 1
        self._lock = threading.Lock()
        self._ejecutando = True
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # ------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------

    def iniciar(self):
        """Vincula el socket y acepta jugadores hasta que se detiene."""
        self._socket.bind((self.host, self.puerto))
        self.puerto_real = self._socket.getsockname()[1]
        self._socket.listen()

        if not self.silencioso:
            self._imprimir_presentacion()

        while self._ejecutando:
            try:
                cliente, direccion = self._socket.accept()
            except OSError:
                break
            if self._ejecutando:
                self._aceptar_cliente(cliente, direccion)

    def detener(self):
        """Detiene el servidor y cierra el socket de escucha."""
        self._ejecutando = False
        try:
            self._socket.close()
        except OSError:
            pass

    def _imprimir_presentacion(self):
        """Muestra el banner de inicio del servidor."""
        print("=" * 50)
        print("        SERVIDOR DEL JUEGO MULTIJUGADOR")
        print("=" * 50)
        print(f"Servidor iniciado en puerto {self.puerto_real}")
        print("Esperando jugadores...")
        print()

    # ------------------------------------------------------------
    # Conexiones
    # ------------------------------------------------------------

    def _aceptar_cliente(self, cliente, direccion):
        """Registra a un nuevo jugador, le avisa su id y le notifica el estado."""
        with self._lock:
            jugador_id = self._siguiente_id
            self._siguiente_id += 1
            x_inicial = 100 + (jugador_id - 1) * 150
            self.jugadores[str(jugador_id)] = {
                "x": x_inicial,
                "y": 300,
                "color": [50, 150, 255],
            }
            self._clientes[cliente] = jugador_id

        if not self.silencioso:
            print(f"Jugador {jugador_id} conectado desde {direccion}")

        self.enviar_mensaje(cliente, {"tipo": TIPO_CONEXION, "id": jugador_id})
        self.enviar_estado()

        hilo = threading.Thread(
            target=self._manejar_cliente,
            args=(cliente, jugador_id),
            daemon=True,
        )
        hilo.start()

    def _manejar_cliente(self, cliente, jugador_id):
        """Lee los mensajes de un cliente hasta que se desconecta."""
        buffer = ""
        try:
            while True:
                datos = cliente.recv(ANCHO_BUFFER)
                if not datos:
                    break
                buffer += datos.decode("utf-8")
                buffer = self._procesar_buffer(cliente, jugador_id, buffer)
        except OSError as error:
            if not self.silencioso:
                print(f"Error con jugador {jugador_id}: {error}")
        finally:
            self._desconectar(cliente, jugador_id)

    def _procesar_buffer(self, cliente, jugador_id, buffer):
        """Procesa los mensajes completos y devuelve el buffer restante.

        Args:
            cliente: Socket del cliente emisor.
            jugador_id (int): Id del jugador emisor.
            buffer (str): Buffer acumulado del cliente.

        Returns:
            str: El texto de mensajes aún sin línea completa.
        """
        while True:
            mensaje, buffer = extraer_linea(buffer)
            if mensaje is None:
                return buffer
            self._procesar_mensaje(cliente, jugador_id, mensaje)

    def _procesar_mensaje(self, cliente, jugador_id, mensaje):
        """Atiende un mensaje individual del cliente."""
        if mensaje.get("tipo") != TIPO_POSICION:
            return

        x = mensaje.get("x")
        y = mensaje.get("y")
        if x is None or y is None:
            return

        with self._lock:
            if str(jugador_id) in self.jugadores:
                self.jugadores[str(jugador_id)]["x"] = x
                self.jugadores[str(jugador_id)]["y"] = y

        self.enviar_estado()

    def _desconectar(self, cliente, jugador_id):
        """Elimina al jugador desconectado y notifica a los demás."""
        with self._lock:
            self.jugadores.pop(str(jugador_id), None)
            self._clientes.pop(cliente, None)

        if not self.silencioso:
            print(f"Jugador {jugador_id} desconectado")

        try:
            cliente.close()
        except OSError:
            pass

        self.enviar_estado()

    # ------------------------------------------------------------
    # Comunicación
    # ------------------------------------------------------------

    def enviar_mensaje(self, cliente, mensaje):
        """Envía un mensaje codificado a un cliente específico."""
        cliente.sendall(codificar_mensaje(mensaje))

    def enviar_estado(self):
        """Notifica el estado actual del juego a todos los clientes."""
        with self._lock:
            estado = {"tipo": TIPO_ESTADO, "jugadores": self.jugadores.copy()}
            clientes = list(self._clientes.keys())

        for cliente in clientes:
            try:
                self.enviar_mensaje(cliente, estado)
            except OSError as error:
                if not self.silencioso:
                    print("Error enviando estado:", error)


def main():
    """Punto de entrada CLI del servidor multijugador."""
    parser = argparse.ArgumentParser(description="Servidor del juego La Lleva en red")
    parser.add_argument("--host", default=HOST_DEFECTO, help="Dirección de escucha")
    parser.add_argument("--puerto", type=int, default=PUERTO_DEFECTO, help="Puerto de escucha")
    args = parser.parse_args()

    servidor = ServidorMultijugador(args.host, args.puerto)
    try:
        servidor.iniciar()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.detener()


if __name__ == "__main__":
    main()