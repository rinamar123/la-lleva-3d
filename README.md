# La Lleva - Juego Tradicional Colombiano

Juego construido con Python y **Pygame (pygame-ce)**. Los jugadores compiten por
evitar ser "la lleva": el objetivo es que el otro jugador sea quien más tiempo
permanezca como la lleva, y gana quien menos tiempo lo sea.

## Características

- Modo 1 jugador contra la computadora (IA con dificultad ajustable)
- Multijugador local (2 jugadores)
- Multijugador en red por sockets (servidor + clientes en `juego_lleva/red/`)
- Física realista: aceleración, inercia y diagonal normalizada (velocidad en píxeles por segundo)
- Muñecos procedimentales animados (cabeza, cuerpo, brazos y piernas con marcha y giro)
- Lleva inicial aleatoria
- Obstáculos: cajas (se deslizan y rebotan) y zonas lentas
- Power-ups: velocidad, escudo y congelar al rival
- Toque por alcance con tropiezo breve y flash de impacto
- Efectos visuales al tocar (anillo + partículas) y al recoger power-ups
- Duración de ronda configurable (30 / 60 / 90 s)
- Ranking de mejores tiempos con persistencia
- Interfaz animada con partículas y transiciones de pantalla
- Notificaciones de eventos durante la partida (toasts)
- Menú navegable por teclado y mouse
- Sonido y música generados proceduralmente con volumen ajustable
- Pausa durante la partida
- Modo ventana / pantalla completa
- Preferencias guardadas en `assets/settings.json`
- Versión para navegador (móvil y escritorio) con controles táctiles

## Cambios y mejoras realizadas

Desarrollo organizado en entregas sobre la rama `desarrollo`. Resumen de lo
implementado:

### Jugabilidad y contenido

- **Física realista**: el movimiento usa *delta time* (velocidad en píxeles por
  segundo) con aceleración, inercia, rozamiento y desaceleración al soltar las
  teclas. La diagonal se normaliza, de modo que moverse en diagonal no es más
  rápido que en línea recta. Cada jugador tiene velocidad (`vx`/`vy`), dirección
  de cara y conserva la inercia al rebotar.
- **Muñecos procedimentales**: los personajes se dibujan con pygame en tiempo
  real (cabeza, pelo, ojos, torso con brillo, brazos y piernas). Caminan con
  marcha animada según su velocidad, se voltean hacia donde corren, dejan
  sombra y rastro de partículas, y quien lleva "la lleva" luce pañuelo rojo
  ondeante y aura pulsante. Sin dependencia de sprites externos.
- **Balance de IA**: la IA persigue a "la lleva" y huye si no la lleva, evitando
  las cajas por repulsión, alejándose de las paredes y con un **tiempo de
  reacción** propio de cada dificultad (Rápida/Normal/Difícil).
- **Colisiones que deslizan**: al chocar con una caja el jugador se desliza
  alrededor de ella corrigiendo el eje de menor penetración; si entra a gran
  velocidad rebota perdiendo energía.
- **Toque por alcance**: el contacto se detecta por distancia entre centros
  (`ALCANCE_TOQUE`) antes de que los cuerpos se solapen, y al recibir la lleva el
  jugador **tropieza** brevemente con un destello de impacto en pantalla.
- **Power-ups**: velocidad (verde), escudo azul que bloquea un toque y
  congelación del rival (cian). Se generan con una frecuencia temporal, envejecen
  y expiran, con efectos y mensajes al recogerlos.
- **Entorno**: cajones de madera con sombra y charcos azules pulsantes que
  ralentizan al jugador.
- **Efectos al tocar**: anillo expansivo y partículas en el punto del contacto,
  audio de toque, pisadas al correr, y transferencia correcta del rol de "la
  lleva".
- **Sonido procedimental**: la música y los efectos se sintetizan en tiempo de
  ejecución con módulos estándar (`array`, `math`), sin `numpy` ni archivos de
  audio externos.

### Arquitectura y calidad de código

- **Separación en capas**: `core` (orquestación), `models` (estado), `views`
  (renderizado), `ui` (interfaz), `servicios` (lógica de negocio), `controles`
  (entrada) e `interfaces` (abstracciones). Las reglas de la ronda, el ranking,
  las colisiones, los power-ups y la síntesis de audio son **servicios
  independientes**, desacoplados de la interfaz.
- **Pruebas unitarias**: suite con **111 pruebas** usando `unittest`
  (puntajes, reglas de la ronda, ranking con persistencia, colisiones y
  deslizamiento, toque por alcance, física del jugador y de la IA, power-ups,
  configuración persistente, síntesis de audio, control táctil y multijugador
  en red).

### Interfaz y experiencia de usuario

- **Navegación por teclado** en el menú (flechas + Enter y atajos 1/2/3) además
  del mouse.
- **Pantalla de nombres** para los jugadores (edición con teclado, TAB para
  cambiar de jugador).
- **Toasts**: notificaciones breves en pantalla durante la partida
  (quién es la lleva, bloqueos, power-ups).
- **Pantallas** de ayuda, countdown, pausa, fin de ronda (con revancha por medio
  de **R**) y ranking con normalización de nombres.
- **Opciones persistentes**: duración de ronda, dificultad, volumen y pantalla
  completa se guardan automáticamente en `assets/settings.json`.

### Versión web (compilación a WebAssembly)

- El juego se compila a WebAssembly con **pygbag** y funciona en el navegador
  del celular sin instalar nada.
- **Bucle asíncrono**: `main.py` detecta el navegador (`emscripten`) y corre un
  bucle cooperativo que cede el control al navegador cada frame
  (`await asyncio.sleep(0)`).
- **Controles táctiles**: `ControladorTactil` dibuja cruces de dirección para
  J1 (izquierda) y J2 (derecha) además de un botón de pausa; aparecen tras el
  primer toque y se fusionan con el teclado físico mediante un proxy de
  `pygame.key.get_pressed()` (`TeclasFusionadas`).
- **Robustez en navegador**: el audio se desactiva si la síntesis falla y el
  ranking tolera errores de escritura, sin romper la partida.
- **Recursos del CDN reparados**: la CDN de pygbag ya no sirve
  `browserfs.min.js` (404) y su cabecera de seguridad (COEP) bloqueaba el
  cargador. Se versionó el recurso en `web/vendor/`, el servidor ya no envía
  COEP y el wheel de pygame-ce para wasm se sirve localmente en `web/cdn/`.
  Hoy todo el runtime (intérprete incluido) se publica local con
  `web/descargar_runtime.py` y la web carga sin internet: si el CDN público
  cae o está bloqueado, antes la página quedaba en negro y ahora muestra un
  aviso con el archivo que falló.
- **Automatización**: `web/compilar_web.py` compila y completa los recursos
  faltantes; `web/probar_web.py` verifica la web compilada con un navegador
  headless (Playwright + Chromium, con modo `--offline`).

### Rendimiento en navegador

- **Resolución reducida**: la web ahora renderiza a **1280×720** en lugar de
  1908×1080 (~2.2× menos píxeles por frame), con el canvas reescalado por el
  navegador a pantalla completa sin cambiar el layout (las posiciones de la UI
  usan constantes relativas).
- **Sin doble limitador de FPS**: el `pygame.time.Clock.tick()` se desactiva en
  el navegador (`_ritmo()`); es el `flip`/`requestAnimationFrame` el que marca
  el ritmo, eliminando tartamudeos del *sleep* emulado.

## Versión Web (navegador y móvil)

El juego se compila a WebAssembly con [pygbag](https://pygbag.github.io/) y se
puede jugar desde el navegador del celular sin instalar nada.

Compilar (genera `juego_lleva/build/web/`; pygbag 0.9.3 deja el build "colgado"
tras escribir los archivos, por eso el script espera a que aparezcan y completa
los recursos locales. La primera vez descarga el runtime de Python para web
—unos 22 MB— a `web/cdn/`, que queda ignorado por git):

```bash
.venv/bin/pip install -r requirements-dev.txt    # pygbag + playwright (test web)
.venv/bin/python web/compilar_web.py
```

Servir y probar (desde la PC o el celular de la misma red):

```bash
.venv/bin/python servidor_web.py juego_lleva/build/web
```

Para exponerlo a internet y jugar desde el celular fuera de la red local
(usa Cloudflare Tunnel; muestra la URL pública al levantar):

```bash
bash web/servir_movil.sh
```

Verificar automáticamente la web compilada (abre Chromium headless, hace clic y
guarda una captura). Con `--offline` lanza el navegador sin resolver hosts
externos, así que falla si el build vuelve a depender de internet:

```bash
.venv/bin/python web/probar_web.py http://localhost:8000/ 30 /tmp/captura.png
.venv/bin/python web/probar_web.py --offline http://localhost:8000/ 30
```

El servidor muestra la IP local para abrir el juego desde el celular
(`http://<ip-pc>:8000/`). Notas:

- El build es autosuficiente: el runtime (intérprete, xterm, manifiesto y wheel
  de pygame-ce) se sirve desde `build/web/cdn/`, así que el celular y una URL
  pública no necesitan internet. Si algo falta, la página muestra un aviso con
  el archivo que falló en vez de quedar en negro.
- En pantalla táctil aparecen cruces de control para J1 (izquierda) y J2
  (derecha) más un botón de pausa. En el escritorio funcionan los controles
  normales.
- La primera vez un toque/clic suele ser necesario para activar el audio.

## Instalación

1. Clonar el repositorio
   ```bash
   git clone https://github.com/Andres-Developer-23/Juego-La-Lleva.git
   cd Juego-La-Lleva
   ```

2. Crear entorno virtual
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. Instalar dependencias
   ```bash
   pip install -r requirements.txt
   # Solo para la versión web (pygbag + playwright):
   pip install -r requirements-dev.txt
   ```

4. Ejecutar el juego (desde la raíz del proyecto)
   ```bash
   python -m juego_lleva
   ```

## Controles

| Acción | Control |
|--------|---------|
| Menú | Flechas + Enter, o 1, 2, 3 (atajos) |
| Moverse (J1) | W A S D |
| Moverse (J2) | Flechas |
| Configurar | Flechas entre opciones, Izq/Der para cambiar |
| Pausar / continuar | P o ESC |
| Volver al menú desde pausa | Q |
| Revancha / menú | ENTER o R / ESC |
| Música | M |
| Pantalla completa | F11 |
| En móvil: moverse | Cruces táctiles (J1 izquierda, J2 derecha) |
| En móvil: pausar | Botón PAUSA (arriba a la derecha) |

## Multijugador en red

Además del local, el proyecto incluye un prototipo de multijugador por
sockets. La lógica de red vive en `juego_lleva/red/` (protocolo, servidor y
cliente desacoplados de la interfaz) y los launchers de la raíz levantan cada
lado:

```bash
# Terminal 1: el servidor
python servidor.py --host 0.0.0.0 --puerto 5555

# Terminales 2 y 3: un cliente por jugador
python cliente.py --host 127.0.0.1 --puerto 5555
```

El servidor asigna el id de cada jugador y retransmite sus posiciones. El
cliente muestra una ventana pygame donde cada jugador se mueve con las flechas.
También se puede iniciar cada componente como módulo:

```bash
python -m juego_lleva.red.servidor --puerto 5555
```

## Multijugador en línea (cada jugador desde su dispositivo)

Además del multijugador local y del prototipo por sockets, el modo **En Línea**
sirve la partida desde un servidor web: **2 a 4 jugadores** se unen desde el
navegador del celular o de la PC, sin instalar nada. La simulación es
autoritativa en el servidor (hilo propio a 30 Hz en `juego_lleva/red/sala.py`);
los clientes solo envían su entrada y leen el snapshot.

```bash
# 1. Compilar una vez la versión web
.venv/bin/python web/compilar_web.py

# 2. Levantar el servidor (sirve la web y la API de la sala)
.venv/bin/python servidor_web.py juego_lleva/build/web --max-jugadores 3

# 3. Abrir http://<ip-local>:8000/ en cada dispositivo y elegir "En Linea"
```

`servidor_web.py` acepta `--puerto` (por defecto 8000) y `--max-jugadores
2|3|4`. En la pantalla de sala cada jugador escribe su nombre y marca **Listo**
(R/ESPACIO); cuando todos están listos empieza `countdown → jugando → fin` y
luego la siguiente ronda. ESC o el botón **Salir** abandonan la sala.

### API de la sala (`/api/sala/*`)

Los cuerpos van en JSON (también se acepta `application/x-www-form-urlencoded`
como defensa):

| Ruta | Cuerpo | Respuesta |
|------|--------|-----------|
| `POST /api/sala/unirse` | `{"nombre":"Ana"}` | `{"token","id","fase","max_jugadores",…}` |
| `POST /api/sala/sync` | `{"token":"…","listo":true,"entrada":{"arriba":true,…}}` | snapshot completo (fase, jugadores, victorias, eventos) |
| `POST /api/sala/salir` | `{"token":"…"}` | `{"ok":true}` |
| `GET /api/sala` | — | estado público: fase, jugadores, victorias |

Errores: `400` cuerpo ilegible, `401` token desconocido, `409` sala llena o
partida en curso, `413` cuerpo mayor de 16 KB.

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/sala/unirse \
  -H 'Content-Type: application/json' -d '{"nombre":"Ana"}' \
  | python -c 'import sys, json; print(json.load(sys.stdin)["token"])')

curl -s http://localhost:8000/api/sala
curl -s -X POST http://localhost:8000/api/sala/sync \
  -H 'Content-Type: application/json' \
  -d "{\"token\":\"$TOKEN\",\"listo\":true,\"entrada\":{\"arriba\":false,\"abajo\":false,\"izquierda\":false,\"derecha\":false}}"
curl -s -X POST http://localhost:8000/api/sala/salir \
  -H 'Content-Type: application/json' -d "{\"token\":\"$TOKEN\"}"
```

## Cómo Jugar

1. Elegir modo (Un Jugador contra la IA o Multijugador local)
2. Ingresar nombres de los jugadores
3. La lleva inicial se elige al azar
4. El jugador con la lleva (rojo) debe tocar al otro
5. Al ser tocado, ese jugador pasa a ser la lleva
6. Recoge power-ups: velocidad (verde), escudo (azul, bloquea un toque) y congelar (cian, inmoviliza al rival)
7. Cuando expira el tiempo, gana quien menos tiempo fue la lleva
8. Los tiempos se registran en el ranking

## Opciones

La pantalla de Opciones (botón del menú o tecla 3) permite configurar:

- **Duración de la ronda**: 30, 60 o 90 segundos
- **Dificultad de la IA**: Fácil, Normal o Difícil
- **Volumen de la música y de los efectos**
- **Pantalla completa** (también con F11)

Las preferencias se guardan automáticamente en `assets/settings.json`.

## Arquitectura

El proyecto sigue una separación en capas que facilita entenderlo y probarlo:

```
Eventos de entrada (teclado / mouse / táctil)
        │
        ▼
core/juego.py  ── orquesta estados (menú, nombres, jugando, pausa…)
        │
        ├── servicios/   → lógica de negocio (reglas de ronda, ranking,
        │                  colisiones, power-ups, puntaje, audio)
        ├── models/      → estado de jugadores y del entorno
        ├── interfaces/  → contratos (abstracciones) de los servicios
        ├── views/       → renderizado (jugadores, entorno, efectos, power-ups)
        ├── ui/          → menús, HUD, toasts
        ├── controles/   → entrada (teclado y control táctil)
        └── red/         → multijugador online (protocolo, cliente, servidor)
```

Las reglas del juego no dependen de la interfaz: se pueden probar de forma
automática con la suite de pruebas sin abrir la ventana.

## Estructura del Proyecto

```
Juego-La-Lleva/
├── juego_lleva/
│   ├── __init__.py      # Paquete real del proyecto (versión y doc)
│   ├── __main__.py      # Permite ejecutar con `python -m juego_lleva`
│   ├── main.py          # Punto de entrada desktop/web
│   ├── red/             # Multijugador en red
│   │   ├── protocolo.py #   Tipos de mensaje y codificación JSON
│   │   ├── servidor.py  #   ServidorMultijugador (sockets + hilos)
│   │   └── cliente.py   #   ClienteMultijugador (solo red, sin UI)
│   ├── core/            # Configuración y orquestación
│   ├── models/          # Modelos de datos
│   ├── views/           # Renderizado
│   ├── ui/              # Interfaz de usuario
│   ├── servicios/       # Lógica de negocio
│   ├── controles/       # Manejo de entrada (teclado y táctil)
│   ├── interfaces/      # Abstracciones
│   ├── tests/           # 111 pruebas unitarias
│   └── assets/          # Fondos (regenerables con generar_assets.py)
├── cliente.py           # Launcher del cliente de red (pygame + red)
├── servidor.py          # Launcher del servidor de red
├── web/                 # Soporte para la versión navegador
│   ├── vendor/          # browserfs.min.js y semillas del runtime (la CDN dio 404)
│   ├── cdn/             # Runtime completo servido localmente (gitignore, ~22 MB)
│   ├── compilar_web.py  # Compila con pygbag y completa recursos
│   ├── descargar_runtime.py  # Descarga el runtime a web/cdn/ (una vez)
│   └── probar_web.py    # Verificación con navegador headless (--offline)
├── servidor_web.py      # Servidor de la versión compilada (sin COEP)
├── requirements.txt     # Dependencias de ejecución (pygame-ce)
└── requirements-dev.txt # Dependencias de desarrollo/web (pygbag, playwright)
```

## Pruebas

Ejecutar la suite de pruebas desde la raíz del proyecto:

```bash
python -m unittest discover -s juego_lleva/tests -t . -p "test_*.py" -v
```

Las **198 pruebas** cubren: puntajes, reglas de la ronda (regla clásica),
ranking con persistencia, colisiones y deslizamiento contra cajas, rebote a
alta velocidad, toque por alcance, física del jugador (inercia, diagonal
normalizada, tropiezo) y de la IA (persecución/huida, reacción), power-ups,
configuración persistente, síntesis de audio, control táctil para la versión
web, el multijugador en red (protocolo de mensajes e integración
cliente-servidor), las **vistas gráficas** (estilos de personaje, estados,
cacheo de superficies y UI a 720p) y el **modo en línea** (sala y fases,
snapshot HTTP con `ThreadingHTTPServer`, bots de extremo a extremo,
controlador con predicción/interpolación, validación de la API y geometría
compartida de botones).

### Regenerar fondos

Los fondos `assets/fondos/campo.png` y `assets/fondos/menu_bg.jpg` se generan
de forma procedural (parque nocturno y plaza con noria):

```bash
SDL_VIDEODRIVER=dummy python juego_lleva/assets/generar_assets.py
```

## Requisitos

- Python 3.12+
- pygame-ce 2.5+

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Ver [LICENSE](LICENSE).

## Versión 3D de escritorio con Ursina

La versión original de Pygame se conserva. Se agregó un cliente 3D independiente
que reutiliza la simulación existente de `juego_lleva/red/simulacion.py` para
mantener movimiento, colisiones, obstáculos, power-ups, transferencia de la
lleva y puntuación.

Instala las dependencias de escritorio y Ursina desde la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-3d.txt
```

Ejecuta la versión 3D:

```powershell
python -m juego_lleva.ursina3d
```

Controles: WASD para moverse en relación con la cámara, mouse para mirar y ESC
para pausar/liberar el mouse. La versión original con menús, ranking, audio,
modo local y modo online sigue disponible con:

```powershell
python -m juego_lleva
```

## Versión web 3D multijugador (Three.js + servidor original)

La carpeta `web3d/` contiene el cliente 3D en primera persona. A diferencia de
una demostración local contra IA, esta versión se conecta a la sala compartida
del proyecto original (`SalaEnLinea` y `SimulacionRonda`). Se conservan las
reglas del juego, la transferencia de la lleva, obstáculos, zonas lentas,
potenciadores, cronómetro y resultado. Cada navegador controla su propio
jugador, tiene cámara individual y ve en su minimapa a todos los participantes.

Para ejecutarla localmente en Windows, desde la raíz del proyecto:

```powershell
python servidor_web.py web3d --puerto 8000 --max-jugadores 4
```

Abre `http://localhost:8000`. Para jugar en la misma red, comparte la dirección
IPv4 del equipo servidor, por ejemplo `http://192.168.1.20:8000`. Los jugadores
escriben sus nombres, entran a la misma sala y todos pulsan **LISTO PARA JUGAR**.
Se necesitan al menos dos jugadores. El servidor permite hasta cuatro.

El cliente y la API deben servirse desde el mismo origen. **GitHub Pages por sí
solo no sirve para este multijugador**, porque solo aloja archivos estáticos y
no ejecuta el servidor Python. Se incluye `render.yaml` como configuración de
referencia para desplegar el servicio Python en un proveedor compatible. El
alojamiento gratuito, si está disponible en el proveedor, puede suspender el
servicio por inactividad y no garantiza disponibilidad permanente.

Three.js se carga desde jsDelivr, así que el navegador necesita Internet para
obtener esa biblioteca. La versión anterior Pygame/Pygbag permanece en `web/`.
La versión de escritorio Ursina sigue siendo un modo 3D local; el multijugador
compartido de esta entrega se realiza mediante el cliente web 3D y la API
existente del proyecto.

### Pruebas

Las funciones puras de conversión de coordenadas y controles de la versión
Ursina se prueban con:

```powershell
python -m unittest juego_lleva.tests.test_desktop3d_logic -v
```

Para la suite original, instala primero `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s juego_lleva/tests -t . -p "test_*.py" -v
```
