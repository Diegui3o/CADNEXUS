import argparse
import json
from pathlib import Path

from pdf_colocacion import colocar_imagen
from reglas import clave_firma


def main():
    parser = argparse.ArgumentParser()
    for nombre in ("planos", "firmas", "salida"):
        parser.add_argument(f"--{nombre}", required=True, type=Path)
    args = parser.parse_args()
    for carpeta in (args.planos, args.firmas):
        if not carpeta.is_dir():
            parser.error(f"No se encontro la carpeta {carpeta}")

    config = Path(__file__).with_name("config.json")
    reglas = json.loads(config.read_text(encoding="utf-8-sig"))
    args.salida.mkdir(parents=True, exist_ok=True)
    for muestra in reglas["muestras"]:
        origen = args.planos / muestra["archivo"]
        clave = clave_firma(muestra["texto"], reglas["alias"])
        firma = args.firmas / f"{clave}.png"
        destino = args.salida / f"{origen.name}"
        if not origen.is_file():
            print(f"Pendiente {origen.name}: falta PDF")
            continue
        if not clave or not firma.is_file():
            print(f"Pendiente {origen.name}: falta imagen para {muestra['texto']}")
            continue
        if destino.exists():
            print(f"Ya existe {destino.name}")
            continue
        colocar_imagen(origen, destino, firma, muestra["caja"])
        print(f"Creado {destino.name} con {firma.name}")


if __name__ == "__main__":
    main()
