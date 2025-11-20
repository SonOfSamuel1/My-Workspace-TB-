#!/usr/bin/env python3
"""
Convert Markdown documents to PDF using markdown2 and reportlab
"""

import markdown
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import re
import sys

def markdown_to_pdf(md_file, pdf_file):
    """Convert a Markdown file to PDF"""

    # Read markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Create PDF
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Container for the 'Flowable' objects
    story = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
        borderWidth=0,
        borderPadding=0,
        borderColor=colors.HexColor('#3498db'),
        borderRadius=None,
        leading=22
    )

    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
        spaceBefore=15,
        leading=18
    )

    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#7f8c8d'),
        spaceAfter=8,
        spaceBefore=12,
        leading=16
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )

    # Parse markdown line by line
    lines = md_content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Title (first H1)
        if line.startswith('# ') and i < 5:
            text = line[2:].strip()
            story.append(Paragraph(text, title_style))
            story.append(Spacer(1, 0.3*inch))
            i += 1
            continue

        # H1
        if line.startswith('# '):
            text = line[2:].strip()
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph(text, h1_style))
            i += 1
            continue

        # H2
        if line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(text, h2_style))
            i += 1
            continue

        # H3
        if line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, h3_style))
            i += 1
            continue

        # H4
        if line.startswith('#### '):
            text = line[5:].strip()
            story.append(Paragraph(f"<b>{text}</b>", body_style))
            i += 1
            continue

        # Horizontal rule
        if line.startswith('---'):
            story.append(Spacer(1, 0.1*inch))
            i += 1
            continue

        # Lists (bullet points)
        if line.startswith('- ') or line.startswith('* '):
            text = line[2:].strip()
            # Handle bold and italic
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
            story.append(Paragraph(f"• {text}", body_style))
            i += 1
            continue

        # Numbered lists
        if re.match(r'^\d+\. ', line):
            text = re.sub(r'^\d+\. ', '', line).strip()
            # Handle bold and italic
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
            story.append(Paragraph(text, body_style))
            i += 1
            continue

        # Regular paragraph
        text = line
        # Handle bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        # Handle italic
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        # Handle inline code
        text = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', text)

        story.append(Paragraph(text, body_style))
        i += 1

    # Build PDF
    doc.build(story)
    print(f"PDF created successfully: {pdf_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 convert_to_pdf.py <input.md> <output.pdf>")
        sys.exit(1)

    md_file = sys.argv[1]
    pdf_file = sys.argv[2]

    try:
        markdown_to_pdf(md_file, pdf_file)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
