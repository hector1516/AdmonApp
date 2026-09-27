# AGENTS.md — Admon

Admon es una de las **3 apps del ecosistema ECCSA-Shell** (Field, Admon y el
panel de WorkersAdmon). Antes de tocar el diseño, el banner o la versión, leé
esto: casi todo lo que parece "de esta app" en realidad es del shell y está
generado.

## Lo que NO se edita a mano (se genera)

| Archivo | Quién lo pone |
|---|---|
| `src/styles/app.css` | `ECCSA-Shell/tools/build_shell.py` → `sync_shell.py`. **Es un archivo generado.** Edítalo en el repo `ECCSA-Shell` (`tokens.css` / `src/body.css`) y propagá |
| `src/lib/shell.js` | Lo genera `sync_shell.py` con las versiones |
| `src/components/SyncHeader.svelte` | Copia canónica del shell. No la personalices acá |
| `src/components/ActionsBar.svelte` | ídem |
| `src/components/Changelog.svelte` | ídem |
| `src/lib/changelog.js` | ídem |
| `api/lugar.py` | Copia canónica de la regla de ubicación |
| `ECCSA_SHELL_VERSION` / `ECCSA_SHELL_SHA` | Los estampa `sync_shell.py` |

`check.yml` falla el build si edita `src/styles/app.css` a mano (compara el
SHA). No lo esquives: cambialo en el shell.

Ojo: el CSS de Admon está en `src/styles/app.css`, **no** en `src/app.css`
(que es el de Field). Es la variante Tailwind **v3**.

## Lo que SÍ es de Admon

- **El cableado.** Los componentes del shell no importan nada del proyecto: el
  estado, el usuario y el clic entran por props. Eso es lo que se cablea acá.

  ```svelte
  <SyncHeader
      estado={shellEstado()}
      pendientes={$pendingCount}
      usuario={$auth.user.nombre}
      appVersion={APP_VERSION}
      shellVersion={SHELL_VERSION}
      fetcher={shellFetch}      // API: aporta el header Bearer
      onsync={shellSync}
  />
  ```

- **`fetcher` es obligatorio.** `GET /api/shell/state` exige sesión y Admon
  autentica con `Authorization: Bearer`, no con cookie. Sin `fetcher` da 401 y
  el 🏢/🏠 se queda en `📍` sin que se note. (Así estaba antes: el banner
  mostraba siempre 📍.)

- `ActionsBar` no necesita `onnotif` ni `ononline` si no los tenés: un botón
  se pinta solo si su manejador está. Por eso Admon solo expone ⚙️ y 🚪.

- **El popup de novedades** se monta **una vez**, en `App.svelte`, no en cada
  página: si viviera en el header no saltaría al entrar por cualquier ruta.

## La versión tiene UNA sola fuente

`package.json` → `sync_shell.py` lo lee → lo estampa en `src/lib/shell.js` →
lo pintan el banner, el `.version-badge` y el popup de novedades.

El `.version-badge` de `App.svelte` usa `v{APP_VERSION}`, no un número
escrito a mano. (Estaba fijo en "Admon v1.0.1" mientras `package.json` decía
1.0.0: dos números y ya desincronizados.)

Al sacar una versión, en este orden:

1. `package.json`: subí la versión (SemVer).
2. `public/changelog.json`: poné la misma versión y los cambios, en palabras de
   usuario, una línea por cambio.
3. Corré el check: `ECCSA-Shell/tools/check_changelog.py` falla si los dos
   números no coinciden, y avisa si un cambio es tan largo que no entra en un
   iPhone.

## Deploy

`deploy.yml` dispara en cada push a `master` y decide:

- **hotsync** — no cambió nada de la imagen: compila el frontend en un
  contenedor `node:20-alpine` descartable y copia `dist/` y `api/` al
  contenedor que ya corre. Segundos. `deploy/hotsync.sh` (tiene `--dry-run`).
- **rebuild** — cambió `Dockerfile`, `requirements.txt` o `api/requirements.txt`:
  lanza `schtasks /run /tn AdmonBuild`, que reconstruye y hace rollback si falla.

**El ServerVM no tiene node instalado** (ver commit `16bfa49`): por eso el
build del frontend va dentro del contenedor, no en el host.

El backend corre **uvicorn como PID 1**, sin supervisor: para que cargue código
nuevo hay que reiniciar el contenedor, no un programa de supervisor.

## Base de datos

`ECCSA_Admon` con `pymssql`. El archivo de configuración se resuelve por
prioridad: variables de entorno `HUB_DB_*` > `secretos_local.py` > defaults.
Nunca subir `secretos_local.py`.

Las 3 apps comparten BD, passkeys (RP raíz `ecc-sa.com.mx`), push y PDFs, así
que las versiones de `api/requirements.txt` las manda Field. Ver
`ECCSA-Shell/docs/VERSIONES.md`.

## Comandos

```bash
npm ci && npm run dev            # desarrollo
npm run build                    # build de producción (vite → dist/)
python3 -m py_compile api/*.py   # la API
```
