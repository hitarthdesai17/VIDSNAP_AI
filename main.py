from flask import Flask, render_template , request
import uuid , os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'user_uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/create",methods=["GET","POST"])
def create():
    myid = str(uuid.uuid1())
    if request.method=="POST":
        print(request.files.keys())
        rec_id=request.form.get("uuid")
        desc=request.form.get("text")
        folder = os.path.join(app.config['UPLOAD_FOLDER'],rec_id)
        os.makedirs(folder,exist_ok=True)

        for file in request.files.values():
            filename = secure_filename(file.filename) 
            #Upload File
            if file and filename:
                file.save(os.path.join(folder,filename))
         #Capture the description and save it to file
        with open(os.path.join(folder, "desc.txt"),"w",encoding="utf-8") as f:
                f.write(desc)

    return render_template("create.html",myid=myid)

@app.route("/gallery")
def gallery():
    return render_template("gallery.html")

app.run(debug=True)