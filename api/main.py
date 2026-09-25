from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse, Response
from api.pdf_cotizacion import build_cotizacion_pdf
from api.pdf_reporte import build_service_report_pdf
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
import pymssql
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

app = FastAPI(title="HUB Admon API", version="1.0.0")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

DB_SERVER = os.getenv("HUB_DB_SERVER", "172.26.117.220")
DB_USER = os.getenv("HUB_DB_USER", "sa")
DB_PASSWORD = os.getenv("HUB_DB_PASSWORD", "eyccazo")
DB_DATABASE = os.getenv("HUB_DB_DATABASE", "ECCSA_Admon")


def get_connection():
    conn = pymssql.connect(server=DB_SERVER, user=DB_USER, password=DB_PASSWORD, database=DB_DATABASE, autocommit=True)
    return conn


# --- Helper Functions (usados por IA Tools) ---

def execute_readonly_sql(sql_query: str):
    """Ejecuta SELECT de solo lectura y retorna lista de dicts."""
    try:
        conn = get_connection()
        cursor = conn.cursor(as_dict=True)
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        return [{"Error": str(e)}]


def send_email_with_multiple_pdfs(to_email: str, subject: str, body: str, attachments: list, sender_name: str = "ECCSA", sender_email: str = "sistemas@ecc-sa.com.mx"):
    """Envía email con múltiples adjuntos PDF. Retorna (success, error_msg)."""
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.application import MIMEApplication
        from email.mime.text import MIMEText

        smtp_host = os.getenv("HUB_SMTP_SERVER", "smtp.office365.com")
        smtp_port = int(os.getenv("HUB_SMTP_PORT", "587"))
        smtp_user = os.getenv("HUB_SMTP_USER", "sistemas@ecc-sa.com.mx")
        smtp_pass = os.getenv("HUB_SMTP_PASSWORD", "eyccazo")

        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{smtp_user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain"))

        for pdf_bytes, filename in attachments:
            att = MIMEApplication(pdf_bytes, _subtype="pdf")
            att.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(att)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return True, None
    except Exception as e:
        return False, str(e)


# --- Models ---

class UserLogin(BaseModel):
    email: str = Field(..., description="Usuario con dominio @ecc-ssa.com.mx o @ecc-sa.com.mx")
    password: str = Field(..., description="Contraseña de usuario")


class Token(BaseModel):
    access_token: str
    token_type: str


class UserInfo(BaseModel):
    id: int
    nombre: str
    email: str
    acceso_inventario: bool = False
    acceso_nominas: bool = False
    acceso_cotizaciones: bool = False
    acceso_proveedores: bool = False
    acceso_oc: bool = False
    acceso_calculo: bool = False
    acceso_telegram: bool = False
    acceso_usuarios: bool = False
    acceso_reportes: bool = False
    acceso_registro_reportes: bool = False
    acceso_ia: bool = False
    nickname: str = ""


# --- Auth Dependency ---

def _user_from_token(token: str):
    """Valida el token simple (email|timestamp) contra HUB_Users. Retorna dict o None."""
    try:
        parts = (token or "").split("|")
        if len(parts) < 2:
            return None
        email = parts[0]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Id, Nombre, Email, AccesoInventario, AccesoNominas, AccesoCotizaciones, AccesoProveedores, AccesoOC, AccesoCalculo, AccesoTelegram, AccesoUsuarios, AccesoReportes, AccesoRegistroReportes, AccesoIA, Nickname FROM HUB_Users WHERE LTRIM(RTRIM(Email)) = %s", (email.strip().lower(),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],
                "nombre": row[1],
                "email": row[2],
                # Nickname de Legends: lo usa el Login para sugerir el nombre de la passkey
                "nickname": (row[14] or "").strip() if len(row) > 14 and row[14] else "",
                "acceso_inventario": row[3] == 1,
                "acceso_nominas": row[4] == 1,
                "acceso_cotizaciones": row[5] == 1,
                "acceso_proveedores": row[6] == 1,
                "acceso_oc": row[7] == 1,
                "acceso_calculo": row[8] == 1,
                "acceso_telegram": row[9] == 1,
                "acceso_usuarios": row[10] == 1,
                "acceso_reportes": row[11] == 1,
                "acceso_registro_reportes": row[12] == 1,
                "acceso_ia": row[13] == 1,
            }
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth error: {str(e)}")


def get_current_user(token: str = Depends(oauth2_scheme)):
    user = _user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def _user_from_header_or_query(request: Request):
    """Auth para descargas/iframes: Bearer en header o ?token= en query (como Field)."""
    auth_h = request.headers.get("Authorization", "")
    token = auth_h[7:] if auth_h.startswith("Bearer ") else request.query_params.get("token", "")
    user = _user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


# --- Root / health (sin auth, para Docker HEALTHCHECK y pruebas) ---
# Si existe el frontend compilado (dist/), "/" sirve la SPA; la info JSON
# de la API se mueve a "/api". Sin dist/, "/" sigue devolviendo JSON.

@app.get("/api")
async def api_info():
    return {"message": "HUB Admon API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health")
async def api_health():
    return {"status": "ok"}


# --- Auth Endpoints ---

@app.post("/api/token")
async def login(user: UserLogin):
    """Login with email and password, returns JWT token"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Validate email domain
        valid_domains = ["@ecc-ssa.com.mx", "@ecc-sa.com.mx"]
        valid = any(user.email.endswith(d) for d in valid_domains)
        if not valid:
            raise HTTPException(status_code=400, detail="Email domain not authorized")
        
        cursor.execute("SELECT Id, Nombre, Email, Password, Activo FROM HUB_Users WHERE LTRIM(RTRIM(Email)) = %s", (user.email.strip().lower(),))
        row = cursor.fetchone()
        conn.close()

        if row and row[4] and row[3] == user.password:  # Password plano + Activo, igual que el HUB
            # Create JWT token (email|issued_at)
            import time
            timestamp = int(time.time())
            token = f"{user.email}|{timestamp}"
            return {"access_token": token, "token_type": "bearer"}
        
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")


# --- Auth endpoint compatible con el frontend Svelte (POST /api/auth/login) ---
# Contrato que espera src/lib/stores/auth.ts: { token, user, expiresAt }

class LoginRequest(BaseModel):
    email: str
    password: str


def _build_login_response(email: str, row) -> dict:
    import time
    timestamp = int(time.time())
    token = f"{email}|{timestamp}"
    expires_at = (timestamp + 7 * 24 * 3600) * 1000  # 7 días en ms
    # row: Id, Nombre, Email, Password, Activo, AccesoInventario, AccesoNominas,
    #      AccesoCotizaciones, AccesoProveedores, AccesoOC, AccesoCalculo,
    #      AccesoTelegram, AccesoUsuarios, AccesoReportes, AccesoRegistroReportes,
    #      AccesoIA, Nickname
    b = lambda i: (row[i] == 1) if len(row) > i and row[i] is not None else False
    user = {
        "id": row[0], "nombre": row[1], "email": row[2],
        "acceso_inventario": b(5), "acceso_nominas": b(6),
        "acceso_cotizaciones": b(7), "acceso_proveedores": b(8),
        "acceso_oc": b(9), "acceso_calculo": b(10),
        "acceso_telegram": b(11), "acceso_usuarios": b(12),
        "acceso_reportes": b(13), "acceso_registro_reportes": b(14),
        "acceso_ia": b(15),
        # Para la pantalla de sugerencia de passkey (label = nickname si existe)
        "nickname": (row[16] or "").strip() if len(row) > 16 and row[16] else "",
    }
    return {"token": token, "user": user, "expiresAt": expires_at}


@app.post("/api/auth/login")
async def api_login(body: LoginRequest):
    """Login que usa el frontend Svelte. Valida dominio y password de HUB_Users."""
    try:
        valid_domains = ["@ecc-ssa.com.mx", "@ecc-sa.com.mx"]
        if not any(body.email.endswith(d) for d in valid_domains):
            raise HTTPException(status_code=400, detail="Email domain not authorized")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Id, Nombre, Email, Password, Activo, AccesoInventario, AccesoNominas, AccesoCotizaciones, AccesoProveedores, AccesoOC, AccesoCalculo, AccesoTelegram, AccesoUsuarios, AccesoReportes, AccesoRegistroReportes, AccesoIA, Nickname FROM HUB_Users WHERE LTRIM(RTRIM(Email)) = %s", (body.email.strip().lower(),))
        row = cursor.fetchone()
        conn.close()
        if row and row[4] and row[3] == body.password:
            return _build_login_response(body.email, row)
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")


# --- Cambio de contraseña (igual que Field: actual + nueva) ---

class ChangePasswordRequest(BaseModel):
    actual: str
    nueva: str


@app.post("/api/auth/change-password")
async def api_change_password(body: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    """Cambia el Password en HUB_Users tras verificar el actual. Mínimo 6 caracteres."""
    try:
        if not body.actual or not body.nueva:
            raise HTTPException(status_code=400, detail="Completa los tres campos.")
        if len(body.nueva) < 6:
            raise HTTPException(status_code=400, detail="La nueva contraseña debe tener mínimo 6 caracteres.")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Password, Activo FROM HUB_Users WHERE LTRIM(RTRIM(Email)) = %s",
            (current_user["email"].strip().lower(),),
        )
        row = cursor.fetchone()
        if not row or not row[1]:
            conn.close()
            raise HTTPException(status_code=401, detail="Sesión no válida.")
        if row[0] != body.actual:
            conn.close()
            raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")
        cursor.execute(
            "UPDATE HUB_Users SET Password = %s WHERE LTRIM(RTRIM(Email)) = %s",
            (body.nueva, current_user["email"].strip().lower()),
        )
        conn.close()
        return {"ok": True, "message": "Contraseña actualizada."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- Info del dispositivo (IP vista por el servidor) ---

@app.get("/api/dispositivo/ip")
async def api_device_ip(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        ip = request.client.host if request.client else "?"
    except Exception:
        ip = "?"
    return {"ip": ip}


# --- Push: enviar aviso (solo AccesoUsuarios; usa HUB_PushSubscriptions + VAPID) ---

class PushSendRequest(BaseModel):
    title: str
    body: str
    all: bool = True
    user_ids: List[int] = []


@app.post("/api/push/send")
async def api_push_send(body: PushSendRequest, current_user: dict = Depends(get_current_user)):
    if not current_user.get("acceso_usuarios"):
        raise HTTPException(status_code=403, detail="No access")
    if not body.title.strip() or not body.body.strip():
        raise HTTPException(status_code=400, detail="Escribe título y mensaje.")
    try:
        import json
        from pywebpush import webpush, WebPushException
    except ImportError:
        raise HTTPException(status_code=500, detail="pywebpush no instalado en el servidor.")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # VAPID
        cursor.execute("SELECT VapidPublicKey, VapidPrivateKey FROM HUB_PushConfig WHERE Id = 1")
        vk = cursor.fetchone()
        if not vk or not vk[0] or not vk[1]:
            conn.close()
            raise HTTPException(status_code=500, detail="VAPID no configurado.")
        pub_key, priv_key = vk[0].strip(), vk[1].strip()
        # Destinatarios
        if body.all:
            cursor.execute("SELECT Email FROM HUB_Users WHERE Activo = 1")
            emails = [r[0] for r in cursor.fetchall()]
        else:
            if not body.user_ids:
                conn.close()
                raise HTTPException(status_code=400, detail="Selecciona al menos un usuario o marca Todos.")
            ids = [int(i) for i in body.user_ids]
            placeholders = ",".join(["%s"] * len(ids))
            cursor.execute(f"SELECT Email FROM HUB_Users WHERE Id IN ({placeholders})", tuple(ids))
            emails = [r[0] for r in cursor.fetchall()]
        if not emails:
            conn.close()
            return {"sent": 0}
        eph = ",".join(["%s"] * len(emails))
        cursor.execute(
            f"SELECT Endpoint, P256dhKey, AuthKey FROM HUB_PushSubscriptions WHERE UserEmail IN ({eph})",
            tuple(emails),
        )
        subs = cursor.fetchall()
        payload = json.dumps({"title": body.title.strip(), "body": body.body.strip()})
        sent = 0
        for endpoint, p256dh, auth_key in subs:
            try:
                webpush(
                    subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth_key}},
                    data=payload,
                    vapid_private_key=priv_key,
                    vapid_claims={"sub": "mailto:robot@ecc-sa.com.mx"},
                )
                sent += 1
            except WebPushException as e:
                if e.response is not None and e.response.status_code in (410, 404):
                    try:
                        cursor.execute("DELETE FROM HUB_PushSubscriptions WHERE Endpoint = %s", (endpoint,))
                    except Exception:
                        pass
            except Exception:
                pass
        conn.close()
        return {"sent": sent}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- User Endpoints ---

@app.get("/api/users/me", response_model=UserInfo)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserInfo(**current_user)


@app.get("/api/users", response_model=List[UserInfo])
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users - admin only"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Id, Nombre, Email, AccesoInventario, AccesoNominas, AccesoCotizaciones, AccesoProveedores, AccesoOC, AccesoCalculo, AccesoTelegram, AccesoUsuarios FROM HUB_Users")
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append(UserInfo(
                id=row[0], nombre=row[1], email=row[2],
                acceso_inventario=row[3] == 1,
                acceso_nominas=row[4] == 1,
                acceso_cotizaciones=row[5] == 1,
                acceso_proveedores=row[6] == 1,
                acceso_oc=row[7] == 1,
                acceso_calculo=row[8] == 1,
                acceso_telegram=row[9] == 1,
                acceso_usuarios=row[10] == 1,
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- Detalle / edición de usuario (espejo del Administrador de Usuarios del HUB) ---

# Columnas de HUB_Users administrables (mismo orden que get_all_hub_users del HUB)
_USER_COLS = (
    "Id, Email, Nombre, Password, Activo, FechaIngreso, CurpRfc, "
    "AccesoCotizaciones, AccesoVM, AccesoConfiguracion, AccesoUsuarios, AccesoReportes, "
    "AccesoRegistroReportes, AccesoCotizacionesReportes, AccesoClientes, AccesoRegistroKilometros, "
    "AccesoAutomoviles, AccesoVacaciones, AccesoConfigurarCorreo, AccesoConfigAI, "
    "Notificaciones, AccesoMisVacaciones, AccesoHorasExtras, AccesoMisHorasExtras, AccesoOxxoGas, "
    "AccesoValesOxxoGas, AccesoRegistroTicketOxxoGas, AccesoEdicionBD, AccesoNominas, AccesoInventario, "
    "AccesoCalculo, AccesoProveedores, AccesoOC, AccesoTelegram, AccesoAppConfig, AccesoSolicitarVales, "
    "AccesoAdminVales, AccesoConfigOxxogas, AccesoDeteccionRed, AccesoPdfConfig"
)
# Orden propio (cada columna UNA vez): _user_row_to_dict usa índices fijos
# id=0, email=1, nombre=2, password=3, activo=4, fecha_ingreso=5, curp_rfc=6,
# accesos desde 7 en el orden de `keys`.


def _require_admin(current_user: dict):
    if not current_user.get("acceso_usuarios"):
        raise HTTPException(status_code=403, detail="No access")


def _user_row_to_dict(row) -> dict:
    d = {
        "id": row[0], "email": row[1], "nombre": row[2], "password": row[3],
        "activo": bool(row[4]),
        "fecha_ingreso": str(row[5])[:10] if row[5] else None,
        "curp_rfc": row[6] or "",
    }
    keys = [
        "AccesoCotizaciones", "AccesoVM", "AccesoConfiguracion", "AccesoUsuarios", "AccesoReportes",
        "AccesoRegistroReportes", "AccesoCotizacionesReportes", "AccesoClientes", "AccesoRegistroKilometros",
        "AccesoAutomoviles", "AccesoVacaciones", "AccesoConfigurarCorreo", "AccesoConfigAI",
        "Notificaciones", "AccesoMisVacaciones", "AccesoHorasExtras", "AccesoMisHorasExtras", "AccesoOxxoGas",
        "AccesoValesOxxoGas", "AccesoRegistroTicketOxxoGas", "AccesoEdicionBD", "AccesoNominas", "AccesoInventario",
        "AccesoCalculo", "AccesoProveedores", "AccesoOC", "AccesoTelegram", "AccesoAppConfig",
        "AccesoSolicitarVales", "AccesoAdminVales", "AccesoConfigOxxogas", "AccesoDeteccionRed", "AccesoPdfConfig",
    ]
    for i, k in enumerate(keys):
        v = row[7 + i]
        d[k] = (v == 1) if v is not None else False
    return d


@app.get("/api/users/{user_id:int}")
async def get_user_detail(user_id: int, current_user: dict = Depends(get_current_user)):
    _require_admin(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {_USER_COLS} FROM HUB_Users WHERE Id = %s", (int(user_id),))
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return _user_row_to_dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


class UserUpdateRequest(BaseModel):
    nombre: str = ""
    email: str = ""
    password: str = ""
    activo: bool = True
    fecha_ingreso: Optional[str] = None
    curp_rfc: str = ""
    accesos: Dict[str, bool] = {}


@app.put("/api/users/{user_id:int}")
async def update_user_detail(user_id: int, body: UserUpdateRequest, current_user: dict = Depends(get_current_user)):
    _require_admin(current_user)
    if not body.nombre.strip() or not body.email.strip() or not body.password.strip():
        raise HTTPException(status_code=400, detail="Nombre, correo y contraseña son obligatorios.")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sets = ["Nombre = %s", "Email = %s", "Password = %s", "Activo = %s", "FechaIngreso = %s", "CurpRfc = %s"]
        vals: list = [
            body.nombre.strip(), body.email.strip().lower(), body.password,
            1 if body.activo else 0,
            body.fecha_ingreso or None,
            (body.curp_rfc or "").strip() or None,
        ]
        allowed = [
            "AccesoCotizaciones", "AccesoVM", "AccesoConfiguracion", "AccesoUsuarios", "AccesoReportes",
            "AccesoRegistroReportes", "AccesoCotizacionesReportes", "AccesoClientes", "AccesoRegistroKilometros",
            "AccesoAutomoviles", "AccesoVacaciones", "AccesoConfigurarCorreo", "AccesoConfigAI",
            "Notificaciones", "AccesoMisVacaciones", "AccesoHorasExtras", "AccesoMisHorasExtras", "AccesoOxxoGas",
            "AccesoValesOxxoGas", "AccesoRegistroTicketOxxoGas", "AccesoEdicionBD", "AccesoNominas", "AccesoInventario",
            "AccesoCalculo", "AccesoProveedores", "AccesoOC", "AccesoTelegram", "AccesoAppConfig",
            "AccesoSolicitarVales", "AccesoAdminVales", "AccesoConfigOxxogas", "AccesoDeteccionRed", "AccesoPdfConfig",
        ]
        for k in allowed:
            sets.append(f"{k} = %s")
            vals.append(1 if body.accesos.get(k, False) else 0)
        vals.append(int(user_id))
        cursor.execute(f"UPDATE HUB_Users SET {', '.join(sets)} WHERE Id = %s", tuple(vals))
        conn.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.delete("/api/users/{user_id:int}")
async def delete_user_detail(user_id: int, current_user: dict = Depends(get_current_user)):
    _require_admin(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Email, Nombre FROM HUB_Users WHERE Id = %s", (int(user_id),))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if (row[0] or "").strip().lower() == (current_user.get("email") or "").strip().lower():
            conn.close()
            raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta.")
        try:
            cursor.execute("DELETE FROM HUB_Users WHERE Id = %s", (int(user_id),))
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=400, detail=f"No se pudo eliminar (referencias en otros módulos): {str(e)[:150]}")
        conn.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- Inventory endpoints ---

@app.get("/api/inventory/items")
async def get_inventory_items(current_user: dict = Depends(get_current_user)):
    if not current_user["acceso_inventario"]:
        raise HTTPException(status_code=403, detail="No access")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Id, Marca, Modelo, Descripcion, Cantidad, StockMinimo, Ubicacion, Proveedor, Precio FROM HUB_Inventario")
        rows = cursor.fetchall()
        conn.close()
        items = []
        for row in rows:
            items.append({
                "id": row[0], "marca": row[1], "modelo": row[2], "descripcion": row[3],
                "cantidad": row[4], "stock_minimo": row[5], "ubicacion": row[6],
                "proveedor": row[7], "precio": float(row[8]) if row[8] else 0.0
            })
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/inventory/items/{item_id:int}")
async def get_inventory_item(item_id: int, current_user: dict = Depends(get_current_user)):
    if not current_user["acceso_inventario"]:
        raise HTTPException(status_code=403, detail="No access")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Id, Marca, Modelo, Descripcion, Cantidad, StockMinimo, Ubicacion, Proveedor, Precio FROM HUB_Inventario WHERE Id = %s", (item_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0], "marca": row[1], "modelo": row[2], "descripcion": row[3],
                "cantidad": row[4], "stock_minimo": row[5], "ubicacion": row[6],
                "proveedor": row[7], "precio": float(row[8]) if row[8] else 0.0
            }
        raise HTTPException(status_code=404, detail="Item not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- Cotizaciones de materiales (réplica exacta del módulo HUB) ---
# Tablas: IndiceMateriales (Folio IDENTITY, IdCliente, Contacto, Fecha,
# Descripcion, Autor, Color, Nota) + Partidas (Folio, Partida, Cantidad,
# Descripcion, PrecioCompraUnitario, Factor, Proveedor, TiempoEntregaDias,
# Dolar, Flete). Vista: vw_ResumenCotizaciones. Folio display: CM00001.
# Fórmulas HUB: venta_unit = compra*(1+factor); total_item = venta_unit*cant+flete;
# subtotal = Σ; iva = subtotal*0.16; total = subtotal+iva.
# Color: 0 = enviada, 1 = lista para facturar, 2 = facturada (1 y 2 bloquean edición).

def _require_cotiz(current_user: dict):
    if not current_user.get("acceso_cotizaciones"):
        raise HTTPException(status_code=403, detail="No access")


def _fmt_folio(folio) -> str:
    try:
        return f"CM{int(folio):05d}"
    except Exception:
        return str(folio)


def _fnum(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except Exception:
        return 0.0


def _fstr(v) -> str:
    try:
        return str(v)[:10] if v is not None else ""
    except Exception:
        return ""


def _partida_row_to_dict(folio, row) -> dict:
    # row: Partida, Cantidad, Descripcion, PrecioCompraUnitario, Factor,
    #      Proveedor, TiempoEntregaDias, Dolar, Flete
    compra = _fnum(row[3])
    factor = _fnum(row[4])
    cant = int(row[1] or 0)
    flete = _fnum(row[8])
    venta_unit = compra * (1.0 + factor)
    return {
        "folio": folio, "partida": row[0], "cantidad": cant,
        "descripcion": row[2] or "", "precio_compra": compra, "factor": factor,
        "proveedor": row[5] or "", "tiempo_entrega": int(row[6] or 0),
        "dolar": _fnum(row[7]), "flete": flete,
        "venta_unit": venta_unit, "total_venta": venta_unit * cant + flete,
    }


# ----- Helpers de escritura (sin commit; el llamador hace commit) -----

def _db_get_color(cur, folio) -> Optional[int]:
    cur.execute("SELECT Color FROM IndiceMateriales WHERE Folio = %s", (int(folio),))
    r = cur.fetchone()
    return None if not r else (int(r[0]) if r[0] is not None else 0)


def _db_create_quotation(cur, id_cliente, contacto, descripcion, autor) -> int:
    cur.execute(
        "INSERT INTO IndiceMateriales (IdCliente, Contacto, Fecha, Descripcion, Autor, Color) "
        "VALUES (%s, %s, GETDATE(), %s, %s, 0)",
        (id_cliente.strip().upper(), contacto.strip(), descripcion.strip(), autor),
    )
    cur.execute("SELECT @@IDENTITY")
    r = cur.fetchone()
    if not r or not r[0]:
        raise Exception("No se obtuvo el folio generado.")
    return int(r[0])


def _db_add_partida(cur, folio, cantidad, descripcion, precio_compra, factor, proveedor, tiempo_entrega, dolar, flete) -> int:
    cur.execute("SELECT ISNULL(MAX(Partida), 0) + 1 FROM Partidas WHERE Folio = %s", (int(folio),))
    r = cur.fetchone()
    nxt = int(r[0]) if r and r[0] else 1
    cur.execute(
        "INSERT INTO Partidas (Folio, Partida, Cantidad, Descripcion, PrecioCompraUnitario, Factor, Proveedor, TiempoEntregaDias, Dolar, Flete) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (int(folio), nxt, int(cantidad), descripcion.strip(), float(precio_compra), float(factor),
         (proveedor or "").strip(), int(tiempo_entrega or 0), float(dolar or 0.0), float(flete or 0.0)),
    )
    return nxt


def _db_clone_quotation(cur, folio, autor) -> int:
    cur.execute("SELECT IdCliente, Contacto, Descripcion, Color, Nota FROM IndiceMateriales WHERE Folio = %s", (int(folio),))
    orig = cur.fetchone()
    if not orig:
        raise Exception("Cotización original no encontrada.")
    cur.execute(
        "INSERT INTO IndiceMateriales (IdCliente, Contacto, Fecha, Descripcion, Autor, Color, Nota) "
        "VALUES (%s, %s, GETDATE(), %s, %s, %s, %s)",
        (orig[0], orig[1], orig[2], autor, orig[3], orig[4]),
    )
    cur.execute("SELECT @@IDENTITY")
    r = cur.fetchone()
    if not r or not r[0]:
        raise Exception("No se obtuvo el folio clonado.")
    nuevo = int(r[0])
    cur.execute(
        "SELECT Partida, Cantidad, Descripcion, PrecioCompraUnitario, Factor, Proveedor, TiempoEntregaDias, Dolar, Flete "
        "FROM Partidas WHERE Folio = %s ORDER BY Partida ASC", (int(folio),))
    for p in cur.fetchall():
        cur.execute(
            "INSERT INTO Partidas (Folio, Partida, Cantidad, Descripcion, PrecioCompraUnitario, Factor, Proveedor, TiempoEntregaDias, Dolar, Flete) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (nuevo, p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8]),
        )
    return nuevo


def _validate_partida_input(cantidad, descripcion):
    if int(cantidad or 0) < 1:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0.")
    if not (descripcion or "").strip():
        raise HTTPException(status_code=400, detail="La descripción es obligatoria.")


# ----- Modelos -----

class CotizacionCreate(BaseModel):
    id_cliente: str = ""
    contacto: str = ""
    descripcion: str = ""


class CotizacionUpdate(BaseModel):
    id_cliente: str = ""
    contacto: str = ""
    descripcion: str = ""
    color: int = 0


class CotizacionNota(BaseModel):
    nota: str = ""


class PartidaCreate(BaseModel):
    cantidad: int = 1
    descripcion: str = ""
    precio_compra: float = 0.0
    factor: float = 0.25
    proveedor: str = ""
    tiempo_entrega: int = 1
    dolar: float = 0.0
    flete: float = 0.0


class PartidaUpdate(PartidaCreate):
    pass


class ClienteCreate(BaseModel):
    id_cliente: str = ""
    nombre: str = ""
    dias_pago: int = 30


class ClienteUpdate(BaseModel):
    nombre: str = ""
    dias_pago: int = 30


# ----- Índice / encabezado -----

@app.get("/api/cotizaciones/resumen")
async def cotizaciones_resumen(current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 999 Folio, IdCliente, Cliente, Contacto, Fecha, DescripcionGeneral, "
            "Autor, Estatus, SumaPartidas, FleteCotizacion, Subtotal, IVA, TotalFinal "
            "FROM vw_ResumenCotizaciones ORDER BY Folio DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        return [{
            "folio": r[0], "folio_fmt": _fmt_folio(r[0]),
            "id_cliente": r[1] or "", "cliente": r[2] or "", "contacto": r[3] or "",
            "fecha": _fstr(r[4]), "descripcion": r[5] or "", "autor": r[6] or "",
            "estatus": r[7] or "", "suma_partidas": _fnum(r[8]), "flete": _fnum(r[9]),
            "subtotal": _fnum(r[10]), "iva": _fnum(r[11]), "total": _fnum(r[12]),
        } for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/cotizaciones/{folio:int}")
async def cotizacion_header(folio: int, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT IM.Folio, IM.IdCliente, IM.Contacto, IM.Fecha, IM.Descripcion, IM.Nota, "
            "IM.Autor, IM.Color, C.Cliente AS ClienteNombre "
            "FROM IndiceMateriales IM LEFT JOIN clientes C ON IM.IdCliente = C.IdCliente "
            "WHERE IM.Folio = %s", (int(folio),))
        r = cursor.fetchone()
        conn.close()
        if not r:
            raise HTTPException(status_code=404, detail="Cotización no encontrada")
        return {
            "folio": r[0], "folio_fmt": _fmt_folio(r[0]),
            "id_cliente": r[1] or "", "contacto": r[2] or "", "fecha": _fstr(r[3]),
            "descripcion": r[4] or "", "nota": r[5] or "", "autor": r[6] or "",
            "color": int(r[7] or 0), "cliente_nombre": r[8] or "",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/cotizaciones")
async def cotizacion_create(body: CotizacionCreate, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    idc = (body.id_cliente or "").strip().upper()
    if not idc or not (body.contacto or "").strip() or not (body.descripcion or "").strip():
        raise HTTPException(status_code=400, detail="Cliente, contacto y descripción son obligatorios.")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Cliente FROM clientes WHERE IdCliente = %s", (idc,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"El ID de cliente {idc} no existe.")
        folio = _db_create_quotation(cursor, idc, body.contacto, body.descripcion, current_user.get("nombre") or current_user.get("email"))
        conn.commit()
        conn.close()
        return {"folio": folio, "folio_fmt": _fmt_folio(folio)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.put("/api/cotizaciones/{folio:int}")
async def cotizacion_update(folio: int, body: CotizacionUpdate, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    idc = (body.id_cliente or "").strip().upper()
    if not idc or not (body.contacto or "").strip() or not (body.descripcion or "").strip():
        raise HTTPException(status_code=400, detail="Cliente, contacto y descripción son obligatorios.")
    if int(body.color) not in (0, 1, 2):
        raise HTTPException(status_code=400, detail="Estatus inválido.")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT IdCliente, Contacto, Descripcion, Color FROM IndiceMateriales WHERE Folio = %s", (int(folio),))
        cur_row = cursor.fetchone()
        if not cur_row:
            conn.close()
            raise HTTPException(status_code=404, detail="Cotización no encontrada")
        cur_color = int(cur_row[3] or 0)
        if cur_color in (1, 2):
            # Bloqueada: solo se permite transición de estatus, no editar datos
            if ((cur_row[0] or "") != idc or (cur_row[1] or "") != body.contacto.strip()
                    or (cur_row[2] or "") != body.descripcion.strip()):
                conn.close()
                raise HTTPException(status_code=400, detail="Cotización bloqueada (lista para facturar/facturada).")
        cursor.execute(
            "UPDATE IndiceMateriales SET IdCliente = %s, Contacto = %s, Descripcion = %s, Color = %s WHERE Folio = %s",
            (idc, body.contacto.strip(), body.descripcion.strip(), int(body.color), int(folio)),
        )
        conn.commit()
        conn.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.put("/api/cotizaciones/{folio:int}/nota")
async def cotizacion_nota(folio: int, body: CotizacionNota, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE IndiceMateriales SET Nota = %s WHERE Folio = %s", ((body.nota or "").strip(), int(folio)))
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.delete("/api/cotizaciones/{folio:int}")
async def cotizacion_delete(folio: int, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        color = _db_get_color(cursor, folio)
        if color is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Cotización no encontrada")
        if color in (1, 2):
            conn.close()
            raise HTTPException(status_code=400, detail="Cotización bloqueada (lista para facturar/facturada).")
        cursor.execute("DELETE FROM Partidas WHERE Folio = %s", (int(folio),))
        cursor.execute("DELETE FROM IndiceMateriales WHERE Folio = %s", (int(folio),))
        conn.commit()
        conn.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/cotizaciones/{folio:int}/clonar")
async def cotizacion_clonar(folio: int, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        nuevo = _db_clone_quotation(cursor, folio, current_user.get("nombre") or current_user.get("email"))
        conn.commit()
        conn.close()
        return {"folio": nuevo, "folio_fmt": _fmt_folio(nuevo)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ----- PDF y envío por correo (como el HUB) -----

def _cotizacion_pdf_bytes(folio: int) -> tuple:
    """Arma header + partidas y genera el PDF. Retorna (filename, bytes)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT IM.Folio, IM.IdCliente, IM.Contacto, IM.Fecha, IM.Descripcion, IM.Nota, "
        "IM.Autor, IM.Color, C.Cliente AS ClienteNombre, C.CondicionesPagoDias "
        "FROM IndiceMateriales IM LEFT JOIN clientes C ON IM.IdCliente = C.IdCliente "
        "WHERE IM.Folio = %s", (int(folio),))
    r = cursor.fetchone()
    if not r:
        conn.close()
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    autor = r[6] or ""
    telefono = "8183589075"
    try:
        cursor.execute("SELECT TOP 1 Telefono FROM MAC WHERE Nombre = %s ORDER BY Telefono DESC", (autor,))
        trow = cursor.fetchone()
        if trow and trow[0]:
            telefono = str(trow[0]).strip()
    except Exception:
        pass
    header = {
        "folio": r[0], "id_cliente": r[1] or "", "contacto": r[2] or "",
        "fecha": r[3], "descripcion": r[4] or "", "nota": r[5] or "",
        "autor": autor, "color": int(r[7] or 0), "cliente_nombre": r[8] or "",
        "condiciones_pago": r[9] or 30, "telefono": telefono,
    }
    cursor.execute(
        "SELECT Partida, Cantidad, Descripcion, PrecioCompraUnitario, Factor, "
        "Proveedor, TiempoEntregaDias, Dolar, Flete "
        "FROM Partidas WHERE Folio = %s ORDER BY Partida ASC", (int(folio),))
    parts = [_partida_row_to_dict(int(folio), row) for row in cursor.fetchall()]
    conn.close()
    if not parts:
        raise HTTPException(status_code=400, detail="La cotización no tiene partidas.")
    return f"Cotizacion_{_fmt_folio(folio)}.pdf", build_cotizacion_pdf(header, parts)


@app.get("/api/cotizaciones/{folio:int}/pdf")
async def cotizacion_pdf(folio: int, request: Request):
    _user = _user_from_header_or_query(request)
    _require_cotiz(_user)
    try:
        filename, pdf_bytes = _cotizacion_pdf_bytes(folio)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


class CotizacionEnviar(BaseModel):
    to_email: str = ""
    subject: str = ""
    body: str = ""


def _smtp_send_with_pdf(to_email: str, subject: str, body: str, pdf_bytes: bytes,
                        pdf_filename: str, sender_email: str, cc_email=None):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 SmtpServer, Port, Username, Password, UseSSL, UseTLS, RequireAuth "
                   "FROM HUB_EmailConfig ORDER BY Id ASC")
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise Exception("Sin configuración SMTP (HUB_EmailConfig).")
    server_name, port, username, password = row[0].strip(), int(row[1]), row[2].strip(), row[3].strip()
    use_ssl, use_tls, require_auth = bool(row[4]), bool(row[5]), bool(row[6])
    msg = MIMEMultipart()
    msg["From"] = f"{sender_email}"
    msg["To"] = to_email
    msg["Subject"] = subject
    if cc_email:
        msg["Cc"] = cc_email
    msg.attach(MIMEText(body or "", "plain", "utf-8"))
    part = MIMEApplication(pdf_bytes, _subtype="pdf")
    part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
    msg.attach(part)
    recipients = [to_email] + ([cc_email] if cc_email else [])
    if use_ssl:
        server = smtplib.SMTP_SSL(server_name, port, timeout=20)
    else:
        server = smtplib.SMTP(server_name, port, timeout=20)
        if use_tls:
            server.starttls()
    if require_auth:
        server.login(username, password)
    server.sendmail(username, recipients, msg.as_string())
    server.quit()


@app.post("/api/cotizaciones/{folio:int}/enviar")
async def cotizacion_enviar(folio: int, body: CotizacionEnviar, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    to_email = (body.to_email or "").strip()
    if not to_email or "@" not in to_email:
        raise HTTPException(status_code=400, detail="Correo destinatario inválido.")
    try:
        filename, pdf_bytes = _cotizacion_pdf_bytes(folio)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    try:
        _smtp_send_with_pdf(to_email, (body.subject or "").strip() or f"Envío cotización {_fmt_folio(folio)}",
                            body.body or "", pdf_bytes, filename,
                            current_user.get("email"), cc_email=current_user.get("email"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo enviar: {str(e)[:200]}")
    return {"ok": True}


# ----- Partidas -----

@app.get("/api/cotizaciones/{folio:int}/partidas")
async def cotizacion_partidas(folio: int, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Partida, Cantidad, Descripcion, PrecioCompraUnitario, Factor, "
            "Proveedor, TiempoEntregaDias, Dolar, Flete "
            "FROM Partidas WHERE Folio = %s ORDER BY Partida ASC", (int(folio),))
        rows = cursor.fetchall()
        conn.close()
        return [_partida_row_to_dict(int(folio), r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/cotizaciones/{folio:int}/partidas")
async def cotizacion_partida_add(folio: int, body: PartidaCreate, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    _validate_partida_input(body.cantidad, body.descripcion)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        color = _db_get_color(cursor, folio)
        if color is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Cotización no encontrada")
        if color in (1, 2):
            conn.close()
            raise HTTPException(status_code=400, detail="Cotización bloqueada.")
        num = _db_add_partida(cursor, folio, body.cantidad, body.descripcion, body.precio_compra,
                              body.factor, body.proveedor, body.tiempo_entrega, body.dolar, body.flete)
        conn.commit()
        conn.close()
        return {"ok": True, "partida": num}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.put("/api/cotizaciones/{folio:int}/partidas/{partida:int}")
async def cotizacion_partida_update(folio: int, partida: int, body: PartidaUpdate, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    _validate_partida_input(body.cantidad, body.descripcion)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        color = _db_get_color(cursor, folio)
        if color is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Cotización no encontrada")
        if color in (1, 2):
            conn.close()
            raise HTTPException(status_code=400, detail="Cotización bloqueada.")
        cursor.execute(
            "UPDATE Partidas SET Cantidad = %s, Descripcion = %s, PrecioCompraUnitario = %s, "
            "Factor = %s, Proveedor = %s, TiempoEntregaDias = %s, Dolar = %s, Flete = %s "
            "WHERE Folio = %s AND Partida = %s",
            (int(body.cantidad), body.descripcion.strip(), float(body.precio_compra), float(body.factor),
             (body.proveedor or "").strip(), int(body.tiempo_entrega or 0), float(body.dolar or 0.0),
             float(body.flete or 0.0), int(folio), int(partida)),
        )
        conn.commit()
        conn.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.delete("/api/cotizaciones/{folio:int}/partidas/{partida:int}")
async def cotizacion_partida_delete(folio: int, partida: int, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        color = _db_get_color(cursor, folio)
        if color is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Cotización no encontrada")
        if color in (1, 2):
            conn.close()
            raise HTTPException(status_code=400, detail="Cotización bloqueada.")
        cursor.execute("DELETE FROM Partidas WHERE Folio = %s AND Partida = %s", (int(folio), int(partida)))
        conn.commit()
        conn.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ----- Clientes -----

@app.get("/api/clientes")
async def clientes_list(current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT IdCliente, Cliente, CondicionesPagoDias FROM clientes ORDER BY IdCliente ASC")
        rows = cursor.fetchall()
        conn.close()
        return [{"id_cliente": r[0], "nombre": r[1], "dias_pago": r[2]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/clientes")
async def cliente_create(body: ClienteCreate, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    idc = (body.id_cliente or "").strip().upper()
    if not idc or not (body.nombre or "").strip():
        raise HTTPException(status_code=400, detail="ID y razón social son obligatorios.")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Cliente FROM clientes WHERE IdCliente = %s", (idc,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"El ID {idc} ya está registrado.")
        cursor.execute(
            "INSERT INTO clientes (IdCliente, Cliente, CondicionesPagoDias) VALUES (%s, %s, %s)",
            (idc, body.nombre.strip(), int(body.dias_pago or 0)),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "id_cliente": idc}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.put("/api/clientes/{id_cliente}")
async def cliente_update(id_cliente: str, body: ClienteUpdate, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    if not (body.nombre or "").strip():
        raise HTTPException(status_code=400, detail="La razón social no puede estar vacía.")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE clientes SET Cliente = %s, CondicionesPagoDias = %s WHERE IdCliente = %s",
            (body.nombre.strip(), int(body.dias_pago or 0), id_cliente.strip().upper()),
        )
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.delete("/api/clientes/{id_cliente}")
async def cliente_delete(id_cliente: str, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM clientes WHERE IdCliente = %s", (id_cliente.strip().upper(),))
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=400, detail="No se puede eliminar: tiene cotizaciones asociadas.")
        conn.commit()
        conn.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/clientes/{id_cliente}/nombre")
async def cliente_nombre(id_cliente: str, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Cliente FROM clientes WHERE IdCliente = %s", (id_cliente.strip().upper(),))
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Cliente no existe.")
        return {"id_cliente": id_cliente.strip().upper(), "nombre": row[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


class ContactoRename(BaseModel):
    anterior: str = ""
    nuevo: str = ""


@app.put("/api/clientes/{id_cliente}/contactos")
async def cliente_contacto_rename(id_cliente: str, body: ContactoRename, current_user: dict = Depends(get_current_user)):
    """Renombra un contacto en todas las cotizaciones del cliente (los contactos
    son historial en IndiceMateriales.Contacto, no catálogo: renombrar = UPDATE)."""
    _require_cotiz(current_user)
    anterior = (body.anterior or "").strip()
    nuevo = (body.nuevo or "").strip()
    if not anterior or not nuevo:
        raise HTTPException(status_code=400, detail="Contacto anterior y nuevo son obligatorios.")
    if anterior == nuevo:
        return {"ok": True, "actualizados": 0}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE IndiceMateriales SET Contacto = %s WHERE IdCliente = %s AND Contacto = %s",
            (nuevo, id_cliente.strip().upper(), anterior),
        )
        try:
            n = cursor.rowcount
        except Exception:
            n = 0
        conn.commit()
        conn.close()
        return {"ok": True, "actualizados": int(n or 0)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/clientes/{id_cliente}/contactos")
async def cliente_contactos(id_cliente: str, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT Contacto FROM IndiceMateriales "
            "WHERE IdCliente = %s AND Contacto IS NOT NULL AND LTRIM(RTRIM(Contacto)) <> '' "
            "ORDER BY Contacto ASC", (id_cliente.strip().upper(),))
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ----- Sync offline (outbox estilo Field) -----
# Entidades: cotizacion (create/update/delete/nota), partida (add/update/delete).
# Los pendientes locales usan id_local (uuid); el servidor asigna folio real y
# devuelve el mapeo para reescribir partidas del mismo lote.

class SyncItem(BaseModel):
    entity: str = ""
    action: str = ""
    id_local: str = ""
    payload: Dict[str, Any] = {}


class SyncPushRequest(BaseModel):
    items: List[SyncItem] = []


@app.post("/api/sync/push")
async def sync_push(body: SyncPushRequest, current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    autor = current_user.get("nombre") or current_user.get("email")
    results = []
    idmap: Dict[str, int] = {}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for it in body.items:
            r: dict = {"id_local": it.id_local, "status": "error", "message": ""}
            try:
                p = it.payload or {}

                def _folio_of(pl: dict) -> Optional[int]:
                    if pl.get("folio") is not None:
                        return int(pl["folio"])
                    lid = pl.get("id_local") or it.id_local
                    return idmap.get(lid)

                if it.entity == "cotizacion" and it.action == "create":
                    folio = _db_create_quotation(cursor, p.get("id_cliente", ""), p.get("contacto", ""),
                                                 p.get("descripcion", ""), autor)
                    idmap[it.id_local] = folio
                    r.update({"status": "ok", "folio": folio, "folio_fmt": _fmt_folio(folio)})
                elif it.entity == "cotizacion" and it.action == "update":
                    folio = _folio_of(p)
                    if folio is None:
                        raise Exception("Sin folio (aún no sincronizada).")
                    cursor.execute(
                        "UPDATE IndiceMateriales SET IdCliente = %s, Contacto = %s, Descripcion = %s, Color = %s WHERE Folio = %s",
                        ((p.get("id_cliente") or "").strip().upper(), (p.get("contacto") or "").strip(),
                         (p.get("descripcion") or "").strip(), int(p.get("color", 0)), folio),
                    )
                    r.update({"status": "ok", "folio": folio})
                elif it.entity == "cotizacion" and it.action == "delete":
                    folio = _folio_of(p)
                    if folio is None:
                        raise Exception("Sin folio (aún no sincronizada).")
                    cursor.execute("DELETE FROM Partidas WHERE Folio = %s", (folio,))
                    cursor.execute("DELETE FROM IndiceMateriales WHERE Folio = %s", (folio,))
                    r.update({"status": "ok", "folio": folio})
                elif it.entity == "cotizacion" and it.action == "nota":
                    folio = _folio_of(p)
                    if folio is None:
                        raise Exception("Sin folio (aún no sincronizada).")
                    cursor.execute("UPDATE IndiceMateriales SET Nota = %s WHERE Folio = %s",
                                   ((p.get("nota") or "").strip(), folio))
                    r.update({"status": "ok", "folio": folio})
                elif it.entity == "partida" and it.action == "add":
                    folio = _folio_of(p)
                    if folio is None:
                        raise Exception("Sin folio (aún no sincronizada).")
                    num = _db_add_partida(cursor, folio, int(p.get("cantidad", 1)), p.get("descripcion", ""),
                                          float(p.get("precio_compra", 0.0)), float(p.get("factor", 0.0)),
                                          p.get("proveedor", ""), int(p.get("tiempo_entrega", 0) or 0),
                                          float(p.get("dolar", 0.0) or 0.0), float(p.get("flete", 0.0) or 0.0))
                    r.update({"status": "ok", "folio": folio, "partida": num})
                elif it.entity == "partida" and it.action == "update":
                    folio = _folio_of(p)
                    if folio is None:
                        raise Exception("Sin folio (aún no sincronizada).")
                    cursor.execute(
                        "UPDATE Partidas SET Cantidad = %s, Descripcion = %s, PrecioCompraUnitario = %s, "
                        "Factor = %s, Proveedor = %s, TiempoEntregaDias = %s, Dolar = %s, Flete = %s "
                        "WHERE Folio = %s AND Partida = %s",
                        (int(p.get("cantidad", 1)), (p.get("descripcion") or "").strip(),
                         float(p.get("precio_compra", 0.0)), float(p.get("factor", 0.0)),
                         (p.get("proveedor") or "").strip(), int(p.get("tiempo_entrega", 0) or 0),
                         float(p.get("dolar", 0.0) or 0.0), float(p.get("flete", 0.0) or 0.0),
                         folio, int(p.get("partida", 0))),
                    )
                    r.update({"status": "ok", "folio": folio})
                elif it.entity == "partida" and it.action == "delete":
                    folio = _folio_of(p)
                    if folio is None:
                        raise Exception("Sin folio (aún no sincronizada).")
                    cursor.execute("DELETE FROM Partidas WHERE Folio = %s AND Partida = %s",
                                   (folio, int(p.get("partida", 0))))
                    r.update({"status": "ok", "folio": folio})
                else:
                    r["message"] = f"Entidad/acción no soportada: {it.entity}/{it.action}"
            except Exception as e:
                r["message"] = str(e)[:200]
            results.append(r)
        conn.commit()
        conn.close()
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/sync/pull")
async def sync_pull(current_user: dict = Depends(get_current_user)):
    _require_cotiz(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 999 Folio, IdCliente, Cliente, Contacto, Fecha, DescripcionGeneral, "
            "Autor, Estatus, SumaPartidas, FleteCotizacion, Subtotal, IVA, TotalFinal "
            "FROM vw_ResumenCotizaciones ORDER BY Folio DESC"
        )
        cots = [{
            "folio": r[0], "id_cliente": r[1] or "", "cliente": r[2] or "", "contacto": r[3] or "",
            "fecha": _fstr(r[4]), "descripcion": r[5] or "", "autor": r[6] or "",
            "estatus": r[7] or "", "suma_partidas": _fnum(r[8]), "flete": _fnum(r[9]),
            "subtotal": _fnum(r[10]), "iva": _fnum(r[11]), "total": _fnum(r[12]),
        } for r in cursor.fetchall()]
        cursor.execute("SELECT IdCliente, Cliente, CondicionesPagoDias FROM clientes ORDER BY IdCliente ASC")
        clis = [{"id_cliente": r[0], "nombre": r[1], "dias_pago": r[2]} for r in cursor.fetchall()]
        conn.close()
        return {"cotizaciones": cots, "clientes": clis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- Dashboard endpoint ---

class KPIData(BaseModel):
    modulo: str
    valor: float
    etiqueta: str


@app.get("/api/dashboard/kpis")
async def get_dashboard_kpis(current_user: dict = Depends(get_current_user)):
    """Get KPIs filtered by user permissions"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        kpis = []
        
        # Inventory KPI
        if current_user["acceso_inventario"]:
            cursor.execute("SELECT COUNT(*) FROM HUB_Inventario WHERE Cantidad <= StockMinimo")
            row = cursor.fetchone()
            kpis.append({"modulo": "inventario", "valor": row[0] if row else 0, "etiqueta": "Items con stock bajo"})
        
        # Cotizaciones KPI (la vista trae Estatus como texto; IndiceMateriales no tiene esa columna)
        if current_user["acceso_cotizaciones"]:
            cursor.execute("SELECT COUNT(*) FROM vw_ResumenCotizaciones WHERE Estatus LIKE '%PENDIENTE%'")
            row = cursor.fetchone()
            kpis.append({"modulo": "cotizaciones", "valor": row[0] if row else 0, "etiqueta": "Cotizaciones pendientes"})
        
        # Users count
        cursor.execute("SELECT COUNT(*) FROM HUB_Users WHERE Activo = 1")
        row = cursor.fetchone()
        kpis.append({"modulo": "usuarios", "valor": row[0] if row else 0, "etiqueta": "Usuarios activos"})
        
        conn.close()
        return {"kpis": kpis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- PDF generation endpoint (placeholder) ---

@app.post("/api/pdf/generate")
async def generate_pdf(current_user: dict = Depends(get_current_user)):
    """Generate PDF for cotización or reporte"""
    if not current_user["acceso_cotizaciones"]:
        raise HTTPException(status_code=403, detail="No access")
    try:
        # This would integrate with the pdf_generator module
        # For now, return a placeholder
        return {"message": "PDF generation endpoint - integrate pdf_generator module"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ===== REPORTES DE SERVICIO (AccesoRegistroReportes / AccesoReportes) =====

class ReporteCreate(BaseModel):
    cliente: str
    contacto: str = ""
    correo_contacto: str = ""
    fecha: str  # YYYY-MM-DD
    tecnico: str
    descripcion: str = ""
    notas: str = ""
    fecha_inicio: str  # HH:MM
    fecha_fin: str  # HH:MM
    tiempo_traslado: float = 0.0
    tiempo_comida: int = 0
    maquina_linea: str = ""
    tecnicos_adicionales: List[str] = []


class ReporteUpdate(BaseModel):
    cliente: str = ""
    contacto: str = ""
    correo_contacto: str = ""
    fecha: str = ""
    tecnico: str = ""
    descripcion: str = ""
    estatus: str = ""
    notas: str = ""
    fecha_inicio: str = ""
    fecha_fin: str = ""
    tiempo_traslado: float = 0.0
    tiempo_comida: int = 0
    maquina_linea: str = ""
    tecnicos_adicionales: List[str] = []


class ReporteFotosSave(BaseModel):
    fotos: List[str]  # base64 strings


class ReporteTecnicosSave(BaseModel):
    tecnicos: List[str]


class ReporteSignatureSave(BaseModel):
    signature_base64: str


def _require_reporte(current_user: dict):
    if not (current_user.get("acceso_registro_reportes") or current_user.get("acceso_reportes")):
        raise HTTPException(status_code=403, detail="Requiere permiso de Reportes de Servicio")


def _folio_from_id(cur, next_id: int) -> str:
    return f"RS-{str(next_id).zfill(5)}"


@app.get("/api/reportes")
async def api_list_reportes(tecnico: str = "", eliminados: bool = False, current_user: dict = Depends(get_current_user)):
    """Lista reportes (top 500). Filtra por técnico si se pasa. eliminados=true muestra papelera."""
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        where_eliminado = "AND Eliminado = 1" if eliminados else "AND (Eliminado = 0 OR Eliminado IS NULL)"
        
        if tecnico:
            cursor.execute(f"""
                SELECT IdReporte, Folio, Cliente, Contacto, CorreoContacto, Fecha, Tecnico,
                       DescripcionServicio, Estatus, Notas, MaquinaLinea, FechaHoraInicio, FechaHoraFin,
                       TiempoTraslado, TiempoComida, FirmaConformidad, Cotizacion, Eliminado, FechaEliminado
                FROM ReportesServicio
                WHERE (Tecnico = %s
                   OR IdReporte IN (SELECT IdReporte FROM ReportesServicioTecnicos
                                    INNER JOIN HUB_Users u ON u.Id = ReportesServicioTecnicos.IdUsuario
                                    WHERE u.Nombre = %s))
                   {where_eliminado}
                ORDER BY Fecha DESC, IdReporte DESC
            """, (tecnico.strip(), tecnico.strip()))
        else:
            cursor.execute(f"""
                SELECT TOP 500 IdReporte, Folio, Cliente, Contacto, CorreoContacto, Fecha, Tecnico,
                       DescripcionServicio, Estatus, Notas, MaquinaLinea, FechaHoraInicio, FechaHoraFin,
                       TiempoTraslado, TiempoComida, FirmaConformidad, Cotizacion, Eliminado, FechaEliminado
                FROM ReportesServicio
                WHERE 1=1 {where_eliminado}
                ORDER BY Fecha DESC, IdReporte DESC
            """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip([c[0] for c in cursor.description], r)) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/reportes/{id_reporte}")
async def api_get_reporte(id_reporte: int, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT IdReporte, Folio, Cliente, Contacto, CorreoContacto, Fecha, Tecnico,
                   DescripcionServicio, Estatus, Notas, MaquinaLinea, FechaHoraInicio, FechaHoraFin,
                   TiempoTraslado, TiempoComida, FirmaConformidad, Cotizacion
            FROM ReportesServicio
            WHERE IdReporte = %s
        """, (int(id_reporte),))
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Reporte no encontrado")
        return dict(zip([c[0] for c in cursor.description], row))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/reportes")
async def api_create_reporte(body: ReporteCreate, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ISNULL(MAX(IdReporte), 0) + 1 FROM ReportesServicio")
        row = cursor.fetchone()
        next_id = int(row[0]) if row else 1
        folio = f"RS-{str(next_id).zfill(5)}"

        fecha_str = str(body.fecha)
        cursor.execute("""
            INSERT INTO ReportesServicio (
                Folio, Cliente, Contacto, CorreoContacto, Fecha, Tecnico,
                DescripcionServicio, Estatus, Notas, MaquinaLinea,
                FechaHoraInicio, FechaHoraFin, TiempoTraslado, TiempoComida
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Borrador', %s, %s, %s, %s, %s, %s)
        """, (
            folio,
            body.cliente.strip(),
            body.contacto.strip() if body.contacto else None,
            body.correo_contacto.strip() if body.correo_contacto else None,
            fecha_str,
            body.tecnico.strip(),
            body.descripcion.strip() if body.descripcion else None,
            body.notas.strip() if body.notas else None,
            body.maquina_linea.strip() if body.maquina_linea else None,
            body.fecha_inicio,
            body.fecha_fin,
            float(body.tiempo_traslado or 0.0),
            1 if body.tiempo_comida else 0,
        ))
        conn.commit()
        cursor.execute("SELECT SCOPE_IDENTITY()")
        row = cursor.fetchone()
        id_reporte = int(row[0]) if row and row[0] else None

        # Tecnicos adicionales
        if id_reporte and body.tecnicos_adicionales:
            for t in body.tecnicos_adicionales:
                cursor.execute("SELECT Id FROM HUB_Users WHERE Nombre = %s", (t.strip(),))
                ur = cursor.fetchone()
                if ur:
                    cursor.execute("INSERT INTO ReportesServicioTecnicos (IdReporte, IdUsuario) VALUES (%s, %s)", (id_reporte, ur[0]))
            conn.commit()

        conn.close()
        return {"ok": True, "folio": folio, "id_reporte": id_reporte}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.put("/api/reportes/{id_reporte}")
async def api_update_reporte(id_reporte: int, body: ReporteUpdate, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Build dynamic update
        fields = []
        vals = []
        if body.cliente:
            fields.append("Cliente = %s"); vals.append(body.cliente.strip())
        if body.contacto is not None:
            fields.append("Contacto = %s"); vals.append(body.contacto.strip() if body.contacto else None)
        if body.correo_contacto is not None:
            fields.append("CorreoContacto = %s"); vals.append(body.correo_contacto.strip() if body.correo_contacto else None)
        if body.fecha:
            fields.append("Fecha = %s"); vals.append(str(body.fecha))
        if body.tecnico:
            fields.append("Tecnico = %s"); vals.append(body.tecnico.strip())
        if body.descripcion is not None:
            fields.append("DescripcionServicio = %s"); vals.append(body.descripcion.strip() if body.descripcion else None)
        if body.estatus:
            fields.append("Estatus = %s"); vals.append(body.estatus.strip())
        if body.notas is not None:
            fields.append("Notas = %s"); vals.append(body.notas.strip() if body.notas else None)
        if body.maquina_linea is not None:
            fields.append("MaquinaLinea = %s"); vals.append(body.maquina_linea.strip() if body.maquina_linea else None)
        if body.fecha_inicio:
            fields.append("FechaHoraInicio = %s"); vals.append(body.fecha_inicio)
        if body.fecha_fin:
            fields.append("FechaHoraFin = %s"); vals.append(body.fecha_fin)
        if body.tiempo_traslado is not None:
            fields.append("TiempoTraslado = %s"); vals.append(float(body.tiempo_traslado or 0.0))
        if body.tiempo_comida is not None:
            fields.append("TiempoComida = %s"); vals.append(1 if body.tiempo_comida else 0)

        if fields:
            vals.append(int(id_reporte))
            cursor.execute(f"UPDATE ReportesServicio SET {', '.join(fields)} WHERE IdReporte = %s", tuple(vals))

        # Tecnicos adicionales (replace)
        if body.tecnicos_adicionales is not None:
            cursor.execute("DELETE FROM ReportesServicioTecnicos WHERE IdReporte = %s", (int(id_reporte),))
            for t in body.tecnicos_adicionales:
                cursor.execute("SELECT Id FROM HUB_Users WHERE Nombre = %s", (t.strip(),))
                ur = cursor.fetchone()
                if ur:
                    cursor.execute("INSERT INTO ReportesServicioTecnicos (IdReporte, IdUsuario) VALUES (%s, %s)", (id_reporte, ur[0]))

        conn.commit()
        conn.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.delete("/api/reportes/{id_reporte}")
async def api_delete_reporte(id_reporte: int, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Soft delete: marcar como eliminado en lugar de borrar
        cursor.execute("SELECT Folio FROM ReportesServicio WHERE IdReporte = %s", (int(id_reporte),))
        row = cursor.fetchone()
        folio = row[0] if row else str(id_reporte)
        cursor.execute("UPDATE ReportesServicio SET Eliminado = 1, FechaEliminado = GETDATE() WHERE IdReporte = %s", (int(id_reporte),))
        conn.commit()
        conn.close()
        return {"ok": True, "folio": folio, "message": "Movido a papelera"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/reportes/{id_reporte}/restaurar")
async def api_restaurar_reporte(id_reporte: int, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE ReportesServicio SET Eliminado = 0, FechaEliminado = NULL WHERE IdReporte = %s", (int(id_reporte),))
        conn.commit()
        cursor.execute("SELECT Folio FROM ReportesServicio WHERE IdReporte = %s", (int(id_reporte),))
        row = cursor.fetchone()
        conn.close()
        return {"ok": True, "folio": row[0] if row else "", "message": "Restaurado desde papelera"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.delete("/api/reportes/{id_reporte}/purge")
async def api_purge_reporte(id_reporte: int, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Folio FROM ReportesServicio WHERE IdReporte = %s", (int(id_reporte),))
        row = cursor.fetchone()
        folio = row[0] if row else str(id_reporte)
        cursor.execute("DELETE FROM ReportesServicioFotos WHERE IdReporte = %s", (int(id_reporte),))
        cursor.execute("DELETE FROM ReportesServicioTecnicos WHERE IdReporte = %s", (int(id_reporte),))
        cursor.execute("DELETE FROM ReportesServicio WHERE IdReporte = %s", (int(id_reporte),))
        conn.commit()
        conn.close()
        return {"ok": True, "folio": folio, "message": "Eliminado permanentemente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/reportes/{id_reporte}/fotos")
async def api_get_fotos(id_reporte: int, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT IdFoto, FotoComprimida, Orden FROM ReportesServicioFotos WHERE IdReporte = %s ORDER BY Orden", (int(id_reporte),))
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "base64": r[1], "orden": r[2]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/reportes/{id_reporte}/fotos")
async def api_save_fotos(id_reporte: int, body: ReporteFotosSave, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ReportesServicioFotos WHERE IdReporte = %s", (int(id_reporte),))
        for i, b64 in enumerate(body.fotos):
            cursor.execute("INSERT INTO ReportesServicioFotos (IdReporte, FotoComprimida, Orden) VALUES (%s, %s, %s)", (int(id_reporte), b64, i))
        conn.commit()
        conn.close()
        return {"ok": True, "guardadas": len(body.fotos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.delete("/api/reportes/{id_reporte}/fotos/{id_foto}")
async def api_delete_foto(id_reporte: int, id_foto: int, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ReportesServicioFotos WHERE IdFoto = %s AND IdReporte = %s", (int(id_foto), int(id_reporte)))
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/reportes/{id_reporte}/tecnicos")
async def api_get_tecnicos(id_reporte: int, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.Nombre FROM ReportesServicioTecnicos t
            INNER JOIN HUB_Users u ON u.Id = t.IdUsuario
            WHERE t.IdReporte = %s
        """, (int(id_reporte),))
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/reportes/{id_reporte}/tecnicos")
async def api_save_tecnicos(id_reporte: int, body: ReporteTecnicosSave, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ReportesServicioTecnicos WHERE IdReporte = %s", (int(id_reporte),))
        for t in body.tecnicos:
            cursor.execute("SELECT Id FROM HUB_Users WHERE Nombre = %s", (t.strip(),))
            ur = cursor.fetchone()
            if ur:
                cursor.execute("INSERT INTO ReportesServicioTecnicos (IdReporte, IdUsuario) VALUES (%s, %s)", (int(id_reporte), ur[0]))
        conn.commit()
        conn.close()
        return {"ok": True, "guardados": len(body.tecnicos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/reportes/{id_reporte}/firma")
async def api_save_firma(id_reporte: int, body: ReporteSignatureSave, current_user: dict = Depends(get_current_user)):
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE ReportesServicio SET FirmaConformidad = %s, Estatus = 'Firmado' WHERE IdReporte = %s", (body.signature_base64, int(id_reporte)))
        conn.commit()
        cursor.execute("SELECT Folio FROM ReportesServicio WHERE IdReporte = %s", (int(id_reporte),))
        row = cursor.fetchone()
        conn.close()
        return {"ok": True, "folio": row[0] if row else ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/reportes/{id_reporte}/pdf")
async def api_reporte_pdf(id_reporte: int, request: Request, current_user: dict = Depends(_user_from_header_or_query)):
    """Genera PDF del reporte de servicio IDÉNTICO al HUB (pdf_generator.generate_service_report_pdf)."""
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Reporte completo
        cursor.execute("""
            SELECT IdReporte, Folio, Cliente, Contacto, CorreoContacto, Fecha, Tecnico,
                   DescripcionServicio, Estatus, Notas, MaquinaLinea, FechaHoraInicio, FechaHoraFin,
                   TiempoTraslado, TiempoComida, FirmaConformidad, Cotizacion
            FROM ReportesServicio WHERE IdReporte = %s
        """, (int(id_reporte),))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Reporte no encontrado")

        # Técnicos adicionales
        cursor.execute("""
            SELECT u.Nombre FROM ReportesServicioTecnicos t
            INNER JOIN HUB_Users u ON u.Id = t.IdUsuario
            WHERE t.IdReporte = %s
        """, (int(id_reporte),))
        tecnicos_rows = cursor.fetchall()
        tecnicos_adicionales = [r[0] for r in tecnicos_rows if r[0] != row[6]]  # excluir técnico principal

        # Fotos
        cursor.execute("SELECT IdFoto, FotoComprimida, Orden FROM ReportesServicioFotos WHERE IdReporte = %s ORDER BY Orden", (int(id_reporte),))
        fotos_rows = cursor.fetchall()
        fotos = [{"FotoComprimida": r[1], "Orden": r[2]} for r in fotos_rows]

        # Nombre del cliente (razón social)
        cursor.execute("SELECT Cliente FROM clientes WHERE IdCliente = %s", (row[2],))
        cliente_row = cursor.fetchone()
        cliente_nombre = cliente_row[0] if cliente_row else None

        conn.close()

        # Build report dict compatible with HUB pdf_generator
        report = {
            "IdReporte": row[0],
            "Folio": row[1],
            "Cliente": row[2],
            "Contacto": row[3],
            "CorreoContacto": row[4],
            "Fecha": row[5],
            "Tecnico": row[6],
            "DescripcionServicio": row[7],
            "Estatus": row[8],
            "Notas": row[9],
            "MaquinaLinea": row[10],
            "FechaHoraInicio": row[11],
            "FechaHoraFin": row[12],
            "TiempoTraslado": row[13],
            "TiempoComida": row[14],
            "FirmaConformidad": row[15],
            "Cotizacion": row[16],
        }

        pdf_bytes = build_service_report_pdf(report, tecnicos_adicionales=tecnicos_adicionales, fotos=fotos, cliente_nombre=cliente_nombre)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{row[1]}.pdf"'})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


@app.get("/api/reportes/{id_reporte}/enviar")
async def api_reporte_enviar(id_reporte: int, email: str, current_user: dict = Depends(get_current_user)):
    """Envía PDF del reporte por email (adjunto) — usa el mismo PDF IDÉNTICO al HUB."""
    _require_reporte(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT IdReporte, Folio, Cliente, Contacto, CorreoContacto, Fecha, Tecnico,
                   DescripcionServicio, Estatus, Notas, MaquinaLinea, FechaHoraInicio, FechaHoraFin,
                   TiempoTraslado, TiempoComida, FirmaConformidad, Cotizacion
            FROM ReportesServicio WHERE IdReporte = %s
        """, (int(id_reporte),))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Reporte no encontrado")

        cursor.execute("""
            SELECT u.Nombre FROM ReportesServicioTecnicos t
            INNER JOIN HUB_Users u ON u.Id = t.IdUsuario
            WHERE t.IdReporte = %s
        """, (int(id_reporte),))
        tecnicos_rows = cursor.fetchall()
        tecnicos_adicionales = [r[0] for r in tecnicos_rows if r[0] != row[6]]

        cursor.execute("SELECT IdFoto, FotoComprimida, Orden FROM ReportesServicioFotos WHERE IdReporte = %s ORDER BY Orden", (int(id_reporte),))
        fotos_rows = cursor.fetchall()
        fotos = [{"FotoComprimida": r[1], "Orden": r[2]} for r in fotos_rows]

        cursor.execute("SELECT Cliente FROM clientes WHERE IdCliente = %s", (row[2],))
        cliente_row = cursor.fetchone()
        cliente_nombre = cliente_row[0] if cliente_row else None

        conn.close()

        report = {
            "IdReporte": row[0],
            "Folio": row[1],
            "Cliente": row[2],
            "Contacto": row[3],
            "CorreoContacto": row[4],
            "Fecha": row[5],
            "Tecnico": row[6],
            "DescripcionServicio": row[7],
            "Estatus": row[8],
            "Notas": row[9],
            "MaquinaLinea": row[10],
            "FechaHoraInicio": row[11],
            "FechaHoraFin": row[12],
            "TiempoTraslado": row[13],
            "TiempoComida": row[14],
            "FirmaConformidad": row[15],
            "Cotizacion": row[16],
        }

        pdf_bytes = build_service_report_pdf(report, tecnicos_adicionales=tecnicos_adicionales, fotos=fotos, cliente_nombre=cliente_nombre)

        # Send email
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.application import MIMEApplication
        from email.mime.text import MIMEText

        smtp_host = os.getenv("HUB_SMTP_SERVER", "smtp.office365.com")
        smtp_port = int(os.getenv("HUB_SMTP_PORT", "587"))
        smtp_user = os.getenv("HUB_SMTP_USER", "sistemas@ecc-sa.com.mx")
        smtp_pass = os.getenv("HUB_SMTP_PASSWORD", "eyccazo")

        msg = MIMEMultipart()
        msg["Subject"] = f"Reporte de Servicio {row[1]} - {row[2]}"
        msg["From"] = smtp_user
        msg["To"] = email
        msg.attach(MIMEText(f"Adjunto reporte de servicio {row[1]} para el cliente {row[2]}.", "plain"))
        att = MIMEApplication(pdf_bytes, _subtype="pdf")
        att.add_header("Content-Disposition", "attachment", filename=f"{row[1]}.pdf")
        msg.attach(att)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return {"ok": True, "message": f"Enviado a {email}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando email: {str(e)}")


# ===== ECCSA IA CHAT (AccesoIA) =====

class IaConversacionCreate(BaseModel):
    titulo: str = "Nueva conversación"


class IaMensajeCreate(BaseModel):
    contenido: str


def _require_ia(current_user: dict):
    """En el HUB, Jarvis está disponible para todos los usuarios logueados sin permiso especial."""
    pass  # No restriction


def _cleanup_fifo_conversaciones(cursor, user_id: int):
    """FIFO cleanup: mantiene solo las últimas 10 conversaciones por usuario (igual que HUB)."""
    cursor.execute("""
        DELETE FROM HUB_JarvisMensajes 
        WHERE IdConversacion IN (
            SELECT Id FROM HUB_JarvisConversaciones 
            WHERE IdUsuario = %s 
            ORDER BY FechaCreacion DESC
            OFFSET 10 ROWS
        )
    """, (user_id,))
    cursor.execute("""
        DELETE FROM HUB_JarvisConversaciones 
        WHERE Id IN (
            SELECT Id FROM HUB_JarvisConversaciones 
            WHERE IdUsuario = %s 
            ORDER BY FechaCreacion DESC
            OFFSET 10 ROWS
        )
    """, (user_id,))


@app.get("/api/ia/conversaciones")
async def ia_list_conversaciones(current_user: dict = Depends(get_current_user)):
    _require_ia(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # FIFO cleanup: max 10 conversations per user
        _cleanup_fifo_conversaciones(cursor, current_user["id"])
        # Listar del usuario
        cursor.execute("""
            SELECT Id, Titulo, FechaCreacion
            FROM HUB_JarvisConversaciones
            WHERE IdUsuario = %s
            ORDER BY FechaCreacion DESC
        """, (current_user["id"],))
        rows = cursor.fetchall()
        conn.close()
        return [{"Id": r[0], "Titulo": r[1], "FechaCreacion": r[2]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/ia/conversaciones")
async def ia_create_conversacion(body: IaConversacionCreate, current_user: dict = Depends(get_current_user)):
    _require_ia(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO HUB_JarvisConversaciones (IdUsuario, Titulo)
            VALUES (%s, %s);
            SELECT SCOPE_IDENTITY();
        """, (current_user["id"], body.titulo[:200]))
        row = cursor.fetchone()
        id_conv = int(row[0]) if row else None
        conn.commit()
        conn.close()
        return {"Id": id_conv, "Titulo": body.titulo, "FechaCreacion": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/ia/conversaciones/{id_conversacion}/mensajes")
async def ia_get_mensajes(id_conversacion: int, current_user: dict = Depends(get_current_user)):
    _require_ia(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Verificar propiedad
        cursor.execute("SELECT Id FROM HUB_JarvisConversaciones WHERE Id = %s AND IdUsuario = %s", (id_conversacion, current_user["id"]))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        # Obtener mensajes
        cursor.execute("""
            SELECT Id, [Role], Contenido, FechaRegistro
            FROM HUB_JarvisMensajes
            WHERE IdConversacion = %s
            ORDER BY FechaRegistro ASC, Id ASC
        """, (id_conversacion,))
        rows = cursor.fetchall()
        conn.close()
        return [{"Id": r[0], "Role": r[1], "Contenido": r[2], "FechaRegistro": r[3]} for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/ia/conversaciones/{id_conversacion}/mensajes")
async def ia_send_mensaje(id_conversacion: int, body: IaMensajeCreate, current_user: dict = Depends(get_current_user)):
    """
    CLON EXACTO del HUB views/edwin_jarvis.py process_jarvis_query
    3 Tools: execute_query, send_quote_pdf, send_service_reports
    System instruction con schema completo + admin/non-admin filtering
    """
    _require_ia(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Verificar propiedad
        cursor.execute("SELECT Id FROM HUB_JarvisConversaciones WHERE Id = %s AND IdUsuario = %s", (id_conversacion, current_user["id"]))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Conversación no encontrada")

        # 1. Guardar mensaje del usuario
        cursor.execute("""
            INSERT INTO HUB_JarvisMensajes (IdConversacion, [Role], Contenido)
            VALUES (%s, 'user', %s)
        """, (id_conversacion, body.contenido))
        conn.commit()

        # 2. Obtener config IA (api_key + model)
        cursor.execute("SELECT ApiKey, Modelo FROM HUB_AiConfig WHERE Id = 1")
        ai_cfg_row = cursor.fetchone()
        if not ai_cfg_row or not ai_cfg_row[0]:
            # Guardar mensaje de error
            cursor.execute("INSERT INTO HUB_JarvisMensajes (IdConversacion, [Role], Contenido) VALUES (%s, 'model', %s)",
                          (id_conversacion, "❌ No hay una clave de API (API Key) configurada para Google Gemini. Por favor configúrala en el HUB en 'Configuración IA'."))
            conn.commit()
            conn.close()
            return await ia_get_mensajes(id_conversacion, current_user)

        api_key, model_name = ai_cfg_row[0], ai_cfg_row[1] or 'gemini-1.5-flash'

        # 3. Obtener historial para contexto (últimos 8 turnos = 16 mensajes)
        cursor.execute("""
            SELECT [Role], Contenido FROM HUB_JarvisMensajes 
            WHERE IdConversacion = %s 
            ORDER BY FechaRegistro DESC
        """, (id_conversacion,))
        historial_rows = cursor.fetchall()
        historial = []
        for r in reversed(historial_rows[-16:]):
            role = r[0] if r[0] in ('user', 'model') else 'user'
            historial.append({"role": role, "parts": [r[1]]})

        # 4. Obtener info usuario para system_instruction
        cursor.execute("SELECT Nombre, Email, Id FROM HUB_Users WHERE Id = %s", (current_user["id"],))
        user_row = cursor.fetchone()
        user_name = user_row[0] if user_row else "Colaborador"
        user_email = user_row[1] if user_row else ""
        user_id = user_row[2] if user_row else current_user["id"]
        is_admin = current_user.get("acceso_usuarios", False)

        # 5. Definir Tools (igual que HUB)
        def execute_query(sql_query: str) -> str:
            """Ejecuta una consulta SQL SELECT de solo lectura en la base de datos de ECCSA."""
            # Admin filter injection block for non-admin users
            if not is_admin:
                sql_upper = sql_query.upper()
                if "FROM HUB_USER" in sql_upper or "FROM HUB_VACACIONES" in sql_upper or "FROM HUB_HORASEXTRAS" in sql_upper or "FROM HUB_REGISTROREPORTES" in sql_upper or "FROM HUB_REPORTES" in sql_upper:
                    if f"IDUSUARIO = {user_id}" not in sql_upper and f"ID = {user_id}" not in sql_upper and f"USUARIO = {user_id}" not in sql_upper:
                        if " WHERE " in sql_upper:
                            sql_query += f" AND IdUsuario = {user_id}"
                        else:
                            if "HUB_HORASEXTRASREGISTROS" in sql_upper:
                                sql_query += f" WHERE IdUsuario = {user_id}"
                            elif "HUB_VACACIONESREGISTROS" in sql_upper:
                                sql_query += f" WHERE IdUsuario = {user_id}"
                            elif "HUB_USERS" in sql_upper:
                                sql_query += f" WHERE Id = {user_id}"
            res = execute_readonly_sql(sql_query)
            try:
                import json
                return json.dumps(res, default=str, ensure_ascii=False)
            except:
                return str(res)

        def send_quote_pdf(folio: str, recipient_email: str = None) -> str:
            """Genera el PDF de la cotización indicada y la envía por correo electrónico."""
            target_email = (recipient_email or user_email).strip()
            try:
                q_rows = execute_readonly_sql(f"SELECT * FROM IndiceMateriales WHERE Folio = '{folio.strip()}'")
                if not q_rows or "Error" in q_rows[0] or len(q_rows) == 0:
                    return f"No se encontró ninguna cotización con folio {folio} en la base de datos."
                pdf_bytes = build_cotizacion_pdf(q_rows[0], q_rows[1:]) if len(q_rows) > 1 else build_cotizacion_pdf(q_rows[0], [])
                if not pdf_bytes:
                    return f"Error al generar el archivo PDF para la cotización {folio}."
                
                import random
                butler_quotes = [
                    "Es un honor servirle. He preparado y despachado el documento solicitado con la mayor diligencia.",
                    "Como siempre, me he tomado la libertad de gestionar el envío de este documento para facilitar sus labores.",
                    "Hecho. He enviado la cotización adjunta. Avíseme si requiere que prepare alguna bebida o asista en otra labor.",
                    "El archivo ha sido enviado. Quedo a su entera disposición para cualquier requerimiento adicional, señor.",
                    "Confirmado. El reporte digital ha sido enviado al buzón indicado de forma inmediata."
                ]
                quote = random.choice(butler_quotes)
                
                from api.main import send_email_with_multiple_pdfs
                success, msg_err = send_email_with_multiple_pdfs(
                    to_email=target_email,
                    subject=f"ECCSA IA: Cotización de Materiales {folio}",
                    body=f"Hola,\n\n{quote}\n\nAquí tienes el PDF de la cotización {folio} que solicitaste.\n\nSaludos,\nECCSA IA",
                    attachments=[(pdf_bytes, f"Cotizacion_{folio}.pdf")] if pdf_bytes else [],
                    sender_name="ECCSA IA",
                    sender_email="robot@ecc-sa.com.mx"
                )
                if success:
                    return f"La cotización {folio} ha sido generada en PDF y enviada a {target_email} exitosamente."
                else:
                    return f"Error SMTP al enviar el correo: {msg_err}"
            except Exception as ex:
                return f"Error al procesar la cotización: {str(ex)}"

        def send_service_reports(folios: list, recipient_email: str = None) -> str:
            """Genera los PDFs de los folios de reporte indicados y los envía consolidados al correo."""
            target_email = (recipient_email or user_email).strip()
            try:
                attachments = []
                for f in folios:
                    f_clean = f.strip()
                    rep_rows = execute_readonly_sql(f"SELECT * FROM HUB_RegistroReportes WHERE Folio = '{f_clean}'")
                    if not rep_rows or "Error" in rep_rows[0]:
                        continue
                    pdf_bytes = build_service_report_pdf(rep_rows[0], [], [], None)
                    if pdf_bytes:
                        attachments.append((pdf_bytes, f"Reporte_Servicio_{f_clean}.pdf"))
                
                if not attachments:
                    return "No se pudieron generar los PDFs de los folios provistos."
                
                import random
                butler_quotes = [
                    "Cumpliendo con su solicitud, he recopilado y enviado los reportes de servicio técnico pertinentes.",
                    "Los reportes de campo solicitados ya han sido despachados a su correo. Espero sean de utilidad.",
                    "Operación completada. Adjunto el historial de servicios técnicos solicitados.",
                    "He enviado la correspondencia electrónica con los adjuntos correspondientes. Quedo atento a nuevas instrucciones."
                ]
                quote = random.choice(butler_quotes)
                
                from api.main import send_email_with_multiple_pdfs
                success, msg_err = send_email_with_multiple_pdfs(
                    to_email=target_email,
                    subject=f"ECCSA IA: Reportes de Servicio Técnico",
                    body=f"Hola,\n\n{quote}\n\nAdjunto a este correo encontrarás los reportes de servicio que solicitaste:\n{', '.join(folios)}\n\nSaludos,\nECCSA IA",
                    attachments=attachments,
                    sender_name="ECCSA IA",
                    sender_email="robot@ecc-sa.com.mx"
                )
                if success:
                    return f"Se han enviado los reportes ({', '.join(folios)}) en PDF a {target_email} exitosamente."
                else:
                    return f"Error SMTP al enviar los reportes por correo: {msg_err}"
            except Exception as ex:
                return f"Error al procesar reportes: {str(ex)}"

        tools_dict = {
            "execute_query": execute_query,
            "send_quote_pdf": send_quote_pdf,
            "send_service_reports": send_service_reports
        }

        # 6. System instruction CLON EXACTO del HUB
        system_instruction = f"""Eres ECCSA IA, el asistente de inteligencia artificial personalizado de ECCSA Automation.
Te estás comunicando con el usuario {user_name} cuyo correo electrónico es {user_email} (su IdUsuario es {user_id}).
Debes dirigirte a él o ella por su nombre de pila ({user_name}) y hablar de forma extremadamente formal, servicial y profesional.

Tienes acceso directo de consulta a la base de datos de ECCSA mediante la herramienta `execute_query`.
ESTRUCTURA DE NUESTRAS TABLAS EN SQL SERVER:
1. `HUB_Users` (Id, Email, Nombre, Activo, FechaIngreso)
2. `IndiceMateriales` (Folio, IdCliente, Contacto, Fecha, Descripcion, Autor, Color) -- Contiene el encabezado de las cotizaciones de materiales.
3. `Partidas` (Folio, Partida, Cantidad, Descripcion, PrecioCompraUnitario, Factor, Proveedor, TiempoEntregaDias, Dolar, Flete) -- Contiene las partidas/artículos de las cotizaciones de materiales.
4. `HUB_RegistroReportes` (IdReporte, Folio, Cliente, Contacto, CorreoContacto, FechaHoraInicio, FechaHoraFin, TiempoTraslado, TiempoComida, Tecnico, DescripcionServicio, Notas, Estatus)
5. `HUB_HorasExtrasRegistros` (Id, IdUsuario, Fecha, HoraEntrada, HoraSalida, HorasComida, HorasTraslado, HorasExtrasCalculadas, Descripcion, Cliente, Estatus)
6. `HUB_VacacionesRegistros` (Id, IdUsuario, Fecha, Tipo, Comentarios)
7. `clientes` (IdCliente, Cliente, Contacto, Telefono, Email) -- Catálogo de clientes de la empresa.
8. `vw_ResumenCotizaciones` (Folio, IdCliente, Cliente, Contacto, Fecha, DescripcionGeneral, Autor, Estatus, SumaPartidas, FleteCotizacion, Subtotal, IVA, TotalFinal) -- Vista útil para consultar resúmenes de cotizaciones.

REGLAS DE SEGURIDAD:
- Solo ejecuta consultas SQL SELECT de lectura. Tienes prohibido alterar nada en la base de datos.
- Si el usuario NO es Administrador (Administrador es cuando is_admin={is_admin} es True, actualmente is_admin={is_admin}), solo puedes mostrarle información perteneciente a su propio IdUsuario ({user_id}) de las tablas de horas extras, vacaciones, reportes de servicio, etc. Para esto, siempre inyecta la condición `IdUsuario = {user_id}` en tus consultas SQL.
- Tienes prohibido inventar o consultar datos de nómina u horas de otros usuarios si el usuario no es administrador.

HABILIDADES DE ENVÍO DE DOCUMENTOS:
- Si el usuario te pide que le envíes una cotización, llama a la herramienta `send_quote_pdf` pasándole el folio. Puede enviar a otro correo o usuario si te lo especifica en el argumento `recipient_email`.
- Si te pide que le envíes reportes de servicio por correo, llama a la herramienta `send_service_reports` pasándole la lista de folios. Puede enviar a otro correo o usuario si te lo especifica en el argumento `recipient_email`.

CONTESTAR PREGUNTAS GENERALES:
- Puedes contestar libremente sobre cualquier otro tema (SAT, cotizaciones, explicaciones técnicas, cálculos matemáticos, redacción de correos profesionales, etc.) usando tu propio conocimiento general. Si te preguntan por códigos del SAT para partidas de cotización, haz una consulta a las partidas de la cotización pedida, analiza los productos, sugiere las claves del SAT más convenientes y explica el porqué.

Sé claro, directo, estructurado y presenta los datos de forma elegante en tablas Markdown cuando corresponda.
"""

        # 7. Llamar a Gemini con function calling
        import google.generativeai as genai
        import google.ai.generativelanguage as glm
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            tools=[execute_query, send_quote_pdf, send_service_reports]
        )
        
        chat = model.start_chat(history=historial[:-1] if len(historial) > 1 else [])
        response = chat.send_message(body.contenido)

        # 8. Handle Function Calling loop (max 8 loops como HUB)
        loop_count = 0
        while response.candidates and response.candidates[0].content.parts and loop_count < 8:
            has_fcall = False
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    has_fcall = True
                    name_tool = part.function_call.name
                    args = dict(part.function_call.args)
                    
                    if name_tool in tools_dict:
                        tool_func = tools_dict[name_tool]
                        func_result = tool_func(**args)
                        
                        response = chat.send_message(
                            glm.Content(
                                parts=[
                                    glm.Part(
                                        function_response=glm.FunctionResponse(
                                            name=name_tool,
                                            response={'result': func_result}
                                        )
                                    )
                                ]
                            )
                        )
                        break
            
            if not has_fcall:
                break
            loop_count += 1
        
        # 9. Obtener respuesta final
        try:
            respuesta = response.text.strip()
        except Exception:
            texts = [p.text for p in response.candidates[0].content.parts if p.text]
            respuesta = "".join(texts).strip() if texts else "🤖 *ECCSA IA*: Disculpe la molestia, señor. He procesado la consulta en nuestra base de datos, pero la respuesta no contiene texto legible."

        # 10. Guardar respuesta del model
        cursor.execute("""
            INSERT INTO HUB_JarvisMensajes (IdConversacion, [Role], Contenido)
            VALUES (%s, 'model', %s)
        """, (id_conversacion, respuesta))

        # 11. Auto-título si es primera conversación (título = primeras 50 chars del primer mensaje)
        cursor.execute("SELECT Titulo FROM HUB_JarvisConversaciones WHERE Id = %s", (id_conversacion,))
        titulo_row = cursor.fetchone()
        titulo_actual = titulo_row[0] if titulo_row else "Nueva conversación"
        nuevo_titulo = titulo_actual
        if titulo_actual == "Nueva conversación":
            corto = body.contenido[:50].strip()
            if len(body.contenido) > 50:
                corto += "..."
            nuevo_titulo = corto
            cursor.execute("UPDATE HUB_JarvisConversaciones SET Titulo = %s WHERE Id = %s", (nuevo_titulo, id_conversacion))

        conn.commit()

        # 12. Devolver mensajes actualizados
        cursor.execute("""
            SELECT Id, [Role], Contenido, FechaRegistro
            FROM HUB_JarvisMensajes
            WHERE IdConversacion = %s
            ORDER BY FechaRegistro ASC, Id ASC
        """, (id_conversacion,))
        rows = cursor.fetchall()
        conn.close()

        mensajes = [{"Id": r[0], "Role": r[1], "Contenido": r[2], "FechaRegistro": r[3]} for r in rows]
        return {"mensajes": mensajes, "titulo": nuevo_titulo}
        
    except HTTPException:
        raise
    except Exception as e:
        # En caso de error, guardar mensaje de error
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO HUB_JarvisMensajes (IdConversacion, [Role], Contenido) VALUES (%s, 'model', %s)",
                          (id_conversacion, f"🤖 *ECCSA IA*: Disculpe, he experimentado un percance técnico al procesar su solicitud. Detalle del error: {str(e)}"))
            conn.commit()
            conn.close()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.delete("/api/ia/conversaciones/{id_conversacion}")
async def ia_delete_conversacion(id_conversacion: int, current_user: dict = Depends(get_current_user)):
    _require_ia(current_user)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM HUB_JarvisConversaciones WHERE Id = %s AND IdUsuario = %s", (id_conversacion, current_user["id"]))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        conn.commit()
        conn.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- Passkeys (WebAuthn) — port desde Field -----------------------------------
# Autenticación con huella / Face ID usando la tabla compartida HUB_Passkeys.
# IMPORTANTE: desde este subdominio (admon.ecc-sa.com.mx) el navegador SOLO
# permite passkeys con rpId = ecc-sa.com.mx (el rp raíz). Las passkeys legacy
# (rpId field./hub.ecc-sa.com.mx) NO se pueden usar aquí: el navegador rechaza
# cualquier rpId que no sea sufijo del dominio actual (SecurityError). Por eso
# el registro SIEMPRE usa el rp nuevo y el login también.
import base64 as _passkey_b64
import time as _passkey_time
from urllib.parse import urlparse as _urlparse

import jwt as _pyjwt
from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

RP_ID = "ecc-sa.com.mx"  # rp raíz: funciona en cualquier subdominio (hub, field, admon)
RP_NAME = "ECCSA"
CHALLENGE_TTL = 5 * 60  # desafíos de 5 minutos

_PASSKEY_SECRET_CACHE: Dict[str, str] = {}


def _passkey_secret() -> str:
    """Secreto para los JWT stateless de los challenges.
    Orden: env JWT_SECRET > HUB_Config 'admon_passkey_secret' (se genera y
    persiste la primera vez) > fallback temporal (solo si la BD no responde)."""
    if _PASSKEY_SECRET_CACHE.get("secret"):
        return _PASSKEY_SECRET_CACHE["secret"]
    env = os.getenv("JWT_SECRET") or os.getenv("PASSKEY_JWT_SECRET")
    if env:
        _PASSKEY_SECRET_CACHE["secret"] = env
        return env
    secret = None
    try:
        conn = get_connection()
        cursor = conn.cursor(as_dict=True)
        cursor.execute("SELECT Valor FROM HUB_Config WHERE Clave = 'admon_passkey_secret'")
        row = cursor.fetchone()
        secret = (row.get("Valor") or "").strip() if row else ""
        if not secret:
            secret = _passkey_b64.urlsafe_b64encode(os.urandom(48)).decode("ascii").rstrip("=")
            cursor.execute(
                "UPDATE HUB_Config SET Valor = %s, Actualizado = GETDATE() WHERE Clave = 'admon_passkey_secret'",
                (secret,),
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO HUB_Config (Clave, Valor) VALUES (%s, %s)",
                    ("admon_passkey_secret", secret),
                )
        conn.close()
    except Exception:
        secret = "admon-passkey-boot-secret"  # inestable: solo si la BD falla
    _PASSKEY_SECRET_CACHE["secret"] = secret
    return secret


def _is_allowed_origin(origin: str) -> bool:
    """Allowlist: https://ecc-sa.com.mx o cualquier subdominio (*.ecc-sa.com.mx),
    más localhost para desarrollo."""
    if not origin:
        return False
    p = _urlparse(origin)
    if p.hostname in ("localhost", "127.0.0.1"):
        return True
    if p.scheme != "https":
        return False
    host = p.hostname or ""
    return host == "ecc-sa.com.mx" or host.endswith(".ecc-sa.com.mx")


def _origin_for_request(request: Request) -> str:
    """Origin real de la petición, validado contra la allowlist."""
    origin = request.headers.get("origin", "") if request else ""
    if not _is_allowed_origin(origin):
        raise HTTPException(status_code=400, detail="Origin no permitido")
    return origin


def _b64url_encode(raw: bytes) -> str:
    return _passkey_b64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _issue_challenge(purpose: str):
    """Challenge aleatorio envuelto en JWT stateless (seguro entre reinicios)."""
    raw = os.urandom(32)
    now = int(_passkey_time.time())
    token = _pyjwt.encode(
        {"purpose": purpose, "ch": _b64url_encode(raw), "iat": now, "exp": now + CHALLENGE_TTL},
        _passkey_secret(),
        algorithm="HS256",
    )
    return token, raw


def _read_challenge(state: str, purpose: str) -> bytes:
    try:
        data = _pyjwt.decode(state, _passkey_secret(), algorithms=["HS256"])
    except _pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Desafío expirado, intenta de nuevo")
    except _pyjwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Desafío inválido")
    if data.get("purpose") != purpose or not data.get("ch"):
        raise HTTPException(status_code=400, detail="Desafío inválido")
    return base64url_to_bytes(data["ch"])


def _login_row_by_id(user_id: int):
    """Fila completa (misma forma que api_login) para armar la respuesta de sesión."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT Id, Nombre, Email, Password, Activo, AccesoInventario, AccesoNominas, "
        "AccesoCotizaciones, AccesoProveedores, AccesoOC, AccesoCalculo, AccesoTelegram, "
        "AccesoUsuarios, AccesoReportes, AccesoRegistroReportes, AccesoIA, Nickname "
        "FROM HUB_Users WHERE Id = %s",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


# --- Modelos ---

class PasskeyRegisterOptionsReq(BaseModel):
    label: str = ""


class PasskeyRegisterVerifyReq(BaseModel):
    credential: dict
    state: str
    label: str = ""


class PasskeyLoginOptionsReq(BaseModel):
    rp: str = RP_ID  # el frontend siempre manda ecc-sa.com.mx (único rp válido aquí)


class PasskeyLoginVerifyReq(BaseModel):
    credential: dict
    state: str


@app.post("/api/passkeys/login/options")
async def passkey_login_options(body: PasskeyLoginOptionsReq = None):
    """Opciones de login discoverable (sin correo) para el rp raíz."""
    try:
        state, challenge = _issue_challenge("wk_login")
        options = generate_authentication_options(rp_id=RP_ID, challenge=challenge)
        return {"options": options_to_json(options), "state": state, "rp": RP_ID}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Passkey error: {str(e)}")


@app.post("/api/passkeys/login/verify")
async def passkey_login_verify(body: PasskeyLoginVerifyReq, request: Request = None):
    """Valida el assertion y devuelve la sesión igual que /api/auth/login."""
    challenge = _read_challenge(body.state, "wk_login")
    origin = _origin_for_request(request)
    cred_id = body.credential.get("id", "")
    conn = get_connection()
    cursor = conn.cursor(as_dict=True)
    cursor.execute("SELECT * FROM HUB_Passkeys WHERE CredentialId = %s", (cred_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Passkey no reconocida en este equipo")
    # Passkeys legacy (field./hub.) no se pueden usar desde admon: el navegador
    # exige que el rpId coincida con el dominio actual.
    cred_rp = (row.get("RpId") or RP_ID).strip() or RP_ID
    if cred_rp != RP_ID:
        raise HTTPException(
            status_code=401,
            detail="Tu passkey es de otra app (Field/HUB). Crea una aquí con ＋ Agregar este equipo.",
        )
    # El userHandle debe corresponder al dueño de la credencial
    try:
        raw_handle = body.credential.get("response", {}).get("userHandle")
        handle_uid = int(base64url_to_bytes(raw_handle).decode("utf-8")) if raw_handle else row["IdUsuario"]
    except Exception:
        handle_uid = row["IdUsuario"]
    if handle_uid != row["IdUsuario"]:
        raise HTTPException(status_code=401, detail="Passkey no válida para este usuario")
    try:
        v = verify_authentication_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=RP_ID,
            expected_origin=origin,
            credential_public_key=_passkey_b64.urlsafe_b64decode(row["PublicKey"] + "=="),
            credential_current_sign_count=row["SignCount"],
            require_user_verification=False,
        )
    except Exception as e:
        print(f"[passkey] login FAIL cred={cred_id[:12]}: {e}", flush=True)
        raise HTTPException(status_code=401, detail="No se pudo verificar la passkey")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE HUB_Passkeys SET SignCount = %s, UltimoUso = GETDATE() WHERE Id = %s",
            (v.new_sign_count, row["Id"]),
        )
        conn.close()
    except Exception:
        pass  # el sign count es anti-replay best effort; no bloquea el login
    user_row = _login_row_by_id(row["IdUsuario"])
    if not user_row or not user_row[4]:
        raise HTTPException(status_code=401, detail="Usuario no válido o inactivo")
    print(f"[passkey] login OK uid={user_row[0]}", flush=True)
    return _build_login_response(user_row[2], user_row)


@app.post("/api/passkeys/register/options")
async def passkey_register_options(
    body: PasskeyRegisterOptionsReq = None,
    current_user: dict = Depends(get_current_user),
    request: Request = None,
):
    """Options de registro (requiere sesión). Siempre en el rp raíz."""
    origin = _origin_for_request(request)
    conn = get_connection()
    cursor = conn.cursor(as_dict=True)
    cursor.execute(
        "SELECT CredentialId FROM HUB_Passkeys WHERE IdUsuario = %s",
        (current_user["id"],),
    )
    existing = [dict(r) for r in cursor.fetchall()]
    conn.close()
    exclude = []
    for c in existing:
        try:
            exclude.append(PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["CredentialId"])))
        except Exception:
            continue
    state, challenge = _issue_challenge("wk_reg")
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(current_user["id"]).encode("utf-8"),
        user_name=current_user["email"],
        user_display_name=current_user["nombre"],
        challenge=challenge,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=exclude or None,
    )
    return {"options": options_to_json(options), "state": state}


@app.post("/api/passkeys/register/verify")
async def passkey_register_verify(
    body: PasskeyRegisterVerifyReq,
    current_user: dict = Depends(get_current_user),
    request: Request = None,
):
    """Valida el attestation y guarda la passkey en HUB_Passkeys."""
    challenge = _read_challenge(body.state, "wk_reg")
    origin = _origin_for_request(request)
    try:
        v = verify_registration_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=RP_ID,
            expected_origin=origin,
        )
    except Exception as e:
        print(f"[passkey] register FAIL uid={current_user['id']}: {e}", flush=True)
        raise HTTPException(status_code=400, detail="No se pudo registrar la passkey")
    cred_id = _b64url_encode(v.credential_id)
    pubkey = _b64url_encode(v.credential_public_key)
    transports = ",".join(body.credential.get("transports", []) or [])
    label = (body.label or "Mi equipo")[:100]
    try:
        conn = get_connection()
        cursor = conn.cursor(as_dict=True)
        cursor.execute("SELECT Id FROM HUB_Passkeys WHERE CredentialId = %s", (cred_id,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Esta passkey ya está registrada")
        cursor.execute(
            "INSERT INTO HUB_Passkeys (IdUsuario, CredentialId, PublicKey, SignCount, Transports, Etiqueta, RpId) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (current_user["id"], cred_id, pubkey, v.sign_count, transports, label, RP_ID),
        )
        # Nickname de Legends: inicializar SOLO si está vacío (no sobrescribir)
        cursor.execute("SELECT Nickname FROM HUB_Users WHERE Id = %s", (current_user["id"],))
        u = cursor.fetchone()
        nick = (u.get("Nickname") or "").strip() if u else ""
        if not nick:
            cursor.execute("UPDATE HUB_Users SET Nickname = %s WHERE Id = %s", (label, current_user["id"]))
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar la passkey: {str(e)}")
    print(f"[passkey] register OK uid={current_user['id']} label={label}", flush=True)
    return {"ok": True}


@app.get("/api/passkeys/mine")
async def passkey_mine(current_user: dict = Depends(get_current_user)):
    """Passkeys del usuario con badge nueva/legacy para la UI."""
    conn = get_connection()
    cursor = conn.cursor(as_dict=True)
    cursor.execute(
        "SELECT Id, Etiqueta, FechaCreacion, UltimoUso, RpId FROM HUB_Passkeys "
        "WHERE IdUsuario = %s ORDER BY FechaCreacion DESC",
        (current_user["id"],),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        for k in ("FechaCreacion", "UltimoUso"):
            if r.get(k) is not None:
                r[k] = str(r[k])
        rp = (r.get("RpId") or "").strip()
        r["EsNueva"] = rp == RP_ID
    return {"passkeys": rows}


@app.delete("/api/passkeys/{pid}")
async def passkey_delete(pid: int, current_user: dict = Depends(get_current_user)):
    """Elimina una passkey propia."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM HUB_Passkeys WHERE Id = %s AND IdUsuario = %s", (pid, current_user["id"]))
    deleted = cursor.rowcount
    conn.close()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Passkey no encontrada")
    return {"ok": True}


# --- Servir frontend compilado (dist/) si existe; si no, la API sigue sola ---
# El build de Vite genera dist/ y Docker lo copia a la imagen. Este bloque
# (definido AL FINAL para no tapar las rutas de la API) sirve:
#   "/"            -> index.html de la SPA (o JSON si no hay dist/)
#   "/assets/..."  -> archivos estáticos del build
#   "/admon_logo.png", favicon, etc. -> archivos de dist/
#   "/login", "/dashboard", ... -> index.html (client-side routing)
try:
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    _dist = Path(__file__).resolve().parent.parent / "dist"
    _has_spa = _dist.is_dir() and (_dist / "index.html").exists()
    if _has_spa and (_dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    _SPA_ROUTES = {"login", "dashboard", "cotizaciones", "cotizaciones_materiales", "usuarios", "telegram", "config", "clientes", "registro_reportes", "registro_reportes/", "ia"}
    # Shell y PWA nunca se cachean (el bundle js/css usa hashes y sí se cachea)
    _NO_STORE = {"Cache-Control": "no-store, must-revalidate"}
    _NO_STORE_FILES = {"index.html", "sw.js", "manifest.webmanifest"}

    def _spa_file(name: str):
        resp = FileResponse(str(_dist / name))
        resp.headers.update(_NO_STORE)
        return resp

    @app.get("/")
    async def spa_root():
        if _has_spa:
            return _spa_file("index.html")
        return {"message": "HUB Admon API", "version": "1.0.0"}

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # 1) Archivo real de dist/ (logo, favicon, iconos, etc.)
        if _has_spa:
            candidate = (_dist / full_path)
            try:
                # Evitar path traversal fuera de dist/
                candidate.resolve().relative_to(_dist.resolve())
            except ValueError:
                raise HTTPException(status_code=404, detail="Not found")
            if full_path and candidate.is_file():
                resp = FileResponse(str(candidate))
                if candidate.name in _NO_STORE_FILES:
                    resp.headers.update(_NO_STORE)
                return resp
            # 2) Ruta de la SPA -> index.html (el router del frontend decide)
            first = full_path.split("/", 1)[0]
            if first in _SPA_ROUTES:
                return _spa_file("index.html")
        raise HTTPException(status_code=404, detail="Not found")
except Exception:
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)