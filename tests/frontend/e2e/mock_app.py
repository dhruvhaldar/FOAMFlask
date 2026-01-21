from flask import Flask, render_template, send_from_directory, Response, request
import os
import orjson

# Define paths relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'static', 'html')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

def fast_jsonify(data, status=200):
    json_bytes = orjson.dumps(
        data,
        option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_NAIVE_UTC
    )
    return Response(json_bytes, status=status, mimetype='application/json')

@app.route('/')
@app.route('/post')
@app.route('/run')
@app.route('/geometry')
@app.route('/meshing')
@app.route('/visualizer')
@app.route('/plots')
@app.route('/setup')
def index():
    # Mock options for tutorial dropdown
    options = '<option value="tut1">Tutorial 1</option>'
    return render_template('foamflask_frontend.html', options=options, CASE_ROOT="/tmp/foamflask_test")

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

# Mock API Endpoints for E2E Tests

@app.route('/api/startup_status', methods=['GET'])
def startup_status():
    return fast_jsonify({"status": "completed", "message": "Ready"})

@app.route('/get_case_root', methods=['GET'])
def get_case_root():
    return fast_jsonify({"caseDir": "/tmp/foamflask_test"})

@app.route('/get_docker_config', methods=['GET'])
def get_docker_config():
    return fast_jsonify({"dockerImage": "test/image", "openfoamVersion": "v2206"})

@app.route('/api/cases/list', methods=['GET'])
def list_cases():
    return fast_jsonify({"cases": ["case1", "case2"]})

@app.route('/api/geometry/list', methods=['GET'])
def list_geometry():
    return fast_jsonify({"files": ["geo1.stl", "geo2.stl"], "success": True})

@app.route('/api/available_meshes', methods=['GET'])
def available_meshes():
    return fast_jsonify({"meshes": [{"name": "mesh.vtk", "path": "/tmp/mesh.vtk"}]})

# Post Processing Placeholders (Mock)
@app.route("/api/slice/create", methods=["POST"])
def create_slice():
    return fast_jsonify({"status": "coming_soon", "message": "Slice visualization coming soon"}), 501

@app.route("/api/streamline/create", methods=["POST"])
def create_streamline():
    return fast_jsonify({"status": "coming_soon", "message": "Streamline visualization coming soon"}), 501

@app.route("/api/surface_projection/create", methods=["POST"])
def create_surface_projection():
    return fast_jsonify({"status": "coming_soon", "message": "Surface projection visualization coming soon"}), 501

if __name__ == '__main__':
    app.run(port=5000)
