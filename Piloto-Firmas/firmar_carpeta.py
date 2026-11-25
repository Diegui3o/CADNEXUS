import argparse
import csv
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageOps
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from cajetin import ANCHO, detectar
from firmantes import similitud
from pdf_colocacion import colocar_imagen
from resumen_lote import generar_resumen


def render(pdf, exe, ancho, destino, recorte=()):
    subprocess.run([exe, "-f", "1", "-l", "1", "-scale-to", str(ancho),
                    *recorte, "-gray", "-png", "-singlefile", str(pdf), str(destino)],
                   check=True, capture_output=True, timeout=60)
    with Image.open(destino.with_suffix(".png")) as imagen:
        return imagen.convert("L")


def analizar(pdf, exe, temporal, muestras):
    documento = PdfReader(pdf)
    if len(documento.pages) != 1:
        return None, None, "PDF de varias hojas fuera de esta version"
    pagina = documento.pages[0]
    ancho, alto = float(pagina.mediabox.width), float(pagina.mediabox.height)
    if pagina.rotation % 180:
        ancho, alto = alto, ancho
    if abs(ancho - 2384) > 1 or abs(alto - 1684) > 1:
        return None, None, "Formato fuera de esta version (A1 horizontal)"
    if pagina.cropbox != pagina.mediabox or tuple(pagina.mediabox.lower_left) != (0, 0):
        return None, None, "Limites de pagina fuera de esta version"

    hoja = render(pdf, exe, ANCHO, temporal)
    celdas, estado = detectar(hoja)
    if not celdas:
        return None, None, estado

    x0, y0, x1, y1 = celdas[1]
    factor = 5100 / ancho
    sx = 5100 / hoja.width
    sy = alto * factor / hoja.height
    x, y = round((x0+1)*sx), round((y0+1)*sy)
    w, h = round((x1-x0-2)*sx), round((y1-y0-2)*sy)
    opciones = ("-x", str(x), "-y", str(y), "-W", str(w), "-H", str(h))
    celda = render(pdf, exe, 5100, temporal, opciones)
    tinta = ImageOps.invert(celda)
    mascara = tinta.point([0 if v < 125 else 255 for v in range(256)])
    bordes = mascara.getbbox()
    if bordes is None:
        return None, None, "PROYECTO vacio"
    recorte = mascara.crop(bordes)
    patron = (recorte.width / recorte.height,
              np.asarray(recorte.resize((96, 40), Image.Resampling.BILINEAR)) > 100)

    valores = {}
    for clave, referencia in muestras:
        valores[clave] = max(valores.get(clave, 0), similitud(patron, referencia))
    orden = sorted(valores, key=valores.get, reverse=True)
    clave = orden[0]
    mejor = valores[clave]
    if mejor < .775 or mejor - valores[orden[1]] < .13:
        return None, None, f"Iniciales sin coincidencia suficiente ({mejor:.3f})"
    # Reserve whitespace after all visible ink, not just the dark core.
    visibles = tinta.point([0 if v < 75 else 255 for v in range(256)]).getbbox()
    inicio = x + visibles[2] + 7
    fin = min(inicio+37, x+w-5)
    centro = y+h//2
    if fin-inicio < 19 or h < 24:
        return clave, None, "Espacio insuficiente"
    return clave, (inicio, centro-9, fin, centro+9), f"Similitud {mejor:.3f}"


def main():
    parser = argparse.ArgumentParser()
    for campo in ("planos", "firmas", "salida"):
        parser.add_argument(f"--{campo}", type=Path, required=True)
    parser.add_argument("--pdftoppm", required=True)
    parser.add_argument("--vista-previa", action="store_true")
    args = parser.parse_args()
    if not args.planos.is_dir() or not args.firmas.is_dir():
        parser.error("Comprueba las carpetas de entrada y firmas.")
    if args.planos.resolve() == args.salida.resolve():
        parser.error("Usa una carpeta de salida distinta.")
    args.salida.mkdir(parents=True, exist_ok=True)
    referencia = Path(__file__).with_name("referencias.npz")
    with np.load(referencia) as datos:
        muestras = [(str(c), (float(a), m)) for c, a, m in
                    zip(datos["claves"], datos["aspectos"], datos["mascaras"])]
    nombre_reporte = "vista-previa.csv" if args.vista_previa else "reporte-automatico.csv"
    with TemporaryDirectory(dir=args.salida) as temp, (
        args.salida / nombre_reporte
    ).open("w", newline="", encoding="utf-8-sig") as archivo:
        reporte = csv.writer(archivo, delimiter=";")
        reporte.writerow(("PDF", "Cargo", "Clave", "Estado", "Detalle"))
        for pdf in sorted(args.planos.iterdir()):
            if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
                continue
            clave = None
            try:
                clave, caja, detalle = analizar(pdf, args.pdftoppm, Path(temp)/"hoja", muestras)
                destino = args.salida / f"{pdf.name}"
                firma = args.firmas / f"{clave}.png"
                if caja is None:
                    estado = "Pendiente"
                elif not firma.is_file():
                    estado = "Pendiente"
                    detalle = f"Falta {firma.name}"
                elif args.vista_previa:
                    estado = "Propuesto"
                elif destino.exists():
                    estado = "Ya existe"
                else:
                    parcial = Path(temp) / "copia.pdf"
                    try:
                        colocar_imagen(pdf, parcial, firma, caja)
                        parcial.rename(destino)
                    finally:
                        parcial.unlink(missing_ok=True)
                    estado = "Creado"
            except (OSError, ValueError, PdfReadError, subprocess.SubprocessError) as error:
                estado, detalle = "Error", str(error)
            reporte.writerow((pdf.name, "PROYECTO", clave or "", estado, detalle))
            archivo.flush()
            print(f"{pdf.name}: {estado} {clave or ''}", flush=True)


    generar_resumen(args.salida / nombre_reporte)


if __name__ == "__main__":
    main()


