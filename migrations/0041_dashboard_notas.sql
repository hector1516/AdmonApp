-- Migración 0041: HUB_DashboardNotas (notas que se ven en el Dashboard de la TV)
-- Fecha: 2026-09-28
-- Descripción: El kiosco (dashboard.ecc-sa.com.mx:8101) LEE esta tabla desde
--              siempre, pero su esquema se había creado a mano en producción y
--              nunca se versionó — por eso la base de pruebas no la tenía.
--              Con IF NOT EXISTS es no-op donde ya existe.
--              El CRUD vive en Admon (módulo /notas, endpoints /api/notas):
--              lo que se captura en Admon aparece solo en la pantalla 📌.
--              Mismo esquema que producción (Id, Titulo, Contenido, Color,
--              Autor, Fija, FechaCreacion, FechaModificado).

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'HUB_DashboardNotas')
BEGIN
    CREATE TABLE HUB_DashboardNotas (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Titulo VARCHAR(200) NOT NULL,
        Contenido NVARCHAR(MAX) NULL,
        Color VARCHAR(20) NULL,
        Autor VARCHAR(100) NULL,
        Fija BIT NULL DEFAULT 0,
        FechaCreacion DATETIME NULL DEFAULT GETDATE(),
        FechaModificado DATETIME NULL DEFAULT GETDATE()
    );
    PRINT 'Tabla HUB_DashboardNotas creada';
END
ELSE
BEGIN
    PRINT 'Tabla HUB_DashboardNotas ya existe';
END
