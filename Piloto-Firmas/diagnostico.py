"""Read PDFs from one folder and report grid detection without adding signatures."""
import argparse
import csv
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image
import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError

from cajetin import ANCHO, FILAS, detectar


def revisar(pdf, renderizador, temporal):
    with pdfplumber.open(pdf) as documento:
        for pagina in documento.pages:
            numero = pagina.page_number
            prefijo = temporal / "hoja"
            subprocess.run(
                [renderizador, "-f", str(numero), "-l", str(numero),
                 "-scale-to", str(ANCHO),
                 "-gray", "-png", "-singlefile", str(pdf), str(prefijo)],
                check=True, capture_output=True, timeout=60,
            )
            with Image.open(prefijo.with_suffix(".png")) as imagen:
                celdas, estado = detectar(imagen)
                sx, sy = pagina.width / imagen.width, pagina.height / imagen.height
                if not celdas:
                    yield (pdf.name, numero, "", "", estado, "")
                    continue

            for fila, (x0, y0, x1, y1) in celdas.items():
                caja = ((x0+1)*sx, (y0+1)*sy, (x1-1)*sx, (y1-1)*sy)
                texto = (pagina.crop(caja).extract_text() or "").strip()
                estado_fila = "Texto extraido" if texto else "Sin texto extraible"
                coordenadas = " ".join(f"{v:.2f}" for v in caja)
                yield (pdf.name, numero, FILAS[fila], texto, estado_fila, coordenadas)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--planos", required=True, type=Path)
    parser.add_argument("--salida", required=True, type=Path)
    parser.add_argument("--pdftoppm", default=shutil.which("pdftoppm"))
    args = parser.parse_args()
    if not args.planos.is_dir():
        parser.error("La carpeta de entrada no existe.")
    if not args.pdftoppm:
        parser.error("Indica la ruta de pdftoppm.exe con --pdftoppm.")
    args.salida.mkdir(parents=True, exist_ok=True)
    reporte = args.salida / "diagnostico.csv"
    with TemporaryDirectory(dir=args.salida) as temporal, reporte.open(
        "w", encoding="utf-8-sig", newline=""
    ) as archivo:
        writer = csv.writer(archivo, delimiter=";")
        writer.writerow(("PDF", "Pagina", "Cargo", "Texto extraido", "Estado",
                         "Celda NOMBRE en puntos (origen superior izquierdo)"))
        for pdf in sorted(args.planos.iterdir()):
            if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
                continue
            try:
                writer.writerows(revisar(pdf, args.pdftoppm, Path(temporal)))
            except (OSError, ValueError, subprocess.SubprocessError, PDFSyntaxError) as exc:
                writer.writerow((pdf.name, "", "", "", f"Error: {exc}", ""))
            archivo.flush()
            print(f"Revisado: {pdf.name}", flush=True)


if __name__ == "__main__":
    main()


