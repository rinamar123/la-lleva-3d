# Cambios de la rama `feature/online-fullscreen-mobile`

## Resumen

Esta rama añade y mejora el modo multijugador en línea de **La Lleva**, adapta la versión web a pantallas de escritorio y móviles, y corrige problemas encontrados durante las pruebas: fallos de carga del runtime, movimiento entrecortado y un destello blanco persistente después de los toques.

La partida en línea admite de **2 a 4 jugadores** conectados desde sus propios navegadores. Un servidor Python conserva la autoridad sobre la simulación; cada navegador envía entradas y recibe snapshots del estado.

## Funcionalidades añadidas

### Multijugador en línea

- Servidor web que entrega el juego compilado y expone la API de la sala.
- Gestión de jugadores, nombres, tokens de acceso y capacidad configurable de 2, 3 o 4 participantes.
- Flujo de sala: espera, estado «Listo», cuenta regresiva, partida, fin de ronda y reinicio si quedan participantes suficientes.
- Simulación autoritativa en el servidor, con movimiento, colisiones, obstáculos, power-ups, efectos y puntajes.
- Cliente web asíncrono: usa Fetch en WebAssembly y `urllib` como transporte local de respaldo.
- Controles en línea por WASD, flechas y controles táctiles. El modo local y el prototipo de red por sockets se mantienen.
- Endpoints HTTP para unirse, sincronizar entradas/estado, salir y consultar el estado público de la sala.

### Lanzamiento y compilación web

- `jugar.py` permite levantar el servidor web y el juego con un solo comando, o iniciar solo el servidor con `--solo-web`.
- El launcher y el compilador reconocen los entornos `.venv` y `venv`, y pueden usar el intérprete activo como respaldo.
- El compilador prepara el runtime local para que la página pueda cargar sin depender de un CDN externo; también inyecta un aviso visible si la carga falla.
- `web/probar_web.py` incorpora una comprobación con Chromium y una opción offline para detectar dependencias externas.
- `web/servir_movil.sh` facilita publicar temporalmente el servidor mediante Cloudflare Tunnel.

### Pantalla adaptable y pantalla completa

- El HTML generado normaliza la etiqueta viewport y evita desplazamiento accidental en móviles.
- El canvas conserva su proporción y se escala al mayor tamaño que cabe en el viewport.
- Se añadió un botón de pantalla completa; en navegadores compatibles intenta orientar el dispositivo en horizontal.

## Mejoras de movimiento y efectos

- Se corrigió la predicción local para integrar solo el tiempo transcurrido desde el frame anterior.
- Los rivales se dibujan mediante interpolación temporal de snapshots.
- Las pequeñas diferencias entre la posición predicha y la confirmada por el servidor se corrigen gradualmente para evitar retrocesos bruscos. Las correcciones demasiado grandes se aplican sin suavizado para no ocultar cambios importantes.
- La predicción local respeta el estado congelado del servidor y avanza su reloj incluso en escenas sin obstáculos.
- El flash blanco del toque ahora reduce su duración en cada frame en línea y desaparece en vez de quedar superpuesto.

## Cómo iniciar el modo en línea

Desde la raíz del repositorio, compila la versión web una vez y levanta el servidor:

```bash
./venv/bin/python web/compilar_web.py
./venv/bin/python servidor_web.py juego_lleva/build/web --max-jugadores 3
```

Abre en cada dispositivo la dirección que muestra el servidor, por ejemplo `http://<ip-local>:8000/`. Los dispositivos deben tener acceso al equipo que ejecuta el servidor. En la pantalla del juego, elige **En Línea**, ingresa un nombre y marca **Listo**; la partida comienza cuando al menos dos jugadores estén listos.

También se puede usar el launcher:

```bash
./venv/bin/python jugar.py --solo-web
```

## Pruebas y verificación

- La suite completa ejecutada durante esta rama: **204 pruebas aprobadas**.
- Las pruebas del controlador cubren predicción local, reconciliación visual, interpolación de rivales, estado congelado, límites de pantalla y desaparición del flash de toque.
- El smoke test web se ejecutó con Chromium en modo offline: el canvas inició a 1280×720, sin errores de página ni peticiones externas.
- La API de sala se probó con clientes de prueba para verificar la unión, sincronización, transición de fase y salida.

## Archivos principales

- `juego_lleva/red/sala.py`: ciclo de vida y sincronización de la sala.
- `juego_lleva/red/simulacion.py`: simulación autoritativa de la ronda.
- `juego_lleva/red/cliente_web.py`: transporte HTTP del cliente.
- `juego_lleva/core/controlador_enlinea.py`: flujo de juego online, predicción e interpolación.
- `servidor_web.py`: servidor estático y endpoints de sala.
- `web/compilar_web.py`: compilación, runtime local y ajustes de viewport/fullscreen.
- `jugar.py`: launcher del juego y servidor.

## Alcance del guardado

Este documento describe los cambios de código y documentación de la rama. Los cambios locales de `juego_lleva/assets/ranking.json` y `juego_lleva/assets/settings.json` contienen datos/preferencias del equipo y no forman parte de los commits de la rama.
