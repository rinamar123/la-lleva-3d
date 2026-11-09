# Plan: Multijugador en línea "La Lleva" (3-4 jugadores, cada uno desde su dispositivo)

## Objetivo
Que el juego se sirva desde un **servidor local** y que **3-4 jugadores** se unan a
la **misma partida**, cada uno desde su propio navegador (celular/PC), sin instalar nada.

## Arquitectura
- **Servidor local autoritativo**: un solo proceso Python sirve el build web (pygbag)
  **y** una API JSON (`/api/sala/*`). Un hilo simula la ronda a **30 Hz fija**
  (`SalaEnLinea._bucle`, `FPS_SIMULACION = 30`) y guarda el estado;
  los clientes solo envían input y leen snapshots.
- **Clientes navegador**: envían su dirección (WASD/flechas/táctil) por HTTP y renderizan
  el estado compartido con las vistas existentes.
- **Reglas con N jugadores**: los servicios ya soportan listas de N jugadores
  (`ColisionService`, `PuntajeService`, `RondaService`); se ajusta la elección de rival
  en "congelar" y las posiciones iniciales.
- El prototipo por sockets de escritorio, el modo local (1 jugador / 2 locales) y el
  ranking local **se conservan intactos**.

## Archivos del servidor
- `juego_lleva/red/simulacion.py` — `SimulacionRonda` (lógica de ronda headless).
- `juego_lleva/red/sala.py` — `SalaEnLinea` (registro de jugadores, fases, hilo 30 Hz,
  snapshot, eventos por cliente).
- `servidor_web.py` — acceso HTTP: endpoints `/api/sala/*` + estático, COI
  `credentialless`, fallback de cuerpo url-encoded.

## Archivos del cliente web/pygbag
- `juego_lleva/red/cliente_web.py` — `ClienteEnLinea` async: `unirse/sincronizar/salir`.
- `juego_lleva/core/controlador_enlinea.py` — `ControladorEnLinea`: bucle de sync de
  fondo, sala de espera/"Listo", countdown, juego y fin en línea.
- `juego_lleva/fuentes.py` — `pygame.font.Font(None, tamano)` (wasm-safe).
- `juego_lleva/core/juego.py` + `main.py` — `procesar_frame_async()` (path async solo en
  línea) y mapo de FINGERDOWN→clic (web).

## Archivos modificados
- `juego_lleva/core/config.py` — `BOTONES_MENU` → 7; `COLOR_JUGADOR_3`/`COLOR_JUGADOR_4`.
- `juego_lleva/core/estado.py` — `EstadoJuego.EN_LINEA`.
- `juego_lleva/core/controlador_menu.py` — acción "en_linea".
- `juego_lleva/ui/interfaz.py` — botón menú, `dibujar_sala()`, indicador de red en HUD.
- `juego_lleva/ui/acciones.py` — hitbox del botón en línea.
- `juego_lleva/views/jugador_view.py` — `ESTILOS` y `_color` para 4 jugadores.
- `README.md` — ✓ instrucciones de uso (sección "Multijugador en línea", endpoints y `curl`).

## Detalle del servidor

### `SimulacionRonda`
- **Resolución web**: al iniciarse la sala se sobreescriben las constantes de clase
  `Config.ANCHO_PANTALLA=1280`, `Config.ALTO_PANTALLA=720` para que coincida con los
  clientes navegador (el proceso servidor es una PC normal). Documentado en el módulo.
- Crea N `JugadorHumano` con `teclas` neutras.
- Spawns distribuidos:
  - 2: (300,360), (980,360)
  - 3: (300,200), (640,560), (980,200)
  - 4: (300,200), (980,200), (300,580), (980,580)
- `paso(dt)` — mismo flujo que `ControladorPartida` pero sin pygame:
  1. `entradas[id]` → proxy `__getitem__` que devuelve el estado del botón para el
     código del `teclas` propio (replica de `pygame.key.get_pressed()[codigo]`).
  2. Actualizar `efectos_activos` (velocidad/congelar); saltar movimiento si congelado.
  3. Zona lenta → `mover()`.
  4. Resolver colisiones con obstáculos (`resolver_obstaculo`).
  5. Colisiones jugador-jugador (`detectar_colisiones`): transferencia de la lleva /
     escudo / separación.
  6. Power-ups: frecuencia, recolección, rival aleatorio para "congelar".
  7. Temporizador de ronda → fin; ganador = menos tiempo con la lleva.
- Registra `eventos` con `seq` creciente (toque, escudo, power-ups, fin).

### `SalaEnLinea`
- `max_jugadores` por defecto 3 (flag `--max-jugadores 2|3|4`).
- Alta con `nombre` + `token` (`secrets.token_hex(16)`). Nombres duplicados → sufijo.
- Fases: `esperando → (todos listos) countdown 3s → jugando → fin 10s → reinicio
  automático si siguen ≥2`. Con <2 jugadores vuelve a `esperando`.
- Tolerancia de reconexión: tras `TIMEOUT_DESCONEXION = 8.0` s sin actividad, expulsión.
  Desconexión en `jugando` con <2 jugadores → la ronda se aborta.
- Hilo de simulación a 30 Hz (basado en `time.monotonic()`), independiente de los clientes.
- Todo el estado compartido se serializa bajo un `threading.RLock` único.
- `sincronizar(token, entrada) → snapshot`.

### Snapshot (JSON real servido)
```json
{
  "tipo": "estado_partida",
  "fase": "esperando|countdown|jugando|fin",
  "mi_id": 0,
  "cuenta_regresiva": 2.4,
  "jugadores_online": 3,
  "max_jugadores": 3,
  "listos": {"0": true, "1": false},
  "victorias": {"0": 1, "1": 2},
  "duracion_ronda": 60,
  "tiempo_ronda": 12.5,
  "jugadores": [{
    "id": 0, "nombre": "Ana",
    "x": 120.5, "y": 340.0, "vx": 0.0, "vy": 0.0,
    "es_lleva": true, "direccion_cara": 1, "velocidad_abs": 0.0,
    "escudo": false, "congelado": 0.0, "tropezando": 0.0, "factor_velocidad": 1.0,
    "listo": false
  }],
  "obstaculos": [{"x": 200, "y": 300, "tipo": "caja"}],
  "power_ups": [{"x": 500, "y": 200, "tipo": "velocidad", "vida": 6.0}],
  "tiempos_lleva": {"0": 5.0, "1": 0.0},
  "efectos_activos": {"1": {"congelar": 2.3}},
  "eventos": [{"seq": 12, "tipo": "toque", "x": 400, "y": 300, "a": 0, "b": 2}],
  "ganador": null
}
```
No hay `seq_tick` en el snapshot; la coherencia la da el servidor y los `seq` de eventos.

## Detalle de la API (`servidor_web.py`)
- `POST /api/sala/unirse` `{"nombre":"Ana"}` → `{"token","id","fase","max_jugadores",...}`.
- `POST /api/sala/sync` `{"token","entrada":{"arriba":..,"abajo":..,"izquierda":..,"derecha":..}}`
  → snapshot.
- `POST /api/sala/salir` `{"token"}`.
- `GET /api/sala` → estado público leído bajo el lock (`estado_publico()`): fase,
  jugadores conectados, listos y victorias.
- El handler acepta `application/json` (primario) y, como defensa, deduce `parse_qs`
  si el cuerpo viene url-encoded.
- **Validación de entradas**: `400` si falta `Content-Length` o el cuerpo no es
  legible/campos con tipos incorrectos (`campo_texto`, `campo_token`), `413` si el
  cuerpo supera `MAX_CUERPO = 16 KB`, `409` si la sala está llena o la partida ya
  comenzó, `401` con token desconocido; límite de tasa por token
  (`MAX_SYNC_POR_SEGUNDO`).
- COI (`Cross-Origin-Opener-Policy: credentialless`) para que pygbag cargue sin
  correos aislados. Sigue sirviendo estático e imprime la IP local.

## Detalle del cliente web

### `cliente_web.py` — transporte real (NO usar `pygbag.support`)
- `pygbag.support` **no viaja dentro del build wasm** (`ModuleNotFoundError` en el
  navegador); el glue `RequestHandler` solo existe en el entorno de escritorio.
- Implementación actual: un puente JS propio definido una sola vez
  (`_instalar_fetch_js` → `window.lallevaPost`), que hace `fetch` y vuelca el resultado
  en un objeto JS plano (`window.pglalleva = {done, error, text}`); Python
  (`_post_wasm`) lo **sondea con `asyncio.sleep(0)`** hasta `done`. Sin generadores
  `jsiter` (pygbag devuelve `'undefined'` en lugar de esperar la promesa).
- **Pitfall pygbag**: las propiedades JS que empiezan por `__` no se leen desde Python
  (dan `None`); por eso el objeto se llama `pglalleva` y no `__lalleva`.
- Escritorio/tests: fallback `urllib` de la stdlib (misma interfaz), de modo que la
  suite no depende del navegador. El cuerpo va serializado en JSON de verdad: si se
  mandara url-encoded, la sala recibiría `listo` como texto y `entrada` como cadena,
  los descartaría y la ronda nunca empezaría.
- Peticiones **secuenciales** (el estado `pglalleva` no tolera concurrencia): el bucle
  de sync espera cada respuesta antes de la siguiente.

### `controlador_enlinea.py`
- Entrada propia: WASD + flechas + táctil → `{arriba,abajo,izquierda,derecha}`.
- `_bucle_sync`: tarea asyncio a `PERIODO_SYNC = 1/30` s que envía `(entrada, listo)` y
  aplica cada snapshot; errores seguidos → toast "Reconectando…" y al cabo de
  `_ERRORES_MAX` → "Conexion perdida con la sala" y vuelta al menú.
- Aplicar snapshot reutilizando objetos:
  - `jugadores` = objetos `JugadorHumano` **mutados in-place** (no recreados);
    `jugadores_views` persistentes.
  - `entorno.obstaculos`, `power_ups`, `puntaje_service.tiempos_lleva`,
    `efectos_activos`, `tiempo_ronda`, `duracion_ronda`, `victorias` seteados.
  - Eventos `seq` nuevos → feedback local (audio, `toque_flash`, efectos, toasts).
- **Predicción del jugador propio** (`_predecir_jugador_local`, `_sim_local`): replica
  la física real del servidor (`mover_con_fisica`: impulso/inercia, zonas lentas, cajas
  y límites de pantalla) desde el estado autoritativo del último snapshot + la entrada
  local; en cada snapshot la simulación se re-basifica (`_aplicar_datos_jugador`).
- **Interpolación de rivales**: se guardan `_prev/_cur` con marcas de tiempo y se
  interpola linealmente entre el último y el penúltimo snapshot.
- Fases: `esperando` → `dibujar_sala()` (lista, "X de Y", botón "Listo");
  `countdown` → `renderer.pantalla_countdown`; `fin` → `pantalla_fin_ronda`
  ("La siguiente ronda comienza pronto...", ESC salir).
- HUD con **indicador de red** (verde = snapshot reciente, rojo = sin servidor).

### Boot e input en wasm (pitos descubiertos)
- `pygame.font.SysFont` **cuelga el arranque** en wasm (llama a `fc-list`/cache de
  fuentes sin resultado). Solución `juego_lleva/fuentes.py`: `pygame.font.Font(None, n)`.
- pygbag entrega los clics como eventos SDL `FINGERDOWN`; en `juego.py._capturar_entrada`
  (solo `config.PLATAFORMA_WEB`) cada FINGERDOWN se traduce a `click_realizado` y
  `mouse_pos` escalado por las dimensiones lógicas.
- **Limitación headless**: en Chrome/Playwright headless los eventos JS (puntero/teclado)
  se disparan (listeners `window`) pero **no llegan a `pygame.event.get()`** dentro del
  wasm; en navegador real el input funciona con normalidad. La verificación final del
  flujo es, por tanto, **manual en navegador real**.

## Fases e implementación (estado actual: Fases A/B/C/D ✓)
- **A — Núcleo servidor** ✓ `simulacion.py` + `sala.py` + `test_sala.py`.
- **B — HTTP** ✓ API + `test_sala_http.py` + `test_bots.py`; verificado con `curl`.
- **C — Cliente web** ✓ transporte wasm, controladores, menú, sala, estilos 4 jugadores,
  `main.py` async. Compila y **se juega** de extremo a extremo: probado headless el
  ciclo `unirse → sync (200, JSON válido) → salir` y en navegador real con 2 ventanas
  (countdown → partida → ambos jugando).
- **D — Docs** ✓ `README.md` (cómo levantar, jugar con N dispositivos, endpoints
  `/api/*` con `curl`) y este plan actualizado.

## Tuning de latencia (trabajo en curso)
Síntoma reportado: **mi personaje responde tarde + temblor/jitter constante** (aunque la
predicción ya mueve al jugador propio al instante).
- Causa probable: el **re-base por snapshot** — cada snapshot llega con estado del
  servidor rezagado ~1 tick (33 ms) + RTT, y re-basificar la simulación propia hacia
  ese estado "más viejo" produce un pequeño retroceso/saltido periódico (snapback) que
  se percibe como jitter y como retardo en la reacción.
- Líneas de ataque candidatas:
  1. **Reconciliación**: el cliente guarda un pequeño historial de `(entrada, t)` y el
     servidor confirma por jugador el estado aplicado+su instante; al recibir un snapshot
     se re-expone el historial desde ese instante hasta "ahora" para continuar sin
     saltos (predicción + reconciliación estándar).
  2. Verificar que `_t_pred` se re-basifica contra el instante del servidor y no el de
     llegada; si el servidor enviara su reloj (relativo a la ronda, `tiempo_ronda`), el
     cliente puede anclar la réplica sin estimar RTT.
  3. Subir `FPS_SIMULACION` a 60 (más caro pero más suave) — evaluar solo si 1 no basta.
- Nota: en la prueba en la misma máquina el RTT HTTP es mínimo; el jitter observado
  apunta a la re-base (1), no a la red.

## Build y verificación manual
1. `venv/bin/pip install -r requirements-dev.txt` (pygbag + playwright).
2. `venv/bin/python web/compilar_web.py` (los módulos nuevos de `red/` se incluyen solos).
3. `venv/bin/python servidor_web.py juego_lleva/build/web --max-jugadores 3`
4. Abrir la URL (IP local en el banner) en 3-4 ventanas/dispositivos, unirse y jugar.
5. Smoke de carga con `venv/bin/python web/probar_web.py http://localhost:8000/ 30 /tmp/cap.png`.

## Tests (estilo `unittest` del proyecto) — 198 OK
- `test_sala.py`: límite de N jugadores, tokens, entrada-salida, expulsión por
  inactividad; `paso(dt)` mueve según input; zona lenta; obstáculos; toque transfiere
  la lleva y registra tiempo; escudo; power-ups; countdown→jugando→fin→ganador;
  reinicio; desconexión; snapshot con las claves; `seq` de eventos que no vuelve a
  cero entre rondas; `estado_publico()` bajo lock; contador de resolución web
  (salas solapadas).
- `test_sala_http.py`: `ThreadingHTTPServer` en puerto efímero + `urllib`
  (unirse/sync/salir, 401 con token inválido) — sin navegador; validación de
  cuerpos (`400`, `413`, campos repetidos) y sala llena `409`.
- `test_bots.py`: harness que simula N clientes virtuales a través de la sala para
  recorrer countdown→jugando→fin→siguiente ronda de extremo a extremo.
- `test_controlador_enlinea.py`: cliente simulado mutable; `_predecir_jugador_local`
  (responde a la entrada entre snapshots, respeta el límite de pantalla), `detener()`
  que envía la salida con el token intacto, poda de `_prev/_cur`, indicador de red y
  geometría compartida entre `dibujar_sala`/`detectar_sala`.
- `test_url_sala.py` / `test_juego.py`: toasts presentados en `Renderer.flip()`,
  toque web escalado por las dimensiones lógicas.
- Verificación: `venv/bin/python -m unittest discover -s juego_lleva/tests -q`.

## Revisión posterior (críticos e importantes)

Dos tandas de correcciones sobre el trabajo sin commitear, cada una con sus tests.

**Críticos**
1. **Toque en la web mal escalado** (`core/juego.py`): multiplicaba por `ANCHO`/`ALTO`,
   que no existen en `Config`; ahora usa `ANCHO_PANTALLA`/`ALTO_PANTALLA`.
2. **Toasts fuera de pantalla** (`core/renderer.py`): se dibujaban en
   `_finalizar_frame`, es decir antes de presentar el frame; ahora lo hace
   `Renderer.flip()` y `_finalizar_frame` solo dibuja el fundido.
3. **`detener()` borraba el token antes de avisar a la sala**
   (`core/controlador_enlinea.py`): crea la tarea `salir()` con el token intacto y
   limpia en `_olvidar_credenciales` vía `add_done_callback`; un segundo `salir()`
   responde `token_invalido` en vez de tumbar la sala.
4. **`seq` de eventos volvía a 0** en la ronda siguiente: contador persistente en
   `SalaEnLinea._seq_evento` (sincronizado con `SimulacionRonda.seq_inicial`) y
   `try/except` + `traceback` en `_bucle` para que un error de `_tick` no mate el hilo.
5. **Entradas HTTP sin validar** (`servidor_web.py`): `CuerpoInvalido`,
   `MAX_CUERPO = 16 KB`, `400` (cuerpo ilegible / campo con tipo incorrecto), `409`
   (sala llena), `413`; `campo_texto`/`campo_token`.
6. **`estado_publico()` leído sin lock** → ahora bajo `RLock`; `_snapshot` reasigna
   `estado["jugadores"]` desde los conectados tras `estado.update(sim.estado_red())`.

**Importantes**
- **Geometría compartida**: `rects_sala()` alimenta a `dibujar_sala` y
  `detectar_sala`; `_dentro_boton` semiabierto (dos botones contiguos no comparten
  píxel); alto de botón de menú 44 px; fila de estado de la sala en y=440 dentro del
  panel; nombre/estela con `Config.color_jugador(id)` para los 4 jugadores.
- **Ciclo de vida**: poda de `_prev/_cur` al desconectar; contador de usos en
  `aplicar_resolucion_web`/`restaurar_resolucion` para que dos salas solapadas no dejen
  `Config` a medias; `SalaEnLinea.cerrar()` solo restaura si el hilo terminó;
  `_interrumpir` marca `_detenido = True`.
- **HUD**: indicador de red en y=110, fuera de `zona_pausa`.
- **Tests huecos completados**: `test_snapshot_sala_maneja_mouse_pos` (sí dibuja con
  mouse), bucle final de `test_bots.py` (fases + snapshot coherente) y tests nuevos de
  geometría de botones.

## Notas / fuera de alcance
- No se usa WebSocket (riesgo alto en pygbag; se mantiene HTTP autoritativo).
- Opcionales futuros (no en este alcance): espectadores sobre el máximo, persistencia
  de nicknames en localStorage, modo salas múltiples con código, reconciliación completa
  de predicción propia (ver "Tuning de latencia").