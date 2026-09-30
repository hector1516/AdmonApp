-- Migración 0044: artículo genérico en el índice local de claves SAT
-- Fecha: 2026-09-29
-- Descripción: HUB_SatArticulos es el catálogo auto-alimentado de claves SAT
--              (índice por descripción normalizada). Ahora también guarda el
--              nombre genérico del artículo ("disyuntor", "cable de
--              comunicación") que devuelve la IA o las reglas, para que el
--              botón 🤖 del formulario pueda ofrecerlo en 0 tokens cuando la
--              misma descripción se repite en otra cotización.
--              Si la fila no tiene nombre (las que existían antes de esta
--              migración), el backend hace fallback a las reglas locales.
--
-- Tabla creada por la migración 0037 de HUB (serie HUB), aquí registrada en la
-- serie de Admon como 0044. Nada que HUB o Admon lean hoy cambia de índices:
-- la columna se agrega AL FINAL y los SELECT existentes no la piden.

IF COL_LENGTH('dbo.HUB_SatArticulos', 'ArticuloGenerico') IS NULL
    ALTER TABLE dbo.HUB_SatArticulos ADD ArticuloGenerico NVARCHAR(200) NULL;
