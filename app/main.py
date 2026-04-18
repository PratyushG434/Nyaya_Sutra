from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
import os

# Tell Flask where compiled React files live
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app) # Enable CORS for all routes

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'mp3', 'wav', 'm4a', 'ogg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Serve React frontend
@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

# API Health Check
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "nyaya_sutra backend running"
    })

# File Upload Endpoint
@app.route("/api/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Append UUID to prevent name collisions
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        
        return jsonify({
            "message": "File uploaded successfully",
            "filename": filename,
            "url": f"/api/files/{unique_filename}"
        })
    
    return jsonify({"error": "File type not allowed"}), 400

# Serve uploaded files
@app.route("/api/files/<filename>")
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Enhanced Chat Endpoint
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").lower()
    mode = data.get("mode", "citizen")
    
    # Mock Logic for Timeline/Audit
    response = {
        "reply": f"Processing your query in {mode} mode: \"{user_message}\".",
        "timeline": None,
        "audit_results": None
    }

    if "fraud" in user_message or "harassment" in user_message:
        response["reply"] = "I understand you're facing a difficult situation. Here is a step-by-step legal roadmap to help you navigate this."
        response["timeline"] = [
            {"step": 1, "title": "Collect Evidence (Digital & Physical)", "status": "done"},
            {"step": 2, "title": "File Complaint (Cyber Portal/Police)", "status": "current"},
            {"step": 3, "title": "Verification of Statement", "status": "upcoming"},
            {"step": 4, "title": "Magistrate Hearing", "status": "upcoming"}
        ]
    
    if mode == "advocate" and ("audit" in user_message or "analyze" in user_message):
        response["reply"] = "I have audited the document. Here are the key findings regarding statutory compliance and citations."
        response["audit_results"] = {
            "statutes": ["BNS Section 303", "BNSS Section 173"],
            "precedents": ["State of Haryana v. Bhajan Lal (1992)"],
            "warnings": ["Section 420 IPC is now Section 318 BNS. Please update the draft."]
        }

    return jsonify(response)

# React router fallback support
@app.route("/<path:path>")
def serve_static_files(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)