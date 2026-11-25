import argparse
import csv
import json
from pathlib import Path

from pdf_colocacion import colocar_imagen
from reglas import clave_firma


def main():
    parser = argparse.ArgumentParser()
    for nombre in ("planos", "firmas", "salida"):
        parser.add_argument(f"--{nombre}", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    args = parser.parse_args()
    for carpeta in (args.planos, args.firmas):
        if not carpeta.is_dir():
            parser.error(f"No se encontro la carpeta {carpeta}")
    if args.planos.resolve() == args.salida.resolve():
        parser.error("La carpeta de salida debe ser distinta de la carpeta de entrada.")

    reglas = json.loads(args.config.read_text(encoding="utf-8-sig"))
    fichas = {muestra["archivo"].casefold(): muestra for muestra in reglas["muestras"]}
    args.salida.mkdir(parents=True, exist_ok=True)
    resultados = []
    for origen in sorted(args.planos.iterdir()):
        if not origen.is_file() or origen.suffix.lower() != ".pdf":
            continue
        ficha = fichas.get(origen.name.casefold())
        destino = args.salida / f"{origen.name}"
        if ficha is None:
            estado = "Pendiente: el PDF no tiene datos de ubicacion"
        elif destino.exists():
            estado = "Ya existe la copia"
        else:
            clave = clave_firma(ficha["texto"], reglas["alias"])
            firma = args.firmas / f"{clave}.png"
            if not clave or not firma.is_file():
                estado = f"Pendiente: falta imagen para {ficha['texto']}"
            else:
                try:
                    colocar_imagen(origen, destino, firma, ficha["caja"])
                    estado = f"Creado con {firma.name}"
                except (OSError, ValueError) as error:
                    estado = f"Error: {error}"
        resultados.append((origen.name, estado))
        print(f"{origen.name}: {estado}")

    with (args.salida / "reporte.csv").open("w", newline="", encoding="utf-8-sig") as archivo:
        reporte = csv.writer(archivo, delimiter=";")
        reporte.writerow(("PDF", "Estado"))
        reporte.writerows(resultados)


if __name__ == "__main__":
    main()

