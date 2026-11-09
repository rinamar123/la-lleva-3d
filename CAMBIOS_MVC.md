# Refactorización MVC — Cambios realizados

## Objetivo

Reestructurar el proyecto "La Lleva" para seguir correctamente el patrón **Modelo-Vista-Controlador (MVC)**, mejorando la separación de responsabilidades entre capas.

## Resumen de cambios

- **16 archivos modificados**, **9 archivos nuevos**
- **~233 líneas añadidas**, **~985 líneas eliminadas** (neto: -752 líneas)
- `juego.py`: de **886 → 291 líneas** (reducido un 67%)

---

## Nuevos archivos creados

| Archivo | Responsabilidad |
|---------|----------------|
| `core/renderer.py` | Renderizador centralizado — único punto que ejecuta `pygame.display.flip()` |
| `core/controlador_menu.py` | Input y lógica de menús, nombres, ayuda, ranking, opciones, countdown |
| `core/controlador_partida.py` | Lógica de partida: movimiento, colisiones, power-ups, efectos, partículas |
| `core/controlador_pantallas.py` | Input y lógica de pausa y fin de ronda |
| `models/rect.py` | `Rect` custom sin dependencia de pygame (aisla modelos de pygame) |
| `servicios/efecto_service.py` | Lógica de creación y ciclo de vida de efectos visuales |
| `servicios/particula_service.py` | Ciclo de vida de partículas de rastro (antes en la vista) |
| `ui/acciones.py` | Detección de input para menús y pantallas |
| `views/tactil_view.py` | Renderización del pad táctil (separado del control de input) |

---

## Archivos modificados (cambios principales)

### `core/juego.py`
- **De 886 a 291 líneas** — ahora es un orquestador delgado
- Delega toda la lógica a 3 controladores y el renderer
- Solo maneja: inicialización, eventos globales, estado, y coordinación

### `views/jugador_view.py`
- Eliminada lógica de partículas de rastro (duplicaba `ParticulaService`)
- Eliminado import de `ParticulaService`
- Método `renderizar()` simplificado: solo dibuja, sin gestionar estado

### `views/efecto_view.py`
- Eliminada lógica de creación de efectos (movida a `EfectoService`)
- Solo renderiza efectos que le llegan como parámetro

### `controles/tactil.py`
- Eliminada toda lógica de renderizado (movida a `TactilView`)
- Solo procesa eventos de input táctil

### `ui/interfaz.py`
- Eliminados métodos `obtener_accion_*` (movidos a `AccionesUI`)
- Solo permanece con renderizado de UI

### `models/rect.py`, `models/jugador.py`, `models/obstaculo.py`, `models/power_up.py`, `models/entorno.py`, `interfaces/movible.py`
- Reemplazado `pygame.Rect` por `Rect` custom
- **Modelos completamente libres de pygame**

### `servicios/power_up_service.py`
- Usa `Rect` custom en vez de `pygame.Rect`

### Tests actualizados
- `test_juego.py`: usa controladores en vez de métodos de `Juego`
- `test_efecto_view.py`: usa `EfectoService` directamente
- `test_graficos.py`: usa `ParticulaService` directamente

---

## Separación de responsabilidades (post-refactor)

```
models/         → Lógica de negocio, sin pygame
views/          → Solo renderizado, sin lógica
servicios/      → Lógica pura, sin pygame
ui/             → Detección de input y renderizado de UI
core/           → Orquestación y coordinación
  juego.py        → Orquestador delgado (~291 líneas)
  renderer.py     → Pura vista, cero mutaciones (~100 líneas)
  ctrl_menu.py    → Input de menús (~200 líneas)
  ctrl_partida.py → Toda la lógica de juego (~238 líneas)
  ctrl_pantallas.py → Input de pausa/fin (~70 líneas)
controles/      → Input de dispositivos
interfaces/     → Contratos abstractos
```

## Reglas MVC aplicadas

1. **Renderer**: Solo lee estado y dibuja. Cero mutaciones de estado.
2. **Controladores**: Solo procesan input y lógica. Cero `pygame.draw/blit/display`.
3. **Vistas**: Solo renderizan. Cero lógica de negocio.
4. **Modelos**: Libres de pygame (usan `Rect` custom).
5. **`pygame.display.flip()`**: Un solo punto en `Renderer.flip()`.

## Tests

- **110 tests pasan** (1 fallo pre-existente en `test_fondo_menu_cacheado` por entorno de test)
- Se añadieron tests para `EfectoService` y `ParticulaService`

## Cómo ejecutar

```bash
source venv/bin/activate
python -m juego_lleva
```

## Cómo ejecutar tests

```bash
source venv/bin/activate
python -m pytest juego_lleva/tests/ -v
```
