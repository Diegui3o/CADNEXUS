import re
import unicodedata


def clave_firma(texto, alias):
    texto = unicodedata.normalize("NFKC", texto).upper()
    clave = re.sub(r"[.\s]", "", texto)
    if not re.fullmatch(r"[A-Z]+", clave):
        return None
    return alias.get(clave, clave)
