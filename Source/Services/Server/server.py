# Source/Services/Server/server.py
import os
import secrets

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from Source.Services.Camera.camera_handlerv2 import load_face_recognizer
from Source.Shared.shared_variables import data_lock
from Source.Services.Shared.shared_data import shared_data
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = secrets.token_hex(16)

UPLOAD_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "Camera", "Dataset")
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    """Render the main page (index.html)."""
    with data_lock:
        mode = shared_data["operation_mode"]
        targets = shared_data["current_targets"]
        single_target = shared_data["main_target"]

    print(f"Targs = {targets}")
    print(f"single_T = {single_target}")
    return render_template("index.html", mode=mode, targets=targets, single_target=single_target)

@app.route("/upload", methods=["GET", "POST"])
def upload_page():
    """Handle multiple file uploads."""
    with data_lock:
        mode = shared_data["operation_mode"]
        if mode == "multiple":
            targets = shared_data["current_targets"]
        elif mode == "single":
            targets = [shared_data["main_target"]]

    # Redirect if mode is sleep
    if mode == "sleep":
        flash("System is in sleep mode. Uploads are disabled.")
        return redirect(url_for("index"))

    if request.method == "POST":
        target_name = request.form.get("target_name")
        files = request.files.getlist("files")   # <<< ALTERAÇÃO: pega vários arquivos

        if not target_name:
            flash("Please select a target.")
            return redirect(request.url)

        if not files or all(f.filename == "" for f in files):
            flash("No files selected.")
            return redirect(request.url)

        target_folder = os.path.join(UPLOAD_FOLDER, target_name)
        os.makedirs(target_folder, exist_ok=True)

        saved_any = False

        for file in files:
            if not file or file.filename == "":
                continue

            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(target_folder, filename)
                file.save(filepath)
                saved_any = True
            else:
                flash(f"Invalid file skipped: {file.filename}")

        if saved_any:
            flash(f"Uploaded {len([f for f in files if f.filename != '' and allowed_file(f.filename)])} file(s) of {target_name}")
        else:
            flash("No valid images were uploaded.")

        return redirect(url_for("upload_page"))

    return render_template("upload.html", targets=targets, mode=mode)

@app.route("/set_mode", methods=["POST"])
def set_mode():
    """Change the system operation mode via form or JSON POST."""
    mode = None

    if request.form:
        mode = request.form.get("mode")

    if not mode and request.json:
        mode = request.json.get("mode")

    if not mode:
        flash("Invalid mode.")
        return redirect(url_for("index"))

    with data_lock:
        shared_data["operation_mode"] = mode

    if request.is_json:
        return jsonify({"status": "ok", "new_mode": mode})

    return redirect(url_for("index"))

@app.route("/model_training", methods=["GET"])
def model_training():
    """Train the model with the remaining pictures"""    
    load_face_recognizer()

    return redirect(url_for("index"))

@app.route("/add_single_target", methods=["GET", "POST"])
def add_single_target():
    """Render page to add a single target, and handle the form."""
    with data_lock:
        mode = shared_data["operation_mode"]

    # If system is sleeping, block access
    if mode == "sleep":
        flash("System is in sleep mode.")
        return redirect(url_for("index"))

    # POST — add the target
    if request.method == "POST":
        target_name = request.form.get("target_name", "").strip()

        if not target_name:
            flash("Target name cannot be empty.")
            return redirect(request.url)

        with data_lock:
            if target_name == shared_data["main_target"]:
                flash("Target already set.")
                return redirect(request.url)
            
            shared_data["main_target"] = target_name

        flash(f"Target '{target_name}' added successfully!")
        return redirect(url_for("index"))

    # GET — show page
    return render_template("add_target.html", mode=mode)

@app.route("/multiple_add_target", methods=["GET", "POST"])
def multiple_add_target():
    """Render page to add a new target, and handle the form."""
    with data_lock:
        mode = shared_data["operation_mode"]

    if mode == "sleep":
        flash("System is in sleep mode.")
        return redirect(url_for("index"))

    if request.method == "POST":
        target_name = request.form.get("target_name", "").strip()

        if not target_name:
            flash("Target name cannot be empty.")
            return redirect(request.url)

        with data_lock:
            if target_name in shared_data["current_targets"]:
                flash("Target already tracked.")
                return redirect(request.url)
            
            shared_data["current_targets"].append(target_name)

        flash(f"Target '{target_name}' added successfully!")
        return redirect(url_for("index"))

    # GET — show page
    return render_template("add_target.html", mode=mode)

@app.route("/remove_target", methods=["GET", "POST"])
def remove_target():
    """Remove todas as imagens de um target, incluindo sua pasta."""
    with data_lock:
        targets = shared_data["current_targets"]
        s_target = shared_data["main_target"]
        if s_target and s_target not in targets:
            targets.append(s_target)            

    if request.method == "POST":
        target_name = request.form.get("target_name")

        if not target_name:
            flash("Nenhum target selecionado.", "error")
            return redirect(request.url)

        target_folder = os.path.join(UPLOAD_FOLDER, target_name)

        if os.path.exists(target_folder):
            import shutil
            shutil.rmtree(target_folder)
            flash(f"Target '{target_name}' removido completamente.")

            # Remove também da memória
            with data_lock:
                if target_name in shared_data["current_targets"]:
                    shared_data["current_targets"].remove(target_name)

        else:
            flash("Pasta do target não encontrada.", "error")

        return redirect(url_for("remove_target"))

    return render_template("remove_target.html", targets=targets)


def server_handler():
    """Starts the Flask server using the shared state and lock"""
    print("[server_handler] Starting Flask server...")
    
    # TODO: Change the IP: must be dynamic and fetch the IP of the rasp in the current network
    # use_reloader=False: for Flask to be compatible with multithreading
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
