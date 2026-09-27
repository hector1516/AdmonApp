# Historial de cambios — Admon

> App de administración ECCSA (`AdmonApp`). Versión y novedades visibles para
> el usuario en `public/changelog.json` y en el popup 📋 del shell.

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
