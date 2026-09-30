-- Migración 0043: artículo genérico por partida de cotización de materiales
-- Fecha: 2026-09-29
-- Descripción: Campo nuevo en las partidas de las cotizaciones de materiales
--              (tabla Partidas) con el nombre GENÉRICO del artículo, p. ej.
--              "controlador lógico", "disyuntor", "cable de comunicación".
--              Es distinto de los códigos SAT: SAT es la clave fiscal
--              (44101701 / H87) y esto es cómo se llama el artículo en
--              lenguaje de compras. Va en el PDF de la cotización antes del
--              código y antes de la unidad:
--                "Tiempo entrega: 5 Dias Laborales · Controlador lógico ·
--                 SAT: 44101701 · Unidad: H87"
--
-- Por qué una columna en Partidas y no otro sidecar como HUB_PartidasSat:
--   - Es una propiedad de la partida (siempre existe, aunque la partida no
--     tenga códigos SAT resueltos todavía).
--   - El ciclo de vida es el de la partida: se clona con la cotización, se
--     borra con la partida, se edita con el mismo formulario.
--   - Se agrega AL FINAL de la tabla: los SELECT posicionales de HUB
--     (eccsa_db.py) y de Admon no cambian de índices, y todos los INSERT usan
--     lista de columnas explícita, así que nada se rompe.
--
-- Idempotente: COL_LENGTH = NULL solo cuando la columna no existe, por lo que
-- correrla más de una vez no hace nada.

IF COL_LENGTH('dbo.Partidas', 'ArticuloGenerico') IS NULL
    ALTER TABLE dbo.Partidas ADD ArticuloGenerico NVARCHAR(200) NULL;
