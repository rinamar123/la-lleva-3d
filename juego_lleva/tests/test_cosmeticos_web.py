"""Pruebas de cosméticos y capacidad ampliada de la sala web."""

from juego_lleva.red.sala import SalaEnLinea


def test_jugador_puede_elegir_color_y_accesorio_y_se_comparten():
    sala = SalaEnLinea(max_jugadores=2, iniciar_hilo=False)
    try:
        entrada = sala.unirse("Ana", color="rosa", accesorio="gafas")
        estado = sala.sincronizar(entrada["token"])
        jugador = estado["jugadores"][0]
        assert entrada["color"] == "rosa"
        assert entrada["accesorio"] == "gafas"
        assert jugador["color"] == "rosa"
        assert jugador["accesorio"] == "gafas"
    finally:
        sala.cerrar()


def test_cosmeticos_invalidos_vuelven_a_valores_seguros():
    sala = SalaEnLinea(max_jugadores=2, iniciar_hilo=False)
    try:
        entrada = sala.unirse("Ana", color="javascript", accesorio="jetpack")
        assert entrada["color"] == "azul"
        assert entrada["accesorio"] == "ninguno"
    finally:
        sala.cerrar()


def test_sala_admite_hasta_16_jugadores():
    sala = SalaEnLinea(max_jugadores=16, iniciar_hilo=False)
    try:
        entradas = [sala.unirse(f"J{i}") for i in range(16)]
        assert all("token" in e for e in entradas)
        assert sala.unirse("Jugador extra")["error"] == "sala_llena"
    finally:
        sala.cerrar()
