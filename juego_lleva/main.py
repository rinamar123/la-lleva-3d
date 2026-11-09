"""Punto de entrada principal del juego La Lleva."""

import asyncio
import sys

import pygame

ES_PLATAFORMA_WEB = sys.platform == "emscripten"


def crear_juego():
    """Inicializa pygame y devuelve una instancia del juego."""
    from juego_lleva.core.config import Config
    from juego_lleva.core.juego import Juego
    pygame.init()
    config = Config()
    return Juego(config)


async def _bucle_web(juego):
    """Bucle de juego en la web: cede el control al navegador cada frame."""
    while True:
        await juego.procesar_frame_async()
        await asyncio.sleep(0)


async def _arrancar_web():
    """Arranca el juego web tras un turno del bucle.

    En pygbag/wasm pygame termina de inicializarse de forma asíncrona; una
    espera de un turno antes de importar y crear el juego evita acceder a
    ``pygame`` antes de tiempo durante ``shell.source``.
    """
    await asyncio.sleep(0)
    juego = crear_juego()
    await _bucle_web(juego)


def _lanzar_en_bucle(fabrica):
    """Ejecuta una fábrica de corutinas en el bucle actual o en uno nuevo."""
    try:
        bucle = asyncio.get_running_loop()
    except RuntimeError:
        bucle = None
    if bucle is not None:
        bucle.create_task(fabrica())
    else:
        asyncio.run(fabrica())


def main():
    """Función principal: ejecuta el juego en escritorio o en la web."""
    if ES_PLATAFORMA_WEB:
        _lanzar_en_bucle(_arrancar_web)
    else:
        juego = crear_juego()
        juego.ejecutar()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    main()