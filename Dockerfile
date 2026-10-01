# Admon — backend FastAPI (fase 1: solo API).
# El frontend Svelte se integra después (fase 2: build Node + servir dist/).
# No requiere Node/npm: evita el fallo "npm: command not found".
FROM python:3.11-slim

WORKDIR /app

# pymssql (manylinux) no necesita freetds-dev para instalar, pero curl
# sirve para el HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
# Frontend compilado localmente (npm run build) -> servido por FastAPI en "/"
COPY dist/ ./dist/
# Versión del shell común (ECCSA-Shell): la lee GET /api/shell/state para el
# banner. Es un archivo generado por tools/sync_shell.py en la app.
COPY ECCSA_SHELL_VERSION ./ECCSA_SHELL_VERSION
# Logo ECCSA para el encabezado del PDF de cotizaciones (opcional: el builder lo omite si falta)
COPY eccsa_logo.png ./eccsa_logo.png
# Template del formato de Excel (hoja "Calculo") que llena el endpoint
# /api/reportes/excel. Destino sin espacios para simplificar la ruta en Python.
COPY "formatos excel/Formato Cotizaciones.xlsx" ./formatos_excel/FormatoCotizaciones.xlsx

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Proceso único en primer plano (PID 1): si uvicorn cae, Docker lo reinicia.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
