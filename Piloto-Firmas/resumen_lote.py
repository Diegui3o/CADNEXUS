import argparse
import csv
from collections import Counter
from pathlib import Path


def generar_resumen(reporte):
    with reporte.open(encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.DictReader(archivo, delimiter=";"))

    estados = Counter(fila["Estado"] for fila in filas)
    sin_copia = [fila for fila in filas
                 if fila["Estado"] not in {"Creado", "Ya existe", "Propuesto"}]
    lineas = [
        f"PDF revisados: {len(filas)}",
        f"Copias nuevas con firma: {estados['Creado']}",
        f"Copias con firma que ya existian: {estados['Ya existe']}",
        f"Total con copia firmada: {estados['Creado'] + estados['Ya existe']}",
        f"Sin copia nueva en esta corrida: {len(filas) - estados['Creado']}",
        f"Sin copia firmada: {len(sin_copia)}",
    ]
    if estados["Propuesto"] or reporte.name == "vista-previa.csv":
        lineas.append(f"Propuestos en vista previa (sin crear copia): {estados['Propuesto']}")
    if sin_copia:
        lineas.extend(("", "PDF sin copia firmada y motivo"))
        for fila in sin_copia:
            lineas.append(f"- {fila['PDF']} | {fila['Estado']} | {fila['Detalle']}")
    texto = "\n".join(lineas) + "\n"
    resumen = reporte.with_name(f"{reporte.stem}-resumen.txt")
    resumen.write_text(texto, encoding="utf-8-sig")
    print()
    print(texto, end="")
    print(f"Resumen guardado en {resumen}")
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("reporte", type=Path)
    generar_resumen(parser.parse_args().reporte)

