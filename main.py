from flask import Flask, render_template, request
import uuid
import os
import threading
from werkzeug.utils import secure_filename

from generate_process import watch_loop

app = Flask(__name__)

UPLOAD_FOLDER = "user_uploads"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join("static", "reels"), exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/create", methods=["GET", "POST"])
def create():
    myid = str(uuid.uuid1())

    if request.method == "POST":
        rec_id = request.form.get("uuid") or myid
        desc = request.form.get("text", "")

        folder = os.path.join(app.config["UPLOAD_FOLDER"], rec_id)
        os.makedirs(folder, exist_ok=True)

        input_files = []

        # Save uploaded files
        for file in request.files.values():
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(folder, filename))
                input_files.append(filename)

        # Save description
        with open(
            os.path.join(folder, "desc.txt"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(desc)

        # Create input.txt for FFmpeg concat demuxer
        with open(os.path.join(folder, "input.txt"), "w") as f:
            for fl in input_files:
                f.write(f"file '{fl}'\n")
                f.write("duration 1\n")

            # FFmpeg quirk: last file needs to be repeated without a
            # trailing duration line, or the final image gets cut short
            if input_files:
                f.write(f"file '{input_files[-1]}'\n")

        # IMPORTANT: write the marker file LAST, only once everything
        # (files + desc.txt + input.txt) is fully written to disk.
        # This is the signal the background watcher waits for.
        with open(os.path.join(folder, "ready.flag"), "w") as f:
            f.write("ready")

    return render_template("create.html", myid=myid)


@app.route("/gallery")
def gallery():
    return render_template("gallery.html")


if __name__ == "__main__":
    # Start the background watcher thread that generates audio + reels.
    # daemon=True means it shuts down automatically when the main process exits.
    watcher_thread = threading.Thread(target=watch_loop, daemon=True)
    watcher_thread.start()

    # use_reloader=False is REQUIRED here: Flask's debug reloader spawns a
    # second process, which would start a SECOND watcher thread and cause
    # files to be processed twice / race conditions on done.txt.
    app.run(debug=True, use_reloader=False)