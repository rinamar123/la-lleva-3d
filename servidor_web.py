"""Servidor web local que sirve el juego (build de pygbag) y la API de la sala.

Rutas de la API de multijugador en línea (todas responden JSON):

- POST /api/sala/unirse  {"nombre": "Ana"}            -> token de acceso
- POST /api/sala/sync    {"token": ..., "entrada": {...}, "listo": bool}
                                                     -> snapshot de la partida
- POST /api/sala/salir   {"token": ...}               -> abandonar la sala
- GET  /api/sala                                     -> estado público (diagnóstico)

El cuerpo se acepta tanto como ``application/json`` como url-encoded, para
tolerar el formato exacto que envíe el cliente de pygbag.
"""

import argparse
import http.server
import json
import os
import socket
import webbrowser
from urllib.parse import parse_qs

from juego_lleva.red.sala import SalaEnLinea

HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "no-cache",
    # pygbag (wasm) necesita aislar el contexto para usar SharedArrayBuffer.
    # credentialless mantiene la isla de origen sin exigir CORP en el CDN.
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "credentialless",
}

CODIGO_OK = 200
CODIGO_MAL_REQUEST = 400
CODIGO_NO_AUTORIZADO = 401
CODIGO_EN_CONFLICTO = 409
CODIGO_NO_ENCONTRADO = 404
CODIGO_CUERPO_GRANDE = 413

MAX_CUERPO = 16 * 1024


class CuerpoInvalido(ValueError):
    """Cuerpo de la petición ilegible, gigante o con tipos incorrectos."""

    def __init__(self, codigo, http=CODIGO_MAL_REQUEST):
        super().__init__(codigo)
        self.codigo = codigo
        self.http = http


def leer_cuerpo(manejador):
    """Decodifica el cuerpo de la petición como dict.

    Prefiere JSON y hace fallback a url-encoded para clientes que no fijen
    el Content-Type correctamente.

    Raises:
        CuerpoInvalido: Si la longitud no es un número, excede el tope o el
            cuerpo no se puede decodificar.
    """
    try:
        longitud = int(manejador.headers.get("Content-Length", 0) or 0)
    except (TypeError, ValueError):
        raise CuerpoInvalido("content_length_invalido")
    if longitud <= 0:
        return {}
    if longitud > MAX_CUERPO:
        raise CuerpoInvalido("cuerpo_demasiado_grande", CODIGO_CUERPO_GRANDE)
    cuerpo = manejador.rfile.read(longitud).decode("utf-8", "replace")
    tipo = manejador.headers.get("Content-Type", "")
    if "json" in tipo:
        try:
            datos = json.loads(cuerpo)
            if isinstance(datos, dict):
                return datos
        except (ValueError, TypeError):
            pass
    return {clave: valores[0] if len(valores) == 1 else valores
            for clave, valores in parse_qs(cuerpo).items()}


def campo_texto(datos, clave):
    """Extrae un campo de texto, rechazando listas/dicts (campos repetidos)."""
    valor = datos.get(clave, "")
    if not isinstance(valor, str):
        raise CuerpoInvalido(f"campo_{clave}_invalido")
    return valor


def campo_token(datos):
    """Extrae el token, aceptando ``None`` (la sala responde token_invalido)."""
    valor = datos.get("token")
    if valor is None or isinstance(valor, str):
        return valor
    raise CuerpoInvalido("campo_token_invalido")


def _codigo_token(respuesta):
    """Código HTTP de sync/salir: 401 cuando la sala rechaza el token."""
    return CODIGO_OK if "error" not in respuesta else CODIGO_NO_AUTORIZADO


def crear_manejador(directorio, sala):
    """Crea una clase de manejador HTTP atada a un directorio y una sala."""

    class Manejador(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directorio, **kwargs)

        def end_headers(self):
            for clave, valor in HEADERS.items():
                self.send_header(clave, valor)
            super().end_headers()

        def _responder_json(self, datos, codigo=CODIGO_OK):
            cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_GET(self):
            if self.path == "/api/sala":
                self._responder_json(sala.estado_publico())
                return
            super().do_GET()

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_POST(self):
            if not self.path.startswith("/api/sala/"):
                self._responder_json({"error": "ruta_desconocida"},
                                     CODIGO_NO_ENCONTRADO)
                return
            try:
                datos = leer_cuerpo(self)
                respuesta, codigo = self._procesar(datos)
            except CuerpoInvalido as error:
                respuesta, codigo = {"error": error.codigo}, error.http
            self._responder_json(respuesta, codigo)

        def _procesar(self, datos):
            """Traduce una petición de la API en respuesta y código HTTP.

            Returns:
                tuple: (dict de respuesta, código HTTP).
            """
            if self.path == "/api/sala/unirse":
                nombre = campo_texto(datos, "nombre")
                color = campo_texto(datos, "color") if "color" in datos else "azul"
                accesorio = campo_texto(datos, "accesorio") if "accesorio" in datos else "ninguno"
                respuesta = sala.unirse(nombre, color=color, accesorio=accesorio)
                codigo = CODIGO_OK if "error" not in respuesta else CODIGO_EN_CONFLICTO
                return respuesta, codigo
            if self.path == "/api/sala/sync":
                token = campo_token(datos)
                respuesta = sala.sincronizar(
                    token, entrada=datos.get("entrada"),
                    listo=datos.get("listo"))
                return respuesta, _codigo_token(respuesta)
            if self.path == "/api/sala/salir":
                token = campo_token(datos)
                respuesta = sala.salir(token)
                return respuesta, _codigo_token(respuesta)
            return {"error": "ruta_desconocida"}, CODIGO_NO_ENCONTRADO

        def log_message(self, formato, *argumentos):
            if not self.path.startswith("/api"):
                super().log_message(formato, *argumentos)

    return Manejador


def ip_local():
    """Devuelve la IP local del equipo para acceder desde el celular."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="Sirve el juego compilado con pygbag")
    parser.add_argument("directorio", nargs="?", default="build/web")
    parser.add_argument("--puerto", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--max-jugadores", type=int, default=16, choices=range(2, 17),
                        help="Capacidad de la sala en línea (2-16)")
    parser.add_argument("--sin-abrir", action="store_true",
                        help="No abrir navegador (útil en servidores alojados)")
    args = parser.parse_args()

    sala = SalaEnLinea(max_jugadores=args.max_jugadores)
    manejador = lambda *a, **k: crear_manejador(args.directorio, sala)(*a, **k)
    servidor = http.server.ThreadingHTTPServer(("0.0.0.0", args.puerto), manejador)
    ip = ip_local()
    print(f"Juego disponible en:  http://localhost:{args.puerto}/")
    print(f"Desde tu celular:     http://{ip}:{args.puerto}/")
    print(f"Sala en línea para {args.max_jugadores} jugadores")
    if not args.sin_abrir and os.environ.get("RENDER") is None:
        webbrowser.open(f"http://localhost:{args.puerto}/")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sala.cerrar()
        servidor.server_close()


if __name__ == "__main__":
    main()