"""Fotografía de los usuarios (HUB_UsuariosFotos).

Van en tabla aparte y no en HUB_Users a propósito: HUB_Users se lee en cada
login y en cada listado de la HUB y del kiosco, y meter un binario ahí haría
que todas esas consultas arrastraran la imagen. En HUB_UsuariosFotos solo se
entra cuando se pide la foto (ficha del usuario, avatar de la lista, o la app
futura).

Una fila por usuario (IdUsuario es la PK): volver a subirla REEMPLAZA la foto,
que es lo que se espera de un retrato de empleado. Para el formato se reusa el
mismo criterio que las fotos de los reportes de servicio: lo que se guarda es el
binario tal cual lo subió el cliente, y el content-type va aparte para no
depender de los bytes.
"""

MAX_BYTES = 5 * 1024 * 1024  # 5 MB: de sobra para una foto de celular
TIPOS = ("image/jpeg", "image/png", "image/webp", "image/gif")


def _conn(get_connection):
    return get_connection()


def guardar_foto_usuario(get_connection, id_usuario: int, contenido: bytes,
                         content_type: str, actualizado_por=None) -> dict:
    """Sube o reemplaza la foto del usuario. Devuelve dict con ok/error."""
    if not contenido:
        return {"ok": False, "error": "La imagen llegó vacía."}
    if len(contenido) > MAX_BYTES:
        mb = round(MAX_BYTES / (1024 * 1024))
        return {"ok": False, "error": f"La foto pesa más de {mb} MB. Bájala de tamaño y súbela de nuevo."}
    ct = (content_type or "image/jpeg").split(";")[0].strip().lower()
    if ct not in TIPOS:
        return {"ok": False, "error": "Formato no admitido. Usa JPEG, PNG, WEBP o GIF."}
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "IF EXISTS (SELECT 1 FROM HUB_UsuariosFotos WHERE IdUsuario = %s) "
            "UPDATE HUB_UsuariosFotos SET Archivo = %s, ContentType = %s, BytesArchivo = %s, "
            "FechaSubida = GETDATE(), ActualizadoPor = %s WHERE IdUsuario = %s "
            "ELSE INSERT INTO HUB_UsuariosFotos (IdUsuario, Archivo, ContentType, BytesArchivo, FechaSubida, ActualizadoPor) "
            "VALUES (%s, %s, %s, %s, GETDATE(), %s)",
            (int(id_usuario), contenido, ct, len(contenido),
             int(actualizado_por) if actualizado_por else None, int(id_usuario),
             int(id_usuario), contenido, ct, len(contenido),
             int(actualizado_por) if actualizado_por else None))
        conn.commit()
    except Exception as e:
        return {"ok": False, "error": f"No se pudo guardar la foto: {str(e)[:150]}"}
    finally:
        conn.close()
    return {"ok": True, "bytes": len(contenido), "content_type": ct}


def leer_foto_usuario(get_connection, id_usuario: int):
    """Bytes + content-type de la foto, o None si no tiene."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT Archivo, ContentType FROM HUB_UsuariosFotos WHERE IdUsuario = %s",
                    (int(id_usuario),))
        r = cur.fetchone()
        if not r or not r[0]:
            return None
        return {"bytes": bytes(r[0]), "content_type": r[1] or "image/jpeg"}
    except Exception as e:
        print(f"[foto-usuario] Error leyendo foto de {id_usuario}: {e}")
        return None
    finally:
        conn.close()


def borrar_foto_usuario(get_connection, id_usuario: int) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM HUB_UsuariosFotos WHERE IdUsuario = %s", (int(id_usuario),))
        existed = cur.rowcount > 0
        conn.commit()
    except Exception as e:
        return {"ok": False, "error": f"No se pudo borrar la foto: {str(e)[:150]}"}
    finally:
        conn.close()
    return {"ok": True, "existed": existed}


def listar_fotos(get_connection) -> list:
    """IdUsuario de quienes tienen foto. Lo usa la lista de Usuarios para pintar
    los avatares en una sola consulta, sin traerse los binarios."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT IdUsuario FROM HUB_UsuariosFotos")
        return [int(r[0]) for r in cur.fetchall()]
    except Exception as e:
        print(f"[foto-usuario] Error listando fotos: {e}")
        return []
    finally:
        conn.close()
