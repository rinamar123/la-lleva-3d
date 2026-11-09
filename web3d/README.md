# La Lleva 3D — cliente multijugador integrado

Esta versión web 3D usa Three.js para dibujar el escenario en primera persona,
pero **no crea una simulación separada**: se conecta a la API `/api/sala/*` del
proyecto original. El servidor usa `SalaEnLinea` y `SimulacionRonda` del juego
de Andrés para compartir posiciones, reglas, obstáculos, potenciadores,
transferencia de la lleva, cronómetro y resultado.

Cada navegador tiene su propia cámara y minimapa. El servidor envía a cada
cliente el snapshot de todos los jugadores; el punto azul es el propio jugador,
los naranjas son oponentes y el rojo indica quién tiene la lleva.

## Ejecutar localmente en Windows

Desde la carpeta raíz del proyecto, activa el entorno virtual e instala las
dependencias originales:

```bat
python -m pip install -r requirements.txt
python servidor_web.py web3d --puerto 8000 --max-jugadores 4
```

Abre <http://localhost:8000>. Para jugar con otras personas en la misma red,
comparte la dirección IPv4 del equipo que ejecuta el servidor, por ejemplo
`http://192.168.1.20:8000`. Todos deben usar la misma dirección y puerto.

## Cómo iniciar una partida

1. El primer jugador abre la página, escribe su nombre y pulsa **ENTRAR A LA SALA**.
2. Los demás abren la misma dirección y entran con sus nombres.
3. Cuando haya al menos dos personas, cada una pulsa **LISTO PARA JUGAR**.
4. El servidor inicia la cuenta regresiva y ejecuta la ronda compartida.
5. Cada navegador muestra el mismo estado de partida desde su propia cámara y
   actualiza su minimapa con todos los jugadores.

## Publicación en Internet

GitHub Pages solo sirve archivos estáticos; no ejecuta la API Python ni la sala
multijugador. Para jugar por Internet, despliega el proyecto completo como un
servicio Python (por ejemplo, usando el `render.yaml` de la raíz). El cliente y
la API deben servirse desde el mismo servicio/origen. El servicio gratuito de
alojamiento puede dormir por inactividad, según las condiciones del proveedor.

Three.js se carga desde jsDelivr, por lo que se requiere Internet para iniciar
la escena 3D.
