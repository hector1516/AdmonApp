"""Generador PDF de cotizaciones de materiales (autocontenido, sin eccsa_db).

Réplica el contenido del PDF del HUB (generate_quotation_pdf): encabezado con
folio, datos del cliente, tabla de partidas con totales y nota interna.
Usa fuentes Helvetica integradas (sin TTF externos). Logo opcional.
"""

import io
import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage,
)

NARANJA = colors.HexColor("#EB6C24")
OSCURO = colors.HexColor("#0F172A")
GRIS = colors.HexColor("#64748B")


def _money(v) -> str:
    try:
        return f"${float(v or 0.0):,.2f}"
    except Exception:
        return "$0.00"


def _folio_fmt(folio) -> str:
    try:
        return f"CM{int(folio):05d}"
    except Exception:
        return str(folio)


def _logo_flowables():
    """Logo ECCSA si existe en la imagen (igual que el HUB, tolerante).
    Se reduce a thumbnail JPEG para que el PDF pese KB, no MB."""
    for cand in ("/eccsa_logo.png", "eccsa_logo.png"):
        try:
            if not os.path.exists(cand):
                continue
            try:
                from PIL import Image as PILImage
                im = PILImage.open(cand).convert("RGB")
                im.thumbnail((600, 200))
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=60)
                buf.seek(0)
                return [RLImage(buf, width=60 * mm, height=18 * mm), Spacer(1, 2 * mm)]
            except Exception:
                return [RLImage(cand, width=60 * mm, height=18 * mm), Spacer(1, 2 * mm)]
        except Exception:
            continue
    return []


def build_cotizacion_pdf(header: dict, partidas: list) -> bytes:
    """header: folio, id_cliente, cliente_nombre, contacto, fecha, descripcion,
    nota, autor, color. partidas: lista con partida, cantidad, descripcion,
    proveedor, total_venta (y precio_compra/factor/flete opcionales)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
        title=f"Cotización {_folio_fmt(header.get('folio'))} ECCSA",
        author="ECCSA Admon",
    )
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("Titulo", parent=styles["Heading1"], fontName="Helvetica-Bold",
                            fontSize=16, leading=19, textColor=OSCURO)
    subt = ParagraphStyle("Subt", parent=styles["Normal"], fontName="Helvetica",
                          fontSize=9, leading=12, textColor=GRIS)
    normal = ParagraphStyle("Norm", parent=styles["Normal"], fontName="Helvetica",
                            fontSize=9, leading=12)
    negrita = ParagraphStyle("Neg", parent=styles["Normal"], fontName="Helvetica-Bold",
                             fontSize=9, leading=12)
    right = ParagraphStyle("Right", parent=negrita, alignment=2)

    el = []
    el.extend(_logo_flowables())
    el.append(Paragraph("COTIZACIÓN DE MATERIALES", titulo))
    el.append(Paragraph(
        f"<b><font color=\"#EB6C24\">{_folio_fmt(header.get('folio'))}</font></b>"
        f" &nbsp;&nbsp; Fecha: {header.get('fecha') or ''}", normal))
    el.append(Spacer(1, 4 * mm))

    datos = [
        [Paragraph("<b>Cliente:</b>", negrita),
         Paragraph(f"{header.get('cliente_nombre') or header.get('id_cliente') or 'N/A'}", normal)],
        [Paragraph("<b>Contacto:</b>", negrita),
         Paragraph(f"{header.get('contacto') or 'N/A'}", normal)],
        [Paragraph("<b>Descripción:</b>", negrita),
         Paragraph(f"{header.get('descripcion') or '—'}", normal)],
        [Paragraph("<b>Elaboró:</b>", negrita),
         Paragraph(f"{header.get('autor') or ''}", normal)],
    ]
    t_datos = Table(datos, colWidths=[28 * mm, 152 * mm])
    t_datos.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    el.append(t_datos)
    el.append(Spacer(1, 5 * mm))

    # Tabla de partidas (mismas columnas que el detalle del HUB)
    head = [
        Paragraph("<b>Part.</b>", negrita), Paragraph("<b>Cant.</b>", negrita),
        Paragraph("<b>Descripción</b>", negrita), Paragraph("<b>Proveedor</b>", negrita),
        Paragraph("<b>Total Venta</b>", right),
    ]
    rows = [head]
    subtotal = 0.0
    for p in partidas or []:
        tot = float(p.get("total_venta") or 0.0)
        subtotal += tot
        rows.append([
            Paragraph(str(p.get("partida") or ""), normal),
            Paragraph(str(p.get("cantidad") or ""), normal),
            Paragraph(str(p.get("descripcion") or ""), normal),
            Paragraph(str(p.get("proveedor") or ""), normal),
            Paragraph(_money(tot), right),
        ])
    iva = subtotal * 0.16
    total = subtotal + iva
    rows.append(["", "", "", Paragraph("<b>Subtotal</b>", right), Paragraph(f"<b>{_money(subtotal)}</b>", right)])
    rows.append(["", "", "", Paragraph("<b>IVA 16%</b>", right), Paragraph(f"<b>{_money(iva)}</b>", right)])
    rows.append(["", "", "", Paragraph("<b><font color=\"#EB6C24\">TOTAL</font></b>", right),
                 Paragraph(f"<b><font color=\"#EB6C24\">{_money(total)}</font></b>", right)])

    t = Table(rows, colWidths=[14 * mm, 14 * mm, 78 * mm, 44 * mm, 30 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), OSCURO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -3), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    el.append(t)
    el.append(Spacer(1, 5 * mm))

    nota = (header.get("nota") or "").strip()
    if nota:
        el.append(Paragraph("<b>Nota interna:</b>", negrita))
        el.append(Paragraph(nota, normal))
        el.append(Spacer(1, 4 * mm))

    el.append(Paragraph("Precios en pesos mexicanos (MXN).", subt))

    def _pie(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRIS)
        canvas.drawString(15 * mm, 10 * mm, f"ECCSA · {_folio_fmt(header.get('folio'))}")
        canvas.drawRightString(197 * mm, 10 * mm, f"Pág. {_doc.page}")
        canvas.restoreState()

    doc.build(el, onFirstPage=_pie, onLaterPages=_pie)
    return buf.getvalue()
