import os
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
    StringField, SelectField, DateField, IntegerField,
    TextAreaField, SubmitField, BooleanField
)
from wtforms.validators import DataRequired, Email, Optional as VOptional, Length, NumberRange, URL
from sqlalchemy import or_, text
from werkzeug.routing import BuildError

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

# Admin credentials (env-configurable)
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")

db = SQLAlchemy(app)

# -----------------------------
# Simple i18n (BG default)
# -----------------------------
def get_lang() -> str:
    return session.get("lang", "bg")

translations = {
    "en": {
        "Karate Club": "Karate Club",
        "Players": "Players",
        "+ Add Player": "+ Add Player",
        "Add Player": "Add Player",
        "Edit Player": "Edit Player",
        "Delete": "Delete",
        "Admin Login": "Admin Login",
        "Logout": "Logout",
        "Language": "Language",
        "BG": "BG",
        "EN": "EN",
        "All": "All",
        "Run DB migration": "Run DB migration",

        "Search": "Search",
        "Belt": "Belt",
        "Discipline": "Discipline",
        "Active": "Active",
        "Inactive": "Inactive",
        "Apply": "Apply",
        "Reset": "Reset",
        "Export CSV": "Export CSV",
        "Name": "Name",
        "Email": "Email",
        "Phone": "Phone",
        "Yes": "Yes",
        "No": "No",
        "No players found.": "No players found.",
        "No photo uploaded": "No photo uploaded",

        "First Name": "First Name",
        "Last Name": "Last Name",
        "Gender": "Gender",
        "Birthdate": "Birthdate",
        "Belt Rank": "Belt Rank",
        "Weight (kg)": "Weight (kg)",
        "Height (cm)": "Height (cm)",
        "Join Date": "Join Date",
        "Active Member": "Active Member",
        "Notes": "Notes",
        "Photo (jpg/png/gif/webp, ≤ 2MB)": "Photo (jpg/png/gif/webp, ≤ 2MB)",
        "Save": "Save",
        "Cancel": "Cancel",
        "Joined": "Joined",

        "—": "—",
        "Male": "Male",
        "Female": "Female",
        "Other": "Other",

        "White": "White",
        "Yellow": "Yellow",
        "Orange": "Orange",
        "Green": "Green",
        "Blue": "Blue",
        "Purple": "Purple",
        "Brown": "Brown",
        "Black": "Black",

        "Kata": "Kata",
        "Kumite": "Kumite",
        "Both": "Both",

        "Sportdata": "Sportdata",
        "Sportdata Profiles": "Sportdata Profiles",
        "WKF Profile URL": "WKF Profile URL",
        "BNFK Profile URL": "BNFK Profile URL",
        "ENSO Profile URL": "ENSO Profile URL",
        "Open": "Open",

        "Username": "Username",
        "Password": "Password",

        "Admin login required.": "Admin login required.",
        "Logged in as admin.": "Logged in as admin.",
        "Invalid credentials.": "Invalid credentials.",
        "Logged out.": "Logged out.",
        "Player created.": "Player created.",
        "Player updated.": "Player updated.",
        "Player deleted.": "Player deleted.",

        "DB migration: added columns: {cols}": "DB migration: added columns: {cols}",
        "DB migration: nothing to do.": "DB migration: nothing to do.",
        "DB migration failed: {err}": "DB migration failed: {err}",
    },
    "bg": {
        "Karate Club": "Карате клуб",
        "Players": "Състезатели",
        "+ Add Player": "+ Добави състезател",
        "Add Player": "Добави състезател",
        "Edit Player": "Редактирай състезател",
        "Delete": "Изтрий",
        "Admin Login": "Админ вход",
        "Logout": "Изход",
        "Language": "Език",
        "BG": "BG",
        "EN": "EN",
        "All": "Всички",
        "Run DB migration": "Стартирай миграция",

        "Search": "Търсене",
        "Belt": "Колан",
        "Discipline": "Дисциплина",
        "Active": "Активен",
        "Inactive": "Неактивен",
        "Apply": "Приложи",
        "Reset": "Изчисти",
        "Export CSV": "Експорт CSV",
        "Name": "Име",
        "Email": "Имейл",
        "Phone": "Телефон",
        "Yes": "Да",
        "No": "Не",
        "No players found.": "Няма намерени състезатели.",
        "No photo uploaded": "Няма качена снимка",

        "First Name": "Име",
        "Last Name": "Фамилия",
        "Gender": "Пол",
        "Birthdate": "Дата на раждане",
        "Belt Rank": "Колан",
        "Weight (kg)": "Тегло (кг)",
        "Height (cm)": "Ръст (см)",
        "Join Date": "Дата на присъединяване",
        "Active Member": "Активен член",
        "Notes": "Бележки",
        "Photo (jpg/png/gif/webp, ≤ 2MB)": "Снимка (jpg/png/gif/webp, ≤ 2MB)",
        "Save": "Запази",
        "Cancel": "Откажи",
        "Joined": "Присъединяване",

        "—": "—",
        "Male": "Мъж",
        "Female": "Жена",
        "Other": "Друго",

        "White": "Бял",
        "Yellow": "Жълт",
        "Orange": "Оранжев",
        "Green": "Зелен",
        "Blue": "Син",
        "Purple": "Лилав",
        "Brown": "Кафяв",
        "Black": "Черен",

        "Kata": "Ката",
        "Kumite": "Кумите",
        "Both": "И двете",

        "Sportdata": "Sportdata",
        "Sportdata Profiles": "Sportdata профили",
        "WKF Profile URL": "WKF профил (URL)",
        "BNFK Profile URL": "BNFK профил (URL)",
        "ENSO Profile URL": "ENSO профил (URL)",
        "Open": "Отвори",

        "Username": "Потребител",
        "Password": "Парола",

        "Admin login required.": "Необходим е администраторски вход.",
        "Logged in as admin.": "Влязохте като администратор.",
        "Invalid credentials.": "Невалидни данни за вход.",
        "Logged out.": "Излязохте.",
        "Player created.": "Състезателят е създаден.",
        "Player updated.": "Състезателят е обновен.",
        "Player deleted.": "Състезателят е изтрит.",

        "DB migration: added columns: {cols}": "Миграция: добавени колони: {cols}",
        "DB migration: nothing to do.": "Миграция: няма какво да се прави.",
        "DB migration failed: {err}": "Миграция: грешка: {err}",
    },
}

def _(key: str) -> str:
    lang = get_lang()
    return translations.get(lang, translations["en"]).get(key, key)

# Canonical values (stored in DB)
BELT_VALUES = ["White", "Yellow", "Orange", "Green", "Blue", "Purple", "Brown", "Black"]
DISCIPLINE_VALUES = ["Kata", "Kumite", "Both"]
GENDER_VALUES = ["Male", "Female", "Other"]

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

    # Sportdata profile URLs (optional)
    sportdata_wkf_url = db.Column(db.String(255), nullable=True)
    sportdata_bnfk_url = db.Column(db.String(255), nullable=True)
    sportdata_enso_url = db.Column(db.String(255), nullable=True)

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

# -----------------------------
# Forms
# -----------------------------
class PlayerForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    gender = SelectField("Gender", validators=[VOptional()])
    birthdate = DateField("Birthdate", validators=[VOptional()])

    belt_rank = SelectField("Belt Rank", validators=[DataRequired()])
    discipline = SelectField("Discipline", validators=[DataRequired()])
    weight_kg = IntegerField("Weight (kg)", validators=[VOptional(), NumberRange(min=0, max=500)])
    height_cm = IntegerField("Height (cm)", validators=[VOptional(), NumberRange(min=0, max=300)])

    email = StringField("Email", validators=[VOptional(), Email(), Length(max=120)])
    phone = StringField("Phone", validators=[VOptional(), Length(max=40)])

    join_date = DateField("Join Date", validators=[VOptional()])
    active_member = BooleanField("Active Member", default=True)

    notes = TextAreaField("Notes", validators=[VOptional(), Length(max=5000)])

    # Sportdata URLs
    sportdata_wkf_url = StringField("WKF Profile URL", validators=[VOptional(), URL(), Length(max=255)])
    sportdata_bnfk_url = StringField("BNFK Profile URL", validators=[VOptional(), URL(), Length(max=255)])
    sportdata_enso_url = StringField("ENSO Profile URL", validators=[VOptional(), URL(), Length(max=255)])

    submit = SubmitField("Save")

def set_localized_choices(form: PlayerForm):
    """Set localized labels while keeping canonical values."""
    form.belt_rank.choices = [(v, _(v)) for v in BELT_VALUES]
    form.discipline.choices = [(v, _(v)) for v in DISCIPLINE_VALUES]
    form.gender.choices = [("", _("—"))] + [(v, _(v)) for v in GENDER_VALUES]

# -----------------------------
# Helpers
# -----------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            flash(_("Admin login required."), "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

# -----------------------------
# Context processors
# -----------------------------
@app.context_processor
def inject_i18n():
    return dict(_=_, current_lang=get_lang())

@app.context_processor
def utility_processor():
    def safe_url_for(endpoint, **values):
        try:
            return url_for(endpoint, **values)
        except BuildError:
            return None
    return dict(safe_url_for=safe_url_for)

# -----------------------------
# Routes
# -----------------------------
@app.route("/lang/<lang_code>")
def set_language(lang_code: str):
    if lang_code not in ("en", "bg"):
        lang_code = "en"
    session["lang"] = lang_code
    next_url = request.args.get("next") or request.referrer or url_for("list_players")
    return redirect(next_url)

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
        query = query.filter(or_(Player.first_name.ilike(like), Player.last_name.ilike(like)))

    if belt:
        query = query.filter_by(belt_rank=belt)

    if active == "yes":
        query = query.filter_by(active_member=True)
    elif active == "no":
        query = query.filter_by(active_member=False)

    players = query.order_by(Player.last_name.asc(), Player.first_name.asc()).all()
    return render_template(
        "players_list.html",
        players=players, q=q, belt=belt, active=active,
        belts=BELT_VALUES
    )

@app.route("/players/<int:player_id>")
def player_detail(player_id: int):
    player = Player.query.get_or_404(player_id)
    return render_template("player_detail.html", player=player)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)

# -------- Admin & Auth ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("list_players")
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["is_admin"] = True
            flash(_("Logged in as admin."), "success")
            # Avoid redirect-loop: if next points back to /login, go home
            if next_url.endswith("/login") or next_url.startswith("/login?"):
                next_url = url_for("list_players")
            return redirect(next_url)
        flash(_("Invalid credentials."), "danger")
    return render_template("login.html", next_url=next_url)

@app.route("/logout")
def logout():
    session.pop("is_admin", None)
    flash(_("Logged out."), "info")
    return redirect(url_for("list_players"))

# -------- CRUD ----------
@app.route("/admin/players/new", methods=["GET", "POST"])
@admin_required
def create_player():
    form = PlayerForm()
    set_localized_choices(form)
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
            sportdata_wkf_url=form.sportdata_wkf_url.data or None,
            sportdata_bnfk_url=form.sportdata_bnfk_url.data or None,
            sportdata_enso_url=form.sportdata_enso_url.data or None,
        )
        # handle optional photo upload
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

        db.session.add(player)
        db.session.commit()
        flash(_("Player created."), "success")
        return redirect(url_for("list_players"))
    return render_template("player_form.html", form=form, title=_("Add Player"))

@app.route("/admin/players/<int:player_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_player(player_id: int):
    player = Player.query.get_or_404(player_id)
    form = PlayerForm(obj=player)
    set_localized_choices(form)
    if form.validate_on_submit():
        form.populate_obj(player)
        # normalize to None if empty
        player.sportdata_wkf_url = form.sportdata_wkf_url.data or None
        player.sportdata_bnfk_url = form.sportdata_bnfk_url.data or None
        player.sportdata_enso_url = form.sportdata_enso_url.data or None

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
        flash(_("Player updated."), "success")
        return redirect(url_for("player_detail", player_id=player.id))
    return render_template("player_form.html", form=form, title=_("Edit Player"))

@app.route("/admin/players/<int:player_id>/delete", methods=["POST"])
@admin_required
def delete_player(player_id: int):
    player = Player.query.get_or_404(player_id)
    if player.photo_filename:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, player.photo_filename))
        except FileNotFoundError:
            pass
    db.session.delete(player)
    db.session.commit()
    flash(_("Player deleted."), "info")
    return redirect(url_for("list_players"))

# -------- Export ----------
@app.route("/export/csv")
def export_csv():
    players = Player.query.order_by(Player.last_name.asc(), Player.first_name.asc()).all()

    def generate():
        yield "id,first_name,last_name,belt_rank,discipline,active_member,email,phone,sportdata_wkf_url,sportdata_bnfk_url,sportdata_enso_url\n"
        for p in players:
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
                esc(p.sportdata_wkf_url or ""),
                esc(p.sportdata_bnfk_url or ""),
                esc(p.sportdata_enso_url or ""),
            ]
            yield ",".join(row) + "\n"

    headers = {"Content-Disposition": 'attachment; filename=\"karate_players.csv\"'}
    return Response(generate(), mimetype="text/csv", headers=headers)

# -------- Admin migration (idempotent) ----------
@app.route("/admin/migrate")
@admin_required
def migrate():
    """
    Adds columns sportdata_wkf_url, sportdata_bnfk_url, sportdata_enso_url if missing.
    Safe to run multiple times.
    """
    try:
        with db.engine.begin() as conn:
            result = conn.execute(text("PRAGMA table_info(player)"))
            existing_cols = {row[1] for row in result}  # row[1] is column name

            to_add = []
            if "sportdata_wkf_url" not in existing_cols:
                to_add.append(("sportdata_wkf_url", "VARCHAR(255)"))
            if "sportdata_bnfk_url" not in existing_cols:
                to_add.append(("sportdata_bnfk_url", "VARCHAR(255)"))
            if "sportdata_enso_url" not in existing_cols:
                to_add.append(("sportdata_enso_url", "VARCHAR(255)"))

            for name, coltype in to_add:
                conn.execute(text(f"ALTER TABLE player ADD COLUMN {name} {coltype}"))

        if to_add:
            added = ", ".join([name for name, _ in to_add])
            flash(_("DB migration: added columns: {cols}").format(cols=added), "success")
        else:
            flash(_("DB migration: nothing to do."), "info")
    except Exception as e:
        flash(_("DB migration failed: {err}").format(err=str(e)), "danger")

    return redirect(url_for("list_players"))

# -----------------------------
# Startup DB init + auto-migrate
# -----------------------------
def auto_migrate_sportdata_columns():
    """Ensure Sportdata columns exist. Safe to run multiple times."""
    with db.engine.begin() as conn:
        result = conn.execute(text("PRAGMA table_info(player)"))
        existing_cols = {row[1] for row in result}

        to_add = []
        if "sportdata_wkf_url" not in existing_cols:
            to_add.append(("sportdata_wkf_url", "VARCHAR(255)"))
        if "sportdata_bnfk_url" not in existing_cols:
            to_add.append(("sportdata_bnfk_url", "VARCHAR(255)"))
        if "sportdata_enso_url" not in existing_cols:
            to_add.append(("sportdata_enso_url", "VARCHAR(255)"))

        for name, coltype in to_add:
            conn.execute(text(f"ALTER TABLE player ADD COLUMN {name} {coltype}"))

with app.app_context():
    db.create_all()
    try:
        auto_migrate_sportdata_columns()
    except Exception as e:
        app.logger.exception("Auto-migrate failed: %s", e)

# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    # Tip: in dev, set FLASK_DEBUG=1 (Linux/macOS) or $env:FLASK_DEBUG=1 (PowerShell)
    app.run(host="0.0.0.0", port=5000)