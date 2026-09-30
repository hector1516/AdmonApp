"""Códigos SAT CFDI 4.0 para partidas de cotizaciones de materiales.

Implementa el plan "Tabla de códigos SAT auto-alimentada" (PlanesFuturos.md §1)
adaptado a la regla de desarrollo de esta fase: SOLO se agregan tablas nuevas
(HUB_SatArticulos + sidecar HUB_PartidasSat), ninguna tabla existente se altera.

Orden de resolución (reglas duras de ahorro de tokens):
  1. Sidecar HUB_PartidasSat por (Folio, Partida) con la MISMA descripción
     normalizada → 0 llamadas (partida que no cambió = no re-preguntar).
  2. Índice HUB_SatArticulos por ClaveNormalizada → 0 llamadas (material repetido).
  3. Reglas de keywords locales (PLC, motor, bomba…) → 0 llamadas.
  4. 1 sola llamada a Gemini por partida nueva; prompt corto, respuesta JSON de
     4 campos (códigos + artículo genérico); si no hay API key o falla → la
     partida se guarda SIN códigos (nunca se rompe el guardado por la IA).

Fuente en ambos: 'SEED' (reglas), 'IA' (Gemini) o 'MANUAL' (captura del usuario).

OJO con el artículo genérico ('controlador lógico', 'disyuntor'): NO se guarda
en estas tablas, vive en Partidas.ArticuloGenerico (migración Admon 0043) porque
es una propiedad de la partida, no del catálogo SAT. Aquí solo se SUGIERE
(botón 🤖 → sugerir_para_ui) y se imprime en el PDF antes del código y la unidad.
"""

import json
import re
import unicodedata

# ---------------------------------------------------------------------------
# Normalización (llave de lookup compartida por índice y sidecar)
# ---------------------------------------------------------------------------

def normalizar(descripcion: str) -> str:
    """lower + trim + sin acentos + espacios colapsados. Devuelve '' si no hay texto."""
    if not descripcion:
        return ""
    d = str(descripcion).strip().lower()
    d = "".join(c for c in unicodedata.normalize("NFKD", d) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", d)


# ---------------------------------------------------------------------------
# 3) Reglas de keywords locales (0 tokens) — extendidas del HUB
# (en el HUB varias keywords estaban en minúsculas y tras .upper() nunca
#  matcheaban; aquí se normaliza todo y se añaden variantes sin acento)
# ---------------------------------------------------------------------------

# Estructura: (lista de keywords, clave producto/servicio, clave unidad,
#              artículo genérico de compras — cómo se llama sin marca ni modelo)
REGLAS = [
    (["PLC", "CONTROL LOGICO PROGRAMABLE"], "44101701", "H87", "controlador lógico"),
    (["MOTOR", "MOTOR ELECTRICO"], "84039000", "H87", "motor eléctrico"),
    (["BOMBA"], "84131000", "H87", "bomba"),
    (["VALVULA"], "84818000", "H87", "válvula"),
    (["SENSOR"], "90278000", "H87", "sensor"),
    (["TRANSFORMADOR"], "85044090", "H87", "transformador"),
    (["CONTROLADOR"], "84799090", "H87", "controlador"),
    (["INVERSOR"], "85044090", "H87", "inversor"),
    (["PANEL"], "85389000", "H87", "panel de control"),
    (["MEDIDOR"], "90278000", "H87", "medidor"),
    (["MANOMETRO"], "90268000", "H87", "manómetro"),
    (["MANGUERA"], "40092200", "MTR", "manguera"),
    (["ACOPLAMIENTO"], "84129000", "H87", "acoplamiento"),
    (["JUNTA"], "40169100", "H87", "junta"),
    (["BALANZA"], "84233000", "H87", "balanza"),
    (["BASURA", "RESIDUO"], "38249900", "H87", "material de limpieza"),
    (["SOFTWARE", "LICENCIA"], "44111200", "E48", "licencia de software"),
]


def buscar_interna(descripcion: str):
    """Búsqueda por keywords en la descripción.
    Devuelve (clave, unidad, artículo genérico) o None."""
    d = normalizar(descripcion)
    if not d:
        return None
    d_up = d.upper()
    for keywords, clave, unidad, generico in REGLAS:
        for kw in keywords:
            if kw in d_up:
                return clave, unidad, generico
    return None


# ---------------------------------------------------------------------------
# 4) Gemini (1 sola llamada por partida nueva, solo en miss total)
# ---------------------------------------------------------------------------

def _cfg_ia(cur):
    """ApiKey + Modelo de HUB_AiConfig (misma fuente que la IA ECCSA).
    La columna del modelo se llama Model (fallback Modelo por si cambia)."""
    for col in ("Model", "Modelo"):
        try:
            cur.execute(f"SELECT ApiKey, {col} FROM HUB_AiConfig WHERE Id = 1")
            r = cur.fetchone()
            if r and r[0]:
                return str(r[0]).strip(), (str(r[1]).strip() if r[1] else None)
            return None, None
        except Exception:
            continue
    try:
        cur.execute("SELECT ApiKey FROM HUB_AiConfig WHERE Id = 1")
        r = cur.fetchone()
        if r and r[0]:
            return str(r[0]).strip(), None
    except Exception:
        pass
    return None, None


def _sugerir_ia(descripcion: str, api_key: str, modelo: str | None):
    """Devuelve (clave_prod_serv, clave_unidad, razon, articulo_generico) o None.
    Nunca lanza. El 4º campo es el nombre genérico del artículo en compras
    (p. ej. 'disyuntor'), distinto de los códigos SAT."""
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=modelo or "gemini-1.5-flash",
            system_instruction=(
                "Eres un experto en claves SAT CFDI 4.0 para México. "
                "Asigna la clave más específica y correcta a cada producto o servicio. "
                "NUNCA uses '99839200' (Otros) a menos que sea absolutamente imposible. "
                "Responde SOLO con JSON: "
                '{"clave_prod_serv": "8 digitos", "clave_unidad": "1 a 3 caracteres", '
                '"articulo_generico": "nombre corto en minúsculas", "razon": "breve"}.'
            ),
        )
        prompt = (
            "Asigna la clave SAT CFDI 4.0, la unidad de medida y el nombre genérico del "
            "artículo a esta partida de cotización:\n\n"
            f"DESCRIPCIÓN: {descripcion}\n\n"
            "Catálogo común (producto/servicio → unidad típica H87 pieza):\n"
            "- 84039000 Motores eléctricos | 84131000 Bombas | 84136000 Bombas de engranes\n"
            "- 84818099 Otras válvulas | 85044090 Convertidores eléctricos | 85371091 Paneles de control\n"
            "- 85444209 Cables con aislamiento | 90268000 Instrumentos de medida | 90278000 Sensores/medidores\n"
            "- 44101701 PLCs / control numérico | 44111200 Software (unidad E48 servicio)\n"
            "- 73079999 Conexiones de acero | 40169999 Piezas de caucho | 99839200 Otros (último recurso)\n\n"
            "Unidad: H87 = pieza, E48 = servicio, MTR = metro, KGM = kilogramo, "
            "L = litro. Usa H87 si no aplica otra.\n\n"
            "articulo_generico = cómo se llama el artículo en compras, en minúsculas, de 1 a 4 "
            "palabras, SIN marca, SIN modelo, SIN código ni número de parte "
            '(ej. "disyuntor", "controlador lógico", "cable de comunicación").\n\n'
            'Responde EXACTAMENTE este JSON sin texto adicional: '
            '{"clave_prod_serv": "########", "clave_unidad": "XXX", '
            '"articulo_generico": "nombre generico", "razon": "explicacion breve"}'
        )
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        start = text.index("{")
        end = text.rindex("}") + 1
        data = json.loads(text[start:end])
        clave = str(data.get("clave_prod_serv", "")).strip()
        unidad = str(data.get("clave_unidad", "")).strip().upper()
        razon = str(data.get("razon", "")).strip()
        articulo = " ".join(str(data.get("articulo_generico", "")).split())[:200]
        if not re.match(r"^\d{8}$", clave):
            return None
        if not re.match(r"^[A-Z0-9]{1,3}$", unidad):
            unidad = "H87"
        return clave, unidad, razon[:200], articulo
    except Exception as e:
        print(f"[sat] Error sugiriendo clave vía IA: {e}")
        return None


# ---------------------------------------------------------------------------
# Validación de códigos capturados por el usuario
# ---------------------------------------------------------------------------

def validar_codigos(clave_prod_serv, clave_unidad):
    """Devuelve un mensaje de error o None si los códigos son válidos/vacíos."""
    clave_prod_serv = (clave_prod_serv or "").strip()
    clave_unidad = (clave_unidad or "").strip().upper()
    if not clave_prod_serv and not clave_unidad:
        return None
    if not clave_prod_serv or not clave_unidad:
        return "Captura ambos códigos (producto/servicio y unidad) o déjalos vacíos."
    if not re.match(r"^\d{8}$", clave_prod_serv):
        return "La clave de producto/servicio SAT debe tener 8 dígitos."
    if not re.match(r"^[A-Z0-9]{1,3}$", clave_unidad):
        return "La clave de unidad SAT debe tener de 1 a 3 caracteres (ej. H87)."
    return None


# ---------------------------------------------------------------------------
# Persistencia (índice + sidecar) — solo esquemas NUEVOS, nunca tablas existentes
# ---------------------------------------------------------------------------

def _upsert_indice(cur, norm, descripcion, clave, unidad, fuente, razon=None, articulo_generico=None):
    """Inserta o actualiza HUB_SatArticulos por ClaveNormalizada (UNIQUE).
    'articulo_generico' se guarda solo si viene con texto: un origen que no lo
    sabe (captura MANUAL) no borra el que ya aprendió la IA en una fila previa."""
    art = " ".join(str(articulo_generico or "").split())[:200]
    try:
        cur.execute(
            "SELECT IdArticulo FROM HUB_SatArticulos WHERE ClaveNormalizada = %s",
            (norm,))
        r = cur.fetchone()
        if r:
            cur.execute(
                "UPDATE HUB_SatArticulos SET ClaveProdServ = %s, ClaveUnidad = %s, "
                "Fuente = %s, DescripcionClave = COALESCE(%s, DescripcionClave), "
                "ArticuloGenerico = CASE WHEN %s <> '' THEN %s "
                "ELSE ISNULL(ArticuloGenerico, '') END, "
                "FechaUso = GETDATE() WHERE IdArticulo = %s",
                (clave, unidad, fuente, razon, art, art, int(r[0])))
        else:
            cur.execute(
                "INSERT INTO HUB_SatArticulos "
                "(ClaveNormalizada, DescripcionEjemplo, ClaveProdServ, ClaveUnidad, "
                "DescripcionClave, Fuente, ArticuloGenerico, FechaUso) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, GETDATE())",
                (norm, str(descripcion)[:500], clave, unidad, razon, fuente, art))
    except Exception as e:
        print(f"[sat] Error upsert índice: {e}")


def _upsert_sidecar(cur, folio, partida, norm, clave, unidad, fuente):
    """Inserta/actualiza el snapshot HUB_PartidasSat (tabla nueva sidecar)."""
    try:
        cur.execute(
            "SELECT Id FROM HUB_PartidasSat WHERE Folio = %s AND Partida = %s",
            (int(folio), int(partida)))
        r = cur.fetchone()
        if r:
            cur.execute(
                "UPDATE HUB_PartidasSat SET ClaveNormalizada = %s, ClaveProdServ = %s, "
                "ClaveUnidad = %s, Fuente = %s, FechaAct = GETDATE() WHERE Id = %s",
                (norm, clave, unidad, fuente, int(r[0])))
        else:
            cur.execute(
                "INSERT INTO HUB_PartidasSat (Folio, Partida, ClaveNormalizada, "
                "ClaveProdServ, ClaveUnidad, Fuente) VALUES (%s, %s, %s, %s, %s, %s)",
                (int(folio), int(partida), norm, clave, unidad, fuente))
    except Exception as e:
        print(f"[sat] Error upsert sidecar: {e}")


def leer_sidecar(cur, folio, partida):
    """Snapshot SAT de una partida. Devuelve dict (con clave_normalizada) o None."""
    try:
        cur.execute(
            "SELECT ClaveProdServ, ClaveUnidad, Fuente, ClaveNormalizada FROM HUB_PartidasSat "
            "WHERE Folio = %s AND Partida = %s",
            (int(folio), int(partida)))
        r = cur.fetchone()
        if r:
            return {"clave_prod_serv": r[0], "clave_unidad": r[1], "fuente": r[2],
                    "clave_normalizada": r[3]}
    except Exception:
        pass
    return None


def guardar_partida_sat(cur, folio, partida, descripcion, sat_prod_serv=None, sat_unidad=None):
    """Hook de guardado de partida (POST/PUT). Devuelve dict con los códigos
    {'clave_prod_serv', 'clave_unidad', 'fuente'} o None si no se pudo resolver.

    Reglas:
    - El usuario envía códigos explícitos → fuente MANUAL (si cambian) y se
      respetan; si son iguales a los ya guardados y la descripción no cambió,
      no se reescribe nada.
    - Sin códigos explícitos → sidecar con la misma descripción → índice →
      reglas → Gemini. Si la descripción CAMBIÓ y no hay resolución nueva,
      el sidecar viejo se elimina (códigos obsoletos)."""
    norm = normalizar(descripcion)
    if not norm:
        return None

    existente = leer_sidecar(cur, folio, partida)
    explicitos = bool((sat_prod_serv or "").strip())

    # Captura manual del usuario
    if explicitos:
        clave = sat_prod_serv.strip()
        unidad = (sat_unidad or "").strip().upper()
        err = validar_codigos(clave, unidad)
        if err:
            raise ValueError(err)
        # Round-trip idéntico (mismos códigos y misma descripción): no tocar nada
        if existente and existente["clave_prod_serv"] == clave \
                and existente["clave_unidad"] == unidad \
                and existente.get("clave_normalizada") == norm:
            return {"clave_prod_serv": clave, "clave_unidad": unidad,
                    "fuente": existente["fuente"]}
        _upsert_sidecar(cur, folio, partida, norm, clave, unidad, "MANUAL")
        _upsert_indice(cur, norm, descripcion, clave, unidad, "MANUAL")
        return {"clave_prod_serv": clave, "clave_unidad": unidad, "fuente": "MANUAL"}

    # Sin códigos explícitos: sidecar vigente con la misma descripción → 0 tokens
    if existente and existente.get("clave_normalizada") == norm:
        return {"clave_prod_serv": existente["clave_prod_serv"],
                "clave_unidad": existente["clave_unidad"],
                "fuente": existente["fuente"]}

    # Si el sidecar es de OTRA descripción y no logramos re-resolver, se borra
    # al final (para no imprimir códigos obsoletos en el PDF).

    # Índice por descripción
    try:
        cur.execute(
            "SELECT ClaveProdServ, ClaveUnidad, Fuente FROM HUB_SatArticulos "
            "WHERE ClaveNormalizada = %s AND Activo = 1", (norm,))
        r = cur.fetchone()
    except Exception:
        r = None
    if r:
        clave, unidad, fuente = r[0], r[1], r[2]
        _upsert_sidecar(cur, folio, partida, norm, clave, unidad, fuente)
        try:
            cur.execute(
                "UPDATE HUB_SatArticulos SET FechaUso = GETDATE() WHERE ClaveNormalizada = %s",
                (norm,))
        except Exception:
            pass
        return {"clave_prod_serv": clave, "clave_unidad": unidad, "fuente": fuente}

    # Reglas de keywords (0 tokens)
    hit = buscar_interna(descripcion)
    if hit:
        clave, unidad, generico = hit
        _upsert_sidecar(cur, folio, partida, norm, clave, unidad, "SEED")
        _upsert_indice(cur, norm, descripcion, clave, unidad, "SEED", articulo_generico=generico)
        return {"clave_prod_serv": clave, "clave_unidad": unidad, "fuente": "SEED"}

    # Gemini (1 sola llamada, solo si hay API key)
    api_key, modelo = _cfg_ia(cur)
    if api_key:
        ia = _sugerir_ia(descripcion, api_key, modelo)
        if ia:
            clave, unidad, razon, articulo = ia
            _upsert_sidecar(cur, folio, partida, norm, clave, unidad, "IA")
            _upsert_indice(cur, norm, descripcion, clave, unidad, "IA", razon,
                           articulo_generico=articulo)
            return {"clave_prod_serv": clave, "clave_unidad": unidad, "fuente": "IA"}

    # Sin resolución: si había un sidecar con otra descripción, se elimina
    if existente:
        try:
            cur.execute(
                "DELETE FROM HUB_PartidasSat WHERE Folio = %s AND Partida = %s",
                (int(folio), int(partida)))
        except Exception:
            pass
    return None


def sugerir_para_ui(cur, descripcion):
    """Botón 🤖 del formulario: resuelve códigos + artículo genérico para
    mostrarlos SIN guardar partida (solo hace upsert del índice).
    Devuelve dict con 'articulo_generico' (puede venir '' cuando el origen que
    resolvió los códigos no aporta el nombre) o None si nada se resolvió."""
    norm = normalizar(descripcion)
    if not norm:
        return None
    try:
        cur.execute(
            "SELECT ClaveProdServ, ClaveUnidad, Fuente, DescripcionClave, "
            "ISNULL(ArticuloGenerico, '') FROM HUB_SatArticulos "
            "WHERE ClaveNormalizada = %s AND Activo = 1", (norm,))
        r = cur.fetchone()
    except Exception:
        r = None
    if r:
        articulo = str(r[4] or "").strip()
        # Filas guardadas antes de 0044 (sin nombre): lo da la regla local,
        # 0 tokens, y se aprende en el índice para las próximas veces.
        if not articulo:
            hit = buscar_interna(descripcion)
            if hit:
                articulo = hit[2]
                _upsert_indice(cur, norm, descripcion, r[0], r[1], r[2], r[3],
                               articulo_generico=articulo)
        return {"clave_prod_serv": r[0], "clave_unidad": r[1], "fuente": r[2],
                "razon": r[3], "origen": "indice", "articulo_generico": articulo}
    hit = buscar_interna(descripcion)
    if hit:
        clave, unidad, generico = hit
        _upsert_indice(cur, norm, descripcion, clave, unidad, "SEED", articulo_generico=generico)
        return {"clave_prod_serv": clave, "clave_unidad": unidad, "fuente": "SEED",
                "razon": "Regla local por palabras clave", "origen": "reglas",
                "articulo_generico": generico}
    api_key, modelo = _cfg_ia(cur)
    if api_key:
        ia = _sugerir_ia(descripcion, api_key, modelo)
        if ia:
            clave, unidad, razon, articulo = ia
            _upsert_indice(cur, norm, descripcion, clave, unidad, "IA", razon,
                           articulo_generico=articulo)
            return {"clave_prod_serv": clave, "clave_unidad": unidad, "fuente": "IA",
                    "razon": razon, "origen": "ia", "articulo_generico": articulo}
    return None
