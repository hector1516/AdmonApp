#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Admon · deploy completo en WebbApps (Linux) — reconstruye la imagen.
#
# Qué es: el camino "lento" del deploy, para cuando el push tocó un insumo de la
# IMAGEN (Dockerfile, requirements.txt, api/requirements.txt). Reconstruye la
# imagen `hub-admon:latest` y recrea el contenedor con la misma configuración de
# siempre.
#
# De dónde sale la configuración: NO está en este repo, está en el servidor, en
# /opt/apps/admon/app.conf (puertos, red, política de reinicio, app.env), y se
# aplica con /opt/apps/_lib/run_app.sh. Eso es a propósito: el env tiene
# credenciales de la base de datos y no debe viajar en el repo ni quedar en el
# clon del runner.
#
#   sudo /opt/apps/_lib/run_app.sh admon
#
# OJO con APP_AUTO_START=0 en app.conf: deja el contenedor en 'created' y sin
# arrancar (se puso así cuando WebbApps no tenía RAM). Este script lo arranca
# igual al final, porque una app caída no sirve de nada: si la máquina va justa,
# el health check de abajo avisa y el deploy se marca como fallido en vez de
# dejar la app en silencio.
#
# Uso:  bash deploy/rebuild-linux.sh [--dry-run]
# Requisitos: docker + sudo para /opt/apps/_lib/run_app.sh.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CONTAINER=admon
IMAGE=ghcr.io/hector1516/admon:latest
PORT=8103
HEALTH_URL="http://localhost:${PORT}/health"
NODE_IMAGE="node:20-alpine"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_APP=/opt/apps/_lib/run_app.sh

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
run_sudo() {
  if [ "$DRY" = "1" ]; then echo "  [dry-run] sudo $*"; else sudo "$@"; fi
}
say() { echo "[rebuild] $*"; }
die() { say "ERROR: $*" >&2; exit 1; }

# ── 0. Precondiciones ────────────────────────────────────────────────────────
[ "$DRY" = "0" ] && { docker ps >/dev/null 2>&1 || die "'docker' no responde desde $(id -un)"; }
[ -x "$RUN_APP" ] || [ -f "$RUN_APP" ] || die "no existe $RUN_APP (¿estás en WebbApps?)"

# ── 1. Compilar el frontend ──────────────────────────────────────────────────
# El Dockerfile hace `COPY dist/`, o sea que la imagen espera el frontend YA
# compilado: por eso este camino también compila, con node en un contenedor.
BUILD_DIR="$(mktemp -d /tmp/admon-build.XXXXXX)"
say "1/5 compilando el frontend (${NODE_IMAGE})"
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
  [ -f "$BUILD_DIR/dist/index.html" ] || die "el build no produjo dist/index.html"
  say "    dist/ generado ($(find "$BUILD_DIR/dist" -type f | wc -l) archivos)"
fi

# ── 2. Preparar el contexto de docker build ──────────────────────────────────
# Se arma un contexto limpio con dist/ dentro, porque el Dockerfile copia
# `dist/` y el clon del runner no lo tiene (está en .gitignore).
STAGE="$(mktemp -d /tmp/admon-stage.XXXXXX)"
cleanup_stage() {
  [ -n "$STAGE" ] && [ -d "$STAGE" ] && rm -rf "$STAGE" 2>/dev/null || true
}
trap 'cleanup; cleanup_stage' EXIT

say "2/5 armando el contexto de build"
if [ "$DRY" = "1" ]; then
  echo "  [dry-run] copiaría el repo + dist/ a un directorio temporal"
else
  ( cd "$ROOT" && tar cf - --exclude=node_modules --exclude=.git --exclude=dist . ) | tar xf - -C "$STAGE"
  cp -a "$BUILD_DIR/dist" "$STAGE/dist"
  # El Dockerfile copia estos dos archivos; sin ellos el build falla.
  [ -f "$STAGE/ECCSA_SHELL_VERSION" ] || echo "" > "$STAGE/ECCSA_SHELL_VERSION"
  [ -f "$STAGE/eccsa_logo.png" ] || echo "" > "$STAGE/eccsa_logo.png"
fi

# ── 3. Construir la imagen ───────────────────────────────────────────────────
say "3/5 construyendo la imagen ${IMAGE} (esto tarda varios minutos)"
run docker build -t "$IMAGE" "$STAGE"

# ── 3b. Publicar en el registry ──────────────────────────────────────────────
# Arcane (y cualquier otro Docker) detectan actualizaciones comparando el digest
# local contra el del registry. Si esto no corre, la imagen queda solo en este
# servidor y nadie externo se entera de que hay una version nueva.
# Sin GHCR_TOKEN no se rompe nada: se avisa y se sigue.
if [ "${GHCR_TOKEN:-}" != "" ]; then
  say "3b/5 publicando ${IMAGE} en ghcr.io"
  printf '%s' "$GHCR_TOKEN" \
    | docker login ghcr.io -u "${GHCR_USER:-hector1516}" --password-stdin >/dev/null
  run docker push "$IMAGE"
  docker logout ghcr.io >/dev/null 2>&1 || true
else
  say "3b/5 sin GHCR_TOKEN: la imagen queda solo local. Arcane no vera updates."
fi

# ── 4. Despliegue ────────────────────────────────────────────────────────────
# admon es un Project de Arcane (docker.ecc-sa.com.mx) y Arcane es el dueño del
# contenedor: compara el digest local contra el del registry, ve que hay uno
# nuevo, y el operador le da "Update" desde la UI.
#
# Que este script lo recreara lo ROMPERÍA: run_app.sh hace `docker rm admon` y
# el project de Arcane se queda sin contenedor. Por eso solo se recrea si la app
# todavía NO está administrada por Arcane.
COMPOSE_PROJECT=""
if [ "$DRY" = "0" ]; then
  COMPOSE_PROJECT=$(docker inspect \
    -f '{{ index .Config.Labels "com.docker.compose.project" }}' \
    "$CONTAINER" 2>/dev/null || echo "")
fi

if [ -n "$COMPOSE_PROJECT" ]; then
  say "4/5 '$CONTAINER' lo administra Arcane (project=$COMPOSE_PROJECT): no lo recreo."
  say "    La imagen nueva ya está publicada en el registry."
  say "    Para aplicarla: Arcane → Projects → $CONTAINER → Updates → Update."
  say "5/5 no verifico salud: el contenedor sigue corriendo la imagen anterior."
  exit 0
fi

say "4/5 recreando el contenedor con ${RUN_APP} (lee /opt/apps/${CONTAINER}/app.conf)"
run_sudo "$RUN_APP" "$CONTAINER"

# app.conf tiene APP_AUTO_START=0 (la app quedó apagada por falta de RAM cuando
# se migró). Se arranca igual: el health check de abajo es el que avisa si no
# alcanza.
if [ "$DRY" = "0" ]; then
  ESTADO=$(docker inspect -f '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo desconocido)
  if [ "$ESTADO" != "running" ]; then
    say "    el contenedor quedó en '$ESTADO'; lo arranco"
    docker start "$CONTAINER" >/dev/null
  fi
fi

# ── 5. Esperar salud ─────────────────────────────────────────────────────────
say "5/5 esperando salud en ${HEALTH_URL}"
if [ "$DRY" = "1" ]; then
  say "OK · (dry-run) la imagen quedaría reconstruida"
  exit 0
fi

for i in $(seq 1 60); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL" || true)
  if [ "$CODE" = "200" ]; then
    say "OK · imagen reconstruida y contenedor recreado (salud en el intento $i)"
    exit 0
  fi
  sleep 2
done

die "'$CONTAINER' no respondió en ${HEALTH_URL} después de 120 s (diagnóstico: docker logs --tail 50 $CONTAINER)"