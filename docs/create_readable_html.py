#!/usr/bin/env python3
"""
Create a highly readable HTML version of the comprehensive analysis
"""

def create_readable_html():
    # Read the markdown file
    with open('1967-Baker-Road-Comprehensive-Analysis.md', 'r') as f:
        content = f.read()

    # Split into sections
    sections = content.split('\n## ')

    # Create HTML with much better styling
    html_parts = []

    # Add header section
    header = sections[0].replace('# ', '')
    html_parts.append(f'''
    <div class="header-section">
        <h1>{header.split(chr(10))[0]}</h1>
        <div class="subtitle">{header.split(chr(10))[1] if len(header.split(chr(10))) > 1 else ""}</div>
    </div>
    ''')

    # Add table of contents
    toc_items = []
    for i, section in enumerate(sections[1:], 1):
        title = section.split('\n')[0]
        toc_items.append(f'<li><a href="#section-{i}">{title}</a></li>')

    html_parts.append(f'''
    <div class="toc-section">
        <h2>📋 Table of Contents</h2>
        <ul class="toc">
            {"".join(toc_items)}
        </ul>
    </div>
    ''')

    # Add each section
    for i, section in enumerate(sections[1:], 1):
        lines = section.split('\n')
        title = lines[0]
        content = '\n'.join(lines[1:])

        # Convert markdown to basic HTML - FIX BOLD TAGS
        # Replace **text** with <strong>text</strong>
        while '**' in content:
            first_pos = content.find('**')
            if first_pos == -1:
                break
            second_pos = content.find('**', first_pos + 2)
            if second_pos == -1:
                break
            before = content[:first_pos]
            bold_text = content[first_pos+2:second_pos]
            after = content[second_pos+2:]
            content = before + '<strong>' + bold_text + '</strong>' + after

        # Convert ### headers (h3)
        lines_temp = content.split('\n')
        for idx, line in enumerate(lines_temp):
            if line.strip().startswith('###'):
                lines_temp[idx] = '<h3>' + line.replace('###', '').strip() + '</h3>'
        content = '\n'.join(lines_temp)

        # Convert lists
        paragraphs = content.split('\n\n')
        formatted_paragraphs = []
        for para in paragraphs:
            if para.strip().startswith('- '):
                items = [line.strip('- ').strip() for line in para.split('\n') if line.strip().startswith('- ')]
                formatted_paragraphs.append('<ul>' + ''.join([f'<li>{item}</li>' for item in items]) + '</ul>')
            elif para.strip().startswith('| '):
                # Convert markdown table to HTML table
                table_lines = para.strip().split('\n')
                if len(table_lines) >= 2:
                    # Parse header
                    header_cells = [cell.strip() for cell in table_lines[0].split('|') if cell.strip()]
                    # Parse rows (skip separator line)
                    data_rows = []
                    for line in table_lines[2:]:
                        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                        if cells:
                            data_rows.append(cells)

                    # Build HTML table
                    table_html = '<div class="table-container"><table>'
                    table_html += '<thead><tr>'
                    for header in header_cells:
                        table_html += f'<th>{header}</th>'
                    table_html += '</tr></thead><tbody>'
                    for row in data_rows:
                        table_html += '<tr>'
                        for cell in row:
                            # Style financial cells
                            css_class = ''
                            if '$' in cell or '%' in cell:
                                css_class = ' class="currency"'
                                if 'LOSS' in cell or (cell.startswith('-') and '$' in cell):
                                    css_class = ' class="negative"'
                            table_html += f'<td{css_class}>{cell}</td>'
                        table_html += '</tr>'
                    table_html += '</tbody></table></div>'
                    formatted_paragraphs.append(table_html)
                else:
                    formatted_paragraphs.append('<div class="table-container">' + para + '</div>')
            else:
                formatted_paragraphs.append(f'<p>{para}</p>')

        html_parts.append(f'''
        <div class="content-section" id="section-{i}">
            <h2>{title}</h2>
            {"".join(formatted_paragraphs)}
        </div>
        ''')

    # Create full HTML with excellent styling
    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>1967 Baker Road - Investment Analysis</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.8;
            color: #2c3e50;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header-section {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 40px;
            text-align: center;
        }}

        .header-section h1 {{
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}

        .subtitle {{
            font-size: 1.2em;
            opacity: 0.95;
        }}

        .toc-section {{
            background: #f8f9fa;
            padding: 40px;
            border-bottom: 3px solid #e9ecef;
        }}

        .toc-section h2 {{
            color: #495057;
            margin-bottom: 25px;
            font-size: 1.8em;
        }}

        .toc {{
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 12px;
        }}

        .toc li {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            transition: all 0.3s ease;
        }}

        .toc li:hover {{
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }}

        .toc a {{
            color: #495057;
            text-decoration: none;
            font-weight: 500;
        }}

        .toc a:hover {{
            color: #667eea;
        }}

        .content-section {{
            padding: 50px 40px;
            border-bottom: 1px solid #e9ecef;
        }}

        .content-section:last-child {{
            border-bottom: none;
        }}

        h2 {{
            color: #667eea;
            font-size: 2em;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }}

        h3 {{
            color: #495057;
            font-size: 1.5em;
            margin: 30px 0 20px 0;
            padding-left: 15px;
            border-left: 4px solid #667eea;
        }}

        p {{
            margin: 20px 0;
            font-size: 1.05em;
            line-height: 1.8;
            color: #495057;
        }}

        strong {{
            color: #2c3e50;
            font-weight: 600;
        }}

        ul {{
            margin: 20px 0;
            padding-left: 30px;
        }}

        ul li {{
            margin: 12px 0;
            line-height: 1.7;
            color: #495057;
        }}

        ul li::marker {{
            color: #667eea;
            font-weight: bold;
        }}

        .table-container {{
            overflow-x: auto;
            margin: 30px 0;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            font-size: 0.95em;
        }}

        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
            color: #495057;
        }}

        tbody tr:hover {{
            background: #f8f9fa;
        }}

        tbody tr:last-child td {{
            border-bottom: none;
        }}

        td.currency {{
            font-family: 'SF Mono', 'Monaco', monospace;
            text-align: right;
            font-weight: 500;
        }}

        td.negative {{
            color: #dc3545;
            font-weight: 700;
        }}

        td.positive {{
            color: #28a745;
            font-weight: 700;
        }}

        code {{
            background: #f8f9fa;
            padding: 3px 8px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }}

        .highlight {{
            background: #fff3cd;
            padding: 20px;
            border-left: 4px solid #ffc107;
            margin: 25px 0;
            border-radius: 4px;
        }}

        .success {{
            background: #d4edda;
            padding: 20px;
            border-left: 4px solid #28a745;
            margin: 25px 0;
            border-radius: 4px;
        }}

        .danger {{
            background: #f8d7da;
            padding: 20px;
            border-left: 4px solid #dc3545;
            margin: 25px 0;
            border-radius: 4px;
        }}

        @media (max-width: 768px) {{
            .header-section {{
                padding: 40px 20px;
            }}

            .header-section h1 {{
                font-size: 1.8em;
            }}

            .content-section {{
                padding: 30px 20px;
            }}

            .toc {{
                grid-template-columns: 1fr;
            }}
        }}

        @media print {{
            body {{
                background: white;
                padding: 0;
            }}

            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {"".join(html_parts)}
    </div>
</body>
</html>
'''

    # Write the file
    with open('1967-Baker-Road-Analysis-Readable.html', 'w') as f:
        f.write(full_html)

    print("Readable HTML created: 1967-Baker-Road-Analysis-Readable.html")

if __name__ == '__main__':
    create_readable_html()
