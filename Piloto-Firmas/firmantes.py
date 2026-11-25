"""Compare cell ink against visually verified examples. Diagnostic only."""
import argparse
import csv
from itertools import groupby
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageOps
from pypdf import PdfReader

COORDENADAS = "Celda NOMBRE en puntos (origen superior izquierdo)"
PREFIJO = "QLL-ENG-5EX-240005-342-DR-"
REFERENCIAS = {
    "3210-IN5002": {"PROYECTO": "RRA", "REVISO": "ORR",
                    "JEFE DISC.": "ORR", "GER. PROY.": "DZR", "CLIENTE": "AAQ"},
    "3220-IN5004": {"PROYECTO": "DMM"},
}


def patrones(pdf, filas, renderizador, destino):
    pagina = PdfReader(pdf).pages[int(filas[0]["Pagina"]) - 1]
    ancho, alto = float(pagina.mediabox.width), float(pagina.mediabox.height)
    if pagina.rotation % 180:
        ancho, alto = alto, ancho
    numero = filas[0]["Pagina"]
    subprocess.run(
        [renderizador, "-f", numero, "-l", numero, "-scale-to", "5100",
         "-gray", "-png", "-singlefile", str(pdf), str(destino)],
        check=True, capture_output=True, timeout=60,
    )
    with Image.open(destino.with_suffix(".png")) as hoja:
        sx, sy = hoja.width / ancho, hoja.height / alto
        for fila in filas:
            x0, y0, x1, y1 = map(float, fila[COORDENADAS].split())
            caja = (round(x0*sx), round(y0*sy), round(x1*sx), round(y1*sy))
            tinta = ImageOps.invert(hoja.crop(caja).convert("L")).point(
                [0 if v < 125 else 255 for v in range(256)]
            )
            contorno = tinta.getbbox()
            if contorno is None:
                yield fila, None
                continue
            tinta = tinta.crop(contorno)
            if tinta.height < 8 or tinta.width < 4:
                yield fila, None
                continue
            aspecto = tinta.width / tinta.height
            mascara = np.asarray(tinta.resize((96, 40), Image.Resampling.BILINEAR)) > 100
            yield fila, (aspecto, mascara)


def similitud(uno, otro):
    a, primera = uno
    b, segunda = otro
    union = np.count_nonzero(primera | segunda)
    if not union:
        return 0
    return np.count_nonzero(primera & segunda) / union * min(a, b) / max(a, b)


def main():
    parser = argparse.ArgumentParser()
    for clave in ("planos", "diagnostico", "salida"):
        parser.add_argument(f"--{clave}", required=True, type=Path)
    parser.add_argument("--pdftoppm", required=True)
    args = parser.parse_args()

    with args.diagnostico.open(encoding="utf-8-sig", newline="") as archivo:
        filas = [r for r in csv.DictReader(archivo, delimiter=";") if r[COORDENADAS]]
    orden = lambda r: (r["PDF"], r["Pagina"])
    filas.sort(key=orden)
    datos = []
    muestras = {}
    with TemporaryDirectory() as carpeta:
        for (nombre, _), grupo in groupby(filas, key=orden):
            codigo = nombre.removeprefix(PREFIJO).removesuffix("_RAB.pdf")
            for fila, patron in patrones(args.planos / nombre, list(grupo),
                                         args.pdftoppm, Path(carpeta) / "hoja"):
                datos.append((fila, patron))
                etiqueta = REFERENCIAS.get(codigo, {}).get(fila["Cargo"])
                if etiqueta and patron is not None:
                    muestras.setdefault(etiqueta, []).append((nombre, patron))

    if not muestras:
        parser.error("El diagnostico no incluye las muestras verificadas de referencia.")
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo, delimiter=";")
        escritor.writerow(("PDF", "Pagina", "Cargo", "Candidato", "Similitud", "Estado"))
        for fila, patron in datos:
            puntajes = []
            if patron is not None and fila["Cargo"] != "GER. ING.":
                for etiqueta, referencias in muestras.items():
                    valores = [similitud(patron, ref) for origen, ref in referencias
                               if origen != fila["PDF"]]
                    if valores:
                        puntajes.append((max(valores), etiqueta))
            puntajes.sort(reverse=True)
            mejor, candidato = puntajes[0] if puntajes else (0, "")
            margen = mejor - (puntajes[1][0] if len(puntajes) > 1 else 0)
            estado = "Candidato para validar" if mejor >= .72 and margen >= .13 else "Sin coincidencia verificada"
            if fila["Cargo"] == "GER. ING.":
                estado = "Fila fuera de prueba"
            escritor.writerow((fila["PDF"], fila["Pagina"], fila["Cargo"],
                               candidato if estado == "Candidato para validar" else "",
                               f"{mejor:.3f}", estado))


if __name__ == "__main__":
    main()

