"""Convierte las facturas de referencia (JSON) en documentos PDF."""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from lab01_invoice_extraction.generate_data import IRPF_RATE
from lab01_invoice_extraction.schema import Invoice, Party

LAB_DIR = Path(__file__).resolve().parents[2]
GROUND_TRUTH_DIR = LAB_DIR / "data" / "ground_truth"
PDF_DIR = LAB_DIR / "data" / "pdfs"

STYLES = getSampleStyleSheet()


def eur(amount: float) -> str:
    """Formato español de moneda: 4357.2 -> '4.357,20 €'."""
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} €"


def party_block(title: str, party: Party) -> Paragraph:
    """Bloque de texto con los datos del emisor o del cliente."""
    text = (
        f"<b>{title}</b><br/>{escape(party.name)}<br/>"
        f"NIF: {escape(party.tax_id)}<br/>{escape(party.address)}"
    )
    return Paragraph(text, STYLES["Normal"])


def render_invoice(invoice: Invoice, path: Path) -> None:
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )
    story = []

    # Cabecera
    story.append(Paragraph("FACTURA", STYLES["Title"]))
    story.append(Paragraph(
        f"<b>Nº de factura:</b> {invoice.invoice_number}<br/>"
        f"<b>Fecha de expedición:</b> {invoice.issue_date:%d/%m/%Y}",
        STYLES["Normal"],
    ))
    story.append(Spacer(1, 0.6 * cm))

    # Emisor y cliente, en dos columnas
    parties = Table(
        [[party_block("Emisor", invoice.issuer), party_block("Cliente", invoice.recipient)]],
        colWidths=[8.5 * cm, 8.5 * cm],
    )
    parties.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [parties, Spacer(1, 0.8 * cm)]

    # Líneas de detalle
    rows = [["Concepto", "Cant.", "Precio unit.", "IVA", "Importe"]]
    for li in invoice.line_items:
        rows.append([
            Paragraph(escape(li.description), STYLES["Normal"]),
            f"{li.quantity:g}",
            eur(li.unit_price),
            f"{li.vat_rate:g} %",
            eur(li.quantity * li.unit_price),
        ])
    lines = Table(rows, colWidths=[7 * cm, 1.5 * cm, 3 * cm, 1.5 * cm, 4 * cm])
    lines.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story += [lines, Spacer(1, 0.6 * cm)]

    # Totales
    totals = [
        ["Base imponible", eur(invoice.tax_base)],
        ["Cuota IVA", eur(invoice.vat_amount)],
    ]
    if invoice.irpf_amount is not None:
        totals.append([f"Retención IRPF ({IRPF_RATE:g} %)", f"-{eur(invoice.irpf_amount)}"])
    totals.append(["TOTAL A PAGAR", eur(invoice.total)])

    totals_table = Table(totals, colWidths=[5 * cm, 4 * cm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
    ]))
    story.append(totals_table)

    doc.build(story)


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for json_path in sorted(GROUND_TRUTH_DIR.glob("invoice_*.json")):
        invoice = Invoice.model_validate_json(json_path.read_text(encoding="utf-8"))
        pdf_path = PDF_DIR / f"{json_path.stem}.pdf"
        render_invoice(invoice, pdf_path)
        print(f"{pdf_path.name} generado")


if __name__ == "__main__":
    main()