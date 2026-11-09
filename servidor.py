"""Launcher del servidor multijugador en red.

Arranca el servidor de sockets delega en ``juego_lleva.red.servidor``.
Uso:
    python servidor.py [--host 0.0.0.0] [--puerto 5555]
"""

from juego_lleva.red.servidor import main

if __name__ == "__main__":
    main()