"""
tests/test_ficha_nfc.py — La derivación del token de las fichas
==============================================================
El token de una tarjeta NFC está DERIVADO en dos repos: aquí (JavaScript-era
Python, `api/ficha_nfc.py`) y en ECCSA_Colaboradores (`panel/tokens.py`). Si las
dos derivaciones se separan, los tokens dejan de coincidir y las tarjetas ya
grabadas dejan de abrir — SIN NINGÚN ERROR VISIBLE: cada app seguiría sirviendo
su propio token y el enlace simplemente "no funciona".

Este test fija un par (Id → token) conocido, calculado con el secreto real de
producción. Si alguien toca la derivación en un repo y no en el otro, este test
falla en el primero y avisa.

El par es de PRODUCCIÓN a propósito: un valor inventado pasaría igual en los dos
repos si ambos se cambiaran a la vez sin querer. Este no.

Corre: python3 tests/test_ficha_nfc.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import ficha_nfc  # noqa: E402

# Secreto REAL de producción (HUB_Config.colab_ficha_secreto). Es el mismo que
# lee ECCSA_Colaboradores. Va en el test a propósito: el par (Id, token) de
# abajo es laoomprobación de que las dos derivaciones siguen dando lo mismo.
SECRETO_PRODUCCION = os.environ.get(
    "HUB_FICHA_SECRETO_TEST",
    "-RxiJUBIIlGT9Gv5RRn8AJCEaZyhitqHQTJDyvu96nixWS5XCQvdrqYGnoE7_UhU",
)

# (nombre, Id, slug esperado) — calculado con el secreto de arriba.
# Si esto cambia, o se rompió la derivación o se rotó el secreto: en el segundo
# caso hay que actualizar la migración 0060 Y avisar que las tarjetas cambian.
CASOS = [
    ("Hector Pena", 2,
     "hector-pena-J27QK5EMZA682QABNNABJQY1J1APEQYJ"),
    ("José Salazar", 6,
     "jose-salazar-N5YQV43D5SGRWJG2Q868QTTD0G5PPEDY"),
    ("IT Support", 1,
     "it-support-Z85KDFP5J6JMYHMHF6P8Q7CRES6BA4QY"),
]


class TestDerivacion(unittest.TestCase):
    def test_slug_exacto(self):
        """El par (Id → token) no puede cambiar sin querer."""
        for nombre, id_usuario, esperado in CASOS:
            with self.subTest(usuario=nombre):
                self.assertEqual(
                    ficha_nfc.slug_de(nombre, id_usuario, SECRETO_PRODUCCION),
                    esperado)

    def test_longitud_y_alfabeto(self):
        for nombre, id_usuario, _ in CASOS:
            slug = ficha_nfc.slug_de(nombre, id_usuario, SECRETO_PRODUCCION)
            token = slug.rsplit("-", 1)[-1]
            self.assertEqual(len(token), ficha_nfc.LARGO_TOKEN)
            self.assertTrue(all(c in ficha_nfc.ALFABETO for c in token))

    def test_es_determinista(self):
        """El mismo Id da el mismo token siempre: la tarjeta es fija."""
        self.assertEqual(
            ficha_nfc.token_de(2, SECRETO_PRODUCCION),
            ficha_nfc.token_de(2, SECRETO_PRODUCCION))
        self.assertNotEqual(
            ficha_nfc.token_de(2, SECRETO_PRODUCCION),
            ficha_nfc.token_de(3, SECRETO_PRODUCCION))

    def test_sin_secreto_no_hay_token(self):
        """Sin secreto, cadena vacía — nunca un token débil o inventado."""
        self.assertEqual(ficha_nfc.token_de(2, ""), "")
        self.assertEqual(ficha_nfc.slug_de("X", 2, ""), "")
        self.assertEqual(ficha_nfc.url_de("X", 2, ""), "")

    def test_rotar_el_secreto_cambia_el_token(self):
        """Documenta el precio del diseño: rotar el secreto invalida todo."""
        self.assertNotEqual(
            ficha_nfc.token_de(2, SECRETO_PRODUCCION),
            ficha_nfc.token_de(2, "otro-secreto-cualquiera"))

    def test_el_dominio_esta_en_el_hmac(self):
        """Si el dominio no fuera parte del mensaje, el mismo secreto serviría
        para otra cosa y los tokens se repetirían entre aplicaciones."""
        self.assertEqual(ficha_nfc.DOMINIO, b"ficha-nfc-v1:")
        # Mismo secreto y mismo Id, pero con otro dominio: el primer caracter del
        # token tiene que cambiar. Si no, el mismo secreto serviria para dos
        # aplicaciones y los tokens se repetirian entre ellas.
        import hashlib
        import hmac as _h
        otro = _h.new(SECRETO_PRODUCCION.encode("utf-8"),
                      b"otra-cosa-v1:2", hashlib.sha256).digest()
        otro_token = ficha_nfc.ALFABETO[otro[0] >> 3]
        self.assertNotEqual(otro_token, ficha_nfc.token_de(2, SECRETO_PRODUCCION)[0])


class TestSlugify(unittest.TestCase):
    def test_acentos_y_enie(self):
        """Regresión: quitar diacríticos con `encode(ascii, ignore)` BORRA la
        letra acentuada, y 'Pérez' salía 'prez'."""
        self.assertEqual(ficha_nfc.slugify("Hector Peña Ruiz"),
                         "hector-pena-ruiz")
        self.assertEqual(ficha_nfc.slugify("José María Ñuño"),
                         "jose-maria-nuno")
        self.assertEqual(ficha_nfc.slugify("Ángel Pérez"), "angel-perez")

    def test_vacios(self):
        self.assertEqual(ficha_nfc.slugify(""), "colaborador")
        self.assertEqual(ficha_nfc.slugify("   "), "colaborador")
        self.assertEqual(ficha_nfc.slugify(None), "colaborador")


class TestUrl(unittest.TestCase):
    def test_url_completa(self):
        url = ficha_nfc.url_de("Hector Pena", 2, SECRETO_PRODUCCION)
        self.assertTrue(url.startswith("https://colaboradores.ecc-sa.com.mx/"))
        self.assertTrue(url.endswith(CASOS[0][2]))

    def test_base_con_slash_final(self):
        """Una barra duplicada (//slug) rompe algunos lectores de NFC."""
        url = ficha_nfc.url_de("Hector Pena", 2, SECRETO_PRODUCCION,
                               base="https://ejemplo.mx/")
        self.assertNotIn("//hector", url)


if __name__ == "__main__":
    unittest.main(verbosity=2)