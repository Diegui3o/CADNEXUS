from io import BytesIO

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas


def colocar_imagen(origen, destino, firma, caja):
    writer = PdfWriter(clone_from=origen)
    if len(writer.pages) != 1:
        raise ValueError("El piloto requiere un PDF de una sola hoja.")
    page = writer.pages[0]
    if page.rotation:
        page.transfer_rotation_to_content()

    ancho = float(page.mediabox.width)
    alto = float(page.mediabox.height)
    if abs(ancho - 2384) > 1 or abs(alto - 1684) > 1:
        raise ValueError("El tamanio de hoja no coincide con el piloto A1.")
    factor = ancho / 5100
    izquierda, arriba, derecha, abajo = caja
    with Image.open(firma) as archivo:
        imagen = archivo.convert("RGBA")
    limites = imagen.getchannel("A").getbbox()
    if limites is None:
        raise ValueError("La imagen es completamente transparente.")
    imagen = imagen.crop(limites)
    escala = min((derecha - izquierda) * factor / imagen.width,
                 (abajo - arriba) * factor / imagen.height)
    w = imagen.width * escala
    h = imagen.height * escala
    x = (izquierda + derecha) * factor / 2 - w / 2
    y = alto - (arriba + abajo) * factor / 2 - h / 2

    capa = BytesIO()
    dibujo = Canvas(capa, pagesize=(ancho, alto))
    dibujo.drawImage(ImageReader(imagen), x, y, width=w, height=h, mask="auto")
    dibujo.save()
    capa.seek(0)
    page.merge_page(PdfReader(capa).pages[0])
    with destino.open("xb") as archivo:
        writer.write(archivo)
