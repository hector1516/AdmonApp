# Historial de cambios — Admon

> App de administración ECCSA (`AdmonApp`). Versión y novedades visibles para
> el usuario en `public/changelog.json` y en el popup 📋 del shell.

## [1.2.0] - 2026-09-28

### Nuevo
- **Botón "Dashboard" con pestañas**: nuevo botón `📊 Dashboard` en el menú
  que abre una página de pestañas (`src/pages/Panel.svelte`, ruta `/panel`)
  con el módulo **Notas** dentro como primera pestaña (antes era página
  propia) y sitio para las próximas funciones. Cada pestaña es una ruta real
  (`/panel`, `/notas`): el enlace se puede compartir, el botón atrás del
  navegador retrocede de pestaña y `/notas` queda como alias que abre el
  Panel con Notas activa (bookmarks y prefetch siguen igual). Para sumar
  funciones nuevas: entrada en `TABS` de `Panel.svelte`, ruta en `App.svelte`
  con `initialTab` y su bloque `{#if}`.
- **MAC del teléfono en Usuarios** (📡): la ficha de usuario tiene un campo
  nuevo para anotar la MAC del celular, que se guarda/relaciona en
  `HUB_NetworkDevices` (la tabla del escáner de Detección de Red, por
  `IdUsuario`) — así se empieza a medir **entradas y salidas de la oficina**.
  El detalle muestra el estado en vivo (🟢 en la oficina / ⚪ fuera), el último
  evento de entrada/salida y la última vez visto en la red; la lista de
  usuarios muestra el badge `📡 MAC`. Upsert sin borrar historia: quitar la
  MAC solo desvincula (`Activo = 0`) porque `HUB_NetworkPresence` y
  `HUB_NetworkState` tienen FK hacia esa fila. Se rechaza con 400 si la MAC ya
  pertenece a otro usuario activo. Endpoints `GET/PUT
  /api/users/{id}/telefono` + `mac_telefono` en `GET /api/users`.
- **Módulo Notas** (📝): tablero de notas del equipo con editor en panel
  (título, contenido, color y 📌 fijar), edición y borrado; cada nota muestra
  su autor y su fecha. Escribe en **`HUB_DashboardNotas`**, la misma tabla que
  lee la pantalla 📌 del Dashboard de la oficina (kiosco, solo lectura): lo que
  se captura en Admon aparece solo en la TV, con las fijas arriba y las 3
  primeras. Endpoints `GET/POST/PUT/DELETE /api/notas` (sin permiso propio,
  para todos los logueados) y página `src/pages/Notas.svelte` con tarjeta en el
  menú y ruta `/notas` (en `_SPA_ROUTES` y en el prefetch offline).
  Migración `0041_dashboard_notas.sql`: crea la tabla si falta (en producción ya
  existía, creada a mano y sin versionar; por eso la base de pruebas no la
  tenía).
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
- **ECCSA IA se salía de la pantalla del teléfono**: `.chat-page` medía
  `100vh` pero vive debajo del banner fijo (que ya resta `--banner-h`), así
  que la página quedaba `100vh + banner`. Ahora usa
  `calc(100dvh - var(--banner-h))` y llena exacto la pantalla visible
  (`src/pages/EccsaIa.svelte`).

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
