# La Lleva 3D — cliente Ursina para Windows

## Instalación

Desde la carpeta raíz del repositorio, abre PowerShell y ejecuta:

```powershell
py -m venv .venv-ursina
.venv-ursina\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-ursina.txt
python -m juego_lleva.ursina3d
```

El comando anterior inicia el cliente 3D mantenido, que reutiliza la simulación y las reglas del proyecto original. Por compatibilidad, también se puede iniciar con `python -m ursina_game.main`.

## Controles

- WASD: moverse respecto a la cámara.
- Mouse: mirar alrededor.
- ESC: pausar y liberar el mouse.
- En pausa, pulsa CONTINUAR para volver a la partida.

## Funciones disponibles en el cliente Ursina

- Cámara en primera persona.
- Min minimapa con jugadores y obstáculos.
- Configuración de 1 a 8 rivales IA.
- Dificultad fácil, normal y difícil.
- Rondas de 180 segundos.
- Escena de parque 3D con senderos, árboles y bancas.
- Reutiliza la simulación del proyecto para colisiones, obstáculos, power-ups, transferencia de la lleva y puntuación.

## Multijugador

El cliente Ursina de escritorio es actualmente local contra IA. El multijugador compartido existente sigue disponible en la versión web 3D y utiliza el servidor configurado en Render. La creación y unión de salas privadas desde el cliente Ursina aún requiere conectar una API de salas con códigos; no se debe considerar implementada hasta completar y probar esa integración.

La versión Pygame original y la versión web existente se conservan sin reemplazarlas.
