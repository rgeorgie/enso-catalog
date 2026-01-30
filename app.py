# app.py
import os
import json
import calendar
from datetime import date, datetime
from functools import wraps
from typing import Optional, Tuple

from flask import (
    Flask, render_template, request, redirect, url_for, flash, abort,
    send_from_directory, session, Response
)
    # ^ 'abort' imported but unused; kept for parity with your codebase
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from wtforms import (
    StringField, SelectField, DateField, IntegerField,
    TextAreaField, SubmitField, BooleanField, SelectMultipleField
)
from wtforms.validators import DataRequired, Email, Optional as VOptional, Length, NumberRange, URL
from sqlalchemy import or_, and_, text
from werkzeug.routing import BuildError

# -----------------------------
# Config
# -----------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
STATIC_IMG = os.path.join(BASE_DIR, "static", "img")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_IMG, exist_ok=True)

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
# i18n (BG default)
# -----------------------------
def get_lang() -> str:
    return session.get("lang", "bg")

translations = {
    "en": {
        # --- Navigation / Common ---
        "Team ENSO": "Team ENSO",
        "Karate Club": "Karate Club",
        "Players": "Players",
        "Calendar": "Calendar",
        "Fees Report": "Fees Report",
        "Event List": "Event List",
        "+ Add Player": "+ Add Player",
        "Add Player": "Add Player",
        "Edit Player": "Edit Player",
        "Back": "Back",
        "Edit": "Edit",
        "Run DB migration": "Run DB migration",
        "Admin Login": "Admin Login",
        "Logout": "Logout",
        "Language": "Language",
        "BG": "BG", "EN": "EN",
        "All": "All",

        # --- Filters / Table headers ---
        "Search": "Search",
        "Belt": "Belt",
        "Belt Color": "Belt Color",
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
        "yes": "yes",
        "no": "no",
        "No players found.": "No players found.",
        "No photo uploaded": "No photo uploaded",

        # --- Player form / Profile ---
        "First Name": "First Name",
        "Last Name": "Last Name",
        "Gender": "Gender",
        "Birthdate": "Birthdate",
        "Belt Rank": "Belt Rank",
        "Grade Level": "Grade Level",
        "Grade Date": "Grade Date",
        "Weight (kg)": "Weight (kg)",
        "Height (cm)": "Height (cm)",
        "Join Date": "Join Date",
        "Active Member": "Active Member",
        "Notes": "Notes",
        "Photo (jpg/png/gif/webp, ≤ 2MB)": "Photo (jpg/png/gif/webp, ≤ 2MB)",
        "Save": "Save",
        "Cancel": "Cancel",
        "Joined": "Joined",
        "Mother Name": "Mother Name",
        "Mother Phone": "Mother Phone",
        "Father Name": "Father Name",
        "Father Phone": "Father Phone",
        "Profile": "Profile",
        "Contacts": "Contacts",
        "Fee": "Fee",
        "Fee (EUR)": "Fee (EUR)",

        # --- Health / Insurance ---
        "Medical Examination": "Medical Examination",
        "Examination Date": "Examination Date",
        "Expiry Date": "Expiry Date",
        "Insurance Expiry Date": "Insurance Expiry Date",
        "Expired": "Expired",
        "Expires in {d}d": "Expires in {d}d",
        "Valid until {dt}": "Valid until {dt}",
        "Health": "Health",
        "Health & Insurance": "Health & Insurance",

        # --- Fees / Monthly ---
        "Training Fee (EUR)": "Training Fee (EUR)",
        "Monthly Fee Type": "Training fee",
        "Is Monthly (not per session)": "Is Monthly (not per session)",
        "monthly": "monthly",
        "per session": "per session",
        "Month": "Month",
        "Session": "Session",
        "Due date": "Due date",
        "Amount": "Amount",
        "Paid": "Paid",
        "Unpaid": "Unpaid",
        "Toggle Paid": "Toggle Paid",
        "Nothing to show.": "Nothing to show.",
        "Payment toggled.": "Payment toggled.",
        "Monthly Due": "Monthly Due",
        "No payments recorded.": "No payments recorded.",
        "Due Fees": "Due Fees",
        "Status": "Status",
        "Already paid": "Already paid",
        "Due": "Due",
        "Training (Monthly)": "Training (Monthly)",
        "Training (Per-session)": "Training (Per-session)",
        "Sessions paid": "Sessions paid",
        "Sessions taken": "Sessions taken",
        "Remaining sessions": "Remaining sessions",
        "Overused by": "Overused by",
        "Prepaid amount": "Prepaid amount",
        "Per-session price": "Per-session price",
        "Owed amount": "Owed amount",
        "Cost for sessions taken": "Cost for sessions taken",
        "Owed (cost - prepaid)": "Owed (cost - prepaid)",
        "Print Due Fees": "Print Due Fees",
        "Save & Print": "Save & Print",
        "YYYY-MM": "YYYY-MM",
        "Leave empty for current month": "Leave empty for current month",

        # --- Payments / Receipts UI ---
        "Payment Receipt": "Payment Receipt",
        "Date": "Date",
        "Player": "Player",
        "ID": "ID",
        "Category": "Category",
        "Training fee": "Training fee",
        "Plan": "Plan",
        "Per month": "Per month",
        "Per session": "Per session",
        "Sessions": "Sessions",
        "taken": "taken",
        "paid": "paid",
        "Event": "Event",
        "Record payment": "Record payment",
        "Record payment for this debt": "Record payment for this debt",
        "Open payment form": "Open payment form",
        "Receipt": "Receipt",
        "Amount (EUR)": "Amount (EUR)",
        "Note": "Note",
        "Created": "Created",
        "Quick actions": "Quick actions",
        "Training sessions": "Training sessions",
        "Actions":"Actions",
        "New Training Receipt (per month)": "New Training Receipt (per month)",
        "New Training Receipt (per session)": "New Training Receipt (per session)",
        "New Event Receipt": "New Event Receipt",
        "Pay Monthly Dues": "Pay Monthly Dues",
        "Pay Event Fees": "Pay Event Fees",
        "Pay Session Debts": "Pay Session Debts",
        "Pay All Dues": "Pay All Dues",
        "View": "View",
        "Mark session taken": "Mark session taken",
        "Toggle paid": "Toggle paid",
        "New receipt": "New receipt",
        "Recent Event Registrations": "Recent Event Registrations",
        "No per-session receipts found.": "No per-session receipts found.",
        "Outstanding Debts": "Outstanding Debts",
        "No outstanding debts.": "No outstanding debts.",
        "Print": "Print",
        "Go to Calendar": "Go to Calendar",
        "Session receipts": "Session receipts",

        # --- Debts / Events dues ---
        "Unpaid Event Registrations": "Unpaid Event Registrations",
        "No unpaid event registrations in this month.": "No unpaid event registrations in this month.",

        # --- Sports Calendar / Events ---
        "Sports Calendar": "Sports Calendar",
        "New Event": "New Event",
        "Edit Event": "Edit Event",
        "Event": "Event",
        "Start Date": "Start Date",
        "End Date": "End Date",
        "Location": "Location",
        "Sportdata URL": "Sportdata URL",
        "Categories": "Categories",
        "Add Category": "Add Category",
        "Category Name": "Category Name",
        "Category Fee (EUR)": "Category Fee (EUR)",
        "Category Fee": "Category Fee",
        "Delete Category": "Delete Category",
        "Registrations": "Registrations",
        "Athlete": "Athlete",
        "Athlete(s)": "Athlete(s)",
        "Select Categories": "Select Categories",
        "Fee Override (EUR)": "Fee Override (EUR)",
        "Add Registration": "Add Registration",
        "Export Registrations CSV": "Export Registrations CSV",
        "Event created.": "Event created.",
        "Event updated.": "Event updated.",
        "Event deleted.": "Event deleted.",
        "Category added.": "Category added.",
        "Category deleted.": "Category deleted.",
        "Registration added.": "Registration added.",
        "Registration updated.": "Registration updated.",
        "Registration deleted.": "Registration deleted.",
        "Paid status updated.": "Paid status updated.",
        "No categories yet.": "No categories yet.",
        "No registrations yet.": "No registrations yet.",
        "All-day": "All-day",
        "Events": "Events",
        "Remove": "Remove",
        "Participants": "Participants",
        "Entries": "Entries",
        "Total expected": "Total expected",
        "Total paid": "Total paid",
        "Total unpaid": "Total unpaid",
        "override": "override",
        "computed": "computed",
        "Dates": "Dates",

        # --- Medals ---
        "Medals": "Medals",
        "Gold": "Gold",
        "Silver": "Silver",
        "Bronze": "Bronze",
        "Set medal": "Set medal",
        "None": "None",
        "Medals Report": "Medals Report",
        "Year": "Year",
        "Total": "Total",

        # --- Sportdata profiles ---
        "Sportdata": "Sportdata",
        "Sportdata Profiles": "Sportdata Profiles",
        "WKF Profile URL": "WKF Profile URL",
        "BNFK Profile URL": "BNFK Profile URL",
        "ENSO Profile URL": "ENSO Profile URL",
        "Open": "Open",

        # --- Auth / Flash ---
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

        # --- Enums / Days ---
        "—": "—",
        "Male": "Male", "Female": "Female", "Other": "Other",
        "White": "White", "Yellow": "Yellow", "Orange": "Orange",
        "Green": "Green", "Blue": "Blue", "Purple": "Purple",
        "Brown": "Brown", "Black": "Black",
        "Kata": "Kata", "Kumite": "Kumite", "Both": "Both",
        "Mon": "Mon", "Tue": "Tue", "Wed": "Wed", "Thu": "Thu", "Fri": "Fri", "Sat": "Sat", "Sun": "Sun",

        # --- Forms / Admin forms ---
        "Kind": "Kind",
        "Training (per month)": "Training (per month)",
        "Training (per session)": "Training (per session)",
        "Event Registration ID": "Event Registration ID",
        "Player ID": "Player ID",
        "Month (YYYY-MM)": "Month (YYYY-MM)",
        "Currency": "Currency",
        "Method": "Method",
    },
    "bg": {
        # --- Navigation / Common ---
        "Team ENSO": "Team ENSO",
        "Karate Club": "Карате клуб",
        "Players": "Състезатели",
        "Calendar": "Календар",
        "Fees Report": "Отчет за такси",
        "Event List": "Списък събития",
        "+ Add Player": "+ Добави състезател",
        "Add Player": "Добави състезател",
        "Edit Player": "Редакция на състезател",
        "Back": "Назад",
        "Edit": "Редакция",
        "Run DB migration": "Стартирай миграция",
        "Admin Login": "Админ вход",
        "Logout": "Изход",
        "Language": "Език",
        "BG": "BG", "EN": "EN",
        "All": "Всички",

        # --- Filters / Table headers ---
        "Search": "Търсене",
        "Belt": "Колан",
        "Belt Color": "Цвят на колана",
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
        "yes": "да",
        "no": "не",
        "No players found.": "Няма намерени състезатели.",
        "No photo uploaded": "Няма качена снимка",

        # --- Player form / Profile ---
        "First Name": "Име",
        "Last Name": "Фамилия",
        "Gender": "Пол",
        "Birthdate": "Дата на раждане",
        "Belt Rank": "Колан",
        "Grade Level": "Степен (кю/дан)",
        "Grade Date": "Дата на изпит",
        "Weight (kg)": "Тегло (кг)",
        "Height (cm)": "Ръст (см)",
        "Join Date": "Дата на присъединяване",
        "Active Member": "Активен член",
        "Notes": "Бележки",
        "Photo (jpg/png/gif/webp, ≤ 2MB)": "Снимка (jpg/png/gif/webp, ≤ 2MB)",
        "Save": "Запази",
        "Cancel": "Откажи",
        "Joined": "Присъединяване",
        "Mother Name": "Име на майката",
        "Mother Phone": "Телефон на майката",
        "Father Name": "Име на бащата",
        "Father Phone": "Телефон на бащата",
        "Actions":"Действия",
        "Profile": "Профил",
        "Contacts": "Контакти",
        "Fee": "Такса",
        "Fee (EUR)": "Такса (EUR)",

        # --- Health / Insurance ---
        "Medical Examination": "Медицински преглед",
        "Examination Date": "Дата на преглед",
        "Expiry Date": "Валидност до",
        "Insurance Expiry Date": "Срок на застраховка",
        "Expired": "Изтекла",
        "Expires in {d}d": "Изтича след {d} дни",
        "Valid until {dt}": "Валидна до {dt}",
        "Health": "Здраве",
        "Health & Insurance": "Здраве и застраховка",

        # --- Fees / Monthly ---
        "Training Fee (EUR)": "Такса за тренировка (EUR)",
        "Monthly Fee Type": "Такса за тренировка",
        "Is Monthly (not per session)": "Месечна (не на тренировка)",
        "monthly": "месечно",
        "per session": "на тренировка",
        "Month": "Месец",
        "Session": "Сесия",
        "Due date": "Падеж",
        "Amount": "Сума",
        "Paid": "Платено",
        "Unpaid": "Неплатено",
        "Toggle Paid": "Смени статус",
        "Nothing to show.": "Няма данни.",
        "Payment toggled.": "Плащането е променено.",
        "Monthly Due": "Месечна такса",
        "No payments recorded.": "Няма записани плащания.",
        "Due Fees": "Дължими такси",
        "Status": "Статус",
        "Already paid": "Вече платено",
        "Due": "Дължимо",
        "Training (Monthly)": "Тренировка (месечно)",
        "Training (Per-session)": "Тренировка (на тренировка)",
        "Sessions paid": "Платени тренировки",
        "Sessions taken": "Взети тренировки",
        "Remaining sessions": "Оставащи тренировки",
        "Overused by": "Надвишени с",
        "Prepaid amount": "Предплатена сума",
        "Per-session price": "Цена на тренировка",
        "Owed amount": "Дължима сума",
        "Cost for sessions taken": "Стойност на взетите тренировки",
        "Owed (cost - prepaid)": "Дължима сума (стойност − предплатено)",
        "Print Due Fees": "Принтирай дължими такси",
        "Save & Print": "Запази и принтирай",
        "YYYY-MM": "ГГГГ-ММ",
        "Leave empty for current month": "Остави празно за текущия месец",

        # --- Payments / Receipts UI ---
        "Payment Receipt": "Квитанция за плащане",
        "Date": "Дата",
        "Player": "Състезател",
        "ID": "ID",
        "Category": "Категория",
        "Training fee": "Такса за тренировка",
        "Plan": "План",
        "Per month": "Месечно",
        "Per session": "На тренировка",
        "Sessions": "Тренировки",
        "taken": "взети",
        "paid": "платени",
        "Event": "Събитие",
        "Record payment": "Запиши плащане",
        "Record payment for this debt": "Запиши плащане за този дълг",
        "Open payment form": "Отвори форма за плащане",
        "Receipt": "Квитанция",
        "Amount (EUR)": "Сума (EUR)",
        "Note": "Бележка",
        "Created": "Създадено",
        "Quick actions": "Бързи действия",
        "Training sessions": "Тренировъчни сесии",
        "New Training Receipt (per month)": "Нова квитанция за тренировка (месечно)",
        "New Training Receipt (per session)": "Нова квитанция за тренировка (на тренировка)",
        "New Event Receipt": "Нова квитанция за събитие",
        "Pay Monthly Dues": "Плати месечна такса",
        "Pay Event Fees": "Плати такса за събитие",
        "Pay Session Debts": "Плати дължими тренировки",
        "Pay All Dues": "Плати всички дължими",
        "View": "Виж",
        "Mark session taken": "Отбележи взета тренировка",
        "Toggle paid": "Смени статус",
        "New receipt": "Нова квитанция",
        "Recent Event Registrations": "Последни записвания за събития",
        "No per-session receipts found.": "Няма намерени квитанции за тренировки.",
        "Outstanding Debts": "Неплатени задължения",
        "No outstanding debts.": "Няма неплатени задължения.",
        "Print": "Принтирай",
        "Go to Calendar": "Към календара",
        "Session receipts": "Квитанции за тренировки",

        # --- Debts / Events dues ---
        "Unpaid Event Registrations": "Неплатени записвания за събития",
        "No unpaid event registrations in this month.": "Няма неплатени записвания за този месец.",

        # --- Sports Calendar / Events ---
        "Sports Calendar": "Спортен календар",
        "New Event": "Ново събитие",
        "Edit Event": "Редакция на събитие",
        "Event": "Събитие",
        "Start Date": "Начална дата",
        "End Date": "Крайна дата",
        "Location": "Локация",
        "Sportdata URL": "Sportdata URL",
        "Categories": "Категории",
        "Add Category": "Добави категория",
        "Category Name": "Име на категория",
        "Category Fee (EUR)": "Такса за категория (EUR)",
        "Category Fee": "Такса за категория",
        "Delete Category": "Изтрий категория",
        "Registrations": "Записвания",
        "Athlete": "Състезател",
        "Athlete(s)": "Състезател(и)",
        "Select Categories": "Избери категории",
        "Fee Override (EUR)": "Ръчна такса (EUR)",
        "Add Registration": "Добави записване",
        "Export Registrations CSV": "Експорт CSV (записвания)",
        "Event created.": "Събитието е създадено.",
        "Event updated.": "Събитието е обновено.",
        "Event deleted.": "Събитието е изтрито.",
        "Category added.": "Категорията е добавена.",
        "Category deleted.": "Категорията е изтрита.",
        "Registration added.": "Записването е добавено.",
        "Registration updated.": "Записването е обновено.",
        "Registration deleted.": "Записването е изтрито.",
        "Paid status updated.": "Статусът е обновен.",
        "No categories yet.": "Няма категории.",
        "No registrations yet.": "Няма записвания.",
        "All-day": "Целодневно",
        "Events": "Събития",
        "Remove": "Премахни",
        "Participants": "Състезатели",
        "Entries": "Записи",
        "Total expected": "Общо очаквано",
        "Total paid": "Общо платено",
        "Total unpaid": "Общо неплатено",
        "override": "override",
        "computed": "computed",
        "Dates": "Дати",

        # --- Medals ---
        "Medals": "Медали",
        "Gold": "Злато",
        "Silver": "Сребро",
        "Bronze": "Бронз",
        "Set medal": "Задай медал",
        "None": "Няма",
        "Medals Report": "Отчет за медали",
        "Year": "Година",
        "Total": "Общо",

        # --- Sportdata profiles ---
        "Sportdata": "Sportdata",
        "Sportdata Profiles": "Sportdata профили",
        "WKF Profile URL": "WKF профил (URL)",
        "BNFK Profile URL": "BNFK профил (URL)",
        "ENSO Profile URL": "ENSO профил (URL)",
        "Open": "Отвори",

        # --- Auth / Flash ---
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

        # --- Enums / Days ---
        "—": "—",
        "Male": "Мъж", "Female": "Жена", "Other": "Друго",
        "White": "Бял", "Yellow": "Жълт", "Orange": "Оранжев",
        "Green": "Зелен", "Blue": "Син", "Purple": "Лилав",
        "Brown": "Кафяв", "Black": "Черен",
        "Kata": "Ката", "Kumite": "Кумите", "Both": "И двете",
        "Mon": "Пон", "Tue": "Вт", "Wed": "Ср", "Thu": "Чет", "Fri": "Пет", "Sat": "Съб", "Sun": "Нед",

        # --- Forms / Admin forms ---
        "Kind": "Вид",
        "Training (per month)": "Тренировка (месечно)",
        "Training (per session)": "Тренировка (на тренировка)",
        "Event Registration ID": "ID на записване за събитие",
        "Player ID": "ID на състезател",
        "Month (YYYY-MM)": "Месец (ГГГГ-ММ)",
        "Currency": "Валута",
        "Method": "Метод",
    },
}

def _(key: str) -> str:
    lang = get_lang()
    return translations.get(lang, translations["en"]).get(key, key)

# -----------------------------
# Grading scheme & belt palette
# -----------------------------
GRADING_SCHEME = {
    "grades": [
        "10 kyu", "9 kyu", "8 kyu", "7 kyu", "6 kyu",
        "5 kyu", "4 kyu", "3 kyu", "2 kyu", "1 kyu",
        "1 dan", "2 dan", "3 dan", "4 dan", "5 dan",
    ],
    "belt_colors": ["White", "Yellow", "Orange", "Green", "Blue", "Purple", "Brown", "Black"],
    "grade_to_color": {
        "10 kyu": "White",
        "9 kyu": "White",
        "8 kyu": "Yellow",
        "7 kyu": "Orange",
        "6 kyu": "Green",
        "5 kyu": "Blue",
        "4 kyu": "Purple",
        "3 kyu": "Brown",
        "2 kyu": "Brown",
        "1 kyu": "Brown",
        "1 dan": "Black",
        "2 dan": "Black",
        "3 dan": "Black",
        "4 dan": "Black",
        "5 dan": "Black",
    },
}

BELT_PALETTE = {
    "White":  "#f8f9fa",
    "Yellow": "#ffd60a",
    "Orange": "#ff7f11",
    "Green":  "#2dc653",
    "Blue":   "#228be6",
    "Purple": "#9c36b5",
    "Brown":  "#8d5524",
    "Black":  "#111111",
}

DISCIPLINE_VALUES = ["Kata", "Kumite", "Both"]
GENDER_VALUES = ["Male", "Female", "Other"]

# -----------------------------
# Helpers
# -----------------------------
def belt_hex(belt: Optional[str]) -> str:
    return BELT_PALETTE.get(belt or "", "#6c757d")

def ideal_text_color(bg_hex: str) -> str:
    try:
        c = bg_hex.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        yiq = (r * 299 + g * 587 + b * 114) / 1000
        return "#000000" if yiq >= 128 else "#ffffff"
    except Exception:
        return "#000000"

def belt_chip_style(belt: Optional[str]) -> str:
    bg = belt_hex(belt)
    fg = ideal_text_color(bg)
    return f"background:{bg};color:{fg};padding:.35rem .6rem;border-radius:999px;display:inline-block;min-width:64px;text-align:center;"

def validity_badge(exp_date: Optional[date], warn_days: int = 30) -> Tuple[str, str]:
    if not exp_date:
        return "—", "secondary"
    today = date.today()
    if exp_date < today:
        return _("Expired"), "danger"
    days = (exp_date - today).days
    if days < warn_days:
        return _("Expires in {d}d").format(d=days), "warning"
    return _("Valid until {dt}").format(dt=exp_date.isoformat()), "success"

def first_working_day(year: int, month: int) -> date:
    for d in calendar.Calendar().itermonthdates(year, month):
        if d.month == month and d.weekday() < 5:
            return d
    return date(year, month, 1)

def parse_month_str(month_str: Optional[str]) -> tuple[int, int]:
    t = date.today()
    if not month_str:
        return t.year, t.month
    try:
        y, m = month_str.split("-")
        return int(y), int(m)
    except Exception:
        return t.year, t.month

def is_auto_debt_note(note: Optional[str]) -> bool:
    """
    Treat only notes containing 'AUTO_DEBT from' as debt records (created by tick/list actions).
    This excludes 'MANUAL_OWED' or other non-debt payment notes.
    """
    n = (note or "")
    return "AUTO_DEBT from" in n

def ensure_payments_for_month(year: int, month: int) -> int:
    players = Player.query.filter_by(active_member=True).all()
    created = 0
    for p in players:
        if not p.monthly_fee_is_monthly:
            continue
        if p.monthly_fee_amount is None:
            continue
        exists = Payment.query.filter_by(player_id=p.id, year=year, month=month).first()
        if not exists:
            db.session.add(Payment(
                player_id=p.id,
                year=year,
                month=month,
                amount=p.monthly_fee_amount,
                paid=False
            ))
            created += 1
    if created:
        db.session.commit()
    return created

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
# Models
# -----------------------------
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), nullable=True)
    birthdate = db.Column(db.Date, nullable=True)

    belt_rank = db.Column(db.String(20), nullable=False, default="White")
    grade_level = db.Column(db.String(20), nullable=True)
    grade_date = db.Column(db.Date, nullable=True)

    discipline = db.Column(db.String(10), nullable=False, default="Both")
    weight_kg = db.Column(db.Integer, nullable=True)
    height_cm = db.Column(db.Integer, nullable=True)

    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(40), nullable=True)

    join_date = db.Column(db.Date, nullable=True)
    active_member = db.Column(db.Boolean, default=True)

    notes = db.Column(db.Text, nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)

    sportdata_wkf_url = db.Column(db.String(255), nullable=True)
    sportdata_bnfk_url = db.Column(db.String(255), nullable=True)
    sportdata_enso_url = db.Column(db.String(255), nullable=True)

    medical_exam_date = db.Column(db.Date, nullable=True)
    medical_expiry_date = db.Column(db.Date, nullable=True)
    insurance_expiry_date = db.Column(db.Date, nullable=True)

    # Fees (EUR)
    monthly_fee_amount = db.Column(db.Integer, nullable=True)
    monthly_fee_is_monthly = db.Column(db.Boolean, default=True)  # True: monthly; False: per session

    # Parents
    mother_name = db.Column(db.String(120), nullable=True)
    mother_phone = db.Column(db.String(40), nullable=True)
    father_name = db.Column(db.String(120), nullable=True)
    father_phone = db.Column(db.String(40), nullable=True)

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1..12
    amount = db.Column(db.Integer, nullable=True)  # EUR
    paid = db.Column(db.Boolean, default=False)
    paid_on = db.Column(db.Date, nullable=True)

    player = db.relationship("Player", backref=db.backref("payments", lazy="dynamic"))

    __table_args__ = (db.UniqueConstraint("player_id", "year", "month", name="uq_payment_player_month"),)


# ---- Sports Calendar models ----
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)  # if None, single-day
    location = db.Column(db.String(200), nullable=True)
    sportdata_url = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    categories = db.relationship("EventCategory", backref="event", cascade="all, delete-orphan", lazy="dynamic")
    registrations = db.relationship("EventRegistration", backref="event", cascade="all, delete-orphan", lazy="dynamic")

    def spans(self, d: date) -> bool:
        ed = self.end_date or self.start_date
        return self.start_date <= d <= ed

class EventCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    fee = db.Column(db.Integer, nullable=True)  # EUR

class EventRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False, index=True)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False, index=True)

    fee_override = db.Column(db.Integer, nullable=True)  # EUR
    paid = db.Column(db.Boolean, default=False)
    paid_on = db.Column(db.Date, nullable=True)

    player = db.relationship("Player", backref=db.backref("event_registrations", cascade="all, delete-orphan", lazy="dynamic"))

    # association objects (holds medal per category)
    reg_categories = db.relationship("EventRegCategory", backref="registration", cascade="all, delete-orphan", lazy="joined")

    def computed_fee(self) -> Optional[int]:
        if self.fee_override is not None:
            return self.fee_override
        total = 0
        counted = False
        for rc in self.reg_categories or []:
            if rc.category and rc.category.fee is not None:
                total += int(rc.category.fee)
                counted = True
        return total if counted else None

class EventRegCategory(db.Model):
    """Association object: one row per (registration, category) with medal."""
    __tablename__ = "event_reg_category"
    registration_id = db.Column(db.Integer, db.ForeignKey("event_registration.id"), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("event_category.id"), primary_key=True)
    medal = db.Column(db.String(10), nullable=True)  # 'gold' | 'silver' | 'bronze' | None

    category = db.relationship("EventCategory")

# -----------------------------
# PaymentRecord (generic receipts)
# -----------------------------
class PaymentRecord(db.Model):
    """
    kind: 'training_month' | 'training_session' | 'event'
    """
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(20), nullable=False)

    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False, index=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payment.id"), nullable=True, index=True)
    event_registration_id = db.Column(db.Integer, db.ForeignKey("event_registration.id"), nullable=True, index=True)

    # Training (monthly)
    year = db.Column(db.Integer, nullable=True)
    month = db.Column(db.Integer, nullable=True)  # 1..12

    # Training (per-session)
    sessions_paid = db.Column(db.Integer, default=0)
    sessions_taken = db.Column(db.Integer, default=0)

    # Money
    amount = db.Column(db.Integer, nullable=False)  # EUR
    currency = db.Column(db.String(8), nullable=False, default="EUR")
    method = db.Column(db.String(32), nullable=True)    # cash/card/bank
    note = db.Column(db.Text, nullable=True)

    # Receipt & timestamps
    receipt_no = db.Column(db.String(40), unique=True, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    player = db.relationship("Player")
    payment = db.relationship("Payment")
    event_registration = db.relationship("EventRegistration")
    related_receipt_id = db.Column(db.Integer, db.ForeignKey("payment_record.id"), nullable=True, index=True)
    related_receipt = db.relationship("PaymentRecord", remote_side=[id], backref="related_payments")

    def assign_receipt_no(self):
        if not self.id:
            return
        stamp = (self.paid_at or datetime.utcnow()).strftime("%Y%m%d")
        self.receipt_no = f"RCPT-{stamp}-{self.id:06d}"
        db.session.add(self)
        db.session.commit()

# -----------------------------
# Forms
# -----------------------------
class PlayerForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    gender = SelectField("Gender", validators=[VOptional()])
    birthdate = DateField("Birthdate", validators=[VOptional()])
    grade_level = SelectField("Grade Level", validators=[VOptional()])
    grade_date = DateField("Grade Date", validators=[VOptional()])

    discipline = SelectField("Discipline", validators=[DataRequired()])
    weight_kg = IntegerField("Weight (kg)", validators=[VOptional(), NumberRange(min=0, max=500)])
    height_cm = IntegerField("Height (cm)", validators=[VOptional(), NumberRange(min=0, max=300)])

    email = StringField("Email", validators=[VOptional(), Email(), Length(max=120)])
    phone = StringField("Phone", validators=[VOptional(), Length(max=40)])

    join_date = DateField("Join Date", validators=[VOptional()])
    active_member = BooleanField("Active Member", default=True)

    medical_exam_date = DateField("Examination Date", validators=[VOptional()])
    medical_expiry_date = DateField("Expiry Date", validators=[VOptional()])
    insurance_expiry_date = DateField("Insurance Expiry Date", validators=[VOptional()])

    monthly_fee_amount = IntegerField("Training Fee (EUR)", validators=[VOptional(), NumberRange(min=0, max=10000)])
    monthly_fee_is_monthly = BooleanField("Is Monthly (not per session)", default=True)

    mother_name = StringField("Mother Name", validators=[VOptional(), Length(max=120)])
    mother_phone = StringField("Mother Phone", validators=[VOptional(), Length(max=40)])
    father_name = StringField("Father Name", validators=[VOptional(), Length(max=120)])
    father_phone = StringField("Father Phone", validators=[VOptional(), Length(max=40)])

    notes = TextAreaField("Notes", validators=[VOptional(), Length(max=5000)])

    sportdata_wkf_url = StringField("WKF Profile URL", validators=[VOptional(), URL(), Length(max=255)])
    sportdata_bnfk_url = StringField("BNFK Profile URL", validators=[VOptional(), URL(), Length(max=255)])
    sportdata_enso_url = StringField("ENSO Profile URL", validators=[VOptional(), URL(), Length(max=255)])

    submit = SubmitField("Save")

class EventForm(FlaskForm):
    title = StringField("Event", validators=[DataRequired(), Length(max=200)])
    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[VOptional()])
    location = StringField("Location", validators=[VOptional(), Length(max=200)])
    sportdata_url = StringField("Sportdata URL", validators=[VOptional(), URL(), Length(max=255)])
    notes = TextAreaField("Notes", validators=[VOptional(), Length(max=5000)])
    submit = SubmitField("Save")

class EventCategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(max=120)])
    fee = IntegerField("Category Fee (EUR)", validators=[VOptional(), NumberRange(min=0, max=100000)])
    submit = SubmitField("Save")

class EventRegistrationForm(FlaskForm):
    player_ids = SelectMultipleField("Athlete", coerce=int, validators=[DataRequired()])
    category_ids = SelectMultipleField("Select Categories", coerce=int, validators=[VOptional()])
    fee_override = IntegerField("Fee Override (EUR)", validators=[VOptional(), NumberRange(min=0, max=100000)])
    paid = BooleanField("Paid", default=False)
    submit = SubmitField("Add Registration")

def set_localized_choices(form: PlayerForm):
    form.grade_level.choices = [(g, g) for g in GRADING_SCHEME["grades"]]
    form.discipline.choices = [(v, _(v)) for v in DISCIPLINE_VALUES]
    form.gender.choices = [("", _("—"))] + [(v, _(v)) for v in GENDER_VALUES]

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
    return dict(
        safe_url_for=safe_url_for,
        belt_chip_style=belt_chip_style,
        validity_badge=validity_badge,
        first_working_day=first_working_day,
        EventRegistration=EventRegistration,
        EventRegCategory=EventRegCategory,
    )

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
    month_str = request.args.get("month")

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

    if month_str:
        y, m = parse_month_str(month_str)
    else:
        t = date.today()
        y, m = t.year, t.month
    ensure_payments_for_month(y, m)
    month_year = (y, m)

    for p in players:
        sess_records = (PaymentRecord.query
                        .filter_by(player_id=p.id, kind='training_session')
                        .order_by(PaymentRecord.paid_at.desc())
                        .all())

        # exclude only true AUTO_DEBT (not MANUAL_OWED)
        sess_receipts = [r for r in sess_records if not is_auto_debt_note(r.note)]

        explicit_sessions_paid = sum((r.sessions_paid or 0) for r in sess_receipts)
        total_prepaid_amount = sum((r.amount or 0) for r in sess_receipts)

        # per-session price only from profile
        per_session_price = None
        if p.monthly_fee_amount is not None and not p.monthly_fee_is_monthly:
            per_session_price = float(p.monthly_fee_amount)

        # infer sessions_paid from amounts only when price is known
        inferred_sessions_paid = 0
        if per_session_price:
            for r in sess_receipts:
                if (r.sessions_paid or 0) == 0 and (r.amount or 0) > 0:
                    try:
                        inferred_sessions_paid += int(round(float(r.amount) / float(per_session_price)))
                    except Exception:
                        pass
        total_sessions_paid = explicit_sessions_paid + inferred_sessions_paid

        # total taken is stored sum (tracking/ticked receipts)
        total_sessions_taken = sum((r.sessions_taken or 0) for r in sess_records)

        prepaid_credit = float(total_prepaid_amount)
        expected_cost = owed_amount = None
        if per_session_price is not None:
            expected_cost = total_sessions_taken * per_session_price
            owed_amount = expected_cost - prepaid_credit

        p.total_sessions_paid = total_sessions_paid
        p.total_sessions_taken = total_sessions_taken
        p.total_prepaid_amount = total_prepaid_amount
        p.prepaid_credit = int(round(prepaid_credit)) if prepaid_credit is not None else None
        p.per_session_price = per_session_price
        p.expected_cost = expected_cost
        p.owed_amount = int(round(owed_amount)) if owed_amount is not None else None

        # debts shown from true auto-debt only
        try:
            debts_all = (PaymentRecord.query
                         .filter(PaymentRecord.player_id == p.id)
                         .filter(PaymentRecord.note.like('%AUTO_DEBT%'))
                         .all())
            outstanding = [d for d in debts_all if is_auto_debt_note(d.note) and 'AUTO_DEBT_PAID' not in (d.note or '')]
            recorded_debt_total = sum((d.amount or 0) for d in outstanding)
        except Exception:
            recorded_debt_total = 0

        expected_owed = p.owed_amount or 0
        p.debt_total_recorded = int(recorded_debt_total)
        p.debt_total_expected = int(expected_owed)
        p.has_debt = bool(recorded_debt_total or (expected_owed and expected_owed > 0))

        # monthly dues
        p.monthly_due_amount = None
        p.monthly_due_paid = None
        if month_year:
            yy, mm = month_year
            pay_row = Payment.query.filter_by(player_id=p.id, year=yy, month=mm).first()
            if pay_row:
                p.monthly_due_amount = pay_row.amount or 0
                p.monthly_due_paid = bool(pay_row.paid)

    return render_template(
        "players_list.html",
        players=players, q=q, belt=belt, active=active,
        belts=GRADING_SCHEME["belt_colors"]
    )

@app.route("/players/<int:player_id>")
def player_detail(player_id: int):
    player = Player.query.get_or_404(player_id)
    today = date.today()
    try:
        ensure_payments_for_month(today.year, today.month)
    except Exception:
        pass

    current_payment = Payment.query.filter_by(player_id=player.id, year=today.year, month=today.month).first()
    regs = (EventRegistration.query
            .filter_by(player_id=player.id)
            .join(Event)
            .order_by(Event.start_date.desc())
            .all())

    sess_records_all = (PaymentRecord.query
                        .filter_by(player_id=player.id, kind='training_session')
                        .order_by(PaymentRecord.paid_at.desc())
                        .all())

    payment_count = db.session.query(PaymentRecord).filter_by(player_id=player.id).count()

    sess_receipts = [r for r in sess_records_all if not is_auto_debt_note(r.note)]
    explicit_sessions_paid = sum((r.sessions_paid or 0) for r in sess_receipts)
    total_prepaid_amount = sum((r.amount or 0) for r in sess_receipts)

    per_session_price = None
    if player.monthly_fee_amount is not None and not player.monthly_fee_is_monthly:
        per_session_price = float(player.monthly_fee_amount)

    inferred_sessions_paid = 0
    if per_session_price:
        for r in sess_receipts:
            if (r.sessions_paid or 0) == 0 and (r.amount or 0) > 0:
                try:
                    inferred_sessions_paid += int(round(float(r.amount) / float(per_session_price)))
                except Exception:
                    pass
    total_sessions_paid = explicit_sessions_paid + inferred_sessions_paid

    total_sessions_taken = sum((r.sessions_taken or 0) for r in sess_records_all)

    prepaid_credit = float(total_prepaid_amount)
    expected_cost = owed_amount = None
    if per_session_price is not None:
        expected_cost = total_sessions_taken * per_session_price
        owed_amount = expected_cost - prepaid_credit

    return render_template(
        "player_detail.html",
        player=player,
        current_payment=current_payment,
        regs=regs,
        sess_records=sess_records_all,
        total_sessions_paid=total_sessions_paid,
        total_sessions_taken=total_sessions_taken,
        total_prepaid_amount=total_prepaid_amount,
        prepaid_credit=int(round(prepaid_credit)) if prepaid_credit is not None else None,
        per_session_amount=per_session_price,
        expected_cost=expected_cost,
        owed_amount=int(round(owed_amount)) if owed_amount is not None else None,
        payment_count=payment_count,
    )

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)

# -------- Auth ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("list_players")
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["is_admin"] = True
            flash(_("Logged in as admin."), "success")
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

# -------- CRUD Players ----------
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
            grade_level=form.grade_level.data or None,
            grade_date=form.grade_date.data,
            discipline=form.discipline.data,
            weight_kg=form.weight_kg.data,
            height_cm=form.height_cm.data,
            email=form.email.data,
            phone=form.phone.data,
            join_date=form.join_date.data,
            active_member=bool(form.active_member.data),

            medical_exam_date=form.medical_exam_date.data,
            medical_expiry_date=form.medical_expiry_date.data,
            insurance_expiry_date=form.insurance_expiry_date.data,

            monthly_fee_amount=form.monthly_fee_amount.data,
            monthly_fee_is_monthly=bool(form.monthly_fee_is_monthly.data),

            mother_name=form.mother_name.data or None,
            mother_phone=form.mother_phone.data or None,
            father_name=form.father_name.data or None,
            father_phone=form.father_phone.data or None,

            sportdata_wkf_url=form.sportdata_wkf_url.data or None,
            sportdata_bnfk_url=form.sportdata_bnfk_url.data or None,
            sportdata_enso_url=form.sportdata_enso_url.data or None,
        )

        if player.grade_level and player.grade_level in GRADING_SCHEME["grade_to_color"]:
            player.belt_rank = GRADING_SCHEME["grade_to_color"][player.grade_level]

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

    return render_template(
        "player_form.html",
        form=form,
        title=_("Add Player"),
        belt_colors_json=json.dumps(BELT_PALETTE),
        grade_to_color_json=json.dumps(GRADING_SCHEME.get("grade_to_color", {}))
    )

@app.route("/admin/players/<int:player_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_player(player_id: int):
    player = Player.query.get_or_404(player_id)
    form = PlayerForm(obj=player)
    set_localized_choices(form)
    if form.validate_on_submit():
        form.populate_obj(player)
        if player.grade_level and player.grade_level in GRADING_SCHEME["grade_to_color"]:
            player.belt_rank = GRADING_SCHEME["grade_to_color"][player.grade_level]

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

    return render_template(
        "player_form.html",
        form=form,
        title=_("Edit Player"),
        belt_colors_json=json.dumps(BELT_PALETTE),
        grade_to_color_json=json.dumps(GRADING_SCHEME.get("grade_to_color", {})),
        player=player,
    )

@app.route("/admin/players/<int:player_id>/delete", methods=["POST"])
@admin_required
def delete_player(player_id: int):
    player = Player.query.get_or_404(player_id)
    if player.photo_filename:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, player.photo_filename))
        except FileNotFoundError:
            pass
    try:
        PaymentRecord.query.filter_by(player_id=player.id).delete(synchronize_session=False)
        Payment.query.filter_by(player_id=player.id).delete(synchronize_session=False)
        regs = EventRegistration.query.filter_by(player_id=player.id).all()
        for r in regs:
            db.session.delete(r)
        db.session.delete(player)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Failed to fully delete player and related records.", "danger")
        return redirect(url_for("player_detail", player_id=player.id))
    flash(_("Player deleted."), "info")
    return redirect(url_for("list_players"))

# -------- Fees Report + Toggle + CSV ----------
@app.route("/reports/fees")
@admin_required
def fees_report():
    month_str = request.args.get("month")
    year, month = parse_month_str(month_str)
    ensure_payments_for_month(year, month)

    # Get all active players
    players = Player.query.filter_by(active_member=True).order_by(Player.last_name.asc(), Player.first_name.asc()).all()
    payments = {p.player_id: p for p in Payment.query.filter_by(year=year, month=month).all()}

    # Build a list of dicts for all players, including per-session
    report_rows = []
    for player in players:
        payment = payments.get(player.id)
        if payment:
            # Monthly fee (existing logic)
            report_rows.append({
                'player': player,
                'player_id': player.id,
                'amount': payment.amount,
                'paid': payment.paid,
                'id': payment.id,
                'year': payment.year,
                'month': payment.month,
                'is_monthly': True,
            })
        else:
            # Per-session: show row for per-session players
            if player.monthly_fee_is_monthly is False and player.monthly_fee_amount:
                # Calculate sessions paid/taken and owed for this month
                # Find receipts for this player/month
                from sqlalchemy import extract
                receipts = PaymentRecord.query.filter_by(player_id=player.id, kind='training_session').filter(
                    extract('year', PaymentRecord.paid_at) == year,
                    extract('month', PaymentRecord.paid_at) == month
                ).all()
                sessions_paid = sum(r.sessions_paid or 0 for r in receipts)
                sessions_taken = sum(r.sessions_taken or 0 for r in receipts)
                prepaid_amount = sum(r.amount or 0 for r in receipts)
                per_session_amount = player.monthly_fee_amount
                owed_amount = max(0, (sessions_taken - sessions_paid) * per_session_amount)
                report_rows.append({
                    'player': player,
                    'player_id': player.id,
                    'amount': None,
                    'paid': None,
                    'id': None,
                    'year': year,
                    'month': month,
                    'is_monthly': False,
                    'sessions_paid': sessions_paid,
                    'sessions_taken': sessions_taken,
                    'prepaid_amount': prepaid_amount,
                    'per_session_amount': per_session_amount,
                    'owed_amount': owed_amount,
                })

    due = first_working_day(year, month)
    return render_template(
        "report_fees.html",
        payments=report_rows,
        year=year,
        month=month,
        due_date=due,
        today=date.today()
    )

@app.route("/admin/fees/<int:payment_id>/toggle", methods=["POST"])
@admin_required
def toggle_payment(payment_id: int):
    pay = Payment.query.get_or_404(payment_id)
    pay.paid = not pay.paid
    pay.paid_on = date.today() if pay.paid else None
    db.session.commit()
    flash(_("Payment toggled."), "success")
    month_str = f"{pay.year:04d}-{pay.month:02d}"
    return redirect(url_for("fees_report", month=month_str))

@app.route("/admin/reports/fees/export")
@admin_required
def fees_export_csv():
    month_str = request.args.get("month")
    year, month = parse_month_str(month_str)
    due = first_working_day(year, month)
    payments = (Payment.query
                .filter_by(year=year, month=month)
                .join(Player)
                .order_by(Player.last_name.asc(), Player.first_name.asc())
                .all())

    def generate():
        yield "player_id,full_name,belt,amount_eur,paid,paid_on,due_date\n"
        for p in payments:
            full_name = p.player.full_name()
            belt = p.player.belt_rank or ""
            amount = "" if p.amount is None else p.amount
            paid = "yes" if p.paid else "no"
            paid_on = p.paid_on.isoformat() if p.paid_on else ""
            yield f"{p.player_id},{full_name},{belt},{amount},{paid},{paid_on},{due.isoformat()}\n"

    headers = {"Content-Disposition": f'attachment; filename=\"fees_{year:04d}-{month:02d}.csv\"'}
    return Response(generate(), mimetype="text/csv", headers=headers)

# -------- Players CSV ----------
@app.route("/export/csv")
def export_csv():
    players = Player.query.order_by(Player.last_name.asc(), Player.first_name.asc()).all()

    def generate():
        yield (
            "id,first_name,last_name,belt_color,grade_level,grade_date,discipline,active_member,"
            "email,phone,mother_name,mother_phone,father_name,father_phone,"
            "medical_exam_date,medical_expiry_date,insurance_expiry_date,"
            "monthly_fee_amount_eur,monthly_fee_is_monthly,"
            "sessions_paid,sessions_taken,prepaid_amount_eur,per_session_amount_eur,owed_amount_eur,"
            "sportdata_wkf_url,sportdata_bnfk_url,sportdata_enso_url\n"
        )
        def esc(val: Optional[str]) -> str:
            if val is None:
                return ""
            s = str(val)
            if any(c in s for c in [",", '"', "\n"]):
                s = '"' + s.replace('"', '""') + '"'
            return s

        for p in players:
            sess_records = (PaymentRecord.query
                            .filter_by(player_id=p.id, kind='training_session')
                            .all())
            explicit_sessions_paid = sum((r.sessions_paid or 0) for r in sess_records)
            sessions_taken = sum((r.sessions_taken or 0) for r in sess_records)
            prepaid_amount = sum((r.amount or 0) for r in sess_records)
            per_session_amount = int(p.monthly_fee_amount) if (p.monthly_fee_amount is not None and not p.monthly_fee_is_monthly) else ""
            owed_amount = ""
            if per_session_amount != "":
                inferred = 0
                try:
                    for r in sess_records:
                        if (r.sessions_paid or 0) == 0 and (r.amount or 0) > 0:
                            inferred += int(round(float(r.amount) / float(per_session_amount)))
                except Exception:
                    inferred = 0
                sessions_paid = explicit_sessions_paid + inferred
                prepaid_credit = float(prepaid_amount)
                owed_amount = (sessions_taken * per_session_amount) - int(round(prepaid_credit))
            row = [
                str(p.id),
                esc(p.first_name),
                esc(p.last_name),
                esc(p.belt_rank or ""),
                esc(p.grade_level or ""),
                esc(p.grade_date or ""),
                esc(p.discipline),
                "yes" if p.active_member else "no",
                esc(p.email or ""),
                esc(p.phone or ""),
                esc(p.mother_name or ""), esc(p.mother_phone or ""),
                esc(p.father_name or ""), esc(p.father_phone or ""),
                esc(p.medical_exam_date or ""),
                esc(p.medical_expiry_date or ""),
                esc(p.insurance_expiry_date or ""),
                esc(p.monthly_fee_amount if p.monthly_fee_amount is not None else ""),
                "yes" if p.monthly_fee_is_monthly else "no",
                str(sessions_paid), str(sessions_taken), str(prepaid_amount), str(per_session_amount), str(owed_amount),
                esc(p.sportdata_wkf_url or ""),
                esc(p.sportdata_bnfk_url or ""),
                esc(p.sportdata_enso_url or ""),
            ]
            yield ",".join(row) + "\n"

    headers = {"Content-Disposition": 'attachment; filename="karate_players.csv"'}
    return Response(generate(), mimetype="text/csv", headers=headers)

# -------- Sports Calendar ----------
@app.route("/events")
def events_calendar():
    month_str = request.args.get("month")
    y, m = parse_month_str(month_str)
    first = date(y, m, 1)
    last_day = calendar.monthrange(y, m)[1]
    last = date(y, m, last_day)

    events = (
        Event.query
        .filter(Event.start_date <= last)
        .filter((Event.end_date == None) | (Event.end_date >= first))  # noqa: E711
        .order_by(Event.start_date.asc(), Event.title.asc())
        .all()
    )

    cal = calendar.monthcalendar(y, m)
    weeks = []
    for wk in cal:
        row = []
        for d in wk:
            if d == 0:
                row.append({"day": None, "events": []})
            else:
                dt = date(y, m, d)
                row.append({"day": dt, "events": [e for e in events if e.spans(dt)]})
        weeks.append(row)

    prev_y, prev_m = (y - 1, 12) if m == 1 else (y, m - 1)
    next_y, next_m = (y + 1, 1) if m == 12 else (y, m + 1)

    return render_template(
        "events_calendar.html",
        year=y, month=m, month_name=calendar.month_name[m],
        weeks=weeks,
        prev_str=f"{prev_y:04d}-{prev_m:02d}",
        next_str=f"{next_y:04d}-{next_m:02d}",
    )

@app.route("/event-list")
def event_list():
    events = Event.query.order_by(Event.start_date.desc()).all()
    return render_template(
        "event_list.html",
        events=events,
        _=_,
        current_lang=get_lang(),
    )

@app.route("/events/<int:event_id>")
def event_detail(event_id: int):
    ev = Event.query.get_or_404(event_id)
    regs = (EventRegistration.query
            .filter_by(event_id=ev.id)
            .join(Player)
            .order_by(Player.last_name.asc(), Player.first_name.asc())
            .all())

    unique_participants = len({r.player_id for r in regs})
    entries_count = len(regs)

    def expected_fee(r: EventRegistration) -> Optional[int]:
        if r.fee_override is not None:
            return r.fee_override
        total = 0
        counted = False
        for rc in r.reg_categories or []:
            if rc.category and rc.category.fee is not None:
                total += int(rc.category.fee)
                counted = True
        return total if counted else None

    total_expected = sum(f for r in regs if (f := expected_fee(r)) is not None)
    total_paid = sum(f for r in regs if r.paid and (f := expected_fee(r)) is not None)
    total_unpaid = total_expected - total_paid

    gold = silver = bronze = 0
    for r in regs:
        for rc in r.reg_categories or []:
            if rc.medal == "gold": gold += 1
            elif rc.medal == "silver": silver += 1
            elif rc.medal == "bronze": bronze += 1

    return render_template(
        "event_detail.html",
        ev=ev, regs=regs,
        unique_participants=unique_participants,
        entries_count=entries_count,
        total_expected=total_expected,
        total_paid=total_paid,
        total_unpaid=total_unpaid,
        medal_gold=gold, medal_silver=silver, medal_bronze=bronze
    )

@app.route("/admin/events/new", methods=["GET", "POST"])
@admin_required
def event_new():
    form = EventForm()
    # Pre-fill date if provided in query string
    date_str = request.args.get("date")
    if date_str and not form.start_date.data:
        try:
            form.start_date.data = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            pass
    if form.validate_on_submit():
        ev = Event(
            title=form.title.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            location=form.location.data,
            sportdata_url=form.sportdata_url.data or None,
            notes=form.notes.data,
        )
        db.session.add(ev)
        db.session.commit()
        flash(_("Event created."), "success")
        return redirect(url_for("event_detail", event_id=ev.id))
    return render_template("event_form.html", form=form, title=_("New Event"))

@app.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@admin_required
def event_edit(event_id: int):
    ev = Event.query.get_or_404(event_id)
    form = EventForm(obj=ev)
    if form.validate_on_submit():
        form.populate_obj(ev)
        db.session.commit()
        flash(_("Event updated."), "success")
        return redirect(url_for("event_detail", event_id=ev.id))
    return render_template("event_form.html", form=form, title=_("Edit Event"))

@app.route("/admin/events/<int:event_id>/delete", methods=["POST"])
@admin_required
def event_delete(event_id: int):
    ev = Event.query.get_or_404(event_id)
    db.session.delete(ev)
    db.session.commit()
    flash(_("Event deleted."), "info")
    return redirect(url_for("events_calendar"))

@app.route("/admin/events/<int:event_id>/categories", methods=["GET", "POST"])
@admin_required
def event_categories(event_id: int):
    ev = Event.query.get_or_404(event_id)
    form = EventCategoryForm()
    if form.validate_on_submit():
        cat = EventCategory(event_id=ev.id, name=form.name.data, fee=form.fee.data)
        db.session.add(cat)
        db.session.commit()
        flash(_("Category added."), "success")
        return redirect(url_for("event_categories", event_id=ev.id))
    cats = ev.categories.order_by(EventCategory.name.asc()).all()
    return render_template("event_categories.html", ev=ev, cats=cats, form=form)

@app.route("/admin/events/<int:event_id>/categories/<int:cat_id>/delete", methods=["POST"])
@admin_required
def event_category_delete(event_id: int, cat_id: int):
    ev = Event.query.get_or_404(event_id)
    cat = EventCategory.query.filter_by(id=cat_id, event_id=ev.id).first_or_404()
    db.session.delete(cat)
    db.session.commit()
    flash(_("Category deleted."), "info")
    return redirect(url_for("event_categories", event_id=ev.id))

# -------- Registrations --------
@app.route("/admin/events/<int:event_id>/registrations", methods=["GET", "POST"])
@admin_required
def event_registrations(event_id: int):
    ev = Event.query.get_or_404(event_id)
    form = EventRegistrationForm()

    players = Player.query.filter_by(active_member=True).order_by(Player.last_name.asc(), Player.first_name.asc()).all()
    form.player_ids.choices = [(p.id, p.full_name()) for p in players]
    cats = ev.categories.order_by(EventCategory.name.asc()).all()
    form.category_ids.choices = [(c.id, c.name) for c in cats]

    if form.validate_on_submit():
        selected_cats = [EventCategory.query.get(cid) for cid in form.category_ids.data]
        selected_cats = [c for c in selected_cats if c and c.event_id == ev.id]
        for pid in form.player_ids.data:
            reg = EventRegistration(
                event_id=ev.id,
                player_id=pid,
                fee_override=form.fee_override.data,
                paid=bool(form.paid.data),
                paid_on=(date.today() if form.paid.data else None),
            )
            reg.reg_categories = [EventRegCategory(category_id=c.id) for c in selected_cats]
            db.session.add(reg)
        db.session.commit()
        flash(_("Registration added."), "success")
        return redirect(url_for("event_registrations", event_id=ev.id))

    paid_filter = request.args.get("paid", "").strip().lower()
    q = request.args.get("q", "").strip()

    regs_query = (EventRegistration.query
                  .filter_by(event_id=ev.id)
                  .join(Player))

    if paid_filter == "paid":
        regs_query = regs_query.filter(EventRegistration.paid.is_(True))
    elif paid_filter == "unpaid":
        regs_query = regs_query.filter(EventRegistration.paid.is_(False))

    if q:
        like = f"%{q}%"
        regs_query = (regs_query
                      .outerjoin(EventRegistration.reg_categories)
                      .outerjoin(EventRegCategory.category)
                      .filter(or_(
                          Player.first_name.ilike(like),
                          Player.last_name.ilike(like),
                          EventCategory.name.ilike(like)
                      )))

    regs = (regs_query
            .order_by(Player.last_name.asc(), Player.first_name.asc(), EventRegistration.id.asc())
            .distinct()
            .all())

    unique_participants = len({r.player_id for r in regs})
    entries_count = len(regs)

    def expected_fee(r: EventRegistration) -> Optional[int]:
        if r.fee_override is not None:
            return r.fee_override
        total = 0
        counted = False
        for rc in r.reg_categories or []:
            if rc.category and rc.category.fee is not None:
                total += int(rc.category.fee)
                counted = True
        return total if counted else None

    total_expected = sum(f for r in regs if (f := expected_fee(r)) is not None)
    total_paid = sum(f for r in regs if r.paid and (f := expected_fee(r)) is not None)
    total_unpaid = total_expected - total_paid

    return render_template(
        "event_registrations.html",
        ev=ev, regs=regs, form=form,
        q=q, paid_filter=paid_filter,
        unique_participants=unique_participants,
        entries_count=entries_count,
        total_expected=total_expected,
        total_paid=total_paid,
        total_unpaid=total_unpaid
    )

@app.route("/admin/events/registrations/<int:reg_id>/toggle", methods=["POST"])
@admin_required
def event_reg_toggle_paid(reg_id: int):
    reg = EventRegistration.query.get_or_404(reg_id)
    reg.paid = not reg.paid
    reg.paid_on = date.today() if reg.paid else None
    db.session.commit()
    flash(_("Paid status updated."), "success")
    return redirect(url_for("event_registrations", event_id=reg.event_id))

@app.route("/admin/events/registrations/<int:reg_id>/delete", methods=["POST"])
@admin_required
def event_reg_delete(reg_id: int):
    reg = EventRegistration.query.get_or_404(reg_id)
    ev_id = reg.event_id
    db.session.delete(reg)
    db.session.commit()
    flash(_("Registration deleted."), "info")
    return redirect(url_for("event_registrations", event_id=ev_id))

@app.route("/admin/events/registrations/<int:reg_id>/categories/<int:cat_id>/remove", methods=["POST"])
@admin_required
def event_reg_remove_category(reg_id: int, cat_id: int):
    rc = EventRegCategory.query.filter_by(registration_id=reg_id, category_id=cat_id).first_or_404()
    ev_id = rc.registration.event_id
    db.session.delete(rc)
    db.session.commit()
    flash(_("Registration updated."), "success")
    return redirect(url_for("event_registrations", event_id=ev_id))

@app.route("/admin/events/registrations/<int:reg_id>/categories/<int:cat_id>/medal", methods=["POST"])
@admin_required
def event_reg_set_medal(reg_id: int, cat_id: int):
    rc = EventRegCategory.query.filter_by(registration_id=reg_id, category_id=cat_id).first_or_404()
    val = (request.form.get("medal") or "").lower()
    if val not in ("gold", "silver", "bronze", "none", ""):
        val = ""
    rc.medal = None if val in ("none", "") else val
    db.session.commit()
    flash(_("Registration updated."), "success")
    return redirect(url_for("event_registrations", event_id=rc.registration.event_id))

@app.route("/admin/events/<int:event_id>/export")
@admin_required
def event_export_csv(event_id: int):
    ev = Event.query.get_or_404(event_id)
    regs = (EventRegistration.query
            .filter_by(event_id=ev.id)
            .join(Player)
            .order_by(Player.last_name.asc(), Player.first_name.asc())
            .all())

    def generate():
        yield "player_id,full_name,categories,medals,fee_eur,paid,paid_on,event_title,start_date,end_date,location\n"
        for r in regs:
            cats = "; ".join([rc.category.name for rc in r.reg_categories]) if r.reg_categories else ""
            medals = "; ".join([rc.medal or "" for rc in r.reg_categories]) if r.reg_categories else ""
            expected = r.fee_override if r.fee_override is not None else (
                sum((rc.category.fee or 0) for rc in r.reg_categories) if r.reg_categories else ""
            )
            paid = "yes" if r.paid else "no"
            paid_on = r.paid_on.isoformat() if r.paid_on else ""
            endd = (ev.end_date or ev.start_date).isoformat()
            yield f"{r.player_id},{r.player.full_name()},{cats},{medals},{expected},{paid},{paid_on},{ev.title},{ev.start_date.isoformat()},{endd},{ev.location or ''}\n"

    headers = {"Content-Disposition": f'attachment; filename="event_{ev.id}_registrations.csv"'}
    return Response(generate(), mimetype="text/csv", headers=headers)

# -------- Medals Year Report --------
@app.route("/reports/medals")
@admin_required
def medals_report():
    try:
        year = int(request.args.get("year") or date.today().year)
    except Exception:
        year = date.today().year

    start = date(year, 1, 1)
    end = date(year, 12, 31)

    rows = (db.session.query(EventRegCategory, EventRegistration, Event, Player)
            .join(EventRegCategory.registration)
            .join(EventRegistration.player)
            .join(EventRegistration.event)
            .filter(and_(Event.start_date >= start, Event.start_date <= end))
            .all())

    per_player = {}
    club_totals = {"gold": 0, "silver": 0, "bronze": 0, "total": 0}

    for rc, reg, ev, pl in rows:
        if pl.id not in per_player:
            per_player[pl.id] = {"player": pl, "gold": 0, "silver": 0, "bronze": 0, "total": 0}
        if rc.medal in ("gold", "silver", "bronze"):
            per_player[pl.id][rc.medal] += 1
            per_player[pl.id]["total"] += 1
            club_totals[rc.medal] += 1
            club_totals["total"] += 1

    sorted_players = sorted(
        per_player.values(),
        key=lambda x: (-x["gold"], -x["silver"], -x["bronze"], x["player"].last_name, x["player"].first_name)
    )

    return render_template(
        "report_medals.html",
        year=year,
        players=sorted_players,
        club_totals=club_totals
    )

@app.route('/admin/reports/debts')
@admin_required
def report_debts():
    # find true AUTO_DEBT records that have no related payment
    debts = (PaymentRecord.query
             .filter(PaymentRecord.note.like('%AUTO_DEBT%'))
             .order_by(PaymentRecord.created_at.desc())
             .all())
    outstanding = []
    for d in debts:
        if not is_auto_debt_note(d.note):
            continue
        paid = PaymentRecord.query.filter_by(related_receipt_id=d.id).first()
        if not paid:
            outstanding.append(d)
    return render_template('report_debts.html', debts=outstanding)

# -------- Admin tools to fix missing receipt numbers ----------
@app.route("/admin/tools/fix_receipt_numbers", methods=["POST"])
@admin_required
def fix_receipt_numbers():
    missing = PaymentRecord.query.filter(PaymentRecord.receipt_no == None).all()  # noqa: E711
    cnt = 0
    for r in missing:
        try:
            db.session.flush()
            r.assign_receipt_no()
            cnt += 1
        except Exception:
            pass
    flash(f"Assigned receipt numbers to {cnt} receipt(s).", "success")
    return redirect(request.referrer or url_for('list_players'))

# -------- Migration ----------
@app.route("/admin/migrate")
@admin_required
def migrate():
    try:
        with db.engine.begin() as conn:
            result = conn.execute(text("PRAGMA table_info(player)"))
            existing = {row[1] for row in result}
            to_add = []
            if "sportdata_wkf_url" not in existing: to_add.append(("sportdata_wkf_url", "VARCHAR(255)"))
            if "sportdata_bnfk_url" not in existing: to_add.append(("sportdata_bnfk_url", "VARCHAR(255)"))
            if "sportdata_enso_url" not in existing: to_add.append(("sportdata_enso_url", "VARCHAR(255)"))
            if "grade_level" not in existing: to_add.append(("grade_level", "VARCHAR(20)"))
            if "grade_date" not in existing: to_add.append(("grade_date", "DATE"))
            if "medical_exam_date" not in existing: to_add.append(("medical_exam_date", "DATE"))
            if "medical_expiry_date" not in existing: to_add.append(("medical_expiry_date", "DATE"))
            if "insurance_expiry_date" not in existing: to_add.append(("insurance_expiry_date", "DATE"))
            if "monthly_fee_amount" not in existing: to_add.append(("monthly_fee_amount", "INTEGER"))
            if "monthly_fee_is_monthly" not in existing: to_add.append(("monthly_fee_is_monthly", "BOOLEAN"))
            if "mother_name" not in existing: to_add.append(("mother_name", "VARCHAR(120)"))
            if "mother_phone" not in existing: to_add.append(("mother_phone", "VARCHAR(40)"))
            if "father_name" not in existing: to_add.append(("father_name", "VARCHAR(120)"))
            if "father_phone" not in existing: to_add.append(("father_phone", "VARCHAR(40)"))
            for name, coltype in to_add:
                conn.execute(text(f"ALTER TABLE player ADD COLUMN {name} {coltype}"))

            result2 = conn.execute(text("PRAGMA table_info(payment_record)"))
            existing2 = {row[1] for row in result2}
            if "related_receipt_id" not in existing2:
                conn.execute(text("ALTER TABLE payment_record ADD COLUMN related_receipt_id INTEGER"))

        db.create_all()

        if to_add:
            added = ", ".join([name for name, _ in to_add])
            flash(_("DB migration: added columns: {cols}").format(cols=added), "success")
        else:
            flash(_("DB migration: nothing to do.").format(), "info")
    except Exception as e:
        flash(_("DB migration failed: {err}").format(err=str(e)), "danger")

    return redirect(url_for("list_players"))

def auto_migrate_on_startup():
    with db.engine.begin() as conn:
        result = conn.execute(text("PRAGMA table_info(player)"))
        existing = {row[1] for row in result}
        to_add = []
        for col, t in [
            ("sportdata_wkf_url", "VARCHAR(255)"),
            ("sportdata_bnfk_url", "VARCHAR(255)"),
            ("sportdata_enso_url", "VARCHAR(255)"),
            ("grade_level", "VARCHAR(20)"),
            ("grade_date", "DATE"),
            ("medical_exam_date", "DATE"),
            ("medical_expiry_date", "DATE"),
            ("insurance_expiry_date", "DATE"),
            ("monthly_fee_amount", "INTEGER"),
            ("monthly_fee_is_monthly", "BOOLEAN"),
            ("mother_name", "VARCHAR(120)"),
            ("mother_phone", "VARCHAR(40)"),
            ("father_name", "VARCHAR(120)"),
            ("father_phone", "VARCHAR(40)"),
        ]:
            if col not in existing:
                to_add.append((col, t))
        for name, coltype in to_add:
            conn.execute(text(f"ALTER TABLE player ADD COLUMN {name} {coltype}"))
        result2 = conn.execute(text("PRAGMA table_info(payment_record)"))
        existing2 = {row[1] for row in result2}
        if "related_receipt_id" not in existing2:
            conn.execute(text("ALTER TABLE payment_record ADD COLUMN related_receipt_id INTEGER"))

with app.app_context():
    db.create_all()
    try:
        auto_migrate_on_startup()
    except Exception as e:
        app.logger.exception("Auto-migrate failed: %s", e)

# -----------------------------
# Payments & Receipts (admin-only)
# -----------------------------
@app.route("/admin/payments/new", methods=["GET", "POST"])
@admin_required
def payment_new():
    player_id = request.values.get("player_id", type=int)
    reg_id = request.values.get("reg_id", type=int)

    if request.method == "GET":
        player = Player.query.get(player_id) if player_id else None
        reg = EventRegistration.query.get(reg_id) if reg_id else None
        default_amount = reg.computed_fee() if reg else None
        return render_template(
            "payment_new.html",
            player=player,
            reg=reg,
            today=date.today(),
            default_amount=default_amount
        )

    kind = request.form.get("kind")
    amount = request.form.get("amount", type=int)
    currency = (request.form.get("currency") or "EUR").strip().upper()
    method = request.form.get("method") or None
    note = request.form.get("note") or None

    if kind == "event" and amount is None:
        rid = request.form.get("reg_id", type=int)
        reg_tmp = EventRegistration.query.get(rid) if rid else None
        if reg_tmp:
            amount = reg_tmp.computed_fee()

    if kind not in ("training_month", "training_session", "event"):
        flash("Invalid payment kind.", "danger")
        return redirect(url_for("payment_new", player_id=player_id, reg_id=reg_id))
    if amount is None or amount < 0:
        flash("Amount is required.", "danger")
        return redirect(url_for("payment_new", player_id=player_id, reg_id=reg_id))

    record = PaymentRecord(kind=kind, amount=amount, currency=currency, method=method, note=note)

    if kind.startswith("training_"):
        pid = request.form.get("player_id", type=int)
        player = Player.query.get(pid)
        if not player:
            flash("Player is required for training payments.", "danger")
            return redirect(url_for("payment_new", player_id=player_id))
        record.player_id = player.id

        if kind == "training_month":
            month_str = request.form.get("month")
            y, m = parse_month_str(month_str)
            record.year = y
            record.month = m
            pay = Payment.query.filter_by(player_id=player.id, year=y, month=m).first()
            record.payment_id = pay.id if pay else None
        else:
            sessions_paid = request.form.get("sessions_paid", type=int) or 0
            record.sessions_paid = max(0, sessions_paid)
            record.sessions_taken = 0
            if player.monthly_fee_amount is not None and not player.monthly_fee_is_monthly:
                try:
                    per_price = float(player.monthly_fee_amount)
                    record.amount = int(round(record.sessions_paid * per_price))
                except Exception:
                    pass

    else:
        rid = request.form.get("reg_id", type=int)
        reg = EventRegistration.query.get(rid)
        if not reg:
            flash("Event registration is required for event payments.", "danger")
            return redirect(url_for("payment_new", reg_id=reg_id))
        record.player_id = reg.player_id
        record.event_registration_id = reg.id

    db.session.add(record)
    db.session.commit()
    try:
        record.assign_receipt_no()
    except Exception:
        pass

    try:
        if record.payment_id:
            pay_row = Payment.query.get(record.payment_id)
            if pay_row and not pay_row.paid:
                pay_row.paid = True
                pay_row.paid_on = date.today()
                db.session.add(pay_row)

        if record.event_registration_id:
            reg_row = EventRegistration.query.get(record.event_registration_id)
            if reg_row and not reg_row.paid:
                reg_row.paid = True
                reg_row.paid_on = date.today()
                db.session.add(reg_row)

        db.session.commit()
    except Exception:
        db.session.rollback()

    flash("Payment recorded. Receipt generated.", "success")
    return redirect(url_for("receipt_view", rid=record.id))

@app.route("/admin/players/<int:player_id>/due/print")
@admin_required
def player_due_print(player_id: int):
    month_str = request.args.get("month")
    year, month = parse_month_str(month_str)
    ensure_payments_for_month(year, month)

    player = Player.query.get_or_404(player_id)
    pay = Payment.query.filter_by(player_id=player.id, year=year, month=month).first()

    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    regs_unpaid = (EventRegistration.query
                   .join(Event)
                   .filter(EventRegistration.player_id == player.id)
                   .filter(EventRegistration.paid.is_(False))
                   .filter(Event.start_date >= first, Event.start_date <= last)
                   .all())

    monthly_due = (pay.amount or 0) if (pay and not pay.paid and pay.amount is not None) else 0
    events_due = sum([(r.computed_fee() or 0) for r in regs_unpaid])
    due_date = first_working_day(year, month)

    sess_records = (PaymentRecord.query
                    .filter_by(player_id=player.id, kind='training_session')
                    .all())
    sess_receipts = [r for r in sess_records if not is_auto_debt_note(r.note)]
    explicit_sessions_paid = sum((r.sessions_paid or 0) for r in sess_receipts)
    total_sessions_taken = sum((r.sessions_taken or 0) for r in sess_records)
    total_prepaid_amount = sum((r.amount or 0) for r in sess_receipts)
    per_session_amount = int(player.monthly_fee_amount) if (player.monthly_fee_amount is not None and not player.monthly_fee_is_monthly) else None

    inferred_sessions = 0
    if per_session_amount is not None and per_session_amount > 0:
        for r in sess_receipts:
            if (r.sessions_paid or 0) == 0 and (r.amount or 0) > 0:
                try:
                    inferred_sessions += int(round(float(r.amount) / float(per_session_amount)))
                except Exception:
                    pass
    total_sessions_paid = explicit_sessions_paid + inferred_sessions
    prepaid_credit = float(total_prepaid_amount)
    owed_amount = None
    if per_session_amount is not None:
        owed_amount = (total_sessions_taken * per_session_amount) - prepaid_credit

    return render_template(
        "player_due_print.html",
        player=player,
        year=year, month=month, due_date=due_date,
        pay=pay, regs_unpaid=regs_unpaid,
        monthly_due=monthly_due, events_due=events_due,
        sess_records=sess_records,
        total_sessions_paid=total_sessions_paid,
        total_sessions_taken=total_sessions_taken,
        total_prepaid_amount=total_prepaid_amount,
        prepaid_credit=int(round(prepaid_credit)) if prepaid_credit is not None else None,
        per_session_amount=per_session_amount,
        owed_amount=int(round(owed_amount)) if owed_amount is not None else None,
    )

@app.route("/admin/receipts/<int:rid>")
@admin_required
def receipt_view(rid: int):
    rec = PaymentRecord.query.get_or_404(rid)
    player = Player.query.get(rec.player_id)
    ev = None
    if rec.event_registration_id:
        reg = EventRegistration.query.get(rec.event_registration_id)
        ev = Event.query.get(reg.event_id) if reg else None
    return render_template("receipt.html", rec=rec, player=player, ev=ev)

@app.route("/admin/receipts/print_batch")
@admin_required
def receipts_print_batch():
    ids = request.args.get('ids', '')
    if not ids:
        flash('No receipts selected for printing.', 'info')
        return redirect(request.referrer or url_for('list_players'))
    id_list = [int(x) for x in ids.split(',') if x.strip().isdigit()]
    recs = PaymentRecord.query.filter(PaymentRecord.id.in_(id_list)).order_by(PaymentRecord.paid_at.asc()).all()
    if not recs:
        flash('No receipts found.', 'info')
        return redirect(request.referrer or url_for('list_players'))
    return render_template('receipts_print_batch.html', recs=recs)

@app.route("/admin/receipts/<int:rid>/tick", methods=["POST"])
@admin_required
def receipt_tick_session(rid: int):
    rec = PaymentRecord.query.get_or_404(rid)
    if rec.kind != "training_session":
        flash("Only per-session training receipts can track sessions.", "warning")
        return redirect(url_for("receipt_view", rid=rid))
    rec.sessions_taken = (rec.sessions_taken or 0) + 1
    db.session.commit()
    delta = rec.sessions_taken - (rec.sessions_paid or 0)

    player = Player.query.get(rec.player_id)
    per_price = float(player.monthly_fee_amount) if (player and player.monthly_fee_amount is not None and not player.monthly_fee_is_monthly) else None

    if delta > 0:
        debt_amount = int(round(per_price)) if per_price is not None else 0
        debt = PaymentRecord(
            kind='training_session',
            player_id=rec.player_id,
            sessions_paid=0,
            sessions_taken=0,
            amount=debt_amount,
            currency=rec.currency or 'EUR',
            method=None,
            note=f"AUTO_DEBT from receipt {rec.id}: {delta} extra sessions",
            related_receipt_id=rec.id,
        )
        db.session.add(debt)
        db.session.commit()
        try:
            debt.assign_receipt_no()
        except Exception:
            pass
        if per_price is None:
            flash("Session marked. Price not set; created 0-EUR debt. Set price in player profile to settle.", "warning")
        else:
            flash(f"Session marked as taken. Player now owes {debt_amount} {rec.currency or 'EUR'} (debt receipt created).", "warning")
    else:
        flash("Session marked as taken.", "success")
    return redirect(url_for("receipt_view", rid=rid))

@app.route("/admin/players/<int:player_id>/record_session", methods=["POST"])
@admin_required
def record_session(player_id: int):
    player = Player.query.get_or_404(player_id)
    if player.monthly_fee_is_monthly:
        flash('Player is not a per-session payer.', 'warning')
        return redirect(request.referrer or url_for('player_detail', player_id=player.id))

    per_price = float(player.monthly_fee_amount) if (player.monthly_fee_amount is not None and not player.monthly_fee_is_monthly) else None

    allocated = False
    receipts = (PaymentRecord.query
                .filter_by(player_id=player.id, kind='training_session')
                .filter((PaymentRecord.note == None) | (~PaymentRecord.note.like('%AUTO_DEBT%')))
                .order_by(PaymentRecord.paid_at.asc())
                .all())

    for r in receipts:
        paid = (r.sessions_paid or 0)
        taken = (r.sessions_taken or 0)
        available = paid - taken
        if available > 0:
            r.sessions_taken = taken + 1
            db.session.add(r)
            db.session.commit()
            allocated = True
            flash('Session recorded against prepaid sessions.', 'success')
            break
        if paid == 0 and (r.amount or 0) > 0 and per_price is not None and per_price > 0:
            try:
                inferred = int(round(float(r.amount) / float(per_price)))
            except Exception:
                inferred = 0
            if inferred > 0:
                r.sessions_paid = inferred
                r.sessions_taken = 1
                db.session.add(r)
                db.session.commit()
                allocated = True
                flash('Session recorded (inferred from payment).', 'success')
                break

    if not allocated:
        # 1) log the taken session on a non-debt tracking receipt
        tracking = (PaymentRecord.query
                    .filter_by(player_id=player.id, kind='training_session')
                    .filter((PaymentRecord.note == None) | (~PaymentRecord.note.like('%AUTO_DEBT%')))
                    .order_by(PaymentRecord.paid_at.desc())
                    .first())
        if tracking:
            tracking.sessions_taken = (tracking.sessions_taken or 0) + 1
            db.session.add(tracking)
            db.session.commit()
            try:
                if not tracking.receipt_no:
                    tracking.assign_receipt_no()
            except Exception:
                pass
        else:
            tracking = PaymentRecord(
                kind='training_session', player_id=player.id,
                sessions_paid=0, sessions_taken=1,
                amount=0, currency='EUR', method=None,
                note='SESSION_LOG'
            )
            db.session.add(tracking)
            db.session.commit()
            try:
                tracking.assign_receipt_no()
            except Exception:
                pass

        # 2) create a separate AUTO_DEBT with sessions_taken=0
        debt_amount = int(round(per_price)) if per_price is not None else 0
        debt = PaymentRecord(
            kind='training_session', player_id=player.id,
            sessions_paid=0, sessions_taken=0,
            amount=debt_amount, currency='EUR', method=None,
            note=f"AUTO_DEBT from list action: 1 extra session",
        )
        db.session.add(debt)
        db.session.commit()
        try:
            debt.assign_receipt_no()
        except Exception:
            pass
        if per_price is None:
            flash("Session recorded. Price not set; created 0-EUR debt. Set price in player profile to settle.", 'warning')
        else:
            flash(f"Session recorded. Player now owes {debt.amount} EUR (debt receipt created).", 'warning')

    return redirect(request.referrer or url_for('player_detail', player_id=player.id))

@app.route("/admin/receipts/<int:rid>/pay", methods=["POST"])
@admin_required
def receipt_pay_debt(rid: int):
    orig = PaymentRecord.query.get_or_404(rid)
    note = (orig.note or "")
    if not is_auto_debt_note(note):
        flash("Receipt is not an auto-generated training debt.", "warning")
        return redirect(url_for("receipt_view", rid=rid))

    pay = PaymentRecord(
        kind=orig.kind,
        player_id=orig.player_id,
        amount=orig.amount,
        currency=orig.currency or "EUR",
        method=request.form.get("method") or None,
        note=f"Payment for debt receipt {orig.id}",
    )
    db.session.add(pay)
    db.session.commit()
    try:
        pay.assign_receipt_no()
    except Exception:
        pass

    pay.related_receipt_id = orig.id
    db.session.add(pay)
    try:
        orig.note = (orig.note or '') + ' | AUTO_DEBT_PAID'
        db.session.add(orig)
        db.session.commit()
    except Exception:
        db.session.rollback()

    flash('Debt payment recorded. Receipt created.', 'success')
    return redirect(url_for('receipt_view', rid=pay.id))

@app.route("/admin/players/<int:player_id>/pay_due", methods=["POST"])
@admin_required
def player_pay_due(player_id: int):
    kind = (request.form.get("kind") or "all").lower()
    player = Player.query.get_or_404(player_id)
    created = []
    total_amount = 0
    today = date.today()

    ensure_payments_for_month(today.year, today.month)

    # Require per-session price for training debts
    if kind in ("debts", "all") and (not player.monthly_fee_is_monthly) and (player.monthly_fee_amount is None):
        flash("Cannot pay training debts: per-session price is not set in player profile.", "warning")
        return redirect(request.referrer or url_for('player_detail', player_id=player.id))

    # Monthly
    if kind in ("monthly", "all"):
        unpaid = Payment.query.filter_by(player_id=player.id, paid=False).all()
        for p in unpaid:
            amt = p.amount or 0
            rec = PaymentRecord(kind='training_month', player_id=player.id,
                                amount=amt, year=p.year, month=p.month,
                                payment_id=p.id, currency='EUR', note='PAY_FROM_LIST')
            db.session.add(rec)
            db.session.commit()
            try:
                rec.assign_receipt_no()
            except Exception:
                pass
            p.paid = True
            p.paid_on = today
            db.session.add(p)
            total_amount += amt
            created.append(rec)

    # Events
    if kind in ("events", "all"):
        regs = EventRegistration.query.filter_by(player_id=player.id, paid=False).all()
        for r in regs:
            amt = r.computed_fee() or 0
            rec = PaymentRecord(kind='event', player_id=player.id,
                                amount=amt, event_registration_id=r.id,
                                currency='EUR', note='PAY_FROM_LIST')
            db.session.add(rec)
            db.session.commit()
            try:
                rec.assign_receipt_no()
            except Exception:
                pass
            r.paid = True
            r.paid_on = today
            db.session.add(r)
            total_amount += amt
            created.append(rec)

    # Debts (true AUTO_DEBT only)
    debts_to_pay = []
    if kind in ("debts", "all"):
        debts = (PaymentRecord.query
                 .filter(PaymentRecord.player_id == player.id,
                         PaymentRecord.note.like('%AUTO_DEBT%'))
                 .order_by(PaymentRecord.paid_at.asc())
                 .all())
        for d in debts:
            if not is_auto_debt_note(d.note):
                continue
            has_related = bool(getattr(d, 'related_payments', []))
            if not has_related:
                debts_to_pay.append(d)

    unit_price = float(player.monthly_fee_amount) if (player.monthly_fee_amount is not None and not player.monthly_fee_is_monthly) else None

    # 1) Pay explicit AUTO_DEBT receipts
    for d in debts_to_pay:
        d_amt = int(d.amount or 0)
        if d_amt <= 0:
            continue
        pay_rec = PaymentRecord(
            kind=d.kind, player_id=player.id,
            amount=d_amt, currency=d.currency or 'EUR',
            method=None,
            note=f'Payment for debt receipt {d.id}',
            related_receipt_id=d.id
        )
        if unit_price and unit_price > 0:
            try:
                pay_rec.sessions_paid = int(round(float(d_amt) / unit_price))
            except Exception:
                pass
        db.session.add(pay_rec)
        db.session.commit()
        try:
            pay_rec.assign_receipt_no()
        except Exception:
            pass
        created.append(pay_rec)
        total_amount += d_amt

        d.note = (d.note or '') + ' | AUTO_DEBT_PAID'
        db.session.add(d)

    # 2) ALWAYS settle any residual owed in the same click (based on fundamentals)
    if kind in ("debts", "all") and unit_price is not None and unit_price > 0:
        # Recompute fresh from DB AFTER paying explicit debts
        sess_records_all = PaymentRecord.query.filter_by(player_id=player.id, kind='training_session').all()
        # Prepaid = all non-debt training receipts (MANUAL_OWED is prepaid, not debt)
        sess_receipts = [r for r in sess_records_all if not is_auto_debt_note(r.note)]
        total_sessions_taken = sum((r.sessions_taken or 0) for r in sess_records_all)
        total_prepaid_amount = sum((r.amount or 0) for r in sess_receipts)

        expected_cost = int(round(total_sessions_taken * unit_price))
        prepaid_credit_now = int(round(total_prepaid_amount))
        residual_owed = expected_cost - prepaid_credit_now

        if residual_owed > 0:
            rec = PaymentRecord(
                kind='training_session', player_id=player.id,
                sessions_paid=0, sessions_taken=0,
                amount=residual_owed, currency='EUR',
                method=None, note=f'MANUAL_OWED: owed {residual_owed}'
            )
            try:
                rec.sessions_paid = int(round(float(residual_owed) / unit_price))
            except Exception:
                pass
            db.session.add(rec)
            db.session.commit()
            try:
                rec.assign_receipt_no()
            except Exception:
                pass
            created.append(rec)
            total_amount += residual_owed

    if created:
        flash(f"Created {len(created)} payment(s) totaling {total_amount} EUR.", "success")
        ids = ",".join(str(r.id) for r in created)
        return redirect(url_for('receipts_print_batch') + f"?ids={ids}")
    else:
        flash("No outstanding dues found for the selected category.", "info")
    return redirect(request.referrer or url_for('player_detail', player_id=player.id))

@app.route("/admin/events/registrations/<int:reg_id>/fee.json")
@admin_required
def event_reg_fee_json(reg_id: int):
    reg = EventRegistration.query.get_or_404(reg_id)
    fee = reg.computed_fee()
    return {"fee": fee}, 200

# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)