"""Servicio de configuración persistente del juego."""

import json
import os

from juego_lleva.core.config import Config


class ConfiguracionService:
    """Carga, valida y guarda las preferencias del jugador en un archivo JSON."""

    CLAVES = (
        "duracion_ronda",
        "dificultad_ia",
        "volumen_musica",
        "volumen_sfx",
        "pantalla_completa",
    )

    POR_DEFECTO = {
        "duracion_ronda": Config.DURACION_RONDA,
        "dificultad_ia": "normal",
        "volumen_musica": 0.8,
        "volumen_sfx": 0.8,
        "pantalla_completa": False,
    }

    def __init__(self, ruta=None):
        self.ruta = ruta or Config.SETTINGS_PATH
        self.configuracion = dict(self.POR_DEFECTO)
        self._cargar()

    def _cargar(self):
        """Carga la configuración desde disco fusionándola con los valores por defecto."""
        if not os.path.exists(self.ruta):
            return
        try:
            with open(self.ruta, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            if isinstance(datos, dict):
                for clave, valor in datos.items():
                    if clave in self.POR_DEFECTO:
                        self.configuracion[clave] = valor
        except (OSError, json.JSONDecodeError):
            self.configuracion = dict(self.POR_DEFECTO)

    def _guardar(self):
        """Persiste la configuración actual en disco."""
        try:
            os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
            with open(self.ruta, "w", encoding="utf-8") as archivo:
                json.dump(self.configuracion, archivo, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def obtener(self, clave):
        """Devuelve el valor de una clave de configuración.

        Args:
            clave (str): Nombre de la clave.

        Returns:
            El valor almacenado.
        """
        return self.configuracion.get(clave, self.POR_DEFECTO.get(clave))

    def establecer(self, clave, valor):
        """Valida y guarda un valor de configuración.

        Args:
            clave (str): Nombre de la clave.
            valor: Nuevo valor.
        """
        valor = self._normalizar(clave, valor)
        self.configuracion[clave] = valor
        self._guardar()
        return valor

    def _normalizar(self, clave, valor):
        """Ajusta un valor según las reglas de cada clave.

        Args:
            clave (str): Nombre de la clave.
            valor: Valor propuesto.

        Returns:
            El valor validado/normalizado.
        """
        if clave == "duracion_ronda":
            opciones = Config.DURACIONES_RONDA
            return opciones[min(opciones.index(valor) if valor in opciones else 1, len(opciones) - 1)]
        if clave == "dificultad_ia":
            return valor if valor in Config.DIFICULTADES else self.POR_DEFECTO[clave]
        if clave in ("volumen_musica", "volumen_sfx"):
            return max(0.0, min(1.0, float(valor)))
        if clave == "pantalla_completa":
            return bool(valor)
        return valor

    def siguiente(self, clave, direccion=1):
        """Pasa al siguiente/anterior valor de una clave ciclando las opciones.

        Args:
            clave (str): Nombre de la clave.
            direccion (int): Paso (1 o -1).

        Returns:
            El nuevo valor aplicado.
        """
        actual = self.obtener(clave)
        nuevo = self._calcular_siguiente(clave, actual, direccion)
        return self.establecer(clave, nuevo)

    def _calcular_siguiente(self, clave, actual, direccion):
        """Calcula el próximo valor de una clave sin persistirlo.

        Args:
            clave (str): Nombre de la clave.
            actual: Valor actual.
            direccion (int): Paso (1 o -1).

        Returns:
            El siguiente valor.
        """
        if clave == "duracion_ronda":
            opciones = Config.DURACIONES_RONDA
            indice = opciones.index(actual) if actual in opciones else 1
            return opciones[(indice + direccion) % len(opciones)]
        if clave == "dificultad_ia":
            orden = list(Config.DIFICULTADES)
            indice = orden.index(actual) if actual in orden else 1
            return orden[(indice + direccion) % len(orden)]
        if clave in ("volumen_musica", "volumen_sfx"):
            return max(0.0, min(1.0, float(actual) + 0.1 * direccion))
        if clave == "pantalla_completa":
            return not bool(actual)
        return actual