# Publicar La Lleva 3D en Render

El proyecto incluye `render.yaml` para crear un servicio web Python en Render.

## Configuración incluida

- Servicio web Python que escucha en `0.0.0.0` y usa el puerto `PORT` asignado por Render.
- Página del juego servida desde `web3d/`.
- API multijugador alojada en el mismo servicio para que todos los jugadores compartan la misma sala.
- Capacidad configurada: hasta 16 jugadores humanos.
- Ruta de comprobación: `/api/sala`.
- No requiere instalar dependencias externas para el servidor 3D web; usa la biblioteca estándar de Python.

## Publicación

1. Sube el contenido de esta carpeta a un repositorio de GitHub (puedes actualizar el repositorio del proyecto).
2. En Render, crea un **Blueprint** nuevo y conecta ese repositorio.
3. Render detectará `render.yaml`. Confirma la creación del servicio `la-lleva-3d-multijugador`.
4. Espera a que termine el despliegue y abre la URL `https://...onrender.com` que Render asigne.
5. Prueba desde dos dispositivos y, si es posible, desde redes diferentes: entra a la misma URL, escribe nombres distintos y pulsa **Listo para jugar** en ambos.

## Importante sobre el plan gratuito

El servicio gratuito de Render puede entrar en suspensión tras un periodo sin tráfico y tardar un poco en despertar. El estado de la sala vive en memoria: si Render reinicia o suspende el proceso, las salas y partidas activas se pierden. No es un servidor persistente ni una base de datos. Para una demo académica y pruebas iniciales sirve; para uso continuo conviene un servicio siempre activo y almacenamiento/gestión de salas más robustos.

## Ejecución local de comprobación

```bash
python servidor_web.py web3d --puerto 8000 --max-jugadores 16 --sin-abrir
```

Luego abre `http://localhost:8000/`.
