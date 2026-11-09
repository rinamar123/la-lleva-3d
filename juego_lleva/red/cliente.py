"""Cliente de red del multijugador.

Solo se encarga de la conexión y la sincronización con el servidor: recibe el
propio id y el estado de todos los jugadores en un hilo aparte. La interfaz
(pygame) se deja fuera de este módulo para poder probarlo sin ventana.
"""

import socket
import threading

from .protocolo import (
    ANCHO_BUFFER,
    HOST_CLIENTE_DEFECTO,
    PUERTO_DEFECTO,
    TIPO_CONEXION,
    TIPO_ESTADO,
    TIPO_POSICION,
    codificar_mensaje,
    extraer_linea,
)


class ClienteMultijugador:
    """Cliente de red que se conecta al servidor y sincroniza su estado."""

    def __init__(self, host=HOST_CLIENTE_DEFECTO, puerto=PUERTO_DEFECTO, tiempo_espera=5.0,
                 silencioso=False):
        """Inicializa el cliente sin conectarse.

        Args:
            host (str): Dirección del servidor.
            puerto (int): Puerto del servidor.
            tiempo_espera (float): Timeout de conexión en segundos.
            silencioso (bool): True para no imprimir mensajes (útil en tests).
        """
        self.host = host
        self.puerto = puerto
        self.tiempo_espera = tiempo_espera
        self.silencioso = silencioso
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(tiempo_espera)
        self.lock = threading.Lock()
        self.mi_id = None
        self.jugadores = {}
        self.conectado = False
        self._hilo_red = None

    # ------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------

    def conectar(self):
        """Conecta al servidor y arranca el hilo que recibe mensajes.

        Returns:
            ClienteMultijugador: El propio cliente para encadenar llamadas.
        """
        self.socket.connect((self.host, self.puerto))
        self.socket.settimeout(None)
        self.conectado = True
        self._hilo_red = threading.Thread(target=self._recibir_datos, daemon=True)
        self._hilo_red.start()
        return self

    def cerrar(self):
        """Cierra la conexión con el servidor de forma segura."""
        self.conectado = False
        try:
            self.socket.close()
        except OSError:
            pass

    # ------------------------------------------------------------
    # Recepción
    # ------------------------------------------------------------

    def _recibir_datos(self):
        """Hilo que lee mensajes del servidor hasta desconectarse."""
        buffer = ""
        while self.conectado:
            try:
                datos = self.socket.recv(ANCHO_BUFFER)
                if not datos:
                    break
                buffer += datos.decode("utf-8")
                buffer = self._procesar_buffer(buffer)
            except OSError as error:
                if self.conectado and not self.silencioso:
                    print("Error recibiendo:", error)
                break
        self.cerrar()

    def _procesar_buffer(self, buffer):
        """Procesa los mensajes completos y devuelve el buffer restante."""
        while True:
            mensaje, buffer = extraer_linea(buffer)
            if mensaje is None:
                return buffer
            self._procesar_mensaje(mensaje)

    def _procesar_mensaje(self, mensaje):
        """Actualiza el estado local según el tipo de mensaje recibido."""
        tipo = mensaje.get("tipo")

        if tipo == TIPO_CONEXION:
            self.mi_id = str(mensaje["id"])
            if not self.silencioso:
                print(f"Conectado como J{self.mi_id}")
        elif tipo == TIPO_ESTADO:
            with self.lock:
                self.jugadores = {str(k): v for k, v in mensaje.get("jugadores", {}).items()}

    # ------------------------------------------------------------
    # Envío
    # ------------------------------------------------------------

    def enviar_posicion(self, x, y):
        """Envía la posición propia al servidor.

        Args:
            x (float): Coordenada horizontal.
            y (float): Coordenada vertical.

        Returns:
            bool: True si se envió, False si no hay conexión con id asignado.
        """
        if not self.conectado or self.mi_id is None:
            return False
        try:
            self.socket.sendall(codificar_mensaje({"tipo": TIPO_POSICION, "x": x, "y": y}))
            return True
        except OSError as error:
            if not self.silencioso:
                print("Error enviando:", error)
            self.cerrar()
            return False

    # ------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------

    def obtener_jugadores(self):
        """Devuelve una copia segura del estado de los jugadores.

        Returns:
            dict: Mapa id_jugador -> {x, y, color}.
        """
        with self.lock:
            return self.jugadores.copy()