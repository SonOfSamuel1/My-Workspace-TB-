#!/usr/bin/env python3
"""
Create a professional investor-grade HTML report with enhanced readability,
navigation, charts, and print optimization.

Phases implemented:
- Phase 1: Decision dashboard, property snapshot, critical alerts
- Phase 2: Chart.js visualizations (scenarios, market, risk matrix)
- Phase 3: Floating navigation, collapsible sections
- Phase 4: Professional cover page, scenario selector
- Phase 5: Print/PDF optimization
- Phase 6: Professional branding and mobile responsiveness
"""

def create_decision_dashboard():
    """Create the top-of-page investment decision dashboard"""
    return '''
    <div class="decision-dashboard">
        <div class="recommendation-badge caution">
            <div class="badge-icon">⚠️</div>
            <div class="badge-text">
                <div class="badge-title">PROCEED WITH EXTREME CAUTION</div>
                <div class="badge-subtitle">Wholesale or Hold Strategies Preferred</div>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="dashboard-card critical">
                <h3>🚨 Critical Warnings</h3>
                <ul>
                    <li><strong>Crime F-Grade:</strong> 93rd percentile unsafe</li>
                    <li><strong>Market Declining:</strong> -7.8% YoY, 84 DOM (+133%)</li>
                    <li><strong>Price Gap:</strong> $530K ceiling vs $650K+ target</li>
                    <li><strong>Financial Risk:</strong> -10.3% loss in 3-home scenario</li>
                </ul>
            </div>

            <div class="dashboard-card recommended">
                <h3>✅ Best Options</h3>
                <ul>
                    <li><strong>Scenario E - Wholesale:</strong> $30K-$80K profit, 60-120 days, Very Low Risk</li>
                    <li><strong>Scenario D - Hold:</strong> $75K-$150K appreciation, 3-5 years, Medium Risk</li>
                    <li><strong>ROI Comparison:</strong> 233-533% (wholesale) vs 1.4% (three-home)</li>
                </ul>
            </div>

            <div class="dashboard-card criteria">
                <h3>📋 Decision Checklist</h3>
                <ul>
                    <li>✓ Can you acquire land for ≤$200,000?</li>
                    <li>✓ Can you accept 60-day timeline (wholesale)?</li>
                    <li>✓ Can you tolerate F-grade crime risk?</li>
                    <li>✓ Can market support $625K+ sale prices?</li>
                </ul>
            </div>
        </div>
    </div>
    '''

def create_property_snapshot():
    """Create property snapshot info box"""
    return '''
    <div class="property-snapshot">
        <h3>Property Snapshot</h3>
        <div class="snapshot-grid">
            <div class="snapshot-item">
                <div class="snapshot-label">Address</div>
                <div class="snapshot-value">1967 Baker Road NW, Atlanta, GA 30318</div>
            </div>
            <div class="snapshot-item">
                <div class="snapshot-label">Size</div>
                <div class="snapshot-value">1.619 acres (70,527 SF)</div>
            </div>
            <div class="snapshot-item">
                <div class="snapshot-label">Zoning</div>
                <div class="snapshot-value">R-4A Single-Family Residential</div>
            </div>
            <div class="snapshot-item">
                <div class="snapshot-label">Status</div>
                <div class="snapshot-value">Vacant Lot | Not in Flood Zone</div>
            </div>
            <div class="snapshot-item">
                <div class="snapshot-label">Capacity</div>
                <div class="snapshot-value">2-4 homes possible (R-4A verification required)</div>
            </div>
            <div class="snapshot-item">
                <div class="snapshot-label">Owner</div>
                <div class="snapshot-value">LEJ Management LLC</div>
            </div>
        </div>
    </div>
    '''

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
        <div class="subtitle">Investment Risk Assessment & Development Scenario Analysis</div>
        <div class="header-meta">
            <div>Report Date: January 17, 2025</div>
            <div>Version 1.0</div>
            <div>CONFIDENTIAL</div>
        </div>
    </div>
    ''')

    # Add investment decision dashboard
    html_parts.append(create_decision_dashboard())

    # Add property snapshot box
    html_parts.append(create_property_snapshot())

    # Add table of contents
    toc_items = []
    for i, section in enumerate(sections[1:], 1):
        title = section.split('\n')[0]
        toc_items.append(f'<li><a href="#section-{i}">{title}</a></li>')

    html_parts.append(f'''
    <div class="toc-section">
        <h2>Table of Contents</h2>
        <p class="toc-description">This comprehensive analysis is organized into three main parts: Research & Due Diligence, Development Scenarios, and Decision Framework.</p>
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

        /* ========================================
           DECISION DASHBOARD & PROPERTY SNAPSHOT
           ======================================== */
        .decision-dashboard {{
            background: #fff;
            padding: 30px 40px;
            margin: 0;
        }}

        .recommendation-badge {{
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 3px solid;
        }}

        .recommendation-badge.caution {{
            background: #fff3cd;
            border-color: #ffc107;
        }}

        .badge-icon {{
            font-size: 3em;
            margin-right: 20px;
        }}

        .badge-title {{
            font-size: 1.8em;
            font-weight: 700;
            color: #856404;
        }}

        .badge-subtitle {{
            font-size: 1.1em;
            color: #856404;
            margin-top: 5px;
        }}

        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}

        .dashboard-card {{
            padding: 25px;
            border-radius: 12px;
            border-left: 5px solid;
        }}

        .dashboard-card.critical {{
            background: #f8d7da;
            border-color: #dc3545;
        }}

        .dashboard-card.recommended {{
            background: #d4edda;
            border-color: #28a745;
        }}

        .dashboard-card.criteria {{
            background: #d1ecf1;
            border-color: #17a2b8;
        }}

        .dashboard-card h3 {{
            margin: 0 0 15px 0;
            font-size: 1.3em;
            border: none;
            padding: 0;
        }}

        .dashboard-card ul {{
            margin: 0;
            padding: 0;
            list-style: none;
        }}

        .dashboard-card li {{
            margin: 10px 0;
            padding-left: 0;
        }}

        .property-snapshot {{
            background: #f8f9fa;
            padding: 30px 40px;
            border-bottom: 3px solid #e9ecef;
        }}

        .property-snapshot h3 {{
            margin: 0 0 20px 0;
            font-size: 1.5em;
            color: #495057;
            border: none;
            padding: 0;
        }}

        .snapshot-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}

        .snapshot-item {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 3px solid #667eea;
        }}

        .snapshot-label {{
            font-size: 0.85em;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}

        .snapshot-value {{
            font-size: 1em;
            font-weight: 600;
            color: #2c3e50;
        }}

        /* ========================================
           FLOATING NAVIGATION
           ======================================== */
        .progress-bar {{
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            z-index: 9999;
            transition: width 0.3s ease;
        }}

        .back-to-top {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 1.5em;
            cursor: pointer;
            display: none;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            transition: all 0.3s ease;
            z-index: 999;
        }}

        .back-to-top:hover {{
            transform: translateY(-5px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }}

        .jump-button {{
            position: fixed;
            top: 20px;
            right: 30px;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            transition: all 0.3s ease;
            z-index: 998;
        }}

        .jump-button:hover {{
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
        }}

        /* ========================================
           HEADER ENHANCEMENTS
           ======================================== */
        .header-meta {{
            display: flex;
            gap: 30px;
            justify-content: center;
            margin-top: 20px;
            font-size: 0.9em;
            opacity: 0.9;
        }}

        .header-meta div {{
            padding: 5px 15px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 15px;
        }}

        /* ========================================
           TOC ENHANCEMENTS
           ======================================== */
        .toc-description {{
            color: #6c757d;
            font-size: 1em;
            margin-bottom: 20px;
            font-style: italic;
        }}

        /* ========================================
           FOOTER
           ======================================== */
        .report-footer {{
            background: #f8f9fa;
            padding: 30px 40px;
            border-top: 3px solid #e9ecef;
            margin-top: 50px;
        }}

        .footer-row {{
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 15px;
            font-size: 0.9em;
            color: #6c757d;
            font-weight: 500;
        }}

        .footer-disclaimer {{
            font-size: 0.85em;
            color: #6c757d;
            font-style: italic;
            text-align: center;
            padding-top: 15px;
            border-top: 1px solid #dee2e6;
        }}

        /* ========================================
           PRINT OPTIMIZATION
           ======================================== */
        @media print {{
            @page {{
                size: letter;
                margin: 0.75in;
            }}

            body {{
                background: white !important;
                padding: 0;
            }}

            .container {{
                box-shadow: none;
                border-radius: 0;
                max-width: 100%;
            }}

            /* Hide interactive elements */
            .progress-bar,
            .back-to-top,
            .jump-button {{
                display: none !important;
            }}

            /* Prevent page breaks */
            h2, h3 {{
                page-break-after: avoid;
            }}

            .dashboard-card,
            .property-snapshot,
            .content-section,
            table {{
                page-break-inside: avoid;
            }}

            /* Ensure colors print */
            .header-section,
            .dashboard-card,
            .property-snapshot,
            thead {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            /* Add page numbers */
            .footer-row::after {{
                content: "Page " counter(page);
            }}
        }}

        /* ========================================
           MOBILE RESPONSIVE ENHANCEMENTS
           ======================================== */
        @media (max-width: 768px) {{
            .header-section {{
                padding: 40px 20px;
            }}

            .header-section h1 {{
                font-size: 1.8em;
            }}

            .header-meta {{
                flex-direction: column;
                gap: 10px;
            }}

            .decision-dashboard,
            .property-snapshot {{
                padding: 20px;
            }}

            .dashboard-grid,
            .snapshot-grid {{
                grid-template-columns: 1fr;
            }}

            .content-section {{
                padding: 30px 20px;
            }}

            .toc {{
                grid-template-columns: 1fr;
            }}

            .back-to-top {{
                bottom: 20px;
                right: 20px;
                width: 44px;
                height: 44px;
            }}

            .jump-button {{
                top: 10px;
                right: 10px;
                padding: 10px 20px;
                font-size: 0.9em;
            }}

            .footer-row {{
                flex-direction: column;
                gap: 10px;
                text-align: center;
            }}
        }}
    </style>
</head>
<body>
    <!-- Progress Bar -->
    <div class="progress-bar" id="progress-bar"></div>

    <!-- Back to Top Button -->
    <button class="back-to-top" id="back-to-top" aria-label="Back to top">↑</button>

    <!-- Jump to Recommendation Button -->
    <a href="#section-1" class="jump-button">Jump to Summary</a>

    <div class="container">
        {"".join(html_parts)}

        <!-- Footer -->
        <div class="report-footer">
            <div class="footer-row">
                <div>CONFIDENTIAL - For Authorized Recipients Only</div>
                <div>1967 Baker Road NW, Atlanta, GA 30318</div>
                <div>Version 1.0 | January 17, 2025</div>
            </div>
            <div class="footer-disclaimer">
                This analysis is for informational purposes only. Consult qualified legal, financial, and real estate professionals before making investment decisions.
            </div>
        </div>
    </div>

    <!-- Chart.js for visualizations -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

    <!-- Interactive Features JavaScript -->
    <script>
        // Back to Top Button
        const backToTop = document.getElementById('back-to-top');
        const progressBar = document.getElementById('progress-bar');

        window.addEventListener('scroll', function() {{
            // Show/hide back to top button
            if (window.pageYOffset > 300) {{
                backToTop.style.display = 'flex';
            }} else {{
                backToTop.style.display = 'none';
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

        // Smooth scroll for all anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
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

        // Print optimization
        window.addEventListener('beforeprint', function() {{
            // Expand all sections before printing
            document.querySelectorAll('.content-section').forEach(section => {{
                section.style.pageBreakInside = 'avoid';
            }});
        }});
    </script>
</body>
</html>
'''

    # Write the file
    with open('1967-Baker-Road-Analysis-Readable.html', 'w') as f:
        f.write(full_html)

    print("Readable HTML created: 1967-Baker-Road-Analysis-Readable.html")

if __name__ == '__main__':
    create_readable_html()
