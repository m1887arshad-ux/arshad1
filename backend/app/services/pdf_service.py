"""
PDF Invoice Generation Service
Creates professional invoices with business and customer details
"""
from io import BytesIO
from datetime import datetime
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from sqlalchemy.orm import Session
from app.models.invoice import Invoice
from app.models.business import Business


def generate_invoice_pdf(db: Session, invoice_id: int) -> BytesIO:
    """
    Generate PDF for an invoice
    
    Args:
        db: Database session
        invoice_id: ID of the invoice to generate PDF for
        
    Returns:
        BytesIO buffer containing PDF data
    """
    # Fetch invoice with relationships
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")
    
    customer = invoice.customer
    business = db.query(Business).filter(Business.id == customer.business_id).first()
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a56db'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=6
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#374151')
    )
    
    # Title
    elements.append(Paragraph("TAX INVOICE", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Business and Invoice Info Section
    info_data = [
        [
            Paragraph(f"<b>{business.name if business else 'Bharat Medical Store'}</b><br/>"
                     f"India", normal_style),
            Paragraph(f"<b>Invoice #:</b> {invoice.id}<br/>"
                     f"<b>Date:</b> {invoice.created_at.strftime('%d %b %Y, %I:%M %p')}<br/>"
                     f"<b>Status:</b> {invoice.status.upper()}", normal_style)
        ]
    ]
    
    info_table = Table(info_data, colWidths=[3.5*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Customer Information
    elements.append(Paragraph("<b>Bill To:</b>", heading_style))
    customer_info = f"<b>{customer.name}</b>"
    if hasattr(customer, 'phone') and customer.phone:
        customer_info += f"<br/>Phone: {customer.phone}"
    elements.append(Paragraph(customer_info, normal_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Items Table (for now, just show total amount)
    # In future, this can be expanded to show line items
    items_data = [
        [Paragraph("<b>Description</b>", normal_style), 
         Paragraph("<b>Quantity</b>", normal_style),
         Paragraph("<b>Rate</b>", normal_style),
         Paragraph("<b>Amount</b>", normal_style)],
        [Paragraph("Medical supplies as per order", normal_style),
         Paragraph("1", normal_style),
         Paragraph(f"₹{float(invoice.base_amount):.2f}", normal_style),
         Paragraph(f"₹{float(invoice.base_amount):.2f}", normal_style)]
    ]
    
    items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.2*inch, 1.3*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Total Section with GST breakdown
    gst_rate_percent = float(invoice.gst_rate) * 100  # Convert 0.18 to 18
    total_data = [
        ['', '', Paragraph("<b>Subtotal:</b>", normal_style), Paragraph(f"₹{float(invoice.base_amount):.2f}", normal_style)],
        ['', '', Paragraph(f"<b>GST ({gst_rate_percent:.0f}%):</b>", normal_style), Paragraph(f"₹{float(invoice.gst_amount):.2f}", normal_style)],
        ['', '', Paragraph("<b style='fontSize:12'>TOTAL:</b>", heading_style), 
         Paragraph(f"<b style='fontSize:12'>₹{float(invoice.amount):.2f}</b>", heading_style)]
    ]
    
    total_table = Table(total_data, colWidths=[3*inch, 1*inch, 1.2*inch, 1.3*inch])
    total_table.setStyle(TableStyle([
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (2, 2), (-1, 2), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Payment Instructions
    elements.append(Paragraph("<b>Payment Instructions:</b>", heading_style))
    payment_text = ("Please pay the above amount within 30 days. "
                   "For any queries, contact us at the phone number above.")
    elements.append(Paragraph(payment_text, normal_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("Thank you for your business!", footer_style))
    elements.append(Paragraph(f"Invoice generated on {datetime.now().strftime('%d %b %Y at %I:%M %p')}", footer_style))
    
    # Build PDF
    doc.build(elements)
    
    # Reset buffer position to start
    buffer.seek(0)
    return buffer


def format_invoice_message(invoice: Invoice, customer_name: str, business_name: str = None) -> str:
    """
    Format invoice details as a text message for Telegram
    
    Args:
        invoice: Invoice object
        customer_name: Name of the customer
        business_name: Name of the business (optional)
        
    Returns:
        Formatted message string
    """
    business_name = business_name or "Bharat Medical Store"
    gst_rate_percent = float(invoice.gst_rate) * 100
    
    message = f"""
🧾 **INVOICE #{invoice.id}**

📅 Date: {invoice.created_at.strftime('%d %b %Y, %I:%M %p')}
👤 Customer: {customer_name}

💵 Subtotal: ₹{float(invoice.base_amount):.2f}
📊 GST ({gst_rate_percent:.0f}%): ₹{float(invoice.gst_amount):.2f}
💰 **Total Amount: ₹{float(invoice.amount):.2f}**

Status: {invoice.status.upper()}

---
Thank you for your business! 
Please pay within 30 days.

For queries, contact: {business_name}
""".strip()
    
    return message
