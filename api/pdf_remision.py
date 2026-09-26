"""PDF de remisión de materiales (port del HUB `generate_remision_pdf`).

Mismo layout que el HUB: encabezado logo + metadatos ("Remisión" + CM origen +
creado por), tabla solo Part./Cant./Descripción (SIN precios) y bloque de
firma (imagen capturada en Field o línea física).

Adaptaciones a admon:
- Sin caché ni pdf_storage (patrón de los PDFs de admon: siempre frescos).
- Los códigos SAT (HUB_SatArticulos/HUB_PartidasSat, migración 0037) se
  imprimen en una segunda línea gris junto a la descripción cuando existen.

Recibe:
  details: dict con FolioRemision, FolioCotizacion, Contacto, Descripcion,
           Autor, CreadoPor, FechaCreacion, FirmaConformidad, FechaFirma,
           ClienteNombre, UsuarioAsignadoNombre, Telefono
  items:   [{Partida, Cantidad, Descripcion, sat_prod_serv, sat_unidad}]
"""

import datetime
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from api.pdf_cotizacion import NumberedCanvas, _logo_flowables


def build_remision_pdf(details: dict, items: list) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=15,
        rightMargin=15,
        topMargin=15,
        bottomMargin=25,
    )

    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle("RemNorm", fontName="Helvetica", fontSize=8.5, leading=10, textColor=colors.black)
    style_meta_label = ParagraphStyle("RemMLbl", fontName="Helvetica-Bold", fontSize=9, leading=11, alignment=2, textColor=colors.black)
    style_meta_value = ParagraphStyle("RemMVal", fontName="Helvetica", fontSize=9, leading=11, alignment=2, textColor=colors.black)
    style_item_desc = ParagraphStyle("RemItemDesc", fontName="Helvetica", fontSize=8, leading=9.5, textColor=colors.black)
    style_item_header = ParagraphStyle("RemItemHdr", fontName="Helvetica-Bold", fontSize=8.5, leading=10, textColor=colors.black)
    style_firma_label = ParagraphStyle("RemFirma", fontName="Helvetica", fontSize=8, leading=11, textColor=colors.HexColor("#334155"))
    style_logo_subtext = ParagraphStyle("RemLogoSub", fontName="Helvetica-Bold", fontSize=6.5, leading=8, textColor=colors.HexColor("#334155"))

    story = []

    # HEADER (logo + metadatos) — mismo layout que build_cotizacion_pdf
    logo_container = _logo_flowables()
    logo_container.append(Paragraph("Oscar Noe Castillo Zavala - CAZO670914BK8", style_logo_subtext))

    fecha_val = details.get("FechaCreacion")
    if isinstance(fecha_val, (datetime.date, datetime.datetime)):
        fecha_str = fecha_val.strftime("%d/%m/%Y %H:%M")
    else:
        fecha_str = str(fecha_val or "")

    folio_rm = details.get("FolioRemision") or ""
    folio_cm = f"CM{int(details.get('FolioCotizacion') or 0):05d}"

    meta_data = [
        [Paragraph(f"Remision: {folio_rm}", style_meta_label)],
        [Paragraph(f"Cotizacion origen: {folio_cm}", style_meta_value)],
        [Paragraph(f"Fecha: {fecha_str}", style_meta_value)],
        [Paragraph(f"Cliente: {details.get('Contacto') or ''}", style_meta_value)],
        [Paragraph(f"{details.get('ClienteNombre') or ''}", style_meta_value)],
        [Paragraph(f"Elaboro: {details.get('Autor') or ''}", style_meta_value)],
        [Paragraph(f"Creado por: {details.get('CreadoPor') or ''}", style_meta_value)],
        [Paragraph(f"Telefono: {details.get('Telefono') or ''}", style_meta_value)],
    ]
    meta_table = Table(meta_data, colWidths=[380])
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))

    header_data = [[logo_container, meta_table]]
    header_table = Table(header_data, colWidths=[202, 380])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))

    # Descripción general de la cotización origen
    if (details.get("Descripcion") or "").strip():
        story.append(Paragraph(f"<b>Descripcion:</b> {details['Descripcion'].strip()}", style_normal))
        story.append(Spacer(1, 8))

    # TABLA: Part. / Cant. / Descripción (sin precios) + SAT en 2ª línea gris
    items_data = [[
        Paragraph("Part.", style_item_header),
        Paragraph("Cant.", style_item_header),
        Paragraph("Descripcion", style_item_header),
    ]]
    for item in items:
        partida_num = str(item.get("Partida") or "").zfill(3)
        cantidad_num = str(item.get("Cantidad") or "").zfill(3)
        desc_clean = (str(item.get("Descripcion") or "")
                      .replace("\t", " ").replace("\r", " ").replace("\n", " ").strip())
        # Códigos SAT junto a la descripción (mismo gris/estilo que "Tiempo
        # entrega" del PDF de cotización); solo se imprime lo que exista.
        sat_txt = ""
        if item.get("sat_prod_serv"):
            sat_txt = f"SAT: {item['sat_prod_serv']}"
            if item.get("sat_unidad"):
                sat_txt += f" · Unidad: {item['sat_unidad']}"
        desc_full = desc_clean
        if sat_txt:
            desc_full += f"<br/><font color='#64748B'>{sat_txt}</font>"
        items_data.append([
            Paragraph(partida_num, style_item_desc),
            Paragraph(cantidad_num, style_item_desc),
            Paragraph(desc_full, style_item_desc),
        ])

    items_table = Table(items_data, colWidths=[40, 40, 502])
    items_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (1, -1), "CENTER"),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 40))

    # Firma digital (Field/HUB) si ya existe; si no, línea física en blanco
    firma_img = None
    firma_raw = details.get("FirmaConformidad")
    if firma_raw and isinstance(firma_raw, str) and firma_raw.strip():
        try:
            sig_payload = firma_raw.split(",", 1)[1] if "," in firma_raw else firma_raw
            sig_bytes = __import__("base64").b64decode(sig_payload)
            buf = io.BytesIO(sig_bytes)
            try:
                from PIL import Image as PILImage
                im = PILImage.open(buf).convert("RGB")
                im.thumbnail((400, 400))
                out = io.BytesIO()
                im.save(out, format="JPEG", quality=50)
                out.seek(0)
                firma_img = RLImage(out, width=150, height=60)
            except Exception:
                buf.seek(0)
                firma_img = RLImage(buf, width=150, height=60)
        except Exception as e:
            print("[remision] Error renderizando firma:", e)

    if firma_img:
        firmo_txt = details.get("UsuarioAsignadoNombre") or details.get("CreadoPor") or ""
        fecha_firma = details.get("FechaFirma") or details.get("FechaCreacion")
        if isinstance(fecha_firma, (datetime.date, datetime.datetime)):
            fecha_firma_str = fecha_firma.strftime("%d/%m/%Y %H:%M")
        else:
            fecha_firma_str = str(fecha_firma or "")
        sig_inner = [
            [firma_img],
            [Paragraph(f"<b>Firmo:</b> {firmo_txt} &nbsp;&nbsp; <b>Fecha:</b> {fecha_firma_str}",
                       style_firma_label)],
        ]
        sig_inner_table = Table(sig_inner, colWidths=[300])
        sig_inner_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ]))
        firma_data = [
            [sig_inner_table, Paragraph("Fecha de recepcion: ____ / ____ / ______", style_firma_label)],
        ]
    else:
        firma_data = [
            [
                Paragraph("_______________________________________", style_firma_label),
                Paragraph("", style_firma_label),
            ],
            [
                Paragraph("Nombre y firma de quien recibe", style_firma_label),
                Paragraph("Fecha de recepcion: ____ / ____ / ______", style_firma_label),
            ],
        ]
    firma_table = Table(firma_data, colWidths=[300, 282])
    firma_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(firma_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
