# La Lleva 3D — Ursina para Windows

## Preparación
1. Instala Python 3.10 o 3.11 de 64 bits.
2. Abre una terminal en la carpeta raíz del repositorio.
3. Ejecuta:
   ```powershell
   py -m venv .venv-ursina
   .venv-ursina\Scripts\activate
   pip install -r requirements-ursina.txt
   python -m ursina_game.main
   ```

El cliente Ursina es una aplicación de escritorio Windows. El servidor web existente en Render sigue separado y no se reemplaza por esta aplicación.

## Estado de esta primera entrega
Incluye bienvenida animada generada con geometría 3D, menú, selección de cantidad de IA y dificultad, parque 3D, cámara en primera persona y ronda local de 180 segundos.

El modo multijugador con códigos privados requiere ampliar la API del servidor Render para crear y administrar varias salas. La opción del menú se muestra como próxima integración y todavía no se conecta a la sala web existente. No se debe presentar esta primera entrega como multijugador ya operativo.
