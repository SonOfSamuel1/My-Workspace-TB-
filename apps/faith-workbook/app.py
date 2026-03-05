from flask import Flask, send_file, render_template_string
import os

app = Flask(__name__, static_folder='.', template_folder='.')

@app.route('/')
def index():
    with open('index.html', 'r') as f:
        return f.read()

@app.route('/faith-workbook.pdf')
def download_pdf():
    return send_file('faith-workbook.pdf', as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
