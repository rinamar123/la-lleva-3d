# Assets del juego

Los recursos se generan de forma procedural (no se descargan de internet).

## Fondos

- `fondos/campo.png` - Fondo del campo de juego.
- `fondos/menu_bg.jpg` - Fondo del menú principal.

Se regeneran con:

```bash
SDL_VIDEODRIVER=dummy python juego_lleva/assets/generar_assets.py
```

## Personajes

Los jugadores se dibujan proceduralmente en `views/jugador_view.py` (cabeza,
torso, brazos y piernas animados), por lo que no hay sprites externos.
