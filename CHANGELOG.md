# Historial de cambios — Admon

> App de administración ECCSA (`AdmonApp`). Versión y novedades visibles para
> el usuario en `public/changelog.json` y en el popup 📋 del shell.

## [1.2.0] - 2026-09-28

### Nuevo
- **ECCSA IA**: chat de una sola conversación (historial continuo en una
  conversación, con Markdown en las respuestas) y acceso directo desde el
  primer botón del Dashboard. `src/pages/EccsaIa.svelte`, `src/pages/Dashboard.svelte`.
- **Kilómetros → detalle de vehículo como página propia**: al tocar un vehículo
  se abre `/kilometros/vehiculo/:id` (deep-link, se puede compartir), en vez
  del popup anterior. Nueva página `src/pages/KilometroVehiculo.svelte`,
  ruta en `src/App.svelte`, tarjetas navegan en `src/pages/Kilometros.svelte`.

### Corregido
- **Hora de los registros de km**: el backend convierte fechas con offset (p. ej.
  `...Z` de UTC) a hora de México antes de guardar —antes las guardaba crudas,
  6 h adelantadas— y rechaza fechas futuras (`api/main.py`,
  `kilometros_registro`). El formulario ya no depende de la zona horaria del
  dispositivo: usa `Intl` con `America/Mexico_City` (`ahoraLocalInput` en
  `Kilometros.svelte` / `KilometroVehiculo.svelte`) y el detalle renderiza la
  fecha guardada sin convertirla (`fmtFecha`).
- **Datos de producción**: 58 registros históricos de `HUB_RegistroKilometros`
  que estaban +6 h se corrigieron con `DATEADD(hour,-6,...)` (respaldo en el
  servidor); verificados contra bitácora y cola de Telegram: 59/59 a 0 h.
- **Endpoint de ECCSA IA roto en producción**: `SELECT ApiKey, Modelo` contra
  `HUB_AiConfig`, pero la columna se llama `Model` → cada mensaje devolvía
  500. También se actualizó el modelo de respaldo a `gemini-3.5-flash-lite`
  (`api/main.py`).
- **Al tocar una tarjeta de vehículo salía "Not Found"**: la ruta
  `/kilometros/vehiculo/:id` tiene 4 segmentos y `App.svelte` leía el id de
  `split('/')[2]` (que era `"vehiculo"`) en vez de `[3]`; el API respondía
  404. Ahora el detalle abre correctamente (`src/App.svelte`).
- Se quitó la leyenda "N requieren servicio (≥9,500 km) / Ninguno requiere
  servicio" de debajo del KPI "Con lectura esta semana" en Kilómetros.

## [1.1.0] - 2026-09-27

### Nuevo
- **Adopta ECCSA-Shell 1.1.0** (`src/styles/app.css` como variante Tailwind
  v3 generada por el shell; ya no se edita a mano).
- **Banner común**: estado de sincronización, usuario, **oficina o remoto** y
  `v{app} · shell {versión}`, con el mismo markup y los mismos textos que Field
  y el panel.
- **Barra de acciones estándar** (⚙️ configuración · 🚪 salir) en el dashboard.
- **Popup de novedades 📋**: la primera vez que se abre una versión nueva
  muestra qué cambió. El texto vive en `public/changelog.json`, así se edita
  sin recompilar.
- **Modo offline**: últimos 10 registros y detalles de cada módulo en
  IndexedDB, con aviso de datos guardados y contactos de cliente offline.
- **Módulo de Remisiones** con códigos SAT CFDI 4.0 (port del HUB).
- **Tickets de OxxoGas**: consulta de saldo, Go Vale, retiro de Telegram y
  borrado de contacto.
- **Deploy**: script de build+deploy y runbook con el patrón de WorkersAdmon.

### Corregido
- **El banner mostraba siempre `📍`**: el `fetch` de `/api/shell/state` no
  mandaba la cabecera `Authorization: Bearer`, daba 401 y caía al
  `desconocido`. Ahora la app le pasa su `fetcher` al componente del shell.
- La versión de la app estaba **escrita a mano** (`Admon v1.0.1`) y ya no
  coincidía con `package.json` (`1.0.0`). Ahora sale de `$lib/shell.js`, que
  `sync_shell.py` genera desde `package.json`.
- Legends: la semana se calculaba en UTC y vaciaba la puntuación semanal.
- `GET /api/usuarios` no existía y el select de técnicos salía siempre vacío.
- Tickets de OxxoGas: la tarjeta de saldo iba apilada y el saldo offline no
  entraba en el prefetch.
- Dependencias alineadas al mandato de versiones de Field.

### Cambiado
- Las dependencias de `api/requirements.txt` se redujeron a lo que se importa
  de verdad (verificado con escaneo AST).
- Se quitó la guía "Cómo ganar ECCSA Points" del módulo Legends.

## [1.0.0]

Versión inicial de Admon.
