"""Find the approval grid on a rendered landscape sheet."""
import numpy as np


ANCHO = 1700
FILAS = {1: "PROYECTO", 2: "REVISO", 3: "JEFE DISC.",
         4: "GER. ING.", 5: "GER. PROY.", 6: "CLIENTE"}
# The two measured sizes of the same grid. Positions are relative to the grid.
MEDIDAS = (
    ((0, 27, 66, 105), (0, 14, 27, 39, 51, 63, 76, 88, 100)),
    ((0, 28, 69, 109), (0, 15, 27, 40, 53, 65, 78, 91, 104)),
)


def detectar(imagen):
    tinta = np.asarray(imagen.convert("L")) < 175
    alto, ancho = tinta.shape
    if ancho != ANCHO or alto < 200:
        return None, "Formato sin validar"

    # Search the lower half, regardless of the file name or grid position.
    acumulado = np.pad(tinta.cumsum(axis=0), ((1, 0), (0, 0)))
    candidatos = []
    for columnas, filas in MEDIDAS:
        largo = filas[-1] - 6
        tramos = acumulado[largo:] - acumulado[:-largo]
        continuas = tramos > largo * 0.83
        base = continuas[alto // 2:, :ancho - columnas[-1]].copy()
        for dx in columnas[1:]:
            base &= continuas[alto // 2:, dx:dx + base.shape[1]]
        for yy, xx in np.argwhere(base):
            y = int(yy) + alto // 2 - 3
            x = int(xx)
            bordes = []
            for dy in filas:
                opciones = range(max(0, y + dy - 2), min(alto, y + dy + 3))
                muestras = [(int(tinta[i, x+2:x+columnas[-1]-2].sum()), i)
                            for i in opciones]
                if not muestras:
                    break
                cantidad, borde = max(muestras)
                if cantidad < 0.86 * (columnas[-1] - 4):
                    break
                bordes.append(borde)
            if len(bordes) == len(filas):
                candidatos.append((x, tuple(bordes), columnas))
    if not candidatos:
        return None, "Cajetin sin reconocer"
    x, bordes, columnas = candidatos[0]
    if any(abs(cx-x) > 3 or abs(cb[0]-bordes[0]) > 3 for cx, cb, _ in candidatos):
        return None, "Mas de un cajetin posible"

    indices = (1, 2, 3, 4, 5, 7)
    celdas = {fila: (x+columnas[1], bordes[indice],
                     x+columnas[2], bordes[indice+1])
              for fila, indice in enumerate(indices, start=1)}
    return celdas, "Detectado"
