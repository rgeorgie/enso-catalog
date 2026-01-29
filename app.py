import os
from datetime import date
from functools import wraps
from typing import Optional

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    send_from_directory, session, Response
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from wtforms import (
    StringField, SelectField, DateField, DecimalField, IntegerField,
    TextAreaField, SubmitField, BooleanField
)
from wtforms.validators import DataRequired, Email, Optional as VOptional, Length, NumberRange

# -----------------------------
# Config
# -----------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "karate_club.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB

# Admin credentials (set via env for security)
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")

db = SQLAlchemy(app)


# -----------------------------
# Models
# -----------------------------
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), nullable=True)  # "Male", "Female", "Other" / Optional
    birthdate = db.Column(db.Date, nullable=True)

    belt_rank = db.Column(db.String(20), nullable=False, default="White")
    discipline = db.Column(db.String(10), nullable=False, default="Both")  # Kata/Kumite/Both
    weight_kg = db.Column(db.Integer, nullable=True)
    height_cm = db.Column(db.Integer, nullable=True)

    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(40), nullable=True)

    join_date = db.Column(db.Date, nullable=True)
    active_member = db.Column(db.Boolean, default=True)

    notes = db.Column(db.Text, nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


# -----------------------------
# Forms
# -----------------------------
BELT_CHOICES = [
    ("White", "White"),
    ("Yellow", "Yellow"),
    ("Orange", "Orange"),
    ("Green", "Green"),
    ("Blue", "Blue"),
    ("Purple", "Purple"),
    ("Brown", "Brown"),
    ("Black", "Black"),
]

DISCIPLINE_CHOICES = [("Kata", "Kata"), ("Kumite", "Kumite"), ("Both", "Both")]

GENDER_CHOICES = [("", "—"), ("Male", "Male"), ("Female", "Female"), ("Other", "Other")]

class PlayerForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    gender = SelectField("Gender", choices=GENDER_CHOICES, validators=[VOptional()])
    birthdate = DateField("Birthdate", validators=[VOptional()])

    belt_rank = SelectField("Belt Rank", choices=BELT_CHOICES, validators=[DataRequired()])
    discipline = SelectField("Discipline", choices=DISCIPLINE_CHOICES, validators=[DataRequired()])
    weight_kg = IntegerField("Weight (kg)", validators=[VOptional(), NumberRange(min=0, max=500)])
    height_cm = IntegerField("Height (cm)", validators=[VOptional(), NumberRange(min=0, max=300)])

    email = StringField("Email", validators=[VOptional(), Email(), Length(max=120)])
    phone = StringField("Phone", validators=[VOptional(), Length(max=40)])

    join_date = DateField("Join Date", validators=[VOptional()])
    active_member = BooleanField("Active Member", default=True)

    notes = TextAreaField("Notes", validators=[VOptional(), Length(max=5000)])
    submit = SubmitField("Save")


# -----------------------------
# Helpers
# -----------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin login required.", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():
    return redirect(url_for("list_players"))

@app.route("/players")
def list_players():
    q = request.args.get("q", "").strip()
    belt = request.args.get("belt", "")
    active = request.args.get("active", "")

    query = Player.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Player.first_name.ilike(like), Player.last_name.ilike(like))
        )

    if belt:
        query = query.filter_by(belt_rank=belt)

    if active == "yes":
        query = query.filter_by(active_member=True)
    elif active == "no":
        query = query.filter_by(active_member=False)

    players = query.order_by(Player.last_name.asc(), Player.first_name.asc()).all()
    return render_template("players_list.html", players=players, q=q, belt=belt, active=active, belts=BELT_CHOICES)

@app.route("/players/<int:player_id>")
def player_detail(player_id: int):
    player = Player.query.get_or_404(player_id)
    return render_template("player_detail.html", player=player)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# -------- Admin & Auth ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("list_players")
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["is_admin"] = True
            flash("Logged in as admin.", "success")
            return redirect(next_url)
        flash("Invalid credentials.", "danger")
    return render_template("login.html", next_url=next_url)

@app.route("/logout")
def logout():
    session.pop("is_admin", None)
    flash("Logged out.", "info")
    return redirect(url_for("list_players"))

# -------- CRUD ----------
@app.route("/admin/players/new", methods=["GET", "POST"])
@admin_required
def create_player():
    form = PlayerForm()
    if form.validate_on_submit():
        player = Player(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            gender=form.gender.data or None,
            birthdate=form.birthdate.data,
            belt_rank=form.belt_rank.data,
            discipline=form.discipline.data,
            weight_kg=form.weight_kg.data,
            height_cm=form.height_cm.data,
            email=form.email.data,
            phone=form.phone.data,
            join_date=form.join_date.data,
            active_member=bool(form.active_member.data),
            notes=form.notes.data,
        )
        # handle optional photo upload
        file = request.files.get("photo")
        if file and file.filename and allowed_file(file.filename):
            fname = secure_filename(file.filename)
            # make filename unique
            base, ext = os.path.splitext(fname)
            counter = 1
            new_name = fname
            while os.path.exists(os.path.join(UPLOAD_FOLDER, new_name)):
                new_name = f"{base}_{counter}{ext}"
                counter += 1
            file.save(os.path.join(UPLOAD_FOLDER, new_name))
            player.photo_filename = new_name

        db.session.add(player)
        db.session.commit()
        flash("Player created.", "success")
        return redirect(url_for("list_players"))
    return render_template("player_form.html", form=form, title="Add Player")

@app.route("/admin/players/<int:player_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_player(player_id: int):
    player = Player.query.get_or_404(player_id)
    form = PlayerForm(obj=player)
    if form.validate_on_submit():
        form.populate_obj(player)
        file = request.files.get("photo")
        if file and file.filename and allowed_file(file.filename):
            fname = secure_filename(file.filename)
            base, ext = os.path.splitext(fname)
            counter = 1
            new_name = fname
            while os.path.exists(os.path.join(UPLOAD_FOLDER, new_name)):
                new_name = f"{base}_{counter}{ext}"
                counter += 1
            file.save(os.path.join(UPLOAD_FOLDER, new_name))
            player.photo_filename = new_name
        db.session.commit()
        flash("Player updated.", "success")
        return redirect(url_for("player_detail", player_id=player.id))
    return render_template("player_form.html", form=form, title="Edit Player")

@app.route("/admin/players/<int:player_id>/delete", methods=["POST"])
@admin_required
def delete_player(player_id: int):
    player = Player.query.get_or_404(player_id)
    # Optionally remove the photo file
    if player.photo_filename:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, player.photo_filename))
        except FileNotFoundError:
            pass
    db.session.delete(player)
    db.session.commit()
    flash("Player deleted.", "info")
    return redirect(url_for("list_players"))

# -------- Export ----------
@app.route("/export/csv")
def export_csv():
    players = Player.query.order_by(Player.last_name.asc(), Player.first_name.asc()).all()

    def generate():
        yield "id,first_name,last_name,belt_rank,discipline,active_member,email,phone\n"
        for p in players:
            # basic CSV escaping for commas/quotes
            def esc(s: Optional[str]) -> str:
                if s is None:
                    return ""
                s = str(s)
                if any(c in s for c in [",", '"', "\n"]):
                    s = '"' + s.replace('"', '""') + '"'
                return s
            row = [
                str(p.id),
                esc(p.first_name),
                esc(p.last_name),
                esc(p.belt_rank),
                esc(p.discipline),
                "yes" if p.active_member else "no",
                esc(p.email or ""),
                esc(p.phone or ""),
            ]
            yield ",".join(row) + "\n"

    headers = {
        "Content-Disposition": 'attachment; filename="karate_players.csv"'
    }
    return Response(generate(), mimetype="text/csv", headers=headers)


# -----------------------------
# DB Init
# -----------------------------
@app.before_first_request
def init_db():
    db.create_all()


# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    # Tip: in dev, set FLASK_DEBUG=1 (Linux/macOS) or $env:FLASK_DEBUG=1 (PowerShell)
    app.run(host="0.0.0.0", port=5000)
