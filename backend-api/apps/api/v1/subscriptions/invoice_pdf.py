"""E38 · Branded, server-rendered, deterministic A4 invoices.

Every datum comes from an immutable invoice snapshot. No browser-generated
document or unverified payment can claim to be an invoice.
"""
from html import escape
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer


BLUE = colors.HexColor("#274A8B")
TEAL = colors.HexColor("#168E89")
SLATE = colors.HexColor("#5D7192")
BORDER = colors.HexColor("#DDE8EF")
SURFACE = colors.HexColor("#EDF8F5")


def _safe(value):
    return escape(str(value if value is not None else ""), quote=True).replace("\n", "<br/>")


def render_invoice_pdf(invoice):
    issuer = invoice.issuer_snapshot
    buyer = invoice.customer_snapshot
    sale = invoice.sale_snapshot
    out = BytesIO()
    doc = SimpleDocTemplate(
        out, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
        title=f"Facture {_safe(invoice.number)}",
        author=issuer["legal_name"], invariant=1,
    )
    body = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.4, leading=15, textColor=SLATE)
    bold = ParagraphStyle("Bold", parent=body, fontName="Helvetica-Bold", textColor=BLUE)
    title = ParagraphStyle("Title", parent=bold, fontSize=24, leading=30)
    hint = ParagraphStyle("Hint", parent=body, fontSize=8, leading=12)
    right = ParagraphStyle("Right", parent=body, alignment=TA_RIGHT)
    total = ParagraphStyle("Total", parent=right, fontName="Helvetica-Bold", fontSize=14, textColor=BLUE)
    brand = ParagraphStyle("Brand", parent=bold, fontSize=15, leading=21)
    cols = (82*mm, 88*mm)

    def P(value, style=body):
        return Paragraph(_safe(value), style)

    story = [
        Table([[P("G-CONNECT", brand), P("FACTURE", title)]], colWidths=cols,
              style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
                                ("ALIGN",(1,0),(1,0),"RIGHT")]))
    ]
    story += [Spacer(1, 12*mm)]
    heading = [
        [P("ÉMETTEUR", bold), P("CLIENT", bold)],
        [P(issuer["legal_name"], bold), P(buyer["legal_name"], bold)],
        [P(issuer["address"]), P(buyer["address"])],
        [P("Pays : " + issuer["country_code"]), P("Pays : " + buyer["country_code"])],
        [P("Immatriculation : " + issuer["registration_number"]),
         P("Identifiant fiscal : " + (buyer.get("tax_identifier") or "Non communiqué"))],
        [P("Identifiant fiscal : " + issuer["tax_identifier"]), P(buyer["email"])],
        [P(issuer["email"]), P("")],
    ]
    story.append(Table(heading, colWidths=cols, hAlign="LEFT", style=TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LINEBELOW",(0,0),(-1,0),.75,BORDER),
    ])))
    story += [Spacer(1, 11*mm)]
    issue_date = invoice.issued_at.strftime("%d/%m/%Y")
    reference = [
        ["N° de facture", invoice.number],
        ["Date d'émission", issue_date],
        ["Référence du paiement", sale["transaction_id"]],
        ["Prestataire", sale["payment_provider"]],
        ["Paiement vérifié le", sale["verified_at"][:10]],
        ["Abonnement", "#" + str(invoice.subscription_id)],
        ["Période du forfait", sale["starts_at"] + " au " + sale["ends_at"]],
    ]
    info = [[P(k, hint), P(v, bold)] for k,v in reference]
    story.append(Table(info,colWidths=(45*mm,125*mm),hAlign="LEFT",
        style=TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),SURFACE),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LEFTPADDING",(0,0),(-1,-1),11),
        ])))
    story += [Spacer(1, 12*mm)]
    quota_name = "publications" if sale["quota_unit"] == "publications" else "comptes"
    description = f'{sale["offer_name"]} – {sale["capacity"]} {quota_name} – {sale["term_months"]} mois'
    cells = [
        [P("DESCRIPTION",bold),P("PRIX HT",bold)],
        [P(description),P(f'{invoice.amount_net:.2f} {invoice.currency}',right)],
    ]
    story.append(Table(cells,colWidths=cols,style=TableStyle([
        ("BACKGROUND",(0,0),(-1,0),SURFACE),
        ("LINEBELOW",(0,-1),(-1,-1),.7,BORDER),
        ("TOPPADDING",(0,0),(-1,-1),12),
        ("BOTTOMPADDING",(0,0),(-1,-1),12),
    ])))
    story += [Spacer(1,9*mm)]
    if issuer["tax_treatment"] == "included":
        tax_label = f'{issuer["tax_label"]} ({issuer["tax_rate"]} %), comprise dans le prix'
    else:
        tax_label = "Exonération : " + issuer["exemption_reason"]
    summary = [
        [P("Base hors taxe"), P(f"{invoice.amount_net:.2f} {invoice.currency}",right)],
        [P(tax_label), P(f"{invoice.amount_tax:.2f} {invoice.currency}",right)],
        [P("TOTAL ACQUITTÉ", bold), P(f"{invoice.amount_total:.2f} {invoice.currency}",total)],
    ]
    story.append(Table(summary,colWidths=cols,style=TableStyle([
        ("LINEABOVE",(0,2),(-1,2),1.2,TEAL),
        ("TOPPADDING",(0,0),(-1,-1),11),
        ("BOTTOMPADDING",(0,0),(-1,-1),11),
    ])))
    story += [Spacer(1,9*mm),P(
        "Paiement confirmé par le prestataire et rapproché avec le contrat d'abonnement.",
        hint,
    )]

    def footer(canvas, document):
        canvas.saveState()
        w,_ = A4
        canvas.setStrokeColor(BORDER)
        canvas.line(20*mm,18*mm,w-20*mm,18*mm)
        canvas.setFillColor(SLATE)
        canvas.setFont("Helvetica",8)
        canvas.drawString(20*mm,12*mm, "G-Connect · Facture " + invoice.number)
        canvas.drawRightString(w-20*mm,12*mm,"Page " + str(document.page))
        canvas.restoreState()

    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
