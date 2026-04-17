from flask import Flask, send_from_directory, request, jsonify
import os

# Tell Flask where compiled React files live
app = Flask(__name__, static_folder="static", static_url_path="")

# Serve React frontend
@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


# Example API endpoint (test backend connection)
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "nyaya_sutra backend running"
    })


# Example chat endpoint (temporary mock response)
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()

    user_message = data.get("message", "")

    return jsonify({
        "reply": f"You said: {user_message}"
    })


# React router fallback support
@app.route("/<path:path>")
def serve_static_files(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)

    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

