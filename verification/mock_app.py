from flask import Flask, jsonify, send_from_directory, render_template_string
import os
import threading
import sys

# Correct static folder path relative to CWD (root)
app = Flask(__name__, static_folder="static", static_url_path="/static")

# Mock routes for plots
@app.route("/")
def index():
    # Load the actual HTML template but mock the context
    try:
        # Template relies on Flask globals and static folders
        with open("static/html/foamflask_frontend.html", "r") as f:
            template = f.read()
        return render_template_string(template, options="", CASE_ROOT="/tmp/test")
    except Exception as e:
        return str(e)

@app.route("/get_case_root")
def get_case_root():
    return jsonify({"caseDir": "/tmp/test"})

@app.route("/get_docker_config")
def get_docker_config():
    return jsonify({"dockerImage": "test", "openfoamVersion": "test"})

@app.route("/api/cases/list")
def list_cases():
    return jsonify({"cases": ["test_case"]})

@app.route("/api/startup_status")
def startup_status():
    return jsonify({"status": "completed", "message": "Ready"})

@app.route("/api/plot_data")
def plot_data():
    # Return mock data for plots
    import numpy as np
    x = np.linspace(0, 10, 100).tolist()
    y = np.sin(x).tolist()
    return jsonify({
        "time": x,
        "p": y,
        "U_mag": y,
        "Ux": y,
        "Uy": y,
        "Uz": y,
        "nut": y,
        "nuTilda": y,
        "k": y,
        "omega": y
    })

@app.route("/api/residuals")
def residuals():
    import numpy as np
    x = np.linspace(0, 10, 100).tolist()
    y = np.exp(-np.array(x)).tolist()
    return jsonify({
        "time": x,
        "p": y,
        "Ux": y,
        "Uy": y,
        "Uz": y
    })

if __name__ == "__main__":
    app.run(port=5000)
