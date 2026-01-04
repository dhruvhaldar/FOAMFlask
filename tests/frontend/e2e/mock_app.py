from flask import Flask, render_template, send_from_directory, jsonify
import os

# Define paths relative to this script
# __file__ = tests/frontend/e2e/mock_app.py
# dirname 1 = tests/frontend/e2e
# dirname 2 = tests/frontend
# dirname 3 = tests
# dirname 4 = . (root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'static', 'html')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

@app.route('/')
def index():
    # Mock options for tutorial dropdown
    options = '<option value="tut1">Tutorial 1</option>'
    return render_template('foamflask_frontend.html', options=options)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

if __name__ == '__main__':
    app.run(port=5000)
