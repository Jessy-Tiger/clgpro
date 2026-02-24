"""
Invoice generation utility for VRL Logistics
Generates professional PDF invoices for accepted pickup requests
"""

from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.conf import settings
from .models import Invoice


def generate_invoice_pdf(pickup_request):
    """
    Generate a professional PDF invoice for an accepted pickup request
    
    Args:
        pickup_request: PickupRequest object
        
    Returns:
        BytesIO: PDF file buffer
    """
    
    # Create or update invoice record
    invoice, created = Invoice.objects.get_or_create(
        pickup_request=pickup_request,
        defaults={
            'base_charge': 100.00,
            'weight_charge': calculate_weight_charge(pickup_request.parcel_weight),
        }
    )
    invoice.calculate_totals()
    invoice.save()
    
    # Create PDF buffer
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
    )
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#3a3a3a'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#2a2a2a'),
        spaceAfter=6,
    )
    
    # Header - Company Info
    elements.append(Paragraph("VRL LOGISTICS", title_style))
    elements.append(Paragraph("Doorstep Parcel Pickup Service", heading_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Invoice Header
    invoice_data = [
        ['INVOICE', f'Invoice #: {invoice.invoice_number}'],
        ['', f'Date: {invoice.generated_at.strftime("%d-%m-%Y")}'],
        ['', f'Request #: {pickup_request.id}'],
    ]
    
    invoice_table = Table(invoice_data, colWidths=[3*inch, 3.5*inch])
    invoice_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 16),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a1a1a')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, -1), 10),
    ]))
    elements.append(invoice_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Customer Information
    elements.append(Paragraph("CUSTOMER INFORMATION", heading_style))
    
    customer_data = [
        ['Name:', pickup_request.full_name],
        ['Email:', pickup_request.email],
        ['Phone:', pickup_request.phone_number],
        ['Address:', f"{pickup_request.address}, {pickup_request.city}, {pickup_request.state} {pickup_request.pincode}"],
    ]
    
    customer_table = Table(customer_data, colWidths=[1.5*inch, 5*inch])
    customer_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2a2a2a')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d3d3d3')),
    ]))
    elements.append(customer_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Pickup Details
    elements.append(Paragraph("PICKUP DETAILS", heading_style))
    
    pickup_data = [
        ['Pickup Date:', pickup_request.preferred_pickup_date.strftime("%d-%m-%Y")],
        ['Pickup Time:', pickup_request.preferred_pickup_time.strftime("%H:%M")],
        ['Parcel Weight:', pickup_request.parcel_weight],
        ['Parcel Description:', pickup_request.parcel_description[:100] + ('...' if len(pickup_request.parcel_description) > 100 else '')],
    ]
    
    if pickup_request.estimated_price:
        pickup_data.append(['Estimated Value:', f"₹ {pickup_request.estimated_price}"])
    
    pickup_table = Table(pickup_data, colWidths=[1.5*inch, 5*inch])
    pickup_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2a2a2a')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d3d3d3')),
    ]))
    elements.append(pickup_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Charges Table
    elements.append(Paragraph("CHARGES & AMOUNT", heading_style))
    
    charges_data = [
        ['Description', 'Amount'],
        ['Base Pickup Charge', f"₹ {invoice.base_charge:.2f}"],
        ['Weight-based Charge', f"₹ {invoice.weight_charge:.2f}"],
        ['Subtotal', f"₹ {invoice.base_charge + invoice.weight_charge:.2f}"],
        ['CGST (9%)', f"₹ {invoice.tax_amount / 2:.2f}"],
        ['SGST (9%)', f"₹ {invoice.tax_amount / 2:.2f}"],
        ['TOTAL AMOUNT', f"₹ {invoice.total_amount:.2f}"],
    ]
    
    charges_table = Table(charges_data, colWidths=[3.5*inch, 3*inch])
    charges_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#3a3a3a')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d3d3d3')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -2), colors.HexColor('#2a2a2a')),
    ]))
    elements.append(charges_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Terms & Conditions
    elements.append(Paragraph("TERMS & CONDITIONS", heading_style))
    
    terms_text = """
    <b>1. Pickup Confirmation:</b> This invoice confirms that your parcel pickup request has been accepted and approved.<br/>
    <b>2. Pickup Schedule:</b> Our representative will arrive at the specified date and time. Please ensure someone is available to hand over the parcel.<br/>
    <b>3. Payment:</b> Payment can be made at the time of pickup (COD) or online via our website.<br/>
    <b>4. Parcel Safety:</b> Please ensure the parcel is properly packed and protected.<br/>
    <b>5. Liability:</b> Maximum liability is limited to the declared parcel value or ₹500, whichever is lower.<br/>
    <b>6. Contact:</b> For any inquiries, contact us at support@vrllogistics.com or call +91-XXXXXXXXXX
    """
    
    elements.append(Paragraph(terms_text, body_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Footer
    footer_text = f"<i>Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</i>"
    elements.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=body_style,
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4a4a4a')
    )))
    
    # Build PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer


def calculate_weight_charge(weight_str):
    """
    Calculate charge based on weight
    Logic: ₹20 per 500g or part thereof
    
    Args:
        weight_str: Weight string (e.g., '2.5 kg', '500g', etc.)
        
    Returns:
        float: Charge amount in rupees
    """
    try:
        weight_str = weight_str.lower().strip()
        
        # Extract numeric value
        import re
        match = re.search(r'(\d+\.?\d*)', weight_str)
        if not match:
            return 50.00  # Default charge
        
        weight_value = float(match.group(1))
        
        # Convert to grams
        if 'kg' in weight_str:
            weight_value *= 1000
        
        # Calculate charge: ₹20 per 500g or part thereof
        units = (weight_value + 499) / 500  # Ceiling division
        charge = units * 20
        
        return min(charge, 200.00)  # Cap at ₹200
    
    except Exception as e:
        print(f"Error calculating weight charge: {str(e)}")
        return 50.00  # Default fallback


