#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Admon · deploy rápido (hotsync) — sin reconstruir la imagen.
#
# Qué es: el camino rápido del deploy. Reconstruir la imagen de Admon sigue
# siendo más lento que copiar los archivos, así que este script solo:
#   1. compila el frontend con node DENTRO de un contenedor descartable,
#   2. copia dist/ y api/ al contenedor que ya está corriendo,
#   3. reinicia el contenedor (uvicorn corre como PID 1, sin supervisor).
#
# Cuándo se usa: cuando el push NO tocó Dockerfile, requirements.txt,
# api/requirements.txt (eso lo decide .github/workflows/deploy.yml). Si los
# toca, el workflow llama a deploy/build.ps1, que tiene el rollback.
#
# A diferencia de Field, el Dockerfile de Admon ya hace COPY dist/ (el
# frontend se compila fuera de la imagen), así que este camino es aún más
# trivial: no hay nada que compilar dentro.
#
# Uso:  bash deploy/hotsync.sh [--dry-run]
#
# Requisitos: docker. Nada más — ni node, ni npm en el host.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CONTAINER=admon
IMAGE=node:20-alpine
HEALTH_URL=http://localhost:8103/health
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

run() {
  if [ "$DRY" = "1" ]; then
    echo "  [dry-run] $*"
  else
    "$@"
  fi
}

say() { echo "[hotsync] $*"; }

# ── 0. Precondiciones ────────────────────────────────────────────────────────
if [ "$DRY" = "0" ]; then
  # Primero: ¿responde docker? Sin esta comprobación, un runner cuyo servicio
  # no tiene acceso al pipe de Docker Desktop(reporta "el contenedor no está
  # corriendo", que es un diagnóstico FALSO: el problema es el runner).
  # Pasa cuando el servicio corre como NETWORK SERVICE, que es el default de
  # config.cmd --runasservice.
  if ! docker ps >/dev/null 2>&1; then
    say "ERROR: 'docker' no responde desde esta cuenta."
    say "       Si esto es el runner de un deploy, el servicio corre con una"
    say "       cuenta sin acceso a Docker Desktop. En el ServerVM tiene que"
    say "       estar en la misma cuenta que el runner de hubmail (eccsa), no en"
    say "       NETWORK SERVICE."
    docker ps 2>&1 | head -3 | sed 's/^/       /'
    exit 1
  fi
  if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    say "ERROR: el contenedor '$CONTAINER' no está corriendo (docker sí responde)."
    say "       Para una app caída o sin contenedor, usa el deploy completo:"
    say "       schtasks /run /tn AdmonBuild"
    exit 1
  fi
fi

# ── 1. Compilar el frontend ──────────────────────────────────────────────────
# Mismo node que el de desarrollo. El mount anónimo de node_modules evita
# mezclar las dependencias de Linux con las del host.
say "1/3 compilando el frontend (node:20-alpine, npm ci)"
run docker run --rm \
    -v "$ROOT":/app \
    -v /app/node_modules \
    -w /app \
    "$IMAGE" \
    sh -c 'npm ci && npm run build'

[ -d "$ROOT/dist" ] || { say "ERROR: no se generó dist/"; exit 1; }
say "    dist/ generado ($(find "$ROOT/dist" -type f | wc -l) archivos)"

# ── 2. Copiar al contenedor ──────────────────────────────────────────────────
# api/ también se copia: el gate solo manda aquí cuando requirements.txt NO
# cambió, pero el código Python sí puede haber cambiado, y con esto se publica
# sin reconstruir.
say "2/3 copiando dist/ y api/ al contenedor"
run docker cp "$ROOT/dist/." "$CONTAINER:/app/dist"
run docker cp "$ROOT/api/." "$CONTAINER:/app/api"
# La versión del shell la lee GET /api/shell/state para el banner.
run docker cp "$ROOT/ECCSA_SHELL_VERSION" "$CONTAINER:/app/ECCSA_SHELL_VERSION"

# uvicorn corre como PID 1 (no hay supervisor): reiniciar el contenedor es la
# forma de que cargue el código nuevo.
say "    reiniciando el contenedor (uvicorn es el PID 1)"
run docker restart "$CONTAINER"

# ── 3. Health check ──────────────────────────────────────────────────────────
if [ "$DRY" = "0" ]; then
  say "3/3 esperando salud en $HEALTH_URL"
  ok=0
  for i in $(seq 1 40); do
    if curl -fsS --max-time 3 "$HEALTH_URL" >/dev/null 2>&1; then
      ok=1
      break
    fi
    sleep 1
  done
  if [ "$ok" = "0" ]; then
    say "ERROR: la app no respondió en 40s."
    say "       Puede ser que el push sí tocara la imagen. Reconstruye:"
    say "       powershell -ExecutionPolicy Bypass -File deploy\\build.ps1"
    exit 1
  fi
fi

say "OK · Admon actualizado sin reconstruir la imagen"
