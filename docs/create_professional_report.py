#!/usr/bin/env python3
"""
Professional HTML Report Generator for 1967 Baker Road Investment Analysis
Creates a publication-quality, responsive HTML document with enhanced readability
"""

import re
import html

class ProfessionalMarkdownConverter:
    """Converts markdown to properly formatted HTML without external dependencies"""

    def __init__(self):
        self.toc_items = []
        self.section_counter = 0

    def escape_html(self, text):
        """Escape HTML special characters"""
        return html.escape(text)

    def convert_table(self, table_text):
        """Convert markdown table to properly formatted HTML table"""
        lines = [line.strip() for line in table_text.strip().split('\n') if line.strip()]

        if len(lines) < 2:
            return '<p>' + self.escape_html(table_text) + '</p>'

        # Parse header
        headers = [cell.strip() for cell in lines[0].split('|') if cell.strip()]

        # Skip separator line (line 1)

        # Parse rows
        rows = []
        for line in lines[2:]:  # Start from line 2 (after separator)
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:
                rows.append(cells)

        # Build HTML table
        html_parts = ['<div class="table-container"><table>']

        # Add header
        html_parts.append('<thead><tr>')
        for header in headers:
            html_parts.append(f'<th>{self.convert_inline(header)}</th>')
        html_parts.append('</tr></thead>')

        # Add body
        html_parts.append('<tbody>')
        for row in rows:
            html_parts.append('<tr>')
            for i, cell in enumerate(row):
                # Check if this is a currency value
                css_class = ''
                if '$' in cell or '%' in cell:
                    css_class = ' class="currency"'
                    if cell.strip().startswith('-') or 'LOSS' in cell.upper():
                        css_class = ' class="currency negative"'
                    elif any(indicator in cell for indicator in ['profit', 'gain', '+']):
                        css_class = ' class="currency positive"'

                html_parts.append(f'<td{css_class}>{self.convert_inline(cell)}</td>')
            html_parts.append('</tr>')
        html_parts.append('</tbody>')

        html_parts.append('</table></div>')

        return ''.join(html_parts)

    def convert_inline(self, text):
        """Convert inline markdown formatting (bold, italic, etc.) - SIMPLIFIED"""
        # Escape HTML first to prevent injection
        text = html.escape(text)

        # Convert bold (**text**) - simple string replacement
        while '**' in text:
            first = text.find('**')
            if first == -1:
                break
            second = text.find('**', first + 2)
            if second == -1:
                break
            before = text[:first]
            bold_text = text[first+2:second]
            after = text[second+2:]
            text = before + '<strong>' + bold_text + '</strong>' + after

        return text

    def is_table_line(self, line):
        """Check if line is part of a markdown table"""
        return '|' in line and line.strip().startswith('|')

    def convert_list(self, list_lines):
        """Convert markdown list to HTML"""
        html_parts = ['<ul>']
        for line in list_lines:
            # Remove leading dash/asterisk and whitespace
            item_text = re.sub(r'^[\s]*[-*]\s+', '', line)
            html_parts.append(f'<li>{self.convert_inline(item_text)}</li>')
        html_parts.append('</ul>')
        return ''.join(html_parts)

    def extract_toc_from_content(self, content):
        """Extract table of contents structure from markdown"""
        toc = []
        lines = content.split('\n')

        for line in lines:
            # Match headers (## or ###)
            h2_match = re.match(r'^## (.+)$', line)
            h3_match = re.match(r'^### (.+)$', line)

            if h2_match and 'TABLE OF CONTENTS' not in line.upper():
                title = h2_match.group(1).strip()
                # Clean up any markdown formatting
                title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)
                toc.append(('h2', title))
            elif h3_match:
                title = h3_match.group(1).strip()
                title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)
                toc.append(('h3', title))

        return toc

    def convert(self, markdown_text):
        """Main conversion function"""
        lines = markdown_text.split('\n')
        html_parts = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Handle headers
            if line.startswith('# ') and not line.startswith('## '):
                # H1
                title = line[2:].strip()
                self.section_counter += 1
                section_id = f"section-{self.section_counter}"
                html_parts.append(f'<h1 id="{section_id}">{self.convert_inline(title)}</h1>')
                i += 1
                continue

            if line.startswith('## '):
                # H2
                title = line[3:].strip()
                self.section_counter += 1
                section_id = f"section-{self.section_counter}"

                # Check if this is a PART header
                if title.startswith('PART ') or 'PART ' in title.upper():
                    html_parts.append(f'<div class="part-header" id="{section_id}">')
                    html_parts.append(f'<h2>{self.convert_inline(title)}</h2>')
                    html_parts.append('</div>')
                else:
                    html_parts.append(f'<h2 id="{section_id}">{self.convert_inline(title)}</h2>')

                i += 1
                continue

            if line.startswith('### '):
                # H3
                title = line[4:].strip()
                html_parts.append(f'<h3>{self.convert_inline(title)}</h3>')
                i += 1
                continue

            if line.startswith('#### '):
                # H4
                title = line[5:].strip()
                html_parts.append(f'<h4>{self.convert_inline(title)}</h4>')
                i += 1
                continue

            # Handle horizontal rules
            if line.strip() in ['---', '***', '___']:
                html_parts.append('<hr>')
                i += 1
                continue

            # Handle tables
            if self.is_table_line(line):
                # Collect all table lines
                table_lines = []
                while i < len(lines) and self.is_table_line(lines[i]):
                    table_lines.append(lines[i])
                    i += 1

                table_html = self.convert_table('\n'.join(table_lines))
                html_parts.append(table_html)
                continue

            # Handle lists
            if line.strip().startswith(('-', '*', '"')) and line.strip()[1:2] == ' ':
                # Collect all list items
                list_lines = []
                while i < len(lines) and lines[i].strip().startswith(('-', '*', '"')):
                    list_lines.append(lines[i])
                    i += 1

                list_html = self.convert_list(list_lines)
                html_parts.append(list_html)
                continue

            # Handle regular paragraphs
            paragraph_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '-', '*', '|', '"')):
                paragraph_lines.append(lines[i].strip())
                i += 1

            if paragraph_lines:
                paragraph_text = ' '.join(paragraph_lines)

                # Check for special callout patterns
                if paragraph_text.startswith('**CRITICAL') or paragraph_text.startswith('**WARNING'):
                    html_parts.append(f'<div class="alert alert-critical"><p>{self.convert_inline(paragraph_text)}</p></div>')
                elif paragraph_text.startswith('**IMPORTANT') or paragraph_text.startswith('**NOTE'):
                    html_parts.append(f'<div class="alert alert-warning"><p>{self.convert_inline(paragraph_text)}</p></div>')
                elif paragraph_text.startswith('**OPPORTUNITIES') or paragraph_text.startswith('**POSITIVE'):
                    html_parts.append(f'<div class="alert alert-success"><p>{self.convert_inline(paragraph_text)}</p></div>')
                else:
                    html_parts.append(f'<p>{self.convert_inline(paragraph_text)}</p>')

        return '\n'.join(html_parts)


def create_professional_html():
    """Generate the professional HTML report"""

    # Read the markdown file
    with open('1967-Baker-Road-Comprehensive-Analysis.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # Initialize converter
    converter = ProfessionalMarkdownConverter()

    # Extract TOC structure
    toc_structure = converter.extract_toc_from_content(content)

    # Convert markdown to HTML
    body_html = converter.convert(content)

    # Build TOC HTML
    toc_html_parts = ['<nav class="toc-section" aria-label="Table of contents">']
    toc_html_parts.append('<h2>Table of Contents</h2>')
    toc_html_parts.append('<ul class="toc">')

    section_num = 0
    for level, title in toc_structure:
        section_num += 1
        css_class = 'toc-h2' if level == 'h2' else 'toc-h3'
        toc_html_parts.append(f'<li class="{css_class}"><a href="#section-{section_num}">{title}</a></li>')

    toc_html_parts.append('</ul>')
    toc_html_parts.append('</nav>')

    toc_html = '\n'.join(toc_html_parts)

    # Create the complete HTML with professional styling
    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Comprehensive investment analysis for 1967 Baker Road NW property development">
    <title>1967 Baker Road NW - Professional Investment Analysis</title>
    <style>
        /* ========================================
           CSS CUSTOM PROPERTIES (DESIGN TOKENS)
           ======================================== */
        :root {{
            /* Font sizes - modular scale (1.25 ratio) */
            --fs-base: 16px;
            --fs-sm: 14px;
            --fs-md: 16px;
            --fs-lg: 18px;
            --fs-xl: 22px;
            --fs-2xl: 28px;
            --fs-3xl: 35px;
            --fs-4xl: 44px;

            /* Line heights */
            --lh-tight: 1.25;
            --lh-snug: 1.375;
            --lh-normal: 1.5;
            --lh-relaxed: 1.625;
            --lh-loose: 2;

            /* Font weights */
            --fw-normal: 400;
            --fw-medium: 500;
            --fw-semibold: 600;
            --fw-bold: 700;

            /* Spacing scale */
            --space-xs: 8px;
            --space-sm: 12px;
            --space-md: 16px;
            --space-lg: 24px;
            --space-xl: 32px;
            --space-2xl: 48px;
            --space-3xl: 64px;

            /* Colors */
            --color-primary: #667eea;
            --color-primary-dark: #5568d3;
            --color-secondary: #764ba2;
            --color-text: #2d3748;
            --color-text-light: #4a5568;
            --color-text-lighter: #718096;
            --color-bg: #ffffff;
            --color-bg-light: #f7fafc;
            --color-bg-lighter: #f8f9fa;
            --color-border: #e2e8f0;
            --color-success: #28a745;
            --color-warning: #ffc107;
            --color-danger: #dc3545;
            --color-info: #17a2b8;

            /* Shadows */
            --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
            --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
            --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.15);
        }}

        /* ========================================
           RESET & BASE STYLES
           ======================================== */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            font-size: var(--fs-lg);
            line-height: var(--lh-relaxed);
            color: var(--color-text);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: var(--space-lg);
        }}

        /* ========================================
           LAYOUT
           ======================================== */
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: var(--color-bg);
            border-radius: 16px;
            box-shadow: var(--shadow-xl);
            overflow: hidden;
        }}

        .header-section {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: var(--space-3xl) var(--space-xl);
            text-align: center;
        }}

        .header-section h1 {{
            font-size: var(--fs-4xl);
            font-weight: var(--fw-bold);
            margin-bottom: var(--space-md);
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }}

        .header-subtitle {{
            font-size: var(--fs-xl);
            opacity: 0.95;
            font-weight: var(--fw-medium);
        }}

        .content-wrapper {{
            max-width: 900px;
            margin: 0 auto;
            padding: var(--space-2xl) var(--space-xl);
        }}

        /* ========================================
           TYPOGRAPHY
           ======================================== */
        h1 {{
            font-size: var(--fs-4xl);
            font-weight: var(--fw-bold);
            line-height: var(--lh-tight);
            margin: var(--space-3xl) 0 var(--space-xl) 0;
            color: var(--color-primary);
        }}

        h2 {{
            font-size: var(--fs-3xl);
            font-weight: var(--fw-bold);
            line-height: var(--lh-snug);
            margin: var(--space-3xl) 0 var(--space-xl) 0;
            color: var(--color-primary);
            border-bottom: 3px solid var(--color-primary);
            padding-bottom: var(--space-md);
        }}

        h3 {{
            font-size: var(--fs-2xl);
            font-weight: var(--fw-semibold);
            line-height: var(--lh-snug);
            margin: var(--space-2xl) 0 var(--space-lg) 0;
            color: var(--color-text);
            padding-left: var(--space-md);
            border-left: 4px solid var(--color-primary);
        }}

        h4 {{
            font-size: var(--fs-xl);
            font-weight: var(--fw-semibold);
            margin: var(--space-xl) 0 var(--space-md) 0;
            color: var(--color-text-light);
        }}

        p {{
            margin: var(--space-lg) 0;
            line-height: var(--lh-relaxed);
            color: var(--color-text);
        }}

        strong, b {{
            font-weight: var(--fw-bold);
            color: #1a202c;
        }}

        em, i {{
            font-style: italic;
            color: var(--color-text-light);
        }}

        code {{
            background: var(--color-bg-lighter);
            padding: 3px 8px;
            border-radius: 4px;
            font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }}

        hr {{
            border: none;
            border-top: 2px solid var(--color-border);
            margin: var(--space-2xl) 0;
        }}

        /* ========================================
           TABLE OF CONTENTS
           ======================================== */
        .toc-section {{
            background: var(--color-bg-light);
            padding: var(--space-2xl) var(--space-xl);
            border-bottom: 3px solid var(--color-border);
        }}

        .toc-section h2 {{
            color: var(--color-text);
            margin-bottom: var(--space-xl);
            font-size: var(--fs-2xl);
            border-bottom: none;
        }}

        .toc {{
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: var(--space-md);
        }}

        .toc li {{
            background: white;
            padding: var(--space-md) var(--space-lg);
            border-radius: 8px;
            border-left: 4px solid var(--color-primary);
            transition: all 0.3s ease;
        }}

        .toc li.toc-h3 {{
            padding-left: var(--space-2xl);
            border-left-color: var(--color-text-lighter);
            font-size: var(--fs-sm);
        }}

        .toc li:hover {{
            transform: translateX(5px);
            box-shadow: var(--shadow-md);
            border-left-color: var(--color-secondary);
        }}

        .toc a {{
            color: var(--color-text);
            text-decoration: none;
            font-weight: var(--fw-medium);
            display: block;
        }}

        .toc a:hover {{
            color: var(--color-primary);
        }}

        /* ========================================
           TABLES
           ======================================== */
        .table-container {{
            overflow-x: auto;
            margin: var(--space-xl) 0;
            border-radius: 8px;
            box-shadow: var(--shadow-md);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            font-size: var(--fs-md);
        }}

        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        th {{
            padding: var(--space-md) var(--space-lg);
            text-align: left;
            font-weight: var(--fw-semibold);
            font-size: var(--fs-sm);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: var(--space-md) var(--space-lg);
            border-bottom: 1px solid var(--color-border);
            color: var(--color-text);
        }}

        tbody tr:hover {{
            background: var(--color-bg-light);
        }}

        tbody tr:last-child td {{
            border-bottom: none;
        }}

        /* Financial data styling */
        td.currency {{
            font-family: 'SF Mono', 'Monaco', monospace;
            text-align: right;
            font-weight: var(--fw-medium);
        }}

        td.negative {{
            color: var(--color-danger);
            font-weight: var(--fw-bold);
        }}

        td.positive {{
            color: var(--color-success);
            font-weight: var(--fw-bold);
        }}

        /* ========================================
           LISTS
           ======================================== */
        ul {{
            margin: var(--space-lg) 0;
            padding-left: var(--space-2xl);
        }}

        ul li {{
            margin: var(--space-sm) 0;
            line-height: var(--lh-relaxed);
            color: var(--color-text);
        }}

        ul li::marker {{
            color: var(--color-primary);
            font-weight: var(--fw-bold);
        }}

        /* ========================================
           ALERT BOXES
           ======================================== */
        .alert {{
            padding: var(--space-lg);
            margin: var(--space-xl) 0;
            border-radius: 8px;
            border-left: 5px solid;
        }}

        .alert-critical {{
            background-color: #f8d7da;
            border-color: var(--color-danger);
            color: #721c24;
        }}

        .alert-warning {{
            background-color: #fff3cd;
            border-color: var(--color-warning);
            color: #856404;
        }}

        .alert-info {{
            background-color: #d1ecf1;
            border-color: var(--color-info);
            color: #0c5460;
        }}

        .alert-success {{
            background-color: #d4edda;
            border-color: var(--color-success);
            color: #155724;
        }}

        .alert p {{
            margin: 0;
        }}

        /* ========================================
           PART HEADERS
           ======================================== */
        .part-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: var(--space-2xl);
            margin: var(--space-3xl) calc(-1 * var(--space-xl)) var(--space-xl);
            text-align: center;
        }}

        .part-header h2 {{
            color: white;
            border: none;
            margin: 0;
            padding: 0;
            font-size: var(--fs-3xl);
        }}

        /* ========================================
           NAVIGATION
           ======================================== */
        .back-to-top {{
            position: fixed;
            bottom: var(--space-xl);
            right: var(--space-xl);
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            display: none;
            align-items: center;
            justify-content: center;
            font-size: var(--fs-xl);
            box-shadow: var(--shadow-lg);
            transition: all 0.3s ease;
            z-index: 999;
        }}

        .back-to-top:hover {{
            transform: translateY(-5px);
            box-shadow: var(--shadow-xl);
        }}

        .back-to-top.visible {{
            display: flex;
        }}

        .progress-bar {{
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
            z-index: 9999;
        }}

        /* ========================================
           PRINT STYLES
           ======================================== */
        @media print {{
            @page {{
                margin: 1in;
                size: letter;
            }}

            body {{
                background: white;
                padding: 0;
                color: #000;
                font-size: 11pt;
                line-height: 1.5;
            }}

            .container {{
                box-shadow: none;
                border-radius: 0;
                max-width: 100%;
            }}

            .part-header,
            .header-section {{
                background: #667eea !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            h2 {{
                page-break-after: avoid;
                page-break-before: always;
            }}

            h3, h4 {{
                page-break-after: avoid;
            }}

            table {{
                page-break-inside: avoid;
            }}

            .back-to-top,
            .progress-bar {{
                display: none !important;
            }}
        }}

        /* ========================================
           MOBILE RESPONSIVE
           ======================================== */
        @media (max-width: 768px) {{
            :root {{
                --fs-base: 14px;
                --fs-lg: 16px;
                --fs-xl: 18px;
                --fs-2xl: 22px;
                --fs-3xl: 26px;
                --fs-4xl: 32px;
            }}

            body {{
                padding: var(--space-sm);
            }}

            .container {{
                border-radius: 8px;
            }}

            .header-section {{
                padding: var(--space-2xl) var(--space-lg);
            }}

            .content-wrapper {{
                padding: var(--space-lg);
            }}

            .toc {{
                grid-template-columns: 1fr;
            }}

            .part-header {{
                margin-left: calc(-1 * var(--space-lg));
                margin-right: calc(-1 * var(--space-lg));
            }}

            .table-container {{
                margin-left: calc(-1 * var(--space-lg));
                margin-right: calc(-1 * var(--space-lg));
                border-radius: 0;
            }}

            table {{
                min-width: 600px;
            }}

            .back-to-top {{
                bottom: var(--space-lg);
                right: var(--space-lg);
                width: 44px;
                height: 44px;
            }}
        }}
    </style>
</head>
<body>
    <!-- Progress bar -->
    <div class="progress-bar" id="progressBar"></div>

    <!-- Back to top button -->
    <button class="back-to-top" id="backToTop" aria-label="Back to top">�</button>

    <div class="container">
        <!-- Header -->
        <div class="header-section">
            <h1>1967 Baker Road NW</h1>
            <div class="header-subtitle">Comprehensive Investment Analysis</div>
        </div>

        <!-- Table of Contents -->
        {toc_html}

        <!-- Main Content -->
        <main class="content-wrapper" id="main-content">
            {body_html}
        </main>
    </div>

    <!-- JavaScript for interactive features -->
    <script>
        // Back to top button
        const backToTop = document.getElementById('backToTop');
        const progressBar = document.getElementById('progressBar');

        window.addEventListener('scroll', function() {{
            // Show/hide back to top button
            if (window.pageYOffset > 300) {{
                backToTop.classList.add('visible');
            }} else {{
                backToTop.classList.remove('visible');
            }}

            // Update progress bar
            const windowHeight = window.innerHeight;
            const documentHeight = document.documentElement.scrollHeight;
            const scrollTop = window.pageYOffset;
            const scrollPercent = (scrollTop / (documentHeight - windowHeight)) * 100;
            progressBar.style.width = scrollPercent + '%';
        }});

        backToTop.addEventListener('click', function() {{
            window.scrollTo({{
                top: 0,
                behavior: 'smooth'
            }});
        }});

        // Smooth scroll for TOC links
        document.querySelectorAll('.toc a').forEach(anchor => {{
            anchor.addEventListener('click', function(e) {{
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {{
                    target.scrollIntoView({{
                        behavior: 'smooth',
                        block: 'start'
                    }});
                }}
            }});
        }});
    </script>
</body>
</html>
'''

    # Write the file
    output_path = '1967-Baker-Road-Professional-Analysis.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_html)

    print(f" Professional HTML created: {output_path}")
    print(f" Document size: {len(full_html):,} characters")
    print(f" Sections processed: {converter.section_counter}")
    print(f" Features: Responsive design, interactive navigation, print-optimized")

if __name__ == '__main__':
    create_professional_html()
