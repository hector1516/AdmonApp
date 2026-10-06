"""
api/ficha_nfc.py — El enlace público de cada persona (tarjeta NFC)
==================================================================
Derivación del token de las fichas que publica ECCSA_Colaboradores
(colaboradores.ecc-sa.com.mx).

POR QUÉ ESTÁ AQUÍ ADEMÁS
------------------------
La ficha se define en otra app, pero el enlace tiene que aparecer en la
pantalla "⚙️ Administración → 👥 Administración de usuarios", que es donde el
admin ya está para gestionar a la gente. Copiarlo de otro lado obligaría a ir
a otro sitio y pegarlo, que es justo lo que se quiere evitar al grabar una
tarjeta.

La alternativa era preguntarle a colaboradores por cada token: un salto de red
por usuario, un secreto de autenticación NUEVO entre las dos apps, y que esta
pantalla se quedara sin enlaces si colaboradores estuviera caído. Se prefiere
derivar el token aquí, con el secreto compartido.

⚠️ LA DERIVACIÓN ESTÁ ESCRITA EN DOS SITIOS
--------------------------------------------
Acá (JavaScript/Python) y en `panel/tokens.py` de ECCSA_Colaboradores. Si se
separan, los tokens dejan de coincidir y las tarjetas ya grabadas dejan de
abrir, SIN error visible: cada app seguiría sirviendo su propio token.

Por eso `DOMINIO` y `ALFABETO` están repetidos aquí como contrato, y hay un test
en los dos repos que fija un par (Id → token) conocido. Si tocas la derivación,
toca los dos repos en el mismo commit.

El token NO es un dato que este app pueda inventar: sale de
`HUB_Config.colab_ficha_secreto`, la misma clave que lee la otra app. Rotar ese
secreto invalida todas las tarjetas a la vez.
"""
import hashlib
import hmac
import os
import re
import unicodedata

# Crockford Base32 sin I, L, O, U ni 0 y 1. 32 símbolos x 32 caracteres = 160 bits.
# CONTRATO: idéntico a panel/tokens.py de ECCSA_Colaboradores.
ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
LARGO_TOKEN = 32
BITS_POR_CARACTER = 5
BYTES_DE_SEMILLA = (LARGO_TOKEN * BITS_POR_CARACTER) // 8      # 20 bytes

# CONTRATO: idéntico a DOMINIO en panel/tokens.py. Si cambia uno, cambia el otro.
DOMINIO = b"ficha-nfc-v1:"

# Hostname público de las fichas. Va en HUB_Config para poder cambiarlo sin
# redesplegar, pero con este valor por defecto si no está.
BASE_POR_DEFECTO = "https://colaboradores.ecc-sa.com.mx"
CLAVE_BASE = "colab_ficha_base_url"

BASE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(nombre):
    """'Hector Peña' -> 'hector-pena'.

    Los acentos y la eñe se traducen ANTES de filtrar: quitar los diacríticos
    con `encode("ascii", "ignore")` BORRA la letra acentuada en vez de
    convertirla, y "Pérez" salía "prez".
    """
    texto = (nombre or "").lower().replace("ñ", "n")
    texto = "".join(c for c in unicodedata.normalize("NFKD", texto)
                    if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-") or "colaborador"


def token_de(id_usuario, secreto):
    """HMAC-SHA256 del Id con el secreto → 32 caracteres en Base32.

    Determinista: el mismo Id y el mismo secreto dan el mismo token para
    siempre, que es lo que necesita una tarjeta NFC ya grabada.
    """
    if not secreto:
        return ""
    mac = hmac.new(secreto.encode("utf-8"),
                   DOMINIO + str(int(id_usuario)).encode("ascii"),
                   hashlib.sha256)
    numero = int.from_bytes(mac.digest()[:BYTES_DE_SEMILLA], "big")
    return "".join(
        ALFABETO[(numero >> (BITS_POR_CARACTER * (LARGO_TOKEN - 1 - i))) & 31]
        for i in range(LARGO_TOKEN)
    )


def slug_de(nombre, id_usuario, secreto):
    """`hector-pena-<32 caracteres>`, o '' si no hay secreto."""
    token = token_de(id_usuario, secreto)
    return f"{slugify(nombre)}-{token}" if token else ""


def url_de(nombre, id_usuario, secreto, base=BASE_POR_DEFECTO):
    """URL completa de la ficha, o '' si no hay secreto."""
    slug = slug_de(nombre, id_usuario, secreto)
    if not slug:
        return ""
    return f"{(base or BASE_POR_DEFECTO).rstrip('/')}/{slug}"