import base64
import datetime
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_session import Session
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from Forms import (
    DeleteAccountForm,
    LoginForm,
    RegisterForm,
    SendFile,
    UpdatePasswordForm,
    UpdatePublicKeyForm,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
CERT_DIR = os.path.join(BASE_DIR, "certs")
DATABASE_PATH = os.path.join(BASE_DIR, "users.db")
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
print(os.environ["SQLALCHEMY_DATABASE_URI"])
app.config.update(
    static_folder=STATIC_DIR,
    SECRET_KEY=os.environ["SECRET_KEY"],
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{BASE_DIR}/{os.environ['SQLALCHEMY_DATABASE_URI']}",
    SESSION_TYPE="sqlalchemy",
    UPLOAD_FOLDER=UPLOAD_DIR,
    STORAGE_FOLDER=STORAGE_DIR,
    ENCRYPTED_STORAGE=f"{STORAGE_DIR}/encrypted_files",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    DEBUG=True,
    MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 50MB
    MAX_PUBLIC_KEY_SIZE=10 * 1024,  # 10KB for public keys
    PORT=os.environ.get("PORT", 5000),
)
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
Path(app.config["ENCRYPTED_STORAGE"]).mkdir(parents=True, exist_ok=True)

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://",
    default_limits=["1000/day", "100/hour"],
)
socketio = SocketIO(app, manage_session=False, cors_allowed_origins="*")
login_manager = LoginManager(app)
login_manager.login_view = "login"
app.config["SESSION_SQLALCHEMY"] = db
Session(app)

try:
    mongo = MongoClient("localhost", 27017, serverSelectionTimeoutMS=5000)
    file_db = mongo.get_database("file_db")
    aes_keys_col = file_db.get_collection("aes_keys")
    encrypted_files_col = file_db.get_collection("encrypted_files")
except Exception as e:
    app.logger.error(f"Failed to connect to MongoDB: {e}")
    exit(-1)


# ----------------------------------------------------
# Models
# ----------------------------------------------------
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


# ----------------------------------------------------
# ---------------------- ROUTES ----------------------
# ----------------------------------------------------


# ----------------- INDEX ----------------------
@app.route("/")
def index():
    return render_template("index.html")


# -------------- REGISTER ---------------------
@app.route("/register", methods=["GET", "POST"])
# @limiter.limit("5/day")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        try:
            existing_user = Users.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash("Username already taken", "error")
                return redirect(url_for("register"))

            new_user = Users(
                username=form.username.data,
                password=generate_password_hash(form.password.data),
            )
            public_key_file = form.public_key.data
            public_key_content = public_key_file.read().decode("utf-8")

            filename = secure_filename(f"{new_user.username}.pub")
            public_key_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            with open(public_key_path, "w") as f:
                f.write(public_key_content)

            db.session.add(new_user)
            db.session.commit()

            flash("Registration successful", "success")
            return redirect(url_for("login"))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration error: {e}")
            flash("Registration failed", "error")
            return render_template("register.html", form=form)

    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")

    return render_template("register.html", form=form)


# -------------- LOGIN ---------------------
@app.route("/login", methods=["GET", "POST"])
@limiter.limit("100/day")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Login successful!", "info")
            return redirect(url_for("dashboard"))
        else:
            flash("Login unsuccessful: Invalid Username or Password", "error")
            return redirect(url_for("login"))

    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")

    return render_template("login.html", form=form)


# ----------- DASHBOARD --------------------
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# -------------- LOGOUT ---------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logout out", "info")
    return redirect(url_for("index"))


# --------------- UPDATE PASSWORD ----------------------
@app.route("/update_password", methods=["GET", "POST"])
@login_required
@limiter.limit("5/hour")
def update_password():
    form = UpdatePasswordForm()
    if form.validate_on_submit():
        try:
            user = Users.query.get(current_user.id)
            if not check_password_hash(user.password, form.oldpass.data):
                flash("Incorrect current password", "error")
                return redirect(url_for("update_password"))
            user.password = generate_password_hash(form.password.data)
            db.session.commit()
            flash("Password updated!", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            app.logger.error(f"Failed to updated password {e}")
            db.session.rollback()

    return render_template("update_password.html", form=form)


# --------------- UPDATE PUBLIC KEY --------------------
@app.route("/update_public_key", methods=["GET", "POST"])
@login_required
def update_pk():
    form = UpdatePublicKeyForm()
    if form.validate_on_submit():
        # Verify username matches current user
        if form.username.data != current_user.username:
            flash("Username does not match your account", "error")
            return redirect(url_for("update_pk"))

        # Verify password
        user = Users.query.get(current_user.id)
        if not check_password_hash(user.password, form.password.data):
            flash("Incorrect password", "error")
            return redirect(url_for("update_pk"))

        try:
            # Read and validate the public key content
            public_key_file = form.public_key.data
            public_key_content = public_key_file.read().decode("utf-8")

            # Save the public key
            filename = secure_filename(current_user.username + ".pub")
            public_key_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            with open(public_key_path, "w") as f:
                f.write(public_key_content)

            flash("Public key updated successfully!", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            app.logger.error(f"Failed to update public key: {e}")
            flash("Failed to update public key", "error")
            return redirect(url_for("update_pk"))
    return render_template("update_public_key.html", form=form)


@app.route("/send_file", methods=["GET"])
@login_required
def show_send_file():
    form = SendFile()  # your existing WTForms form
    return render_template("send_file.html", form=form)


@app.route("/send_file", methods=["POST"])
@csrf.exempt
@login_required
def send_enc_file():
    data = request.get_json()
    required = [
        "recipient",
        "filename",
        "encrypted_file",
        "wrapped_key_for_recipient",
        "nonce",
    ]
    if not all(k in data for k in required):
        return {"success": False, "error": "missing fields"}, 400

    if not Users.query.filter_by(username=data["recipient"]).first():
        return {"success": False, "error": "recipient not found"}, 404
    if current_user.username == data["recipient"]:
        return {"succes": False, "error": "cannot send file to yourself"}, 500
    stored = secure_filename(
        f"{current_user.username}_{data['filename']}__{os.urandom(8).hex()}.enc"
    )
    path = os.path.join(app.config["ENCRYPTED_STORAGE"], stored)
    with open(path, "wb") as f:
        f.write(base64.b64decode(data["encrypted_file"]))

    encrypted_files_col.insert_one(
        {
            "sender": current_user.username,
            "recipient": data["recipient"],
            "filename": data["filename"],
            "stored_file": stored,
            "wrapped_key_for_recipient": data["wrapped_key_for_recipient"],
            "nonce": data["nonce"],
            "uploaded_at": datetime.datetime.now(),
        }
    )
    return {"success": True}


@app.route("/check_files")
@login_required
def check_files():
    try:
        files = list(
            encrypted_files_col.find(
                {"recipient": current_user.username},
                {
                    "_id": 0,
                    "filename": 1,
                    "sender": 1,
                    "uploaded_at": 1,
                    "stored_file": 1,
                    "wrapped_key_for_recipient": 1,
                    "nonce": 1,
                },
            ).sort("uploaded_at", -1)
        )

        # Convert datetime objects to strings for JSON serialization
        for file in files:
            if "uploaded_at" in file:
                file["uploaded_at"] = file["uploaded_at"].isoformat()

        return {"success": True, "files": files}, 200
    except Exception as e:
        app.logger.error(f"Check files error: {e}")
        return {"success": False, "error": "Failed to retrieve file"}, 500


@app.route("/uploads/public_keys/<filename>")
def serve_public_key(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], secure_filename(filename))


@app.route("/get_reusable_aes_key")
@login_required
def get_reusable_key():
    recipient = request.args.get("recipient")
    if recipient == current_user.username:
        return {
            "exists": False,
            "error": "Unable to get a shared key with yourself",
        }, 500
    doc = aes_keys_col.find_one(
        {"sender": current_user.username, "recipient": recipient}
    )
    if doc:
        return {
            "exists": True,
            "wrapped_for_sender": doc["wrapped_for_sender"],
            "wrapped_for_recipient": doc["wrapped_for_recipient"],
        }
    return {"exists": False}


@app.route("/publish_reusable_aes_key", methods=["POST"])
@login_required
@csrf.exempt
def publish_reusable_aes_key():
    data = request.get_json()
    if current_user.username == data["recipient"]:
        return {"success": False, "error": "Cannot publish a key for yourself"}, 500
    aes_keys_col.update_one(
        {"sender": current_user.username, "recipient": data["recipient"]},
        {
            "$set": {
                "wrapped_for_sender": data["wrapped_for_sender"],
                "wrapped_for_recipient": data["wrapped_for_recipient"],
            }
        },
        upsert=True,
    )
    return {"success": True}


# --------------- DELETE ACCOUNT ----------------------
@app.route("/delete_account", methods=["GET", "POST"])
@login_required
def delete():
    form = DeleteAccountForm()
    if form.validate_on_submit():
        # Delete public key
        pub_key = os.path.join(
            app.config["UPLOAD_FOLDER"], f"{current_user.username}.pub"
        )
        # If the public_key exists then delete the file
        if os.path.exists(pub_key):
            os.remove(pub_key)

        # Get encrypted files BEFORE deleting from DB
        encrypted_files = list(
            encrypted_files_col.find({"sender": current_user.username})
        )
        # delete encrypted files
        for f in encrypted_files:
            path = os.path.join(app.config["ENCRYPTED_STORAGE"], f["stored_file"])
            if os.path.exists(path):
                os.remove(path)

        aes_keys_col.delete_many({"sender": current_user.username})
        aes_keys_col.delete_many({"recipient": current_user.username})
        encrypted_files_col.delete_many({"sender": current_user.username})
        encrypted_files_col.delete_many({"recipient": current_user.username})
        user = Users.query.get(current_user.id)

        db.session.delete(user)
        db.session.commit()
        logout_user()

        flash("Account deleted successfully", "info")
        return redirect(url_for("index"))

    return render_template("delete_account.html", form=form)


@app.route("/get_encrypted_file/<stored_filename>")
@login_required
def get_encrypted_file(stored_filename):
    try:
        # Verify the file belongs to current user
        file_doc = encrypted_files_col.find_one(
            {"stored_file": stored_filename, "recipient": current_user.username}
        )

        if not file_doc:
            return {"success": False, "error": "File not found or access denied"}, 404

        file_path = os.path.join(app.config["ENCRYPTED_STORAGE"], stored_filename)
        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found on disk"}, 404

        with open(file_path, "rb") as f:
            encrypted_data = base64.b64encode(f.read()).decode("utf-8")

        return {"success": True, "encrypted_data": encrypted_data}, 200

    except Exception as e:
        app.logger.error(f"Get encrypted file error: {e}")
        return {"success": False, "error": str(e)}, 500


@app.route("/inbox")
@login_required
def inbox():
    return render_template("inbox.html")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    # Create and initialize the db and login manager
    with app.app_context():
        db.create_all()
    socketio.run(
        app,
        host="0.0.0.0",
        debug=app.config["DEBUG"],
        port=app.config["PORT"],
        ssl_context=(
            os.path.join(CERT_DIR, "cert.pem"),
            os.path.join(CERT_DIR, "key.pem"),
        ),
    )
