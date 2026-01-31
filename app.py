from flask import Flask, render_template, request, send_file, jsonify
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import json
import os
from io import BytesIO

app = Flask(__name__)

# Create necessary directories
os.makedirs('invoices', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('static/images', exist_ok=True)

# Load or initialize invoice counter
COUNTER_FILE = 'data/invoice_counter.json'
if os.path.exists(COUNTER_FILE):
    with open(COUNTER_FILE, 'r') as f:
        counter_data = json.load(f)
else:
    counter_data = {'last_invoice_number': 0}
    with open(COUNTER_FILE, 'w') as f:
        json.dump(counter_data, f)

def get_next_invoice_number():
    """Get and increment the invoice number"""
    with open(COUNTER_FILE, 'r') as f:
        data = json.load(f)
    
    data['last_invoice_number'] += 1
    
    from datetime import datetime
    today = datetime.now()
    date_part = today.strftime("%d%m%y")
    seq_part = f"{data['last_invoice_number']:04d}"
    
    invoice_num = f"NF{seq_part}{date_part}"
    
    with open(COUNTER_FILE, 'w') as f:
        json.dump(data, f)
    
    return invoice_num

def preview_next_invoice_number():
    """Preview the next invoice number without incrementing"""
    with open(COUNTER_FILE, 'r') as f:
        data = json.load(f)
    
    from datetime import datetime
    today = datetime.now()
    date_part = today.strftime("%d%m%y")
    seq_part = f"{data['last_invoice_number'] + 1:04d}"
    
    next_num = f"NF{seq_part}{date_part}"
    return next_num

def number_to_words(num):
    """Convert number to words (Indian numbering system)"""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    
    def convert_below_thousand(n):
        if n == 0:
            return ''
        elif n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            return tens[n // 10] + (' ' + ones[n % 10] if n % 10 != 0 else '')
        else:
            return ones[n // 100] + ' Hundred' + (' and ' + convert_below_thousand(n % 100) if n % 100 != 0 else '')
    
    if num == 0:
        return 'Zero Rupees Only'
    
    crore = num // 10000000
    num %= 10000000
    lakh = num // 100000
    num %= 100000
    thousand = num // 1000
    num %= 1000
    
    result = ''
    if crore > 0:
        result += convert_below_thousand(crore) + ' Crore '
    if lakh > 0:
        result += convert_below_thousand(lakh) + ' Lakh '
    if thousand > 0:
        result += convert_below_thousand(thousand) + ' Thousand '
    if num > 0:
        result += convert_below_thousand(num)
    
    return result.strip() + ' Rupees Only'

def generate_pdf(invoice_data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.6*inch, bottomMargin=0.6*inch, 
                           leftMargin=0.6*inch, rightMargin=0.6*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Define minimalist color palette
    BLACK = colors.HexColor('#000000')
    DARK_GREY = colors.HexColor('#333333')
    MEDIUM_GREY = colors.HexColor('#666666')
    LIGHT_GREY = colors.HexColor('#F5F5F5')
    BORDER_GREY = colors.HexColor('#E0E0E0')
    WHITE = colors.white
    # Payment status colors
    RED = colors.HexColor('#DC2626')
    GREEN = colors.HexColor('#16A34A')
    
    # Custom styles - Premium & Minimalist
    title_style = ParagraphStyle(
        'MinimalTitle',
        parent=styles['Heading1'],
        fontSize=32,
        textColor=BLACK,
        spaceAfter=6,
        spaceBefore=0,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
        leading=38
    )
    
    invoice_label_style = ParagraphStyle(
        'InvoiceLabel',
        parent=styles['Normal'],
        fontSize=11,
        textColor=MEDIUM_GREY,
        fontName='Helvetica',
        leading=14
    )
    
    invoice_value_style = ParagraphStyle(
        'InvoiceValue',
        parent=styles['Normal'],
        fontSize=11,
        textColor=BLACK,
        fontName='Helvetica-Bold',
        leading=14
    )
    
    heading_style = ParagraphStyle(
        'MinimalHeading',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=DARK_GREY,
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        letterSpacing=1
    )
    
    normal_style = ParagraphStyle(
        'MinimalNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=DARK_GREY,
        leading=13,
        fontName='Helvetica'
    )
    
    small_style = ParagraphStyle(
        'MinimalSmall',
        parent=styles['Normal'],
        fontSize=8.5,
        textColor=MEDIUM_GREY,
        leading=11,
        fontName='Helvetica'
    )
    
    bold_style = ParagraphStyle(
        'MinimalBold',
        parent=styles['Normal'],
        fontSize=9,
        textColor=BLACK,
        fontName='Helvetica-Bold'
    )
    
    # Logo section - Wider aspect ratio
    logo_path = 'static/images/nafrok-logo.png'
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=3.5*inch, height=0.7*inch)
        logo.hAlign = 'LEFT'
        story.append(logo)
        story.append(Spacer(1, 0.15*inch))
    
    # Invoice title and number side by side
    header_data = [
        [Paragraph("INVOICE", title_style), 
         [Paragraph(f"<para alignment='right'><font size='9' color='#666666'>INVOICE NO.</font><br/><font size='11' color='#000000'><b>{invoice_data['invoice_number']}</b></font></para>", normal_style)]]
    ]
    
    header_table = Table(header_data, colWidths=[4.5*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.25*inch))
    
    # Thin separator line
    line_table = Table([['']], colWidths=[7*inch])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, BORDER_GREY),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 0.25*inch))
    
    # Company and Client info side by side
    company_content = [
        Paragraph("<b>NAFROK</b>", bold_style),
        Paragraph("Professional Web Design & Development", small_style),
        Paragraph("Bangalore, Karnataka, India", small_style),
        Paragraph("contact.nafrok@gmail.com", small_style),
        Paragraph("+91 8050106590", small_style),
    ]
    
    bill_to_content = [
        Paragraph("BILL TO", heading_style),
        Paragraph(f"<b>{invoice_data['client_name']}</b>", bold_style),
    ]
    if invoice_data.get('client_email'):
        bill_to_content.append(Paragraph(invoice_data['client_email'], small_style))
    if invoice_data.get('client_phone'):
        bill_to_content.append(Paragraph(invoice_data['client_phone'], small_style))
    if invoice_data.get('client_address'):
        bill_to_content.append(Paragraph(invoice_data['client_address'], small_style))
    
    info_table = Table([[company_content, bill_to_content]], colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.25*inch))
    
    # Invoice dates
    dates_data = [
        [Paragraph("Invoice Date", invoice_label_style), Paragraph(invoice_data['invoice_date'], invoice_value_style),
         Paragraph("Due Date", invoice_label_style), Paragraph(invoice_data['due_date'], invoice_value_style)],
    ]
    dates_table = Table(dates_data, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    dates_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(dates_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Services table
    services_data = [
        [Paragraph("<b>DESCRIPTION</b>", heading_style), 
         Paragraph("<b>QTY</b>", heading_style),
         Paragraph("<b>RATE</b>", heading_style), 
         Paragraph("<b>AMOUNT</b>", heading_style)]
    ]
    
    for service in invoice_data['services']:
        desc_text = f"<b>{service['service_type']}</b><br/><font size='8' color='#666666'>{service['description']}</font>"
        services_data.append([
            Paragraph(desc_text, normal_style),
            Paragraph(str(service['quantity']), normal_style),
            Paragraph(f"Rs. {service['rate']:,.2f}", normal_style),
            Paragraph(f"<b>Rs. {service['amount']:,.2f}</b>", bold_style)
        ])
    
    services_table = Table(services_data, colWidths=[3.8*inch, 0.7*inch, 1.2*inch, 1.3*inch])
    services_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GREY),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('LINEBELOW', (0, 0), (-1, 0), 1, BORDER_GREY),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, BORDER_GREY),
    ]))
    story.append(services_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Summary section
    subtotal = sum(s['amount'] for s in invoice_data['services'])
    discount = invoice_data.get('discount', 0)
    total = subtotal - discount
    
    summary_data = []
    
    # Subtotal
    summary_data.append([
        '', '', 
        Paragraph("Subtotal", normal_style), 
        Paragraph(f"Rs. {subtotal:,.2f}", normal_style)
    ])
    
    # Discount with percentage if applicable
    if discount > 0:
        discount_pct = (discount / subtotal * 100) if subtotal > 0 else 0
        discount_text = f"Discount ({discount_pct:.1f}%)" if discount_pct > 0 else "Discount"
        summary_data.append([
            '', '', 
            Paragraph(discount_text, normal_style), 
            Paragraph(f"- Rs. {discount:,.2f}", normal_style)
        ])
    
    # Total
    summary_data.append([
        '', '', 
        Paragraph("<b>TOTAL</b>", bold_style), 
        Paragraph(f"<b>Rs. {total:,.2f}</b>", bold_style)
    ])
    
    summary_table = Table(summary_data, colWidths=[3.8*inch, 0.7*inch, 1.2*inch, 1.3*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('LINEABOVE', (2, -1), (-1, -1), 1.5, BLACK),
        ('BACKGROUND', (2, -1), (-1, -1), LIGHT_GREY),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.15*inch))
    
    # Amount in words
    story.append(Paragraph(f"<i>{number_to_words(int(total))}</i>", small_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Payment Phases - Push to next page if exists
    if invoice_data.get('payment_phases') and len(invoice_data['payment_phases']) > 0:
        # Add page break to push payment schedule to next page
        story.append(PageBreak())
        
        story.append(Paragraph("PAYMENT SCHEDULE", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        phases_data = [
            [Paragraph("<b>PHASE</b>", heading_style), 
             Paragraph("<b>AMOUNT</b>", heading_style),
             Paragraph("<b>DUE DATE</b>", heading_style), 
             Paragraph("<b>STATUS</b>", heading_style)]
        ]
        
        total_paid = 0
        row_idx = 1  # Start from 1 because row 0 is header
        for phase in invoice_data['payment_phases']:
            status_text = phase['status']
            # Color code based on status
            if phase['status'] == 'Paid':
                status_para = Paragraph(f"<b><font color='#16A34A'>{status_text}</font></b>", bold_style)
            else:
                status_para = Paragraph(f"<b><font color='#DC2626'>{status_text}</font></b>", bold_style)
            
            phases_data.append([
                Paragraph(phase['phase_name'], normal_style),
                Paragraph(f"Rs. {phase['amount']:,.2f}", normal_style),
                Paragraph(phase['due_date'], normal_style),
                status_para
            ])
            if phase['status'] == 'Paid':
                total_paid += phase['amount']
            row_idx += 1
        
        balance = total - total_paid
        
        phases_table = Table(phases_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        phases_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GREY),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('LINEBELOW', (0, 0), (-1, 0), 1, BORDER_GREY),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, BORDER_GREY),
        ]))
        story.append(phases_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Payment summary
        payment_summary = [
            ['', Paragraph(f"<b>Total Paid:</b> Rs. {total_paid:,.2f}", bold_style),
             Paragraph(f"<b>Balance Due:</b> Rs. {balance:,.2f}", bold_style)]
        ]
        summary_table = Table(payment_summary, colWidths=[2.5*inch, 2.25*inch, 2.25*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('BACKGROUND', (1, 0), (-1, 0), LIGHT_GREY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Terms and Notes
    if invoice_data.get('payment_terms'):
        story.append(Paragraph("PAYMENT TERMS", heading_style))
        story.append(Paragraph(invoice_data['payment_terms'], small_style))
        story.append(Spacer(1, 0.15*inch))
    
    if invoice_data.get('notes'):
        story.append(Paragraph("NOTES", heading_style))
        story.append(Paragraph(invoice_data['notes'], small_style))
        story.append(Spacer(1, 0.15*inch))
    
    # Bank Details
    if invoice_data.get('bank_details'):
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("BANK DETAILS", heading_style))
        story.append(Paragraph(invoice_data['bank_details'], small_style))
    
    # Standard Terms & Conditions (Always at the end)
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("TERMS & CONDITIONS", heading_style))
    
    terms_style = ParagraphStyle(
        'TermsStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=DARK_GREY,
        leading=12,
        fontName='Helvetica',
        leftIndent=15,
        bulletIndent=8
    )
    
    terms_list = [
        "50% advance payment required to start the project",
        "Remaining 50% due upon project completion",
        "2-3 revisions included in the package price",
        "Additional revisions charged at Rs500 per round",
        "Timeline begins after content and assets are received",
        "Domain and hosting renewals are client's responsibility",
        "Prices are subject to change without prior notice"
    ]
    
    for idx, term in enumerate(terms_list, 1):
        story.append(Paragraph(f"{idx}. {term}", terms_style))
        if idx < len(terms_list):
            story.append(Spacer(1, 0.08*inch))
    
    # Footer
    story.append(Spacer(1, 0.4*inch))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], 
                                 fontSize=8, alignment=TA_CENTER, 
                                 textColor=MEDIUM_GREY, fontName='Helvetica-Oblique')
    story.append(Paragraph("Thank you for your business", footer_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-next-invoice-number')
def get_invoice_number():
    """Preview the next invoice number (doesn't increment)"""
    next_num = preview_next_invoice_number()
    return jsonify({'invoice_number': next_num})

@app.route('/generate-invoice', methods=['POST'])
def generate_invoice():
    try:
        invoice_data = request.json
        
        # Always generate a new invoice number
        invoice_data['invoice_number'] = get_next_invoice_number()
        
        # Generate PDF
        pdf_buffer = generate_pdf(invoice_data)
        
        # Save invoice data
        invoice_file = f"data/invoice_{invoice_data['invoice_number']}.json"
        with open(invoice_file, 'w') as f:
            json.dump(invoice_data, f, indent=2)
        
        # Save PDF
        pdf_filename = f"invoices/{invoice_data['invoice_number']}.pdf"
        with open(pdf_filename, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        return jsonify({'success': True, 'filename': invoice_data['invoice_number']})
    except Exception as e:
        print(f"Error generating invoice: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<invoice_number>')
def download_invoice(invoice_number):
    pdf_path = f"invoices/{invoice_number}.pdf"
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name=f"{invoice_number}.pdf")
    return "Invoice not found", 404

@app.route('/history')
def history():
    invoices = []
    if os.path.exists('data'):
        for filename in os.listdir('data'):
            if filename.startswith('invoice_') and filename.endswith('.json'):
                try:
                    with open(f'data/{filename}', 'r') as f:
                        invoice = json.load(f)
                        if 'invoice_number' in invoice:
                            invoices.append(invoice)
                except:
                    continue
    
    invoices.sort(key=lambda x: x.get('invoice_number', ''), reverse=True)
    return render_template('history.html', invoices=invoices)

if __name__ == '__main__':
    app.run(debug=True, port=5000)