# Deploy de la app Admon (FastAPI + Svelte)

Runbook de despliegue de `admon` (la PWA en `admon.ecc-sa.com.mx`). Repo: **hector1516/AdmonApp**
(no confundir con `hector1516/Admon`, que es el HUB de Streamlit).

## Topología

- Contenedor `admon` → imagen `hub-admon:latest`, puerto host `8103` → `8000` interno.
- Directorio de build en el ServerVM: **`C:\admon`** (clon de AdmonApp; ahí queda también `build.log`).
- La red es `hub_default` y monta el volumen `hubmail_data:/data`.
- **El contenedor no monta `C:\admon`**: el código entra a la imagen durante el `docker build`.
  Editar archivos dentro del contenedor es un error (ver "Verificar qué está vivo" más abajo).

## Flujo canónico (un comando)

```powershell
# 1. Build + deploy (pull, npm build, docker build, recrear contenedor, health, rollback si falla)
powershell -ExecutionPolicy Bypass -File C:\admon\deploy\build.ps1

# o, una vez registrada la tarea (deploy/register_task.ps1, una sola vez):
schtasks /run /tn AdmonBuild
Get-Content C:\admon\build.log -Wait      # termina con "FIN rc=0" o "FIN rc=1"
```

`build.ps1` hace: `git pull --ff-only` → `npm ci` → `npm run build` → `docker build -t hub-admon:sat01`
→ retag (`rollback`←`latest` anterior, `latest`/`legends`←`sat01`) → recrear el contenedor
**leyendo su config actual con `docker inspect`** (env con credenciales, puertos, binds, red,
restart policy; nunca hardcodeados) → health check en `http://localhost:8103/api/health` →
si falla, rollback automático al contenedor anterior.

## Tags de imagen

| Tag | Significado |
|---|---|
| `hub-admon:sat01` | salida del build actual (destino del `docker build`) |
| `hub-admon:latest` | lo que corre en producción (sigue a `sat01`) |
| `hub-admon:legends` | alias de `latest` (histórico) |
| `hub-admon:rollback` | imagen anterior, para volver atrás |

## Verificar qué está REALMENTE vivo

La app se sirve desde la imagen: backend en `/app/api` y el frontend compilado por Vite en
`/app/dist/assets/index-<hash>.js`.

- **No grepear `api/main.py` para validar cambios de UI**: todo cambio de pantalla vive en
  `src/**` y se compila al bundle. Un `grep` de un texto de UI en `api/main.py` da 0
  **siempre**, desplegado o no: no prueba nada (ya pasó: se creyó que un deploy faltaba).
- Lo válido es el **hash del bundle** y el texto **dentro del bundle**:
  - `GET https://admon.ecc-sa.com.mx/` → `assets/index-<hash>.js`, luego `GET` ese JS y contar.
  - Dentro del contenedor (sin `docker` CLI, vía API de Docker):
    `GET /v1.41/containers/<id>/archive?path=/app/dist/assets` → tar con los nombres de los assets.
- **Nunca `docker cp` dentro del contenedor**: lo desincroniza de su imagen y el siguiente
  swap/recreate lo revierte en silencio.

## Lecciones (no repetir)

1. **`docker stop` puede dar timeout y aplicar el stop igual.** El 2026-09-26 el script abortó en
   ese paso y dejó `admon` *exited* con el nombre tomado: **producción cayó ~2 min**. Por eso
   `build.ps1` verifica `.State.Running` antes de renombrar y aborta con prod intacta si sigue
   corriendo. Rescate en ese caso: `docker rename admon admon_old` + `docker run` desde
   `hub-admon:latest` con la config del anterior.
2. **Un `docker rm/stop` que "falla" puede haberse aplicado**: re-consulta `docker inspect` /
   `docker ps -a` antes de reintentar o harás doble trabajo.
3. **`dist/` está gitignored**: sin `npm run build` en el server, la imagen se construye con el
   bundle viejo (o falla). `build.ps1` lo verifica y aborta si no encuentra `index-*.js`.
4. El daemon puede ir lento: los timeouts del cliente no implican fallo del build. Confirmá con
   `Successfully tagged` en el log y con `docker images`.
5. El contenedor de test (`admon_test`, puerto 8104) usa las **mismas variables de entorno que
   producción** → sus endpoints tocan la BD real. Solo usá GETs de lectura.

## Desarrollo local (este workspace)

El código de la app vive en el clon del workspace: `/workspace/admon` (este repo).
Para levantarla contra la BD de pruebas:

```bash
cd /workspace/admon
npm run build
HUB_DB_DATABASE=ECCSA_Admon_Pruebas uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Commits: **locales hasta que se publiquen en AdmonApp**. No hacer force-push ni tocar
`hector1516/Admon` (el HUB).
