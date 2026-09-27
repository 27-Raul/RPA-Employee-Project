"""
document_generator.py
=====================
RPA Module: Document Generator
Generates:
  1. Welcome Letter (PDF)
  2. Employee ID Card (PDF)

Uses reportlab for PDF generation.
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger("RPA_Onboarding")


# ─── Helper: format date ───────────────────────────────────────────────────────
def _format_date(date_str: str) -> str:
    """Converts 'YYYY-MM-DD' → '15 September 2026'."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d %B %Y")
    except Exception:
        return date_str


# ═══════════════════════════════════════════════════════════════════════════════
#  Welcome Letter Generator
# ═══════════════════════════════════════════════════════════════════════════════
def generate_welcome_letter(employee_data: dict, output_folder: str,
                             company_name: str = "ABC Technologies") -> dict:
    """
    Generates a professional Welcome Letter PDF.

    Args:
        employee_data: Dict with all employee fields including 'employee_id'
        output_folder: Folder path where the PDF should be saved
        company_name: Company name from config

    Returns:
        {"success": True/False, "file_path": "...", "error": "..."}
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
        )

        emp_id       = employee_data.get("employee_id", "N/A")
        full_name    = employee_data.get("full_name", "Employee")
        designation  = employee_data.get("designation", "N/A")
        department   = employee_data.get("department", "N/A")
        doj          = _format_date(employee_data.get("date_of_joining", ""))
        manager      = employee_data.get("manager_name", "N/A")
        today        = datetime.now().strftime("%d %B %Y")

        os.makedirs(output_folder, exist_ok=True)
        filename  = f"Welcome_Letter_{emp_id}.pdf"
        file_path = os.path.join(output_folder, filename)

        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            leftMargin=2.5*cm, rightMargin=2.5*cm,
            topMargin=2*cm,    bottomMargin=2*cm
        )

        styles    = getSampleStyleSheet()
        dark_blue = colors.HexColor("#1E3A5F")
        gold      = colors.HexColor("#C9A84C")

        # ── Custom styles ──────────────────────────────────────
        company_style = ParagraphStyle(
            "CompanyStyle", parent=styles["Title"],
            fontSize=22, textColor=dark_blue, spaceAfter=4,
            fontName="Helvetica-Bold"
        )
        tagline_style = ParagraphStyle(
            "Tagline", parent=styles["Normal"],
            fontSize=10, textColor=gold, spaceAfter=2,
            fontName="Helvetica-Oblique"
        )
        date_style = ParagraphStyle(
            "DateStyle", parent=styles["Normal"],
            fontSize=10, textColor=colors.grey, alignment=2  # right align
        )
        heading_style = ParagraphStyle(
            "HeadingStyle", parent=styles["Heading2"],
            fontSize=14, textColor=dark_blue, spaceAfter=6,
            fontName="Helvetica-Bold"
        )
        body_style = ParagraphStyle(
            "BodyStyle", parent=styles["Normal"],
            fontSize=11, leading=18, spaceAfter=8,
            fontName="Helvetica"
        )
        bold_style = ParagraphStyle(
            "BoldStyle", parent=styles["Normal"],
            fontSize=11, leading=18, fontName="Helvetica-Bold"
        )
        footer_style = ParagraphStyle(
            "FooterStyle", parent=styles["Normal"],
            fontSize=9, textColor=colors.grey, alignment=1  # center
        )

        # ── Build document elements ────────────────────────────
        elements = []

        # Header
        elements.append(Paragraph(company_name, company_style))
        elements.append(Paragraph("Innovation · Excellence · Growth", tagline_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=gold, spaceAfter=10))

        # Date
        elements.append(Paragraph(f"Date: {today}", date_style))
        elements.append(Spacer(1, 0.5*cm))

        # Reference block
        info_data = [
            ["Ref No:", f"HR/OB/{emp_id}/{datetime.now().year}"],
            ["To:",     full_name],
        ]
        info_table = Table(info_data, colWidths=[3*cm, 12*cm])
        info_table.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",  (0, 0), (-1, -1), 11),
            ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (0, -1), dark_blue),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.4*cm))

        # Subject
        elements.append(Paragraph(
            f"<b>Subject: Offer of Employment — {designation}</b>", body_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceAfter=8))

        # Salutation
        elements.append(Paragraph(f"Dear <b>{full_name}</b>,", body_style))

        # Body
        elements.append(Paragraph(
            f"We are delighted to welcome you to <b>{company_name}</b>! "
            f"After careful consideration, we are pleased to confirm your appointment as "
            f"<b>{designation}</b> in the <b>{department}</b> Department.",
            body_style
        ))
        elements.append(Paragraph(
            f"Your employment with us will commence on <b>{doj}</b>. "
            f"You will be reporting to <b>{manager}</b>, who will guide you through "
            f"the initial phases of your role.",
            body_style
        ))
        elements.append(Paragraph(
            "We believe that your skills and experience will be a valuable asset to our team. "
            "We are excited about the contributions you will bring to our organization.",
            body_style
        ))

        # Details box
        details_data = [
            ["Employee ID",   emp_id],
            ["Full Name",     full_name],
            ["Department",    department],
            ["Designation",   designation],
            ["Date of Joining", doj],
            ["Reporting To",  manager],
        ]
        det_table = Table(details_data, colWidths=[5*cm, 10*cm])
        det_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (0, -1), dark_blue),
            ("TEXTCOLOR",   (0, 0), (0, -1), colors.white),
            ("BACKGROUND",  (1, 0), (1, -1), colors.HexColor("#EEF3F8")),
            ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE",    (0, 0), (-1, -1), 10),
            ("PADDING",     (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [None, None]),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.white),
        ]))
        elements.append(Spacer(1, 0.3*cm))
        elements.append(det_table)
        elements.append(Spacer(1, 0.5*cm))

        elements.append(Paragraph(
            "Please report to the HR department on your first day with the required documents "
            "(ID proof, address proof, educational certificates, and passport-size photographs).",
            body_style
        ))
        elements.append(Paragraph(
            f"We look forward to a long, productive, and mutually rewarding association with you at <b>{company_name}</b>.",
            body_style
        ))
        elements.append(Spacer(1, 0.8*cm))

        # Sign-off
        elements.append(Paragraph("Yours sincerely,", body_style))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph(f"<b>HR Department</b>", bold_style))
        elements.append(Paragraph(f"<b>{company_name}</b>", bold_style))
        elements.append(Spacer(1, 1.5*cm))

        # Footer
        elements.append(HRFlowable(width="100%", thickness=1, color=gold, spaceBefore=6))
        elements.append(Paragraph(
            f"{company_name} | HR Department | Confidential",
            footer_style
        ))

        doc.build(elements)
        logger.info(f"Welcome Letter generated: {file_path}")
        return {"success": True, "file_path": file_path, "error": None}

    except Exception as e:
        msg = f"Failed to generate welcome letter for {employee_data.get('employee_id', '?')}: {e}"
        logger.error(msg)
        return {"success": False, "file_path": "", "error": msg}


# ═══════════════════════════════════════════════════════════════════════════════
#  Employee ID Card Generator
# ═══════════════════════════════════════════════════════════════════════════════
def generate_id_card(employee_data: dict, output_folder: str,
                      company_name: str = "ABC Technologies") -> dict:
    """
    Generates an Employee ID Card as a PDF (credit-card landscape format).

    Returns:
        {"success": True/False, "file_path": "...", "error": "..."}
    """
    try:
        from reportlab.lib.pagesizes import landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.graphics.shapes import Drawing, Rect, Circle, String
        from reportlab.graphics import renderPDF

        emp_id      = employee_data.get("employee_id", "N/A")
        full_name   = employee_data.get("full_name", "Employee")
        department  = employee_data.get("department", "N/A")
        designation = employee_data.get("designation", "N/A")
        doj         = _format_date(employee_data.get("date_of_joining", ""))

        os.makedirs(output_folder, exist_ok=True)
        filename  = f"ID_Card_{emp_id}.pdf"
        file_path = os.path.join(output_folder, filename)

        # Use credit-card size (landscape 85.6mm x 53.98mm → A5 approx for visibility)
        CARD_W = 9*cm
        CARD_H = 5.5*cm
        page_size = (CARD_W + 2*cm, CARD_H + 2*cm)

        doc = SimpleDocTemplate(
            file_path, pagesize=page_size,
            leftMargin=1*cm, rightMargin=1*cm,
            topMargin=1*cm,  bottomMargin=1*cm
        )

        dark_blue = colors.HexColor("#1E3A5F")
        gold      = colors.HexColor("#C9A84C")
        light_bg  = colors.HexColor("#EEF3F8")

        # Build card as a Table (photo placeholder | info)
        photo_cell = Table([
            [Paragraph(f'<font size="8" color="white">PHOTO</font>', ParagraphStyle("p"))],
        ], colWidths=[2*cm], rowHeights=[2.5*cm])
        photo_cell.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), colors.HexColor("#3A5F8F")),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ]))

        def ps(text, size=9, bold=False, color=dark_blue):
            font = "Helvetica-Bold" if bold else "Helvetica"
            return Paragraph(f'<font name="{font}" size="{size}" color="{color.hexval()}">{text}</font>',
                             ParagraphStyle("x"))

        info_data = [
            [ps(company_name, size=10, bold=True, color=dark_blue)],
            [ps(f"<b>ID:</b> {emp_id}", size=9, bold=False, color=dark_blue)],
            [ps(full_name, size=10, bold=True, color=dark_blue)],
            [ps(designation, size=8)],
            [ps(department, size=8)],
            [ps(f"DOJ: {doj}", size=7, color=colors.grey)],
        ]
        info_table = Table(info_data, colWidths=[6.5*cm])
        info_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), light_bg),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))

        card_table = Table([[photo_cell, info_table]], colWidths=[2.2*cm, 6.5*cm])
        card_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), light_bg),
            ("LINEABOVE",  (0, 0), (-1, 0), 4, gold),
            ("LINEBELOW",  (0, -1), (-1, -1), 2, dark_blue),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("BOX",        (0, 0), (-1, -1), 1, dark_blue),
        ]))

        elements = [card_table]
        doc.build(elements)
        logger.info(f"ID Card generated: {file_path}")
        return {"success": True, "file_path": file_path, "error": None}

    except Exception as e:
        msg = f"Failed to generate ID card for {employee_data.get('employee_id', '?')}: {e}"
        logger.error(msg)
        return {"success": False, "file_path": "", "error": msg}
