"""Cliente HTTP asíncrono de la sala en línea (usado en la web).

En el navegador (pygbag/wasm) realiza los POST con la Fetch API directamente:
define en el navegador una función JS (`window.lallevaPost`) que guarda el
resultado en `window.pglalleva`, y Python lo sondea cediendo el control al
navegador. No se usa ``pygbag.support`` porque ese paquete no viaja dentro del
build wasm (solo existe en el entorno de escritorio); en escritorio/tests se usa
``urllib`` de la biblioteca estándar como respaldo.

Las peticiones deben ser secuenciales: el estado global ``pglalleva`` no
tolera peticiones concurrentes.
"""

import asyncio
import builtins
import json

from juego_lleva.red.url_sala import url_sala

RETARDO_SONDEO_WASM = 0.001
TIMEOUT_POST_SEG = 3.0


class ClienteEnLinea:
    """Cliente del protocolo HTTP de la sala en línea."""

    PERIODO_SYNC = 1.0 / 30

    RUTA_UNIRSE = "/api/sala/unirse"
    RUTA_SYNC = "/api/sala/sync"
    RUTA_SALIR = "/api/sala/salir"

    SALA_LLENA = "sala_llena"
    PARTIDA_EN_CURSO = "partida_en_curso"
    TOKEN_INVALIDO = "token_invalido"

    def __init__(self):
        """Inicializa el cliente sin conexión."""
        self.token = None
        self.mi_id = None
        self.nombre = None

    @property
    def conectado(self):
        """Indica si hay un token de sala vigente."""
        return self.token is not None

    @staticmethod
    def _plataforma():
        """Devuelve el módulo de plataforma inyectado por pygbag (o None)."""
        return getattr(builtins, "__EMSCRIPTEN__", None)

    @staticmethod
    def _instalar_fetch_js(ventana):
        """Define en el navegador el fetch para esta sala (una sola vez)."""
        if getattr(ventana, "lallevaFetchOk", False):
            return
        ventana.eval(
            "window.lallevaFetchOk = true;\n"
            "window.lallevaPost = function (url, data) {\n"
            "  window.pglalleva = { done:false, error:'', text:'' };\n"
            "  fetch(new Request(url, {method:'POST', "
            "headers:{'Accept':'application/json','Content-Type':'application/json'}, "
            "body:data}))\n"
            "   .then(function(r){return r.text();})\n"
            "   .then(function(t){window.pglalleva.text=t; window.pglalleva.done=true;})\n"
            "   .catch(function(e){window.pglalleva.error=String(e); window.pglalleva.done=true;});\n"
            "};\n"
        )

    def _base_url(self):
        """Devuelve el origen de la API de la sala.

        En el navegador es el origen de la página (mismo servidor que la API);
        en escritorio, donde no hay página, la URL de la sala (``url_sala()``).
        """
        plataforma = self._plataforma()
        if plataforma is not None:
            try:
                return plataforma.window.location.origin.rstrip("/")
            except Exception:
                pass
        return url_sala().rstrip("/")

    async def _post_wasm(self, ruta, datos):
        """POST con la Fetch API del navegador (sondeo del resultado en JS).

        El sondeo cede el control al navegador con una espera real
        (``asyncio.sleep`` con Retardo > 0). Con ``sleep(0)`` el bucle solo
        rota dentro de wasm y la cola de tareas del navegador no avanza: SDL
        deja de bombear los eventos de entrada y los clics del usuario llegan
        segundos más tarde, con lo que la interfaz web no responde.
        """
        plataforma = self._plataforma()
        if plataforma is None:
            raise RuntimeError("no hay plataforma wasm")
        ventana = plataforma.window
        self._instalar_fetch_js(ventana)
        url = self._base_url() + ruta
        ventana.lallevaPost(url, json.dumps(datos))
        for _ in range(3000):
            if ventana.pglalleva.done:
                break
            await asyncio.sleep(RETARDO_SONDEO_WASM)
        else:
            raise TimeoutError("el navegador no respondió al POST " + ruta)
        if ventana.pglalleva.error:
            raise RuntimeError(ventana.pglalleva.error)
        return str(ventana.pglalleva.text)

    def _post_local(self, ruta, datos):
        """POST en escritorio con ``urllib`` y el cuerpo ya serializado en JSON.

        El cuerpo va como JSON de verdad (igual que en el navegador): si se
        mandara url-encoded, la sala recibiría ``listo`` como texto y ``entrada``
        como cadena, los descartaría por no ser bool/dict y la partida nunca
        arrancaría. Los errores HTTP también se devuelven como texto, para que
        un 401 con ``token_invalido`` llegue al controlador como snapshot de
        error y no como excepción. ``urllib`` se importa aquí y no arriba para
        que el build wasm no cargue ``ssl``/``socket``, que no existen en el
        navegador.
        """
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen

        peticion = Request(
            self._base_url() + ruta,
            data=json.dumps(datos).encode("utf-8"),
            headers={"Accept": "application/json",
                     "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(peticion, timeout=TIMEOUT_POST_SEG) as respuesta:
                return respuesta.read().decode("utf-8")
        except HTTPError as error:
            return error.read().decode("utf-8")

    async def _post(self, ruta, datos):
        """Envía un POST con JSON y decodifica la respuesta."""
        if self._plataforma() is not None:
            texto = await self._post_wasm(ruta, datos)
        else:
            texto = self._post_local(ruta, datos)
        try:
            respuesta = json.loads(texto)
        except (ValueError, TypeError):
            return {"error": "respuesta_invalida"}
        if isinstance(respuesta, dict):
            return respuesta
        return {"error": "respuesta_invalida"}

    async def unirse(self, nombre):
        """Pide un token a la sala y lo conserva si la respuesta es válida.

        Args:
            nombre (str): Nombre con el que entrar a la sala.

        Returns:
            dict: Datos de entrada a la sala o un mensaje de error.
        """
        respuesta = await self._post(self.RUTA_UNIRSE, {"nombre": nombre})
        if respuesta.get("ok"):
            self.token = respuesta.get("token")
            self.mi_id = respuesta.get("id")
            self.nombre = respuesta.get("nombre")
        return respuesta

    async def sincronizar(self, entrada=None, listo=None):
        """Envía la entrada y el estado de "Listo", y devuelve el snapshot.

        Args:
            entrada (dict, optional): Mapa de teclas presionadas (bool).
            listo (bool, optional): True si el jugador está listo.

        Returns:
            dict: Snapshot de la sala o un mensaje de error.
        """
        datos = {"token": self.token}
        if entrada is not None:
            datos["entrada"] = entrada
        if listo is not None:
            datos["listo"] = listo
        return await self._post(self.RUTA_SYNC, datos)

    async def salir(self):
        """Abandona la sala y descarta el token.

        Returns:
            dict: {"ok": True} o un mensaje de error.
        """
        if self.token is None:
            return {}
        respuesta = await self._post(self.RUTA_SALIR, {"token": self.token})
        self.token = None
        self.mi_id = None
        return respuesta