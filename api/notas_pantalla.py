"""
API de la pestaña "Pantalla de la TV" (módulo Notas del Dashboard).

Dos cosas, sin ninguna llamada de ida y vuelta entre apps:

1) Imagen de portada. NO se manda por HTTP al kiosco: se guarda en
   HUB_PantallaImagenes y el snapshotter de la TV la lee de ahí, la copia a
   /data/media/panel/ y la muestra. Las dos apps ya leen esta misma base, así
   que la imagen viaja por donde viaja todo lo demás; no hace falta endpoint
   de subida en el kiosco ni token compartido, y si la TV está apagada la
   imagen sigue ahí cuando vuelve.

   Se guarda la ACTIVA (Activo=1) y las anteriores se desactivan, para poder
   volver a una anterior sin volver a subirla. Hay un índice único por Clave
   donde Activo=1: al subir se desactiva la anterior en la MISMA transacción,
   y si el INSERT falla la anterior sigue activa (la pantalla nunca queda en
   blanco).

2) Control remoto del kiosco (lo que el snapshotter expone en su panel):
   GET  /api/panel/estado   → no pide token
   POST /api/panel/comando  → SÍ pide token (X-Panel-Token)

   Sin token, el comando responde 403 y el panel queda deshabilitado a
   propósito: escribir en la TV exige credencial.
"""
import io
import os

import pymssql

# Secret compartido con el contenedor del Dashboard (C:\\Dashboard\\deploy\\env.local).
# Viene como variable de entorno; NUNCA se hardcodea ni se escribe en el código.
# Sin ella el kiosco devuelve 403 y la app lo reporta en vez de fallar en silencio.
PANEL_TOKEN = os.getenv("HUB_PANEL_TOKEN", "")
PANEL_URL = os.getenv("HUB_PANEL_URL", "http://10.188.141.31:8101")

CLAVE_PORTADA = "PORTADA"

# Tope defensivo: una foto 1920x1080 moderna pesa unos pocos MB; 12 MB deja
# margen sin permitir que alguien suba un video por accidente.
MAX_BYTES = 12 * 1024 * 1024
CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def _conn(get_connection):
    return get_connection()


def _medidas(contenido: bytes):
    """(ancho, alto) reales de la imagen, o (None, None) si Pillow no está.

    Solo informativos: sirven para avisar en la UI que la imagen no mide
    1920x1080 y se vería estirada o recortada en la TV.
    """
    try:
        from PIL import Image

        with Image.open(io.BytesIO(contenido)) as im:
            return im.width, im.height
    except Exception:
        return None, None


def guardar_imagen_pantalla(get_connection, contenido: bytes, content_type: str,
                            titulo: str = None, id_usuario: int = None) -> dict:
    """Deja `contenido` como la imagen activa de la portada de la pantalla."""
    if not contenido:
        return {"ok": False, "error": "La imagen vino vacía."}
    if len(contenido) > MAX_BYTES:
        return {"ok": False, "error": "La imagen pesa más de 12 MB."}
    if (content_type or "").lower() not in CONTENT_TYPES:
        return {"ok": False, "error": "Solo se aceptan JPG, PNG o WEBP."}

    ancho, alto = _medidas(contenido)
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Desactivar la anterior + insertar la nueva, todo o nada.
        cur.execute("UPDATE HUB_PantallaImagenes SET Activo = 0 WHERE Clave = %s", (CLAVE_PORTADA,))
        cur.execute(
            """INSERT INTO HUB_PantallaImagenes
               (Clave, Titulo, Archivo, ContentType, Ancho, Alto, IdUsuario, Activo)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 1)""",
            (CLAVE_PORTADA, (titulo or "").strip() or None, contenido,
             (content_type or "image/jpeg").lower(), ancho, alto, id_usuario),
        )
        conn.commit()
        return {
            "ok": True,
            "ancho": ancho,
            "alto": alto,
            "titulo": (titulo or "").strip(),
            # La TV no recibe la imagen por HTTP: la toma en su próxima vuelta.
            "aviso": None if (ancho, alto) == (1920, 1080) else
                     "La imagen no es 1920x1080; en la TV se va a recortar.",
        }
    except Exception as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)[:300]}
    finally:
        conn.close()


def listar_imagenes_pantalla(get_connection) -> list:
    """Historial de portadas (sin los bytes) para volver a una anterior."""
    conn = get_connection()
    try:
        cur = conn.cursor(as_dict=True)
        cur.execute(
            """SELECT Id, Titulo, Ancho, Alto, FechaSubida, Activo,
                      DATALENGTH(Archivo) AS bytes
               FROM HUB_PantallaImagenes
               WHERE Clave = %s
               ORDER BY Id DESC""",
            (CLAVE_PORTADA,),
        )
        return cur.fetchall()
    finally:
        conn.close()


def restaurar_imagen_pantalla(get_connection, id_imagen: int) -> dict:
    """Deja activa una imagen del historial sin volver a subirla."""
    conn = get_connection()
    try:
        cur = conn.cursor(as_dict=True)
        cur.execute("SELECT Clave FROM HUB_PantallaImagenes WHERE Id = %s", (int(id_imagen),))
        fila = cur.fetchone()
        if not fila or fila["Clave"] != CLAVE_PORTADA:
            return {"ok": False, "error": "Esa imagen no es de esta pantalla."}
        cur.execute("UPDATE HUB_PantallaImagenes SET Activo = 0 WHERE Clave = %s", (CLAVE_PORTADA,))
        cur.execute("UPDATE HUB_PantallaImagenes SET Activo = 1 WHERE Id = %s", (int(id_imagen),))
        conn.commit()
        return {"ok": True, "id": int(id_imagen)}
    except Exception as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)[:300]}
    finally:
        conn.close()


def borrar_imagen_pantalla(get_connection, id_imagen: int) -> dict:
    """Borra una imagen del historial.

    La activa no se puede borrar: mientras exista, la pantalla tiene qué
    mostrar. Para cambiarla hay que subir o restaurar otra.
    """
    conn = get_connection()
    try:
        cur = conn.cursor(as_dict=True)
        cur.execute("SELECT Activo FROM HUB_PantallaImagenes WHERE Id = %s AND Clave = %s",
                    (int(id_imagen), CLAVE_PORTADA))
        fila = cur.fetchone()
        if not fila:
            return {"ok": False, "error": "Esa imagen no existe."}
        if fila["Activo"]:
            return {"ok": False, "error": "No se puede borrar la imagen que está en pantalla."}
        cur.execute("DELETE FROM HUB_PantallaImagenes WHERE Id = %s", (int(id_imagen),))
        conn.commit()
        return {"ok": True, "id": int(id_imagen)}
    except Exception as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)[:300]}
    finally:
        conn.close()
