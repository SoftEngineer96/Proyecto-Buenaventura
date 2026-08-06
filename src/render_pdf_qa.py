from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
pdf_path = root / "reportes" / "EDA_52_Preguntas_Importaciones_Buenaventura.pdf"
out = root / "reportes" / "validacion_visual"
out.mkdir(exist_ok=True)
pdf = pdfium.PdfDocument(pdf_path)
thumbs = []
for i, page in enumerate(pdf):
    image = page.render(scale=0.75).to_pil().convert("RGB")
    image.thumbnail((300, 390))
    canvas = Image.new("RGB", (320, 430), "white")
    canvas.paste(image, ((320-image.width)//2, 25))
    ImageDraw.Draw(canvas).text((10, 5), f"Pagina {i+1}", fill="black")
    thumbs.append(canvas)
    if i in {0, 1, 2, 7, 12, 17, 22, 23}:
        page.render(scale=1.6).to_pil().convert("RGB").save(out / f"page_{i+1:02d}.png")

cols = 4
rows = (len(thumbs) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 320, rows * 430), "white")
for i, thumb in enumerate(thumbs):
    sheet.paste(thumb, ((i % cols) * 320, (i // cols) * 430))
sheet.save(out / "contact_sheet.png")
print(len(pdf), out / "contact_sheet.png")
