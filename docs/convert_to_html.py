#!/usr/bin/env python3
"""
Simple markdown to HTML converter for the comprehensive analysis
"""

def convert_md_to_html(md_file, html_file):
    with open(md_file, 'r') as f:
        content = f.read()

    # Simple conversions
    html = content
    html = html.replace('&', '&amp;')
    html = html.replace('<', '&lt;')
    html = html.replace('>', '&gt;')

    # Convert headers
    import re
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

    # Convert bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # Convert italic
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Convert line breaks
    html = html.replace('\n\n', '</p><p>')
    html = '<p>' + html + '</p>'

    # Create full HTML
    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>1967 Baker Road - Comprehensive Investment Analysis</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px; }}
        h3 {{ color: #7f8c8d; }}
        p {{ margin: 15px 0; }}
        strong {{ color: #2c3e50; }}
    </style>
</head>
<body>
    <div class="container">
        {html}
    </div>
</body>
</html>
'''

    with open(html_file, 'w') as f:
        f.write(full_html)

    print(f"HTML file created: {html_file}")

if __name__ == '__main__':
    convert_md_to_html(
        '1967-Baker-Road-Comprehensive-Analysis.md',
        '1967-Baker-Road-Comprehensive-Analysis.html'
    )
