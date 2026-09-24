from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
import pymssql
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

app = FastAPI(title="HUB Admon API", version="1.0.0")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

DB_SERVER = os.getenv("HUB_DB_SERVER", "172.26.117.220")
DB_USER = os.getenv("HUB_DB_USER", "sa")
DB_PASSWORD = os.getenv("HUB_DB_PASSWORD", "eyccazo")
DB_DATABASE = os.getenv("HUB_DB_DATABASE", "ECCSA_Admon")


def get_connection():
    conn = pymssql.connect(server=DB_SERVER, user=DB_USER, password=DB_PASSWORD, database=DB_DATABASE, autocommit=True)
    return conn


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


# --- Auth Dependency ---

def get_current_user(token: str = Depends(oauth2_scheme)):
    # Simple JWT validation - in production use PyJWT
    # For now, validate token format and check against DB
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Decode simple token (email|timestamp format)
        parts = token.split("|")
        if len(parts) >= 2:
            email = parts[0]
            cursor.execute("SELECT Id, Nombre, Email, AccesoInventario, AccesoNominas, AccesoCotizaciones, AccesoProveedores, AccesoOC, AccesoCalculo, AccesoTelegram, AccesoUsuarios FROM HUB_Users WHERE LTRIM(RTRIM(Email)) = %s", (email.strip().lower(),))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "id": row[0],
                    "nombre": row[1],
                    "email": row[2],
                    "acceso_inventario": row[3] == 1,
                    "acceso_nominas": row[4] == 1,
                    "acceso_cotizaciones": row[5] == 1,
                    "acceso_proveedores": row[6] == 1,
                    "acceso_oc": row[7] == 1,
                    "acceso_calculo": row[8] == 1,
                    "acceso_telegram": row[9] == 1,
                    "acceso_usuarios": row[10] == 1,
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth error: {str(e)}")
    raise HTTPException(status_code=401, detail="Invalid token")


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

@app.post("/token")
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
    #      AccesoTelegram, AccesoUsuarios
    b = lambda i: (row[i] == 1) if len(row) > i and row[i] is not None else False
    user = {
        "id": row[0], "nombre": row[1], "email": row[2],
        "acceso_inventario": b(5), "acceso_nominas": b(6),
        "acceso_cotizaciones": b(7), "acceso_proveedores": b(8),
        "acceso_oc": b(9), "acceso_calculo": b(10),
        "acceso_telegram": b(11), "acceso_usuarios": b(12),
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
        cursor.execute("SELECT Id, Nombre, Email, Password, Activo, AccesoInventario, AccesoNominas, AccesoCotizaciones, AccesoProveedores, AccesoOC, AccesoCalculo, AccesoTelegram, AccesoUsuarios FROM HUB_Users WHERE LTRIM(RTRIM(Email)) = %s", (body.email.strip().lower(),))
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

@app.get("/users/me", response_model=UserInfo)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserInfo(**current_user)


@app.get("/users", response_model=List[UserInfo])
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


# --- Inventory endpoints ---

@app.get("/inventory/items")
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


@app.get("/inventory/items/{item_id}")
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


# --- Cotizaciones materiales endpoints ---

class Partida(BaseModel):
    id: Optional[int] = None
    tipo: str = "MATERIAL"
    cantidad: float = 1.0
    descripcion: str = ""
    modelo: str = ""
    proveedor: str = ""
    precio_unitario: float = 0.0
    precio_venta_total: float = 0.0


class CotizacionMateriales(BaseModel):
    id: Optional[int] = None
    folio: str = ""
    id_cliente: str = ""
    contacto: str = ""
    descripcion: str = ""
    departamento: str = ""
    elabora: str = ""
    tasa_dolar: float = 20.0
    subtotal_servicios: float = 0.0
    subtotal_materiales: float = 0.0
    subtotal: float = 0.0
    iva: float = 0.0
    total: float = 0.0
    estatus: str = "PENDIENTE"
    notas: str = ""
    partidas: List[Partida] = []


class ItemCreate(BaseModel):
    tipo: str = "MATERIAL"
    cantidad: float = 1.0
    descripcion: str = ""
    modelo: str = ""
    proveedor: str = ""
    precio_unitario: float = 0.0


@app.post("/cotizaciones/materiales")
async def crear_cotizacion_materiales(cot: CotizacionMateriales, current_user: dict = Depends(get_current_user)):
    if not current_user["acceso_cotizaciones"]:
        raise HTTPException(status_code=403, detail="No access")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Calculate totals
        subtotal_materiales = 0.0
        for item in cot.partidas:
            subtotal_materiales += item.precio_unitario * item.cantidad
        
        iva = subtotal_materiales * 0.16
        total = subtotal_materiales + iva
        
        folio = f"CM-{datetime.now().strftime('%Y')}-{datetime.now().strftime('%m')}-{datetime.now().strftime('%d')}"
        
        cursor.execute("""
            INSERT INTO IndiceMateriales (Folio, IdCliente, Contacto, Descripcion, Departamento, Elabora, 
                TasaDolar, SubtotalServicios, SubtotalMateriales, Subtotal, IVA, Total, Estatus, Notas, FechaCreacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, GETDATE())
        """, (folio, cot.id_cliente, cot.contacto, cot.descripcion, cot.departamento, 
              cot.elabora, cot.tasa_dolar, cot.subtotal_servicios, subtotal_materiales, 
              subtotal_materiales, iva, total, cot.estatus, cot.notas))
        
        cursor.execute("SELECT SCOPE_IDENTITY()")
        id_row = cursor.fetchone()
        nueva_id = id_row[0] if id_row else None
        
        # Insert partidas
        for item in cot.partidas:
            cursor.execute("""
                INSERT INTO Partidas (IdIndice, Tipo, Cantidad, Descripcion, Modelo, Proveedor, PrecioUnitario, PrecioVentaTotal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nueva_id, item.tipo, item.cantidad, item.descripcion, item.modelo, 
                  item.proveedor, item.precio_unitario, item.precio_venta_total))
        
        conn.close()
        
        return {"folio": folio, "id": nueva_id, "message": "Cotización de materiales creada exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating cotización: {str(e)}")


@app.get("/cotizaciones/materiales")
async def listar_cotizaciones_materiales(current_user: dict = Depends(get_current_user)):
    if not current_user["acceso_cotizaciones"]:
        raise HTTPException(status_code=403, detail="No access")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Id, Folio, IdCliente, Contacto, Descripcion, Departamento, Elabora, 
                   TasaDolar, SubtotalMateriales, Subtotal, IVA, Total, Estatus, Notas, FechaCreacion
            FROM IndiceMateriales ORDER BY FechaCreacion DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append({
                "id": row[0], "folio": row[1], "id_cliente": row[2], "contacto": row[3],
                "descripcion": row[4], "departamento": row[5], "elabora": row[6],
                "tasa_dolar": row[7], "subtotal_materiales": float(row[8]) if row[8] else 0.0,
                "subtotal": float(row[9]) if row[9] else 0.0,
                "iva": float(row[10]) if row[10] else 0.0,
                "total": float(row[11]) if row[11] else 0.0,
                "estatus": row[12], "notas": row[13], "fecha_creacion": str(row[14]) if row[14] else ""
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/cotizaciones/materiales/{cot_id}")
async def obtener_cotizacion_materiales(cot_id: int, current_user: dict = Depends(get_current_user)):
    if not current_user["acceso_cotizaciones"]:
        raise HTTPException(status_code=403, detail="No access")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Id, Folio, IdCliente, Contacto, Descripcion, Departamento, Elabora, 
                   TasaDolar, SubtotalMateriales, Subtotal, IVA, Total, Estatus, Notas, FechaCreacion
            FROM IndiceMateriales WHERE Id = %s
        """, (cot_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0], "folio": row[1], "id_cliente": row[2], "contacto": row[3],
                "descripcion": row[4], "departamento": row[5], "elabora": row[6],
                "tasa_dolar": row[7], "subtotal_materiales": float(row[8]) if row[8] else 0.0,
                "subtotal": float(row[9]) if row[9] else 0.0,
                "iva": float(row[10]) if row[10] else 0.0,
                "total": float(row[11]) if row[11] else 0.0,
                "estatus": row[12], "notas": row[13], "fecha_creacion": str(row[14]) if row[14] else ""
            }
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/cotizaciones/materiales/{cot_id}/partidas")
async def obtener_partidas_cotizacion(cot_id: int, current_user: dict = Depends(get_current_user)):
    if not current_user["acceso_cotizaciones"]:
        raise HTTPException(status_code=403, detail="No access")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Id, Tipo, Cantidad, Descripcion, Modelo, Proveedor, PrecioUnitario, PrecioVentaTotal
            FROM Partidas WHERE IdIndice = %s
        """, (cot_id,))
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append({
                "id": row[0], "tipo": row[1], "cantidad": row[2], "descripcion": row[3],
                "modelo": row[4], "proveedor": row[5], "precio_unitario": float(row[6]) if row[6] else 0.0,
                "precio_venta_total": float(row[7]) if row[7] else 0.0
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- Dashboard endpoint ---

class KPIData(BaseModel):
    modulo: str
    valor: float
    etiqueta: str


@app.get("/dashboard/kpis")
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
        
        # Cotizaciones KPI
        if current_user["acceso_cotizaciones"]:
            cursor.execute("SELECT COUNT(*) FROM IndiceMateriales WHERE Estatus = 'PENDIENTE'")
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

@app.post("/pdf/generate")
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

    _SPA_ROUTES = {"login", "dashboard", "cotizaciones_materiales", "usuarios", "telegram", "config"}
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