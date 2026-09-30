-- Migración 0045: NSS, Puesto y fotografía en los usuarios
-- Fecha: 2026-09-30
-- Descripción: Tres datos más de cada usuario (HUB_Users), para alimentar
--              módulos futuros (la otra app que se está armando):
--                - NSS     : número de seguridad social. Columna normal, igual
--                            que CurpRfc: quien ya puede editar usuarios lo ve.
--                - Puesto  : "Supervisor de mantenimiento", "Coordinador", …
--                - Foto    : VARBINARY en una tabla APARTE, no en HUB_Users.
--
-- Por qué la foto en tabla aparte: HUB_Users se lee en cada login y en cada
-- listado de la HUB (eccsa_db.py) y también de la app del kiosco; meter un
-- binario ahí haría que todas esas consultas arrastren la imagen. En su tabla
-- solo se entra cuando se pide la foto. Además así la otra app futura la pide
-- sola por (IdUsuario) sin depender de cómo esté HUB_Users.
--
-- Mismo criterio que las fotos de los reportes de servicio (VARBINARY(MAX) y no
-- IMAGE: una foto de celular moderna pasa de los 65 KB de IMAGE).
--
-- Las tres se agregan al FINAL de HUB_Users, así que los SELECT/INSERT con
-- lista explícita de columnas (tanto en Admon como en HUB) no cambian.

IF COL_LENGTH('dbo.HUB_Users', 'NSS') IS NULL
    ALTER TABLE dbo.HUB_Users ADD NSS NVARCHAR(20) NULL;
GO

IF COL_LENGTH('dbo.HUB_Users', 'Puesto') IS NULL
    ALTER TABLE dbo.HUB_Users ADD Puesto NVARCHAR(120) NULL;
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'HUB_UsuariosFotos')
BEGIN
    CREATE TABLE HUB_UsuariosFotos (
        IdUsuario INT NOT NULL PRIMARY KEY,
        -- Bytes de la imagen. VARBINARY(MAX): una foto de celular moderna
        -- (2-5 MB) no cabe en VARBINARY(8000).
        Archivo VARBINARY(MAX) NOT NULL,
        ContentType NVARCHAR(80) NOT NULL DEFAULT 'image/jpeg',
        -- Bytes del archivo tal cual lo subió el usuario, para poder decidir
        -- sin base64 (el base64 pesa 33% más).
        BytesArchivo INT NULL,
        FechaSubida DATETIME NOT NULL DEFAULT GETDATE(),
        ActualizadoPor INT NULL,
        FOREIGN KEY (IdUsuario) REFERENCES HUB_Users(Id),
        FOREIGN KEY (ActualizadoPor) REFERENCES HUB_Users(Id)
    );
    PRINT 'Tabla HUB_UsuariosFotos creada';
END
ELSE
    PRINT 'Tabla HUB_UsuariosFotos ya existe';
GO
