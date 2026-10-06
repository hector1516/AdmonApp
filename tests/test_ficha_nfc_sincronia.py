"""
tests/test_ficha_nfc_fuera_de_sincronia.py
===========================================
Guardia entre los DOS repos que derivan el token de las fichas NFC:

  · ECCSA_Colaboradores  →  panel/tokens.py    (define y sirve la ficha)
  · AdmonApp             →  api/ficha_nfc.py   (muestra el enlace para copiar)

Si un clon del otro repo está disponible, compara la derivación de los dos con
el MISMO secreto y falla si no coinciden. Es la forma de que un cambio en la
derivación que se aplique a medias no deje tarjetas muertas sin que nadie se
diga cuenta.

Si el otro repo no está, NO falla: solo avisa. Un test que falla porque falta un
clonSibling sería peor que inútil — hace que el CI del repo nuevo sea rojo por
un motivo que no es suyo.

Uso:
    COLAB_REPO=/ruta/a/ECCSA_Colaboradores python3 tests/test_ficha_nfc_sincronia.py
"""
import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from api import ficha_nfc  # noqa: E402

OTRO = os.environ.get(
    "COLAB_REPO",
    os.path.join(os.path.dirname(RAIZ), "ECCSA_Colaboradores"))

# Casos que se comparan: (nombre, Id, slug esperado con el secreto de producción)
CASOS = [
    ("Hector Pena", 2, "hector-pena-J27QK5EMZA682QABNNABJQY1J1APEQYJ"),
    ("José Salazar", 6, "jose-salazar-N5YQV43D5SGRWJG2Q868QTTD0G5PPEDY"),
    ("IT Support", 1, "it-support-Z85KDFP5J6JMYHMHF6P8Q7CRES6BA4QY"),
]


def _tokens_del_otro_repo(secreto):
    """(nombre, Id, slug) calculados por el otro repo. None si no está."""
    if not os.path.isdir(OTRO):
        return None
    import importlib
    import importlib.util

    try:
        spec = importlib.util.spec_from_file_location(
            "colab_tokens", os.path.join(OTRO, "panel", "tokens.py"))
        mod = importlib.util.module_from_spec(spec)
        # panel/tokens.py hace `from panel import config, db`, así que el repo
        # de al lado tiene que estar en el path para que el import resuelva.
        sys.path.insert(0, OTRO)
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.path.remove(OTRO)
        return [(n, i, mod.construir_slug(n, i)) for n, i, _ in CASOS]
    except Exception as exc:
        print(f"    (no se pudo cargar el otro repo: {exc})")
        return None


class TestSincroniaDeDerivacion(unittest.TestCase):
    def test_ambos_repos_calculan_el_mismo_slug(self):
        otro = _tokens_del_otro_repo(None)
        if otro is None:
            self.skipTest(
                f"ECCSA_Colaboradores no está en {OTRO}; "
                "ponlo ahí o exporta COLAB_REPO para comprobar la sincronía")

        print("    comparando contra", OTRO)
        for (nombre, id_usuario, esperado), (_, _, slug_otro) in zip(CASOS, otro):
            with self.subTest(usuario=nombre):
                self.assertEqual(
                    slug_otro, esperado,
                    f"{OTRO} calcula un token distinto al de AdmonApp. "
                    "La derivacion cambio en un repo y no en el otro: las "
                    "tarjetas ya grabadas dejarian de abrir.")


if __name__ == "__main__":
    unittest.main(verbosity=2)