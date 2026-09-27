import os
import datetime
import logging
import smtplib
from email.message import EmailMessage

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, ListFlowable, ListItem
from reportlab.lib.units import inch

logger = logging.getLogger('RPA_Onboarding')


def _format_date(date_str: str) -> str:
    """Helper to format date string to readable format."""
    if not date_str:
        return datetime.datetime.now().strftime('%B %d, %Y')
    try:
        dt = datetime.datetime.strptime(str(date_str).split()[0], '%Y-%m-%d')
        return dt.strftime('%B %d, %Y')
    except Exception:
        return str(date_str)


def _extract_fields(employee_data: dict):
    """Safely extracts all required fields regardless of naming convention."""
    emp_id = (employee_data.get('employee_id') or employee_data.get('EmployeeID') or
              employee_data.get('Employee ID') or employee_data.get('id') or 'EMP001')

    full_name = (employee_data.get('full_name') or employee_data.get('Full Name') or
                 employee_data.get('name') or
                 f"{employee_data.get('FirstName', '')} {employee_data.get('LastName', '')}".strip() or
                 'Candidate')

    first_name = employee_data.get('FirstName') or (full_name.split()[0] if full_name else 'Candidate')

    designation = (employee_data.get('designation') or employee_data.get('Designation') or
                   'Systems Engineer')

    department = (employee_data.get('department') or employee_data.get('Department') or 'IT')

    ctc = (employee_data.get('salary') or employee_data.get('Salary') or
           employee_data.get('ctc') or employee_data.get('CTC') or '8,50,000 INR')

    joining_date = (employee_data.get('date_of_joining') or employee_data.get('Date of Joining') or
                    employee_data.get('JoiningDate') or '')

    location = (employee_data.get('location') or employee_data.get('Location') or
                employee_data.get('address') or 'Bangalore')

    manager = (employee_data.get('manager_name') or employee_data.get('Manager Name') or
               employee_data.get('Manager') or 'HR Manager')

    email = (employee_data.get('email') or employee_data.get('Email') or
             employee_data.get('PersonalEmail') or '')

    return {
        'emp_id': emp_id,
        'full_name': full_name,
        'first_name': first_name,
        'designation': designation,
        'department': department,
        'ctc': str(ctc),
        'joining_date': joining_date,
        'formatted_joining_date': _format_date(joining_date),
        'location': location,
        'manager': manager,
        'email': email
    }


def generate_offer_letter(employee_data: dict, output_folder: str, company_name: str = 'Infosys Limited') -> dict:
    """Generates a professional Offer Letter PDF."""
    try:
        fields = _extract_fields(employee_data)
        emp_id = fields['emp_id']
        full_name = fields['full_name']
        first_name = fields['first_name']
        designation = fields['designation']
        department = fields['department']
        ctc = fields['ctc']
        location = fields['location']
        manager = fields['manager']
        email = fields['email']
        formatted_joining_date = fields['formatted_joining_date']

        current_year = datetime.datetime.now().year
        current_date_str = datetime.datetime.now().strftime('%B %d, %Y')

        os.makedirs(output_folder, exist_ok=True)
        file_name = f"OfferLetter_{emp_id}.pdf"
        file_path = os.path.join(output_folder, file_name)

        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=0.8 * inch,
            bottomMargin=0.8 * inch
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name='CompanyHeader',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#007CC3'),
            alignment=1,
            spaceAfter=4
        )

        subtitle_style = ParagraphStyle(
            name='CompanySubHeader',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#555555'),
            alignment=1,
            spaceAfter=8
        )

        normal_style = ParagraphStyle(
            name='StandardNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceAfter=6
        )

        bold_style = ParagraphStyle(
            name='BoldText',
            parent=normal_style,
            fontName='Helvetica-Bold'
        )

        elements = []

        # Header with branding
        elements.append(Paragraph(company_name, title_style))
        elements.append(Paragraph("Navigate Your Next | Global Human Resources", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#007CC3'), spaceBefore=6, spaceAfter=14))

        # Ref & Date
        ref_no = f"HR/OL/{emp_id}/{current_year}"
        elements.append(Paragraph(f"<b>Ref No:</b> {ref_no}", normal_style))
        elements.append(Paragraph(f"<b>Date:</b> {current_date_str}", normal_style))
        elements.append(Spacer(1, 10))

        # Employee Address
        elements.append(Paragraph("<b>To,</b>", normal_style))
        elements.append(Paragraph(f"<b>{full_name}</b>", bold_style))
        if email:
            elements.append(Paragraph(f"Email: {email}", normal_style))
        elements.append(Spacer(1, 10))

        # Subject
        elements.append(Paragraph("<b>Subject: Offer of Employment</b>", bold_style))
        elements.append(Spacer(1, 8))

        # Body
        body_text = f"""Dear {first_name},<br/><br/>
        Congratulations! We are delighted to offer you the position of <b>{designation}</b> in the 
        <b>{department}</b> department at <b>{company_name}</b>. 
        Your expected joining date will be <b>{formatted_joining_date}</b>. You will be reporting to 
        <b>{manager}</b> at our <b>{location}</b> development center.
        <br/><br/>
        Your Total Cost to Company (CTC) will be <b>{ctc}</b> per annum.
        """
        elements.append(Paragraph(body_text, normal_style))
        elements.append(Spacer(1, 10))

        # Details Table
        table_data = [
            ['Employee ID', emp_id],
            ['Candidate Name', full_name],
            ['Designation', designation],
            ['Department', department],
            ['Annual CTC', ctc],
            ['Joining Date', formatted_joining_date],
            ['Work Location', location],
            ['Reporting Manager', manager]
        ]

        t = Table(table_data, colWidths=[2.2 * inch, 3.8 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F7FA')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#003366')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB'))
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # Terms
        terms_text = """<b>Key Terms and Conditions:</b><br/>
        1. <b>Probation:</b> You will be on probation for a period of 6 months from your date of joining.<br/>
        2. <b>Notice Period:</b> Either party may terminate this employment agreement by providing 30 days written notice.<br/>
        3. <b>Code of Conduct:</b> You are expected to adhere to the company's code of conduct and confidentiality guidelines.
        """
        elements.append(Paragraph(terms_text, normal_style))
        elements.append(Spacer(1, 10))

        # Documents to bring
        elements.append(Paragraph("<b>Please bring the following documents on your day of joining:</b>", normal_style))
        doc_list = ListFlowable(
            [
                ListItem(Paragraph("Government ID Proof (Aadhaar / Passport / PAN Card)", normal_style)),
                ListItem(Paragraph("Current & Permanent Address Proof", normal_style)),
                ListItem(Paragraph("All Educational Marksheets & Degree Certificates", normal_style)),
                ListItem(Paragraph("Relieving Letter / Service Certificate from previous employer", normal_style)),
                ListItem(Paragraph("Cancelled Cheque / Bank Account Details for salary disbursement", normal_style)),
                ListItem(Paragraph("4 Passport-size Photographs", normal_style))
            ],
            bulletType='bullet',
            start='square',
            bulletFontName='Helvetica',
            bulletFontSize=7
        )
        elements.append(doc_list)
        elements.append(Spacer(1, 16))

        # Signature Block
        elements.append(Paragraph("Yours sincerely,", normal_style))
        elements.append(Spacer(1, 14))
        elements.append(Paragraph("<b>Head - Talent Acquisition & HR</b>", bold_style))
        elements.append(Paragraph(f"<b>{company_name}</b>", normal_style))

        # Build PDF
        doc.build(elements)
        logger.info(f"Offer letter generated successfully at {file_path}")

        return {'success': True, 'file_path': file_path, 'error': None}

    except Exception as e:
        logger.error(f"Error generating offer letter: {str(e)}", exc_info=True)
        return {'success': False, 'file_path': None, 'error': str(e)}


def build_offer_email_body(employee_data: dict, company_name: str) -> str:
    """Build plain text email body for offer letter."""
    fields = _extract_fields(employee_data)
    first_name = fields['first_name']
    designation = fields['designation']
    department = fields['department']
    ctc = fields['ctc']
    joining_date = fields['formatted_joining_date']

    return f"""Dear {first_name},

Congratulations! We are thrilled to offer you the position of {designation} in the {department} department at {company_name}.

Your annual CTC will be {ctc}, and your expected joining date is {joining_date}.

Please find attached your official Offer Letter containing detailed terms and conditions, along with the list of onboarding documents required on Day 1.

We are excited to welcome you to the {company_name} family!

Best Regards,
Talent Acquisition Team
{company_name}
"""


def build_offer_email_html(employee_data: dict, company_name: str) -> str:
    """Build HTML email body for offer letter with styled card layout."""
    fields = _extract_fields(employee_data)
    first_name = fields['first_name']
    designation = fields['designation']
    department = fields['department']
    ctc = fields['ctc']
    joining_date = fields['formatted_joining_date']
    emp_id = fields['emp_id']

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #F5F7FA; padding: 20px; color: #333333; }}
        .card {{ background-color: #ffffff; padding: 32px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); max-width: 600px; margin: auto; border-top: 5px solid #007CC3; }}
        .header {{ border-bottom: 1px solid #E5E7EB; padding-bottom: 16px; margin-bottom: 20px; }}
        .header h2 {{ margin: 0; color: #007CC3; font-size: 24px; }}
        .tagline {{ font-size: 12px; color: #6B7280; text-transform: uppercase; letter-spacing: 1px; }}
        .details {{ background-color: #F8FAFC; padding: 18px; border-left: 4px solid #007CC3; margin: 20px 0; border-radius: 4px; }}
        .details table {{ width: 100%; border-collapse: collapse; }}
        .details td {{ padding: 6px 0; font-size: 14px; }}
        .details td.label {{ color: #6B7280; width: 40%; font-weight: 600; }}
        .details td.val {{ color: #1E293B; font-weight: 700; }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #94A3B8; border-top: 1px solid #E2E8F0; padding-top: 15px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h2>{company_name}</h2>
            <div class="tagline">Navigate Your Next | Human Resources</div>
        </div>
        <p>Dear <strong>{first_name}</strong>,</p>
        <p>Congratulations! We are delighted to extend an offer of employment for the position of <strong>{designation}</strong> in the <strong>{department}</strong> team at <strong>{company_name}</strong>.</p>
        
        <div class="details">
            <table>
                <tr><td class="label">Employee ID:</td><td class="val">{emp_id}</td></tr>
                <tr><td class="label">Designation:</td><td class="val">{designation}</td></tr>
                <tr><td class="label">Department:</td><td class="val">{department}</td></tr>
                <tr><td class="label">Annual CTC:</td><td class="val">{ctc}</td></tr>
                <tr><td class="label">Joining Date:</td><td class="val">{joining_date}</td></tr>
            </table>
        </div>
        
        <p>Please find attached your official <strong>Offer Letter</strong>. Please review it and feel free to reach out if you have any questions.</p>
        <p>We look forward to welcoming you aboard!</p>
        
        <p style="margin-top:24px;">Warm Regards,<br/><strong>Talent Acquisition &amp; HR</strong><br/>{company_name}</p>
        
        <div class="footer">
            This is an automated communication generated by the {company_name} RPA Onboarding System.
        </div>
    </div>
</body>
</html>"""


def send_offer_email(employee_data: dict, config: dict, offer_letter_path: str = None) -> dict:
    """Send offer email, either in mock mode or via SMTP."""
    try:
        fields = _extract_fields(employee_data)
        emp_id = fields['emp_id']
        to_email = fields['email']
        designation = fields['designation']

        company_name = (config.get('CompanyName') or config.get('company_name') or 'Infosys Limited')
        email_mode = str(config.get('EmailMode') or config.get('email_mode') or 'mock').lower()
        use_mock = (email_mode == 'mock' or not email_mode.startswith('smtp'))

        subject = f"Offer of Employment - {designation} - {company_name}"
        body_text = build_offer_email_body(employee_data, company_name)
        body_html = build_offer_email_html(employee_data, company_name)

        if use_mock:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_dir = os.path.join(base_dir, 'Logs', 'MockEmails')
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            mock_file = os.path.join(log_dir, f"OfferEmail_{emp_id}_{timestamp}.txt")

            with open(mock_file, 'w', encoding='utf-8') as f:
                f.write(f"TO: {to_email}\n")
                f.write(f"SUBJECT: {subject}\n")
                f.write(f"ATTACHMENT: {offer_letter_path}\n")
                f.write(f"MODE: Mock Email (no internet transmission)\n")
                f.write("=" * 60 + "\n\n")
                f.write(body_text)

            logger.info(f"Mock offer email saved for {emp_id} ({fields['full_name']}) to {mock_file}")
            return {'success': True, 'mode': 'mock', 'file': mock_file, 'error': None}

        else:
            smtp_server = config.get('SMTPServer') or config.get('smtp_server')
            smtp_port = int(config.get('SMTPPort') or config.get('smtp_port') or 587)
            smtp_user = config.get('SenderEmail') or config.get('smtp_user')
            smtp_password = config.get('SenderPassword') or config.get('smtp_password')

            if not all([smtp_server, smtp_user, smtp_password]):
                logger.warning("Incomplete SMTP settings in Config.xlsx. Falling back to mock email mode.")
                return send_offer_email(employee_data, {**config, 'EmailMode': 'mock'}, offer_letter_path)

            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = smtp_user
            msg['To'] = to_email

            msg.set_content(body_text)
            msg.add_alternative(body_html, subtype='html')

            if offer_letter_path and os.path.exists(offer_letter_path):
                with open(offer_letter_path, 'rb') as f:
                    pdf_data = f.read()
                msg.add_attachment(
                    pdf_data,
                    maintype='application',
                    subtype='pdf',
                    filename=os.path.basename(offer_letter_path)
                )

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            logger.info(f"Offer email sent via SMTP to {to_email}")
            return {'success': True, 'mode': 'smtp', 'error': None}

    except Exception as e:
        logger.error(f"Error sending offer email for {employee_data.get('employee_id')}: {str(e)}", exc_info=True)
        return {'success': False, 'mode': 'unknown', 'error': str(e)}
