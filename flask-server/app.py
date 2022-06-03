import os, glob
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for, request, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env
from werkzeug.utils import secure_filename
import predict_edible
from predict_edible import proccess_img

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import pyrebase_modific

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# db_path = os.path.join(BASE_DIR, "mushroom.db") # for sqlite db only

app = Flask(__name__)


app.secret_key = 'VehfbdjS673xc'
app.static_folder = 'static'

UPLOAD_FOLDER = BASE_DIR+'/static/uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route("/")
@app.route("/home")
def home():
    return render_template("/home.html")

firebase_config = {
    "apiKey": "AIzaSyCht0LhaaZP89ICldZNXNYgnww5J9iaa38",  #
    "authDomain": "mushroomm-b7709.firebaseapp.com",  #
    "databaseURL": "https://mushroomm-b7709-default-rtdb.firebaseio.com",  # https:///
    "storageBucket": "mushroomm-b7709.appspot.com",  # gs://
    "serviceAccount": f'{BASE_DIR}/mushroomm-b7709-firebase-adminsdk-3z1dn-20eff067a0.json'
}

firebase = pyrebase_modific.initialize_app(firebase_config)

db = firebase.database()
########


@app.route("/map")
def map():
    execute_locations = db.child("locations").get()
    execute_mushrooms = db.child("mushrooms_info").get()


    mushrooms = []
    for fung in execute_mushrooms.each():
        try:
            un_id = fung.key()
            name = fung.val().get("name")
            image_url = fung.val().get("image_url")
            description = fung.val().get("description")
            edible = fung.val().get("edible")
            fruiting = fung.val().get("fruiting")
            created_by = fung.val().get("created_by")
            found_at = fung.val().get("found_at")
            mushrooms.append([un_id, name, image_url, description, edible, fruiting, created_by, found_at])
        except:
            pass

    locations = []
    locations_maps_array = []

    for location in execute_locations.each():
        name = location.val().get("name")
        lat = location.val().get("lat")
        lng = location.val().get("lng")
        locations_maps_array.append([name, lat, lng])
        locations.append([name, lat, lng])

    return render_template(
        "map.html", locations=locations,
        locations_maps_array=locations_maps_array, mushrooms=mushrooms)

def noquote(s):
    return s
pyrebase_modific.pyrebase_modific.quote = noquote

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_form = request.form.get("username").lower()

        existing_user = db.child("Users").order_by_child("username").equal_to(user_form).get().val()


        if len(existing_user) > 0:
            flash("Пользователь с таким никнеймом уже зарегистрирован")
            return redirect(url_for("register"))

        username = request.form.get("username").lower()
        password = generate_password_hash(request.form.get("password"))
        data_user = {"username": username, "password": password}
        db.child("Users").push(data_user)
        session["user"] = request.form.get("username").lower()
        flash("Вы успешно зарегистрировались!")

        return redirect(url_for("home", username=session["user"]))
    return render_template("register.html")

#
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_form = request.form.get("username").lower()
        existing_user =db.child("Users").order_by_child("username").equal_to(user_form).get().val()
        if len(existing_user)>0:
            pass_word = list(existing_user.items())[0][1]['password']
            if check_password_hash(pass_word, request.form.get(
                            "password")):
                    session["user"] = request.form.get("username").lower()
                    return redirect(url_for("home", username=session["user"]))
            else:
                    flash("Неправильное имя или пароль")
                    return redirect(url_for("login"))
        else:
            flash("Неправильное имя или пароль")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    flash("Вы вышли из аккаунта")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/add_mushroom", methods=["GET", "POST"])
def add_mushroom():
    if request.method == "POST":
        name_mush = request.form.get("name")
        image_url = request.form.get("image_url")
        description = request.form.get("description")
        edible = request.form.get("edible")
        fruiting = request.form.get("fruiting")
        created_by = session["user"]
        found_at = request.form.get("found_at")
        data_of_mush = {"name": name_mush, "image_url":image_url, "description":description, "edible":edible, "fruiting":fruiting, "created_by":created_by, "found_at":found_at}
        db.child("mushrooms_info").push(data_of_mush)

        flash("Гриб успешно добавлен в каталог")
        return redirect(url_for("add_mushroom"))

    return render_template("add_mushroom.html")

import time
@app.route("/add_location", methods=["GET", "POST"])
def add_location():
    if request.method == "POST":
        loc_name = request.form.get("location_name")
        if len(loc_name) > 30:
            flash("Слишком большое название")
            return redirect(url_for("add_location"))
        lat = request.form.get("lat")
        lng = request.form.get("lng")
        if (str(lat).replace('.','',1).isdigit()) and (str(lng).replace('.','',1).isdigit()):
            data_of_location = {"date":int(time.time()),"location_name": loc_name, "lat": lat, "lon": lng, "url":"https://i.ibb.co/0h5DL66/Untitled-design-2.png", "username":session["user"] }
            db.child("mushrooms").push(data_of_location)
            flash("Маркер локации успешно добавлен")
            return redirect(url_for("add_location"))
        else:
            flash("Не указаны координаты найденного гриба")
            return redirect(url_for("add_location"))

    return render_template("add_location.html")

@app.route("/check_edible", methods=['GET', 'POST'])
def check_edible():
    return render_template("check_edible.html")

@app.route("/edit_mushroom/<mushroom_id>", methods=["GET", "POST"])
def edit_mushroom(mushroom_id):
    if request.method == "POST":
        name = request.form.get("name")
        image_url = request.form.get("image_url")
        descr = request.form.get("description")
        edible = request.form.get("edible")
        fruiting = request.form.get("fruiting")
        created_by = session["user"]
        found_at = request.form.get("found_at")
        edit_mush_data = {"name":name, "image_url":image_url, "description":descr, "edible":edible, "fruiting":fruiting, "created_by":created_by, "found_at":found_at}
        db.child("mushrooms_info").child(mushroom_id).update(edit_mush_data)
        flash("Гриб успешно отредактирован")
    execute_mushrooms_info= db.child("mushrooms_info").get()
    list_of_mush = []
    for fung in execute_mushrooms_info.each():
        try:
            un_id = fung.key()
            name = fung.val().get("name")
            image_url = fung.val().get("image_url")
            description = fung.val().get("description")
            edible = fung.val().get("edible")
            fruiting = fung.val().get("fruiting")
            created_by = fung.val().get("created_by")
            found_at = fung.val().get("found_at")
            list_of_mush.append([un_id, name, image_url, description, edible, fruiting, created_by, found_at])
        except:
            pass
    return render_template("edit_mushroom.html", mushroom=list_of_mush)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files['file']

    if file.filename == '':
        flash('No image selected for uploading')
        return redirect("check_edible.html")

    if file and allowed_file(file.filename):

        filename = secure_filename(file.filename)

        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(image_path)

        flash('Фото успешно проанализировано')
        predict_edible = proccess_img(image_path, filename)
        if len(predict_edible) == 1:
            url_pic = predict_edible[0][0]
            edible = predict_edible[0][1]

            if edible == 1:
                edible = "НЕСЪЕДОБНЫЙ"
            elif edible == 0:
                edible = "Съедобный"
            else:
                edible = "Не гриб или Ядовитый"
            return render_template('upload.html', url=url_pic, eat=edible,numbr=1)
        else:
            for mushroomers in range(len(predict_edible)):
                edible = predict_edible[mushroomers][1]

                if predict_edible[mushroomers][1] == 1:
                    predict_edible[mushroomers][1] = "Ядовитый"
                elif predict_edible[mushroomers][1] == 0:
                    predict_edible[mushroomers][1] = "Съедобный"
                else:
                    predict_edible[mushroomers][1] = "Не гриб или Ядовитый"
            return render_template('upload.html', urls=predict_edible,numbr=len(predict_edible))
    else:
        flash('Допустимый тип фото -> png, jpg, jpeg')
        return redirect("/check_edible.html")

@app.route('/display/<filename>')
def display_image(filename):
    return redirect(url_for('static', filename='downloads/' + filename), code=301)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('/check_edible.html'), 404


@app.route("/delete_mushroom/<mushroom_id>")
def delete_mushroom(mushroom_id):
    db.child("mushrooms_info").child(mushroom_id).remove()

    flash("Данные о грибе успешно удалены")
    return redirect(url_for("map"))


if __name__ == "__main__":
    app.run(
        host="192.168.1.102",
            port=3000,
            debug=False,
        threaded=False
    )
