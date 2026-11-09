"""Compatibilidad con el primer prototipo Ursina.

El cliente mantenido vive en juego_lleva.ursina3d y reutiliza la simulación
real del proyecto. Ejecutar también es posible con:
    python -m ursina_game.main
"""
from juego_lleva.ursina3d import main

if __name__ == "__main__":
    main()
