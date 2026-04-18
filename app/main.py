from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
import os
import sys

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

UPLOAD_FOLDER      = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'mp3', 'wav', 'm4a', 'ogg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "nyaya_sutra backend running"})

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename        = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        return jsonify({
            "message":  "File uploaded successfully",
            "filename": filename,
            "url":      f"/api/files/{unique_filename}"
        })
    return jsonify({"error": "File type not allowed"}), 400

@app.route("/api/files/<filename>")
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ── Citizen chat ──────────────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    from src.citizen_router import citizenRouter
    
    data  = request.get_json()
    query = data.get("message", "").strip()
    mode  = data.get("mode", "citizen")

    if not query:
        return jsonify({"error": "Empty message"}), 400

    if mode == "citizen":
        try:
            result = citizenRouter(query)
            return jsonify({
                "reply":  result["response"],
                "type":   result["type"],
                "agents": result["agents"]
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"reply": f"Mode '{mode}' not yet implemented."})

# ── Lawyer chat ───────────────────────────────────────────────────────────────
@app.route("/api/lawyer-chat", methods=["POST"])
def lawyer_chat():
    from src.lawyer_router import lawyer_router
    
    query      = request.form.get("message", "").strip()
    mode       = request.form.get("mode", "advocate")
    file_bytes = None

    # ── Read file bytes if uploaded ───────────────────────────────────────────
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '' and allowed_file(file.filename):
            file_bytes = file.read()

    # ── Must have at least a query OR a file ──────────────────────────────────
    if not query and file_bytes is None:
        return jsonify({"error": "Please provide a message or upload a file."}), 400

    if mode == "advocate":
        try:
            result = lawyer_router(query=query, file_bytes=file_bytes)
            return jsonify({
                "reply":     result["response"],
                "type":      result["type"],
                "route":     result["route"],
                "used_file": result.get("used_file", False)
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"reply": f"Mode '{mode}' not yet implemented."})

@app.route("/<path:path>")
def serve_static_files(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    # Detect Databricks environment
    in_databricks = 'DATABRICKS_RUNTIME_VERSION' in os.environ or '/databricks/' in sys.executable
    
    if in_databricks:
        print("✓ Flask app initialized successfully")
        print("⚠ Cannot start Flask server in Databricks file execution")
        print("→ Deploy this app using Databricks Apps or run outside Databricks")
    else:
        app.run(host="0.0.0.0", port=8000, debug=True)
