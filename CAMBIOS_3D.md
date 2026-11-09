# Cambios de la entrega 3D integrada

## Se conserva del proyecto de Andrés

- El juego Pygame original, su arquitectura MVC, menús, ranking y modo local.
- Los modelos y servicios originales de jugadores, obstáculos, zonas lentas,
  potenciadores, colisiones y puntuación.
- La simulación compartida `juego_lleva/red/simulacion.py` y la sala
  `juego_lleva/red/sala.py`, que son la autoridad de la partida multijugador.
- La versión web anterior basada en Pygbag dentro de `web/`.

## Versión 3D de escritorio

- `juego_lleva/ursina3d.py`: escena 3D de escritorio con cámara en primera
  persona y minimapa; utiliza la simulación de las reglas originales. Este modo
  es local y no debe confundirse con el cliente multijugador web.
- `juego_lleva/desktop3d_logic.py`: conversión de coordenadas y entradas
  relativas a cámara.
- `requirements-3d.txt`: dependencias de Ursina junto con las originales.

## Versión web 3D multijugador integrada

- `web3d/`: cliente Three.js en primera persona.
- Cada navegador controla su propio jugador y mantiene su propia cámara.
- Cada minimapa muestra al jugador local, todos los oponentes, los obstáculos
  y quién tiene la lleva.
- El cliente envía entradas a `/api/sala/sync` y recibe snapshots de la partida.
- La simulación, las colisiones, el contacto que transfiere la lleva, los
  obstáculos, los power-ups, el cronómetro y el resultado los calcula el
  servidor original `SalaEnLinea` / `SimulacionRonda`, no una copia simplificada
  dentro del navegador.
- `servidor_web.py` sirve los archivos 3D y la API en el mismo origen.
- `render.yaml` es una configuración de referencia para desplegar el servidor
  Python completo. GitHub Pages por sí solo no puede alojar la API dinámica.

## Validaciones realizadas

- `node --check web3d/game.js`: correcto.
- `python -m compileall -q juego_lleva servidor_web.py`: correcto.
- Pruebas de sala, API HTTP y red: 59/59 correctas.
- Prueba de integración HTTP: dos jugadores se registraron, marcaron listo,
  entraron a la fase de juego y recibieron snapshots con jugadores, obstáculos,
  potenciadores y tiempos de la lleva.
- El endpoint `/api/sala` respondió HTTP 200 y `web3d/index.html` se sirvió
  correctamente por el servidor integrado.

## Validaciones pendientes

No se ha podido hacer una prueba visual real de WebGL, mouse y teclado en un
navegador dentro de este entorno. Tampoco se ha desplegado el servidor en una
cuenta de alojamiento externo. Esas pruebas deben realizarse en Windows y en
el proveedor de alojamiento elegido. La suite completa de Pygame tampoco se
ha ejecutado aquí porque no está instalada la dependencia `pygame-ce`.
