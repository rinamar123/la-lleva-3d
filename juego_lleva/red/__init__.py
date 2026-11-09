"""Multijugador en red: cliente, servidor y protocolo de mensajes."""

from .cliente import ClienteMultijugador
from .servidor import ServidorMultijugador

__all__ = ["ClienteMultijugador", "ServidorMultijugador"]