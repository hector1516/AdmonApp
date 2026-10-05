#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Admon · deploy rápido en WebbApps (Linux) — sin reconstruir la imagen.
#
# Qué es: el camino rápido del deploy. Reconstruir la imagen tarda mucho más que
# copiar los archivos, así que este script solo:
#   1. compila el frontend con node dentro de un contenedor descartable,
#   2. copia dist/ y api/ al contenedor `admon` que ya está corriendo,
#   3. reinicia el contenedor (uvicorn corre como PID 1),
#   4. espera a que conteste /health.
#
# Cuándo se usa: cuando el push NO tocó Dockerfile, requirements.txt,
# api/requirements.txt (lo decide .github/workflows/deploy.yml). Si los toca,
# el workflow llama a deploy/rebuild-linux.sh, que reconstruye la imagen.
#
# La diferencia con la versión Windows (deploy/hotsync.sh): esta corre en el
# servidor Debian WebbApps (10.188.141.17), que es donde está la app que usan
# los usuarios. No hay cygpath ni MSYS aquí, y el build se hace en un directorio
# temporal para no dejar node_modules de root en el clon del runner.
#
# Uso:  bash deploy/hotsync-linux.sh [--dry-run]
# Requisitos: docker, y que el contenedor `admon` esté corriendo.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CONTAINER=admon
PORT=8103
HEALTH_URL="http://localhost:${PORT}/health"
NODE_IMAGE="node:20-alpine"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

BUILD_DIR=""
cleanup() {
  [ -n "$BUILD_DIR" ] && [ -d "$BUILD_DIR" ] && rm -rf "$BUILD_DIR" 2>/dev/null || true
}
trap cleanup EXIT

run() {
  if [ "$DRY" = "1" ]; then echo "  [dry-run] $*"; else "$@"; fi
}
say() { echo "[hotsync] $*"; }

# ── 0. Precondiciones ────────────────────────────────────────────────────────
if [ "$DRY" = "0" ]; then
  # Primero: ¿responde docker? Sin esto, un runner sin permisos reporta "el
  # contenedor no está corriendo", que es un diagnóstico FALSO: el problema es
  # el runner, no el contenedor.
  if ! docker ps >/dev/null 2>&1; then
    say "ERROR: 'docker' no responde desde la cuenta $(id -un)."
    say "       Si esto es el runner, el usuario necesita el grupo 'docker':"
    say "       usermod -aG docker <usuario>   (y volver a iniciar sesión)"
    exit 1
  fi
  if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    say "ERROR: el contenedor '$CONTAINER' no está corriendo (docker sí responde)."
    say "       Para levantarlo: sudo /opt/apps/_lib/run_app.sh $CONTAINER && docker start $CONTAINER"
    exit 1
  fi
fi

# ── 1. Compilar el frontend ──────────────────────────────────────────────────
# Se compila DENTRO de un contenedor node: el host no tiene node ni npm, y así
# el clon del runner no se ensucia con un node_modules de root (que después hace
# fallar al `npm ci` siguiente por permisos).
BUILD_DIR="$(mktemp -d /tmp/admon-build.XXXXXX)"
say "1/4 compilando el frontend (${NODE_IMAGE})"
# El contenedor corre con el MIS usuario que el runner (no root): si no, deja
# node_modules y dist propiedad de root dentro de /tmp y el `rm -rf` de limpieza
# falla con "Permission denied" (y `set -e` convierte eso en un fallo falso).
run docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e npm_config_cache=/tmp/.npmcache \
  -v "$ROOT":/src:ro \
  -v "$BUILD_DIR":/app \
  -w /app \
  "$NODE_IMAGE" \
  sh -lc 'cd /src && tar cf - --exclude=node_modules --exclude=.git --exclude=dist . | tar xf - -C /app && cd /app && npm ci --no-audit --no-fund && npm run build'

if [ "$DRY" = "0" ]; then
  # npm run build deja el resultado en /app/dist dentro del contenedor; ese /app
  # es el Build_DIR montado, así que ya está en el host.
  if [ ! -f "$BUILD_DIR/dist/index.html" ]; then
    say "ERROR: el build no produjo dist/index.html (revisa el log de arriba)"
    exit 1
  fi
  say "    dist/ generado ($(find "$BUILD_DIR/dist" -type f | wc -l) archivos)"
fi

# ── 2. Copiar al contenedor ──────────────────────────────────────────────────
say "2/4 copiando dist/ y api/ al contenedor"
run docker cp "$BUILD_DIR/dist/." "$CONTAINER":/app/dist/
# El código de la API es lo que cambia sin rebuild. Se copia todo api/ para que
# un archivo nuevo (p.ej. un módulo de PDF) llegue sin needing un rebuild.
run docker cp "$ROOT/api/." "$CONTAINER":/app/api/
run docker cp "$ROOT/ECCSA_SHELL_VERSION" "$CONTAINER":/app/ECCSA_SHELL_VERSION

# ── 3. Reiniciar ─────────────────────────────────────────────────────────────
say "3/4 reiniciando el contenedor (uvicorn es el PID 1)"
run docker restart "$CONTAINER" >/dev/null

# ── 4. Esperar salud ─────────────────────────────────────────────────────────
say "4/4 esperando salud en ${HEALTH_URL}"
if [ "$DRY" = "1" ]; then
  say "OK · (dry-run) Admon quedaría actualizado sin reconstruir la imagen"
  exit 0
fi

for i in $(seq 1 40); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL" || true)
  if [ "$CODE" = "200" ]; then
    say "OK · Admon actualizado sin reconstruir la imagen (salud en el intento $i)"
    exit 0
  fi
  sleep 2
done

say "ERROR: '$CONTAINER' no respondió en ${HEALTH_URL} después de 80 s"
say "       Diagnóstico: docker logs --tail 50 $CONTAINER"
exit 1