# Source/Services/Server/server.py
import os
import secrets

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from Source.Shared.shared_variables import system_state, data_lock
from werkzeug.utils import secure_filename

app = Flask(__name__)


app.secret_key = secrets.token_hex(16)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    """Render the main page (index.html)."""
    with data_lock:
        mode = system_state.operation_mode
        targets = system_state.current_targets

    return render_template("index.html", mode=mode, targets=targets)

@app.route("/upload", methods=["GET", "POST"])
def upload_page():
    """Handle file uploads."""
    with data_lock:
        mode = system_state.operation_mode
        targets = system_state.identifiable_targets

    # Redirect if mode is sleep
    if mode == "sleep":
        flash("System is in sleep mode. Uploads are disabled.")
        return redirect(url_for("index"))

    if request.method == "POST":
        target_name = request.form.get("target_name")
        file = request.files.get("file")

        if not target_name:
            flash("Please select a target.")
            return redirect(request.url)

        if not file or file.filename == "":
            flash("No file selected.")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            target_folder = os.path.join(UPLOAD_FOLDER, target_name)
            os.makedirs(target_folder, exist_ok=True)

            filepath = os.path.join(target_folder, filename)
            file.save(filepath)

            flash(f"File saved to {target_folder}")
            return redirect(url_for("upload_page"))

        flash("Invalid file type. Only images are allowed.")
        return redirect(request.url)

    return render_template("upload.html", targets=targets, mode=mode)

@app.route("/set_mode", methods=["POST"])
def set_mode():
    """Change the system operation mode via form or JSON POST."""    
    mode = request.form.get("mode") or request.json.get("mode")

    with data_lock:
        system_state.operation_mode = mode
    return jsonify({"status": "ok", "new_mode": mode})

def server_handler():
    """Starts the Flask server using the shared state and lock"""
    print("[server_handler] Starting Flask server...")
    
    # TODO: Change the IP: must be dynamic and fetch the IP of the rasp in the current network
    # use_reloader=False: for Flask to be compatible with multithreading
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
