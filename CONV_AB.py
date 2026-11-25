
import os
import re

# Carpeta donde están los DWG
CARPETA = r"C:\Users\Rafael\Desktop\SCRIPT\PDF"

for archivo in os.listdir(CARPETA):

    if archivo.lower().endswith(".dwg"):

        # Reemplaza R1, R2, R0, etc. por RAB
        nuevo_nombre = re.sub(
            r"_R\d+\.dwg$",
            "_RAB.dwg",
            archivo,
            flags=re.IGNORECASE
        )

        if nuevo_nombre != archivo:

            ruta_antigua = os.path.join(CARPETA, archivo)
            ruta_nueva = os.path.join(CARPETA, nuevo_nombre)

            os.rename(ruta_antigua, ruta_nueva)

            print(f"RENOMBRADO: {archivo} -> {nuevo_nombre}")

print("\nPROCESO TERMINADO")
