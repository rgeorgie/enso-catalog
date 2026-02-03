import os
import re
import json
import calendar
from datetime import date, datetime, timedelta
from functools import wraps
from typing import Optional, Tuple

from flask import (
    Flask, render_template, request, redirect, url_for, flash, abort,
    send_from_directory, session, Response, stream_with_context
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from wtforms import (
    StringField, SelectField, DateField, IntegerField,
    TextAreaField, SubmitField, BooleanField, SelectMultipleField, FileField, PasswordField
)
from wtforms.validators import DataRequired, Email, Optional as VOptional, Length, NumberRange, URL, Regexp
from sqlalchemy import or_, and_, text
from sqlalchemy.orm import foreign
from werkzeug.routing import BuildError

app = Flask(__name__)

# Place public player detail route after app is defined
@app.route("/players/public/<int:player_id>")
def player_detail_public(player_id: int):
    player = Player.query.get_or_404(player_id)
    regs = (EventRegistration.query
            .filter_by(player_pn=player.pn)
            .join(Event)
            .order_by(Event.start_date.desc())
            .all())

    # Use TrainingSession for session logic (unified with admin view)
    all_sessions = TrainingSession.query.filter_by(player_pn=player.pn).all()
    paid_sessions = [s for s in all_sessions if s.paid]
    unpaid_sessions = [s for s in all_sessions if not s.paid]
    total_sessions_taken = len(all_sessions)
    total_sessions_paid = len(paid_sessions)
    total_sessions_unpaid = len(unpaid_sessions)
    per_session_price = float(player.monthly_fee_amount) if player.monthly_fee_amount and not player.monthly_fee_is_monthly else None
    owed_amount = int(round(total_sessions_unpaid * per_session_price)) if per_session_price else 0
    # Only show session receipts for sessions counted as paid
    all_receipts = PaymentRecord.query.filter_by(player_pn=player.pn, kind='training_session').order_by(PaymentRecord.paid_at.desc()).all()
    sess_records = all_receipts[:total_sessions_paid]

    return render_template(
        "player_detail_public.html",
        player=player,
        regs=regs,
        total_sessions_paid=total_sessions_paid,
        total_sessions_taken=total_sessions_taken,
        total_sessions_unpaid=total_sessions_unpaid,
        per_session_amount=per_session_price,
        owed_amount=owed_amount,
        sess_records=sess_records,
    )

# Place this route after app and admin_required are defined
# (Move to after admin_required function definition)
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
# TrainingSession model (per-session attendance)
# -----------------------------
class TrainingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False)
    __table_args__ = (db.UniqueConstraint('player_id', 'date', name='uq_player_session_date'),)
    player_id = db.Column(db.Integer, nullable=False, index=True)
    player_pn = db.Column(db.String(20), nullable=True, index=True)
    date = db.Column(db.Date, nullable=True)
    paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

# -----------------------------
# i18n (BG default)
# -----------------------------
def get_lang() -> str:
    return session.get("lang", "bg")

translations = {
    "en": {
        # --- Grade/Belt labels ---
        "10 kyu – white belt": "10 kyu – white belt",
        "9 kyu – white with yellow stripe": "9 kyu – white with yellow stripe",
        "8 kyu – yellow belt": "8 kyu – yellow belt",
        "7 kyu – orange belt": "7 kyu – orange belt",
        "6 kyu – orange belt": "6 kyu – orange belt",
        "5 kyu – green belt": "5 kyu – green belt",
        "4 kyu – blue belt": "4 kyu – blue belt",
        "3 kyu – blue belt": "3 kyu – blue belt",
        "2 kyu – brown belt": "2 kyu – brown belt",
        "1 kyu – brown belt": "1 kyu – brown belt",
        "1 dan – black belt": "1 dan – black belt",
        "2 dan – black belt": "2 dan – black belt",
        "3 dan – black belt": "3 dan – black belt",
        "4 dan – black belt": "4 dan – black belt",
        "5 dan – black belt": "5 dan – black belt",
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
        "Previous": "Previous",
        "Next": "Next",
        "Help & User Guide": "Help & User Guide",
        "Getting Started": "Getting Started",
        "Installation & Setup": "Installation & Setup",
        "Prerequisites: Python 3.8+ and pip": "Prerequisites: Python 3.8+ and pip",
        "Create Virtual Environment": "Create Virtual Environment",
        "Install Dependencies": "Install Dependencies",
        "Set Environment Variables": "Set Environment Variables",
        "Run the Application": "Run the Application",
        "Access: Open http://127.0.0.1:5000 in your browser": "Access: Open http://127.0.0.1:5000 in your browser",
        "Language Support": "Language Support",
        "The application supports Bulgarian (default) and English. Use the language switcher in the top navigation to change languages.": "The application supports Bulgarian (default) and English. Use the language switcher in the top navigation to change languages.",
        "Player Management": "Player Management",
        "Adding New Players": "Adding New Players",
        "Navigate to Players → + Add Player": "Navigate to Players → + Add Player",
        "Fill in required information: First Name, Last Name, PN (10-digit Bulgarian ID), Gender, Birthdate, Belt Rank": "Fill in required information: First Name, Last Name, PN (10-digit Bulgarian ID), Gender, Birthdate, Belt Rank",
        "Choose payment type: Monthly or per-session": "Choose payment type: Monthly or per-session",
        "Add optional contact info, parent contacts, medical data, and photo": "Add optional contact info, parent contacts, medical data, and photo",
        "Managing Players": "Managing Players",
        "Search & Filter: Use the search bar and filters for belt rank, active status": "Search & Filter: Use the search bar and filters for belt rank, active status",
        "Edit Player: Click the edit button on any player profile": "Edit Player: Click the edit button on any player profile",
        "Record Sessions: For all players, record training attendance": "Record Sessions: For all players, record training attendance",
        "Payment Management: Track fees, generate receipts, mark payments": "Payment Management: Track fees, generate receipts, mark payments",
        "Training Session Tracking": "Training Session Tracking",
        "Recording Sessions": "Recording Sessions",
        "Go to a player's profile": "Go to a player's profile",
        "Click \"Record Session\" button": "Click \"Record Session\" button",
        "Sessions are automatically marked as paid/unpaid based on payment type": "Sessions are automatically marked as paid/unpaid based on payment type",
        "Viewing Attendance": "Viewing Attendance",
        "Calendar View: Visual calendar with session indicators": "Calendar View: Visual calendar with session indicators",
        "List View: Detailed chronological list of all sessions": "List View: Detailed chronological list of all sessions",
        "Main Calendar: Club-wide calendar showing daily attendance numbers": "Main Calendar: Club-wide calendar showing daily attendance numbers",
        "Payment & Fee Management": "Payment & Fee Management",
        "Payment Types": "Payment Types",
        "Monthly Training": "Monthly Training",
        "Fixed monthly fee for unlimited sessions": "Fixed monthly fee for unlimited sessions",
        "Per-Session Training": "Per-Session Training",
        "Pay per individual training session": "Pay per individual training session",
        "Managing Payments": "Managing Payments",
        "From Player Profile: Use quick action buttons to record payments": "From Player Profile: Use quick action buttons to record payments",
        "Payment Forms: Create receipts for training, events, or outstanding debts": "Payment Forms: Create receipts for training, events, or outstanding debts",
        "Toggle Payment Status: Mark payments as paid/unpaid": "Toggle Payment Status: Mark payments as paid/unpaid",
        "Print Receipts: Generate printable payment receipts": "Print Receipts: Generate printable payment receipts",
        "Event Management": "Event Management",
        "Creating Events": "Creating Events",
        "Admin Access Required": "Admin Access Required",
        "Navigate to Calendar → New Event": "Navigate to Calendar → New Event",
        "Event Details: Title, date range, location, categories with fees": "Event Details: Title, date range, location, categories with fees",
        "Player Registration": "Player Registration",
        "Go to event details": "Go to event details",
        "Click \"Add Registration\"": "Click \"Add Registration\"",
        "Select categories and mark payments": "Select categories and mark payments",
        "Reporting & Exports": "Reporting & Exports",
        "Available Reports": "Available Reports",
        "Fee Reports: Monthly payment summaries": "Fee Reports: Monthly payment summaries",
        "Medal Reports: Competition results by year": "Medal Reports: Competition results by year",
        "Player Lists: Filtered player directories": "Player Lists: Filtered player directories",
        "Payment Exports: Complete transaction history": "Payment Exports: Complete transaction history",
        "Export Formats": "Export Formats",
        "Comma-separated values for spreadsheets": "Comma-separated values for spreadsheets",
        "Complete data packages with photos": "Complete data packages with photos",
        "Printable payment documents": "Printable payment documents",
        "Troubleshooting": "Troubleshooting",
        "Common Issues": "Common Issues",
        "Login Problems": "Login Problems",
        "Verify ADMIN_USER and ADMIN_PASS environment variables": "Verify ADMIN_USER and ADMIN_PASS environment variables",
        "File Upload Errors": "File Upload Errors",
        "Ensure files are under 2MB and in supported formats (JPG, PNG, GIF, WEBP)": "Ensure files are under 2MB and in supported formats (JPG, PNG, GIF, WEBP)",
        "Calendar Display Issues": "Calendar Display Issues",
        "Clear browser cache, check JavaScript is enabled, verify date formats": "Clear browser cache, check JavaScript is enabled, verify date formats",
        "Payment Calculation Errors": "Payment Calculation Errors",
        "Verify player payment type settings and fee amounts": "Verify player payment type settings and fee amounts",
        "Data Recovery": "Data Recovery",
        "Database Backup: Regular exports of karate_club.db": "Database Backup: Regular exports of karate_club.db",
        "Photo Backup: Backup uploads/ directory": "Photo Backup: Backup uploads/ directory",
        "CSV Exports: Keep exported data for reference": "CSV Exports: Keep exported data for reference",
        "Security Best Practices": "Security Best Practices",
        "Strong Passwords: Use complex admin passwords": "Strong Passwords: Use complex admin passwords",
        "Regular Backups: Backup data before major changes": "Regular Backups: Backup data before major changes",
        "Access Control: Limit admin access to authorized personnel": "Access Control: Limit admin access to authorized personnel",
        "File Validation: Only upload trusted files": "File Validation: Only upload trusted files",
        "Session Management: Log out when not using the system": "Session Management: Log out when not using the system",
        "Quick Start Guide": "Quick Start Guide",
        "Add Players": "Add Players",
        "Start by adding your karate club members with their personal information and payment preferences.": "Start by adding your karate club members with their personal information and payment preferences.",
        "Record Sessions": "Record Sessions",
        "Track attendance for each training session to monitor participation and manage payments.": "Track attendance for each training session to monitor participation and manage payments.",
        "Manage Payments": "Manage Payments",
        "Keep track of fees, generate receipts, and monitor outstanding payments.": "Keep track of fees, generate receipts, and monitor outstanding payments.",
        "Edit": "Edit",
        "Run DB migration": "Run DB migration",
        "Admin Login": "Admin Login",
        "Admin exports": "Admin exports",
        "Admin imports": "Admin imports",
        "Imports": "Imports",
        "Exports": "Exports",
        "Export All Payments (CSV)": "Export All Payments (CSV)",
        "Export Players (ZIP)": "Export Players (ZIP)",
        "Export Events (ZIP)": "Export Events (ZIP)",
        "Import Players (ZIP)": "Import Players (ZIP)",
        "Import Players (CSV)": "Import Players (CSV)",
        "Import Payments (CSV)": "Import Payments (CSV)",
        "Export All Profiles (ZIP)": "Export All Profiles (ZIP)",
        "Delete": "Delete",
        "Logout": "Logout",
        "Language": "Language",
        "BG": "BG", "EN": "EN",
        "All": "All",

        # --- Filters / Table headers ---
        "Category Fees": "Category Fees",
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

        # --- Player form / Profile ---
        "First Name": "First Name",
        "Last Name": "Last Name",
        "Gender": "Gender",
        "Birthdate": "Birthdate",
        "PN#": "PN#",
        "Belt Rank": "Belt Rank",
        "Grade Level": "Grade Level",
        "Grade": "Grade",
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
        "Categories & Medals": "Categories & Medals",

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
        "Monthly": "Monthly",
        "Due date": "Due date",
        "Amount": "Amount",
        "Paid": "Paid",
        "Unpaid": "Unpaid",
        "Owed": "Owed",
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
        "Record Session": "Record Session",
        "Pay Due": "Pay Due",
        "Open payment form": "Open payment form",
        "Receipt": "Receipt",
        "Amount (EUR)": "Amount (EUR)",
        "Note": "Note",
        "Created": "Created",
        "Quick actions": "Quick actions",
        "Training sessions": "Training sessions",
        "Actions": "Actions",
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
        "Paste/Import Categories": "Paste/Import Categories",
        "Paste tabular data (one row per category, columns: Name, Age from, Age to, Sex, Fee, Team size, KYU, DAN, Other cut-off date, Limit, Team Limit)": "Paste tabular data (one row per category, columns: Name, Age from, Age to, Sex, Fee, Team size, KYU, DAN, Other cut-off date, Limit, Team Limit)",
        "Import": "Import",
        "Import Event (ZIP)": "Import Event (ZIP)",
        "Sports Calendar": "Sports Calendar",
        "Athletes participated:": "Athletes participated:",
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
        "Income": "Income",
        "Due": "Due", 
        "Net Income": "Net Income",
        "Balance": "Balance",
        "Net club revenue (training fees minus event pass-through)": "Net club revenue (training fees minus event pass-through)",
        "Period Fees Report": "Period Fees Report",
        "Player Summary": "Player Summary",
        "Bulk payment": "Bulk payment",
        "Generated on:": "Generated on:",
        "This will generate a comprehensive report showing all fees (monthly, per-session, and event) for the selected period.": "This will generate a comprehensive report showing all fees (monthly, per-session, and event) for the selected period.",
        "Generate Report": "Generate Report",
        "Period": "Period",
        "Back to Monthly Report": "Back to Monthly Report",
        "Total Income": "Total Income",
        "Total Due": "Total Due",
        "Monthly Fees": "Monthly Fees",
        "Per Session Fees": "Per Session Fees",
        "Event Fees": "Event Fees",
        "Bulk": "Bulk",
        "GRAND TOTAL": "GRAND TOTAL",
        "Payment Details": "Payment Details",
        "No active players found for the selected period.": "No active players found for the selected period.",
        "Period Report": "Period Report",

        # --- Sportdata profiles ---
        "Sportdata": "Sportdata",
        "Sportdata Profiles": "Sportdata Profiles",
        "WKF Profile URL": "WKF Profile URL",
        "BNFK Profile URL": "BNFK Profile URL",
        "ENSO Profile URL": "ENSO Profile URL",
        "Open": "Open",

        # --- Player Detail Page ---
        "No photo uploaded": "No photo uploaded",
        "Export Profile (CSV)": "Export Profile (CSV)",
        "Permanently delete": "Permanently delete",
        "Permanently delete (PURGE)": "Permanently delete (PURGE)",
        "Permanently delete player": "Permanently delete player",
        "This is irreversible. All player data will be removed but related historical rows will keep the PN#.": "This is irreversible. All player data will be removed but related historical rows will keep the PN#.",
        "To confirm, type the word": "To confirm, type the word",
        "in the box below": "in the box below",
        "Total medals": "Total medals",
        "No categories for this registration.": "No categories for this registration.",
        "month (optional)": "month (optional)",
        "Delete Player": "Delete Player",
        "Back to Players List": "Back to Players List",
        "Player Details": "Player Details",

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
        "Failed to fully delete player and related records.": "Failed to fully delete player and related records.",
        "Player deleted (soft). Related registrations and payments preserved and linked by PN#.": "Player deleted (soft). Related registrations and payments preserved and linked by PN#.",
        "Missing or incorrect confirmation token. To permanently delete, POST with confirm=PURGE": "Missing or incorrect confirmation token. To permanently delete, POST with confirm=PURGE",
        "Purge failed: {e}": "Purge failed: {e}",
        "Player permanently deleted and related rows backfilled with PN.": "Player permanently deleted and related rows backfilled with PN.",
        "Backfilled {created_total} missing TrainingSession records.": "Backfilled {created_total} missing TrainingSession records.",
        "No file uploaded": "No file uploaded",
        "No file selected": "No file selected",
        "Close": "Close",
        "DB migration: added columns: {cols}": "DB migration: added columns: {cols}",
        "DB migration: nothing to do.": "DB migration: nothing to do.",
        "DB migration failed: {err}": "DB migration failed: {err}",

        # --- Player Deletion Confirmation ---
        "Confirm Player Deletion": "Confirm Player Deletion",
        "Warning!": "Warning!",
        "This player has outstanding debts. Deleting them may result in lost revenue.": "This player has outstanding debts. Deleting them may result in lost revenue.",
        "Player Information": "Player Information",
        "Name:": "Name:",
        "PN#:": "PN#:",
        "Active Member:": "Active Member:",
        "Outstanding Debts": "Outstanding Debts",
        "Type": "Type",
        "Description": "Description",
        "Total Outstanding": "Total Outstanding",
        "Note:": "Note:",
        "Deleting this player will perform a soft delete - the player record will be deactivated but preserved for historical records. All related payments and registrations will be maintained.": "Deleting this player will perform a soft delete - the player record will be deactivated but preserved for historical records. All related payments and registrations will be maintained.",
        "Purging this player will permanently remove their record from the database. This action cannot be undone. Make sure you have a backup.": "Purging this player will permanently remove their record from the database. This action cannot be undone. Make sure you have a backup.",
        "Delete Player Anyway": "Delete Player Anyway",
        "Purge Player Anyway": "Purge Player Anyway",
        "Are you absolutely sure you want to delete this player despite outstanding debts?": "Are you absolutely sure you want to delete this player despite outstanding debts?",

        # --- Common UI ---
        "yes": "yes",
        "no": "no",

        # --- Debt Types ---
        "monthly": "monthly",
        "sessions": "sessions",
        "event": "event",

        # --- Enums / Days ---
        "—": "—",
        "Male": "Male", "Female": "Female", "Other": "Other",
        "White": "White", "Yellow": "Yellow", "Orange": "Orange",
        "WhiteYellow": "WhiteYellow",
        "Green": "Green", "Blue": "Blue", "Purple": "Purple",
        "Brown": "Brown", "Black": "Black",
        "Kata": "Kata", "Kumite": "Kumite", "Makiwara": "Makiwara", "All Disciplines": "All Disciplines",
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

        # --- Additional Help Section Translations ---
        "Clone/Download the application files": "Clone/Download the application files",
        "(On Windows: .venv\\Scripts\\activate)": "(On Windows: .venv\\Scripts\\activate)",
        "User Roles & Access": "User Roles & Access",
        "Regular Users": "Regular Users",
        "View public player profiles": "View public player profiles",
        "Access basic information": "Access basic information",
        "Administrators": "Administrators",
        "Full access to all features": "Full access to all features",
        "Login required for sensitive operations": "Login required for sensitive operations",
        "Use the admin login form with credentials set in environment variables": "Use the admin login form with credentials set in environment variables",
        "First Name & Last Name": "First Name & Last Name",
        "Player's full name": "Player's full name",
        "PN (Personal Number)": "PN (Personal Number)",
        "Mandatory 10-digit Bulgarian ID number (ЕГН)": "Mandatory 10-digit Bulgarian ID number (ЕГН)",
        "Male/Female/Other": "Male/Female/Other",
        "Date of birth": "Date of birth",
        "Current karate belt level": "Current karate belt level",
        "Kyu/Dan ranking": "Kyu/Dan ranking",
        "Monthly or per-session": "Monthly or per-session",
        "Optional information": "Optional information",
        "Contact details (phone, email)": "Contact details (phone, email)",
        "Parent contacts (for minors)": "Parent contacts (for minors)",
        "Medical examination and insurance expiry dates": "Medical examination and insurance expiry dates",
        "Photo upload (JPG/PNG/GIF/WEBP, max 2MB)": "Photo upload (JPG/PNG/GIF/WEBP, max 2MB)",
        "View Profile": "View Profile",
        "Click on a player's name to see detailed information": "Click on a player's name to see detailed information",
        "Player Profile Features": "Player Profile Features",
        "Training Calendar": "Training Calendar",
        "Interactive calendar showing sessions and events": "Interactive calendar showing sessions and events",
        "Payment History": "Payment History",
        "View all payments and receipts": "View all payments and receipts",
        "Event Registrations": "Event Registrations",
        "See registered events and payment status": "See registered events and payment status",
        "Quick Actions": "Quick Actions",
        "Print due fees, export profile data": "Print due fees, export profile data",
        "Monthly payers": "Monthly payers",
        "Sessions are free (marked as paid)": "Sessions are free (marked as paid)",
        "Per-session payers": "Per-session payers",
        "Sessions require payment": "Sessions require payment",
        "Calendar View": "Calendar View",
        "Visual calendar with session indicators": "Visual calendar with session indicators",
        "List View": "List View",
        "Detailed chronological list of all sessions": "Detailed chronological list of all sessions",
        "Main Calendar": "Main Calendar",
        "Club-wide calendar showing daily attendance numbers": "Club-wide calendar showing daily attendance numbers",
        "Fee Tracking": "Fee Tracking",
        "Outstanding Debts": "Outstanding Debts",
        "View unpaid fees across all players": "View unpaid fees across all players",
        "Complete transaction history": "Complete transaction history",
        "Due Fee Reports": "Due Fee Reports",
        "Generate reports for unpaid amounts": "Generate reports for unpaid amounts",
        "Event Categories": "Event Categories",
        "Define competition categories (age, weight, belt requirements)": "Define competition categories (age, weight, belt requirements)",
        "Set registration fees per category": "Set registration fees per category",
        "Configure team size limits and registration cut-off dates": "Configure team size limits and registration cut-off dates",
        "Select categories and fee overrides if needed": "Select categories and fee overrides if needed",
        "Mark payments and track registration status": "Mark payments and track registration status",
        "Event Reporting": "Event Reporting",
        "Registration Lists": "Registration Lists",
        "View all registered athletes": "View all registered athletes",
        "Payment Tracking": "Payment Tracking",
        "Monitor paid/unpaid registrations": "Monitor paid/unpaid registrations",
        "Export Data": "Export Data",
        "CSV exports for external systems": "CSV exports for external systems",
        "Medal Tracking": "Medal Tracking",
        "Record competition results": "Record competition results",
        "Admin Export/Import Tools": "Admin Export/Import Tools",
        "Bulk Operations": "Bulk Operations",
        "Import multiple players/events": "Import multiple players/events",
        "Data Backup": "Data Backup",
        "Full system backups": "Full system backups",
        "Migration Tools": "Migration Tools",
        "Database schema updates": "Database schema updates",
        "Daily Operations": "Daily Operations",
        "Morning Routine": "Morning Routine",
        "Check Calendar: Review scheduled events and training sessions": "Check Calendar: Review scheduled events and training sessions",
        "Record Attendance: Mark players present for training": "Record Attendance: Mark players present for training",
        "Monitor Payments: Check for overdue fees": "Monitor Payments: Check for overdue fees",
        "Weekly Tasks": "Weekly Tasks",
        "Process Payments: Record weekly/monthly fee collections": "Process Payments: Record weekly/monthly fee collections",
        "Update Medical Records: Verify insurance and medical exam validity": "Update Medical Records: Verify insurance and medical exam validity",
        "Event Preparation: Check upcoming event registrations": "Event Preparation: Check upcoming event registrations",
        "Monthly Procedures": "Monthly Procedures",
        "Generate Fee Reports: Identify outstanding payments": "Generate Fee Reports: Identify outstanding payments",
        "Process Monthly Dues: Record monthly training fees": "Process Monthly Dues: Record monthly training fees",
        "Update Insurance: Renew expiring medical/insurance records": "Update Insurance: Renew expiring medical/insurance records",
        "Backup Data: Export important data for safekeeping": "Backup Data: Export important data for safekeeping",
        "Advanced Features": "Advanced Features",
        "Calendar Integration": "Calendar Integration",
        "Interactive Calendar": "Interactive Calendar",
        "Click dates to create events (admin)": "Click dates to create events (admin)",
        "Event Details": "Event Details",
        "Click events for full information": "Click events for full information",
        "Attendance Tracking": "Attendance Tracking",
        "Daily participation numbers": "Daily participation numbers",
        "Multi-language Support": "Multi-language Support",
        "Localized date formats": "Localized date formats",
        "Data Validation": "Data Validation",
        "PN Validation": "PN Validation",
        "10-digit Bulgarian ID format checking": "10-digit Bulgarian ID format checking",
        "File Upload Security": "File Upload Security",
        "Type and size restrictions": "Type and size restrictions",
        "Duplicate Prevention": "Duplicate Prevention",
        "Automatic duplicate detection": "Automatic duplicate detection",
        "Backup & Recovery": "Backup & Recovery",
        "Automatic Backups": "Automatic Backups",
        "Export critical data regularly": "Export critical data regularly",
        "Data Integrity": "Data Integrity",
        "Foreign key relationships maintained": "Foreign key relationships maintained",
        "Recovery Procedures": "Recovery Procedures",
        "Restore from backups if needed": "Restore from backups if needed",
        "Support & Maintenance": "Support & Maintenance",
        "Regular Maintenance": "Regular Maintenance",
        "Database Cleanup": "Database Cleanup",
        "Remove old temporary files": "Remove old temporary files",
        "Photo Organization": "Photo Organization",
        "Organize uploaded images": "Organize uploaded images",
        "Performance Monitoring": "Performance Monitoring",
        "Check for slow operations": "Check for slow operations",
        "Update Dependencies": "Update Dependencies",
        "Keep Python packages current": "Keep Python packages current",
        "Getting Help": "Getting Help",
        "Documentation": "Documentation",
        "Refer to this guide and inline help": "Refer to this guide and inline help",
        "Error Logs": "Error Logs",
        "Check application logs for issues": "Check application logs for issues",
        "Use export features to verify data integrity": "Use export features to verify data integrity",
        "Report Issues": "Report Issues",
        "GitHub Issues - Report bugs and request features": "GitHub Issues - Report bugs and request features",
        "Note": "Note",
        "This application stores all data locally in SQLite. For production use, consider additional security measures and regular backups.": "This application stores all data locally in SQLite. For production use, consider additional security measures and regular backups.",
        "Overview": "Overview",
        "The Karate Club Management System is a comprehensive web application designed to manage all aspects of a karate club's operations. It handles player registration, training session tracking, payment management, event organization, and reporting.": "The Karate Club Management System is a comprehensive web application designed to manage all aspects of a karate club's operations. It handles player registration, training session tracking, payment management, event organization, and reporting.",
        "Please enter your Personal Number (ЕГН).": "Please enter your Player Number.",
        "Player with Personal Number {pn} not found.": "Player with number {id} not found.",
        "Player account is not active.": "Player account is not active.",
        "Session for today already recorded for {name}.": "Session for today already recorded for {name}.",
        "Wrong Player Number! Please enter your own number.": "Wrong Player Number! Please enter your own number.",
        "Welcome {name}! Your training session has been recorded successfully. Keep up the great work!": "Welcome {name}! 🎉 Your training session has been recorded successfully! You're doing amazing - keep pushing your limits and achieving greatness! 💪",
        "Session recording failed. Please try again.": "Session recording failed. Please try again.",
        "Kiosk Mode - Record Training Session": "Kiosk Mode - Record Training Session",
        "Enter your Personal Number (ЕГН)": "Enter your Player Number",
        "Record Session": "Record Session",
        "Cancel": "Cancel",
        "Click on your name to record a training session": "Click on your name to record a training session",
        "Kiosk Mode": "Kiosk Mode",
        "Search by name...": "Search by name...",
        "All Belts": "All Belts",
        "Search": "Search",
        "Admin View": "Admin View",
        "No players found": "No players found",
        "Try adjusting your search criteria.": "Try adjusting your search criteria.",
        "Selected athlete:": "Selected athlete:",
        "Enter your 10-digit Bulgarian ID number to confirm and record the session.": "Enter your 10-digit Bulgarian ID number to confirm and record the session.",
        "For quick session recording without admin login, use Kiosk Mode: athletes click their name and enter their Personal Number (ЕГН) to record training sessions.": "For quick session recording without admin login, use Kiosk Mode: athletes click their name and enter their Player Number to record training sessions.",
    },
    "bg": {
        # --- Grade/Belt labels ---
        "10 kyu – white belt": "10 кю – бял пояс",
        "9 kyu – white with yellow stripe": "9 кю – бял с жълта лента",
        "8 kyu – yellow belt": "8 кю – жълт пояс",
        "7 kyu – orange belt": "7 кю – оранжев пояс",
        "6 kyu – orange belt": "6 кю – оранжев пояс",
        "5 kyu – green belt": "5 кю – зелен пояс",
        "4 kyu – blue belt": "4 кю – син пояс",
        "3 kyu – blue belt": "3 кю – син пояс",
        "2 kyu – brown belt": "2 кю – кафяв пояс",
        "1 kyu – brown belt": "1 кю – кафяв пояс",
        "1 dan – black belt": "1 дан – черен пояс",
        "2 dan – black belt": "2 дан – черен пояс",
        "3 dan – black belt": "3 дан – черен пояс",
        "4 dan – black belt": "4 дан – черен пояс",
        "5 dan – black belt": "5 дан – черен пояс",
        # --- Navigation / Common ---
        "Team ENSO": "Team ENSO",
        "Karate Club": "Карате клуб",
        "Players": "Спортисти",
        "Calendar": "Календар",
        "Fees Report": "Отчет за такси",
        "Event List": "Списък събития",
        "+ Add Player": "+ Добави Спортист",
        "Add Player": "Добави Спортист",
        "Edit Player": "Редакция на Спортист",
        "Back": "Назад",
        "Previous": "Предишна",
        "Next": "Следваща",
        "Help & User Guide": "Помощ и ръководство",
        "Edit": "Редакция",
        "Run DB migration": "Стартирай миграция",
        "Admin Login": "Админ вход",
        "Admin exports": "Админ експорти",
        "Admin imports": "Админ импорти",
        "Imports": "Импорти",
        "Exports": "Експорти",
        "Export All Payments (CSV)": "Експорт всички плащания (CSV)",
        "Export Players (ZIP)": "Експорт спортисти (ZIP)",
        "Export Events (ZIP)": "Експорт събития (ZIP)",
        "Import Players (ZIP)": "Импорт спортисти (ZIP)",
        "Import Players (CSV)": "Импорт спортисти (CSV)",
        "Import Payments (CSV)": "Импорт плащания (CSV)",
        "Export All Profiles (ZIP)": "Експорт всички профили (ZIP)",
        "Delete": "Изтрий",
        "Logout": "Изход",
        "Language": "Език",
        "BG": "BG", "EN": "EN",
        "All": "Всички",

        # --- Filters / Table headers ---
        "Category Fees": "Такси за категории",
        "Search": "Търсене",
        "Grade": "Степен",
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

        # --- Player form / Profile ---
        "First Name": "Име",
        "Last Name": "Фамилия",
        "Gender": "Пол",
        "Birthdate": "Дата на раждане",
        "PN#": "ЕГН",
        "Belt Rank": "Колан",
        "Grade Level": "Степен (кю/дан)",
        "Grade Date": "Дата на изпит",
        "Weight (kg)": "Тегло (кг)",
        "Height (cm)": "Ръст (см)",
        "Join Date": "Дата на присъединяване",
        "Active Member": "Активен член",
        "Notes": "Бележки",
        "Photo (jpg/png/gif/webp, ≤ 2MB)": "Снимка (jpg/png/gиф/webp, ≤ 2MB)",
        "Save": "Запази",
        "Cancel": "Откажи",
        "Joined": "Присъединяване",
        "Mother Name": "Име на майката",
        "Mother Phone": "Телефон на майката",
        "Father Name": "Име на бащата",
        "Father Phone": "Телефон на бащата",
        "Actions": "Действия",
        "Profile": "Профил",
        "Contacts": "Контакти",
        "Fee": "Такса",
        "Fee (EUR)": "Такса (EUR)",
        "Categories & Medals": "Категории и медали",

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
        "Monthly": "Месечни",
        "Due date": "Падеж",
        "Amount": "Сума",
        "Paid": "Платено",
        "Unpaid": "Неплатено",
        "Owed": "Дължими",
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
        "Player": "Спортист",
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
        "Record Session": "Запиши тренировка",
        "Pay Due": "Плати дължимото",
        "Open payment form": "Отвори форма за плащане",
        "Receipt": "Квитанция",
        "Amount (EUR)": "Сума (EUR)",
        "Note": "Бележка",
        "Created": "Създадено",
        "Quick actions": "Бързи действия",
        "Training sessions": "Тренировки",
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
        "Paste/Import Categories": "Постави/Импортирай категории",
        "Paste tabular data (one row per category, columns: Name, Age from, Age to, Sex, Fee, Team size, KYU, DAN, Other cut-off date, Limit, Team Limit)": "Поставете таблични данни (по един ред за категория, колони: Име, Възраст от, Възраст до, Пол, Такса, Отбор, KYU, DAN, Друга дата, Лимит, Лимит отбор)",
        "Import": "Импортирай",
        "Import Event (ZIP)": "Импортирай събитие (ZIP)",
        "Sports Calendar": "Спортен календар",
        "Athletes participated:": "Участвали спортисти:",
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
        "Athlete": "Спортист",
        "Athlete(s)": "Спортист(и)",
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
        "Participants": "Спортисти",
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
        "Income": "Приходи",
        "Due": "Дължими",
        "Net Income": "Нетен доход",
        "Balance": "Баланс",
        "Net club revenue (training fees minus event pass-through)": "Нетни приходи на клуба (тренировъчни такси минус събитийни пас-тру)",
        "Period Fees Report": "Отчет за такси за период",
        "Player Summary": "Обобщение по играчи",
        "Bulk payment": "Групово плащане",
        "Generated on:": "Генерирано на:",
        "This will generate a comprehensive report showing all fees (monthly, per-session, and event) for the selected period.": "Това ще генерира цялостен отчет, показващ всички такси (месечни, на тренировка и за събития) за избрания период.",
        "Generate Report": "Генерирай отчет",
        "Period": "Период",
        "Back to Monthly Report": "Обратно към месечния отчет",
        "Total Income": "Общо приходи",
        "Total Due": "Общо дължими",
        "Monthly Fees": "Месечни такси",
        "Per Session Fees": "Такси на тренировка",
        "Event Fees": "Такси за събития",
        "Bulk": "Групови",
        "GRAND TOTAL": "ОБЩО",
        "Payment Details": "Детайли за плащането",
        "No active players found for the selected period.": "Няма активни спортисти за избрания период.",
        "Period Report": "Отчет за период",

        # --- Sportdata profiles ---
        "Sportdata": "Sportdata",
        "Sportdata Profiles": "Sportdata профили",
        "WKF Profile URL": "WKF профил (URL)",
        "BNFK Profile URL": "BNFK профил (URL)",
        "ENSO Profile URL": "ENSO профил (URL)",
        "Open": "Отвори",

        # --- Player Detail Page ---
        "No photo uploaded": "Няма качена снимка",
        "Export Profile (CSV)": "Експорт профил (CSV)",
        "Permanently delete": "Изтрий завинаги",
        "Permanently delete (PURGE)": "Изтрий завинаги (ИЗЧИСТИ)",
        "Permanently delete player": "Изтрий спортист завинаги",
        "This is irreversible. All player data will be removed but related historical rows will keep the PN#.": "Това е необратимо. Всички данни за спортиста ще бъдат премахнати, но свързаните исторически редове ще запазят ЕГН.",
        "To confirm, type the word": "За потвърждение, напишете думата",
        "in the box below": "в полето по-долу",
        "Total medals": "Общо медали",
        "No categories for this registration.": "Няма категории за това записване.",
        "month (optional)": "месец (по избор)",
        "Delete Player": "Изтрий Спортист",
        "Back to Players List": "Обратно към списъка със спортисти",
        "Player Details": "Детайли за Спортист",

        # --- Auth / Flash ---
        "Username": "Потребител",
        "Password": "Парола",
        "Admin login required.": "Необходим е администраторски вход.",
        "Logged in as admin.": "Влязохте като администратор.",
        "Invalid credentials.": "Невалидни данни за вход.",
        "Logged out.": "Излязохте.",
        "Player created.": "Спортистът е създаден.",
        "Player updated.": "Спортистът е обновен.",
        "Player deleted.": "Спортистът е изтрит.",
        "Failed to fully delete player and related records.": "Неуспешно пълно изтриване на спортист и свързаните записи.",
        "Player deleted (soft). Related registrations and payments preserved and linked by PN#.": "Спортистът е изтрит (меко). Свързаните регистрации и плащания са запазени и свързани по ЕГН.",
        "Missing or incorrect confirmation token. To permanently delete, POST with confirm=PURGE": "Липсващ или неправилен токен за потвърждение. За постоянно изтриване, изпратете POST с confirm=PURGE",
        "Purge failed: {e}": "Изчистването неуспешно: {e}",
        "Player permanently deleted and related rows backfilled with PN.": "Спортистът е постоянно изтрит и свързаните редове са попълнени с ЕГН.",
        "Backfilled {created_total} missing TrainingSession records.": "Попълнени {created_total} липсващи записи за тренировъчни сесии.",
        "No file uploaded": "Няма качен файл",
        "No file selected": "Няма избран файл",
        "Close": "Затвори",
        "DB migration: added columns: {cols}": "Миграция: добавени колони: {cols}",
        "DB migration: nothing to do.": "Миграция: няма какво да се прави.",
        "DB migration failed: {err}": "Миграция: грешка: {err}",

        # --- Player Deletion Confirmation ---
        "Confirm Player Deletion": "Потвърждение за изтриване на спортист",
        "Warning!": "Внимание!",
        "This player has outstanding debts. Deleting them may result in lost revenue.": "Този спортист има неплатени задължения. Изтриването му може да доведе до загуба на приходи.",
        "Player Information": "Информация за спортист",
        "Name:": "Име:",
        "PN#:": "ЕГН:",
        "Active Member:": "Активен член:",
        "Outstanding Debts": "Неплатени задължения",
        "Type": "Тип",
        "Description": "Описание",
        "Total Outstanding": "Общо неплатено",
        "Note:": "Бележка:",
        "Deleting this player will perform a soft delete - the player record will be deactivated but preserved for historical records. All related payments and registrations will be maintained.": "Изтриването на този спортист ще извърши меко изтриване - записът ще бъде деактивиран, но запазен за исторически данни. Всички свързани плащания и записвания ще бъдат запазени.",
        "Purging this player will permanently remove their record from the database. This action cannot be undone. Make sure you have a backup.": "Изчистването на този спортист ще премахне завинаги записа му от базата данни. Това действие не може да бъде отменено. Уверете се, че имате резервно копие.",
        "Delete Player Anyway": "Изтрий спортиста въпреки това",
        "Purge Player Anyway": "Изчисти спортиста въпреки това",
        "Are you absolutely sure you want to delete this player despite outstanding debts?": "Сигурни ли сте, че искате да изтриете този спортист въпреки неплатените задължения?",

        # --- Common UI ---
        "yes": "да",
        "no": "не",

        # --- Debt Types ---
        "monthly": "месечна",
        "sessions": "тренировки",
        "event": "събитие",

        # --- Enums / Days ---
        "—": "—",
        "Male": "Мъж", "Female": "Жена", "Other": "Друго",
        "White": "Бял", "Yellow": "Жълт", "Orange": "Оранжев",
        "WhiteYellow": "Бял с жълта лента",
        "Green": "Зелен", "Blue": "Син", "Purple": "Лилав",
        "Brown": "Кафяв", "Black": "Черен",
        "Kata": "Ката", "Kumite": "Кумите", "Makiwara": "Макивара", "All Disciplines": "Всички дисциплини",
        "Mon": "Пон", "Tue": "Вт", "Wed": "Ср", "Thu": "Чет", "Fri": "Пет", "Sat": "Съб", "Sun": "Нед",

        # --- Forms / Admin forms ---
        "Kind": "Вид",
        "Training (per month)": "Тренировка (месечно)",
        "Training (per session)": "Тренировка (на тренировка)",
        "Event Registration ID": "ID на записване за събитие",
        "Player ID": "ID на Спортист",
        "Month (YYYY-MM)": "Месец (ГГГГ-ММ)",
        "Currency": "Валута",
        "Method": "Метод",
        "Help & User Guide": "Помощ и ръководство",
        "Getting Started": "Първи стъпки",
        "Installation & Setup": "Инсталация и настройка",
        "Prerequisites: Python 3.8+ and pip": "Предварителни изисквания: Python 3.8+ и pip",
        "Create Virtual Environment": "Създайте виртуална среда",
        "Install Dependencies": "Инсталирайте зависимости",
        "Set Environment Variables": "Задайте променливи на средата",
        "Run the Application": "Стартирайте приложението",
        "Access: Open http://127.0.0.1:5000 in your browser": "Достъп: Отворете http://127.0.0.1:5000 в браузъра",
        "Language Support": "Поддръжка на езици",
        "The application supports Bulgarian (default) and English. Use the language switcher in the top navigation to change languages.": "Приложението поддържа български (по подразбиране) и английски. Използвайте превключвателя за език в горната навигация, за да промените езика.",
        "Player Management": "Управление на спортисти",
        "Adding New Players": "Добавяне на нови спортисти",
        "Navigate to Players → + Add Player": "Отидете в Спортисти → + Добави Спортист",
        "Fill in required information: First Name, Last Name, PN (10-digit Bulgarian ID), Gender, Birthdate, Belt Rank": "Попълнете задължителната информация: Име, Фамилия, ЕГН (10-цифрен български ID), Пол, Дата на раждане, Степен на колан",
        "Choose payment type: Monthly or per-session": "Изберете тип плащане: Месечно или на тренировка",
        "Add optional contact info, parent contacts, medical data, and photo": "Добавете допълнителна информация за контакт, родители, медицински данни и снимка",
        "Managing Players": "Управление на спортисти",
        "Search & Filter: Use the search bar and filters for belt rank, active status": "Търсене и филтриране: Използвайте лентата за търсене и филтрите за степен на колан, активен статус",
        "Edit Player: Click the edit button on any player profile": "Редактиране на спортист: Кликнете бутона за редактиране в профила на всеки спортист",
        "Record Sessions: For all players, record training attendance": "Записване на тренировки: За всички спортисти, записвайте присъствие на тренировки",
        "Payment Management: Track fees, generate receipts, mark payments": "Управление на плащания: Следете такси, генерирайте разписки, маркирайте плащания",
        "Training Session Tracking": "Проследяване на тренировъчни сесии",
        "Recording Sessions": "Записване на сесии",
        "Go to a player's profile": "Отидете в профила на спортист",
        "Click \"Record Session\" button": "Кликнете бутона \"Запиши тренировка\"",
        "Sessions are automatically marked as paid/unpaid based on payment type": "Сесиите се маркират автоматично като платени/неплатени въз основа на типа плащане",
        "Viewing Attendance": "Преглед на присъствие",
        "Calendar View: Visual calendar with session indicators": "Календарен изглед: Визуален календар с индикатори за сесии",
        "List View: Detailed chronological list of all sessions": "Изглед като списък: Подробен хронологичен списък на всички сесии",
        "Main Calendar: Club-wide calendar showing daily attendance numbers": "Основен календар: Календар на клуба, показващ дневни числа на присъствие",
        "Payment & Fee Management": "Управление на плащания и такси",
        "Payment Types": "Типове плащания",
        "Monthly Training": "Месечни тренировки",
        "Fixed monthly fee for unlimited sessions": "Фиксирана месечна такса за неограничени сесии",
        "Per-Session Training": "Тренировки на сесия",
        "Pay per individual training session": "Плащане за всяка отделна тренировъчна сесия",
        "Managing Payments": "Управление на плащания",
        "From Player Profile: Use quick action buttons to record payments": "От профила на спортист: Използвайте бутоните за бързи действия, за да записвате плащания",
        "Payment Forms: Create receipts for training, events, or outstanding debts": "Форми за плащане: Създавайте разписки за тренировки, събития или неизплатени дългове",
        "Toggle Payment Status: Mark payments as paid/unpaid": "Превключване на статуса на плащане: Маркирайте плащанията като платени/неплатени",
        "Print Receipts: Generate printable payment receipts": "Печат на разписки: Генерирайте разписки за печат",
        "Event Management": "Управление на събития",
        "Creating Events": "Създаване на събития",
        "Admin Access Required": "Изисква се администраторски достъп",
        "Navigate to Calendar → New Event": "Отидете в Календар → Ново събитие",
        "Event Details: Title, date range, location, categories with fees": "Детайли за събитието: Заглавие, период от дати, локация, категории с такси",
        "Player Registration": "Записване на спортисти",
        "Go to event details": "Отидете в детайлите на събитието",
        "Click \"Add Registration\"": "Кликнете \"Добави записване\"",
        "Select categories and mark payments": "Изберете категории и маркирайте плащания",
        "Reporting & Exports": "Отчети и експорти",
        "Available Reports": "Налични отчети",
        "Fee Reports: Monthly payment summaries": "Отчети за такси: Месечни обобщения на плащания",
        "Medal Reports: Competition results by year": "Отчети за медали: Резултати от състезания по години",
        "Player Lists: Filtered player directories": "Списъци на спортисти: Филтрирани директории на спортисти",
        "Payment Exports: Complete transaction history": "Експорти на плащания: Пълна история на транзакции",
        "Export Formats": "Формати за експорт",
        "Comma-separated values for spreadsheets": "Стойности, разделени със запетаи, за електронни таблици",
        "Complete data packages with photos": "Пълни пакети с данни със снимки",
        "Printable payment documents": "Документи за плащане, подходящи за печат",
        "Troubleshooting": "Отстраняване на проблеми",
        "Common Issues": "Чести проблеми",
        "Login Problems": "Проблеми с вход",
        "Verify ADMIN_USER and ADMIN_PASS environment variables": "Проверете променливите на средата ADMIN_USER и ADMIN_PASS",
        "File Upload Errors": "Грешки при качване на файлове",
        "Ensure files are under 2MB and in supported formats (JPG, PNG, GIF, WEBP)": "Уверете се, че файловете са под 2MB и в поддържани формати (JPG, PNG, GIF, WEBP)",
        "Calendar Display Issues": "Проблеми с показването на календара",
        "Clear browser cache, check JavaScript is enabled, verify date formats": "Изчистете кеша на браузъра, проверете дали JavaScript е активиран, проверете форматите на датите",
        "Payment Calculation Errors": "Грешки в изчисляването на плащания",
        "Verify player payment type settings and fee amounts": "Проверете настройките за тип плащане на спортист и сумите на таксите",
        "Data Recovery": "Възстановяване на данни",
        "Database Backup: Regular exports of karate_club.db": "Резервно копие на база данни: Редовни експорти на karate_club.db",
        "Photo Backup: Backup uploads/ directory": "Резервно копие на снимки: Резервно копие на директорията uploads/",
        "CSV Exports: Keep exported data for reference": "CSV експорти: Запазвайте експортираните данни за справка",
        "Security Best Practices": "Най-добри практики за сигурност",
        "Strong Passwords: Use complex admin passwords": "Силни пароли: Използвайте сложни администраторски пароли",
        "Regular Backups: Backup data before major changes": "Редовни резервни копия: Правете резервни копия преди големи промени",
        "Access Control: Limit admin access to authorized personnel": "Контрол на достъпа: Ограничете администраторския достъп до упълномощен персонал",
        "File Validation: Only upload trusted files": "Валидация на файлове: Качвайте само доверени файлове",
        "Session Management: Log out when not using the system": "Управление на сесии: Излизайте от системата, когато не я използвате",
        "Quick Start Guide": "Ръководство за бърз старт",
        "Add Players": "Добавете спортисти",
        "Start by adding your karate club members with their personal information and payment preferences.": "Започнете като добавите членовете на вашия клуб по karate с личната им информация и предпочитания за плащане.",
        "Record Sessions": "Записвайте сесии",
        "Track attendance for each training session to monitor participation and manage payments.": "Проследявайте присъствието за всяка тренировъчна сесия, за да наблюдавате участието и управлявате плащанията.",
        "Manage Payments": "Управлявайте плащания",
        "Keep track of fees, generate receipts, and monitor outstanding payments.": "Следете таксите, генерирайте разписки и наблюдавайте неизплатените плащания.",

        # --- Additional Help Section Translations ---
        "Clone/Download the application files": "Клонирайте/изтеглете файловете на приложението",
        "(On Windows: .venv\\Scripts\\activate)": "(В Windows: .venv\\Scripts\\activate)",
        "User Roles & Access": "Потребителски роли и достъп",
        "Regular Users": "Обикновени потребители",
        "View public player profiles": "Преглед на публични профили на спортисти",
        "Access basic information": "Достъп до основна информация",
        "Administrators": "Администратори",
        "Full access to all features": "Пълен достъп до всички функции",
        "Login required for sensitive operations": "Изисква се вход за чувствителни операции",
        "Use the admin login form with credentials set in environment variables": "Използвайте формата за администраторски вход с идентификационни данни, зададени в променливите на средата",
        "First Name & Last Name": "Име и Фамилия",
        "Player's full name": "Пълното име на спортиста",
        "PN (Personal Number)": "ЕГН (Личен номер)",
        "Mandatory 10-digit Bulgarian ID number (ЕГН)": "Задължителен 10-цифрен български идентификационен номер (ЕГН)",
        "Male/Female/Other": "Мъж/Жена/Друго",
        "Date of birth": "Дата на раждане",
        "Current karate belt level": "Текущо ниво на карате колан",
        "Kyu/Dan ranking": "Кю/Дан класиране",
        "Monthly or per-session": "Месечно или на тренировка",
        "Optional information": "Допълнителна информация",
        "Contact details (phone, email)": "Данни за контакт (телефон, имейл)",
        "Parent contacts (for minors)": "Контакти с родители (за непълнолетни)",
        "Medical examination and insurance expiry dates": "Дати на медицински преглед и изтичане на застраховка",
        "Photo upload (JPG/PNG/GIF/WEBP, max 2MB)": "Качване на снимка (JPG/PNG/GIF/WEBP, макс 2MB)",
        "View Profile": "Преглед на профил",
        "Click on a player's name to see detailed information": "Кликнете върху името на спортист, за да видите подробна информация",
        "Player Profile Features": "Функции на профила на спортист",
        "Training Calendar": "Тренировъчен календар",
        "Interactive calendar showing sessions and events": "Интерактивен календар, показващ сесии и събития",
        "Payment History": "История на плащанията",
        "View all payments and receipts": "Преглед на всички плащания и разписки",
        "Event Registrations": "Записвания за събития",
        "See registered events and payment status": "Вижте записаните събития и статуса на плащане",
        "Quick Actions": "Бързи действия",
        "Print due fees, export profile data": "Печат на дължими такси, експорт на данни от профил",
        "Monthly payers": "Месечни платци",
        "Sessions are free (marked as paid)": "Сесиите са безплатни (маркирани като платени)",
        "Per-session payers": "Платци на тренировка",
        "Sessions require payment": "Сесиите изискват плащане",
        "Calendar View": "Календарен изглед",
        "Visual calendar with session indicators": "Визуален календар с индикатори за сесии",
        "List View": "Изглед като списък",
        "Detailed chronological list of all sessions": "Подробен хронологичен списък на всички сесии",
        "Main Calendar": "Основен календар",
        "Club-wide calendar showing daily attendance numbers": "Календар на клуба, показващ дневни числа на присъствие",
        "Fee Tracking": "Проследяване на такси",
        "Outstanding Debts": "Неизплатени дългове",
        "View unpaid fees across all players": "Преглед на неплатени такси за всички спортисти",
        "Complete transaction history": "Пълна история на транзакциите",
        "Due Fee Reports": "Отчети за дължими такси",
        "Generate reports for unpaid amounts": "Генерирайте отчети за неплатени суми",
        "Event Categories": "Категории на събития",
        "Define competition categories (age, weight, belt requirements)": "Дефинирайте категории за състезания (възраст, тегло, изисквания за колан)",
        "Set registration fees per category": "Задайте такси за записване за всяка категория",
        "Configure team size limits and registration cut-off dates": "Конфигурирайте лимити за размер на отбора и крайни срокове за записване",
        "Select categories and fee overrides if needed": "Изберете категории и отмени на такси, ако е необходимо",
        "Mark payments and track registration status": "Маркирайте плащания и проследявайте статуса на записване",
        "Event Reporting": "Отчети за събития",
        "Registration Lists": "Списъци за записване",
        "View all registered athletes": "Преглед на всички записани спортисти",
        "Payment Tracking": "Проследяване на плащания",
        "Monitor paid/unpaid registrations": "Наблюдавайте платени/неплатени записвания",
        "Export Data": "Експорт на данни",
        "CSV exports for external systems": "CSV експорти за външни системи",
        "Medal Tracking": "Проследяване на медали",
        "Record competition results": "Записвайте резултати от състезания",
        "Admin Export/Import Tools": "Инструменти за експорт/импорт на администратор",
        "Bulk Operations": "Масови операции",
        "Import multiple players/events": "Импорт на множество спортисти/събития",
        "Data Backup": "Резервно копие на данни",
        "Full system backups": "Пълни резервни копия на системата",
        "Migration Tools": "Инструменти за миграция",
        "Database schema updates": "Актуализации на схемата на базата данни",
        "Daily Operations": "Дневни операции",
        "Morning Routine": "Утринна рутина",
        "Check Calendar: Review scheduled events and training sessions": "Проверете календара: Прегледайте планирани събития и тренировъчни сесии",
        "Record Attendance: Mark players present for training": "Запишете присъствие: Маркирайте присъстващите спортисти за тренировка",
        "Monitor Payments: Check for overdue fees": "Наблюдавайте плащания: Проверете за просрочени такси",
        "Weekly Tasks": "Седмични задачи",
        "Process Payments: Record weekly/monthly fee collections": "Обработете плащания: Запишете седмични/месечни събирания на такси",
        "Update Medical Records: Verify insurance and medical exam validity": "Актуализирайте медицински записи: Проверете валидността на застраховка и медицински преглед",
        "Event Preparation: Check upcoming event registrations": "Подготовка за събития: Проверете предстоящите записвания за събития",
        "Monthly Procedures": "Месечни процедури",
        "Generate Fee Reports: Identify outstanding payments": "Генерирайте отчети за такси: Идентифицирайте неизплатените плащания",
        "Process Monthly Dues: Record monthly training fees": "Обработете месечни вноски: Запишете месечни такси за тренировки",
        "Update Insurance: Renew expiring medical/insurance records": "Актуализирайте застраховка: Подновете изтичащи медицински/застрахователни записи",
        "Backup Data: Export important data for safekeeping": "Резервно копие на данни: Експортирайте важни данни за съхранение",
        "Advanced Features": "Разширени функции",
        "Calendar Integration": "Интеграция с календар",
        "Interactive Calendar": "Интерактивен календар",
        "Click dates to create events (admin)": "Кликнете върху дати, за да създадете събития (администратор)",
        "Event Details": "Детайли за събитието",
        "Click events for full information": "Кликнете върху събития за пълна информация",
        "Attendance Tracking": "Проследяване на присъствие",
        "Daily participation numbers": "Дневни числа на участие",
        "Multi-language Support": "Поддръжка на множество езици",
        "Localized date formats": "Локализирани формати на дати",
        "Data Validation": "Валидация на данни",
        "PN Validation": "Валидация на ЕГН",
        "10-digit Bulgarian ID format checking": "Проверка на формат на 10-цифрен български ID",
        "File Upload Security": "Сигурност при качване на файлове",
        "Type and size restrictions": "Ограничения за тип и размер",
        "Duplicate Prevention": "Предотвратяване на дубликати",
        "Automatic duplicate detection": "Автоматично откриване на дубликати",
        "Backup & Recovery": "Резервно копие и възстановяване",
        "Automatic Backups": "Автоматични резервни копия",
        "Export critical data regularly": "Експортирайте критични данни редовно",
        "Data Integrity": "Целост на данните",
        "Foreign key relationships maintained": "Поддържат се връзки с външни ключове",
        "Recovery Procedures": "Процедури за възстановяване",
        "Restore from backups if needed": "Възстановете от резервни копия, ако е необходимо",
        "Support & Maintenance": "Поддръжка и обслужване",
        "Regular Maintenance": "Редовно обслужване",
        "Database Cleanup": "Почистване на база данни",
        "Remove old temporary files": "Премахнете стари временни файлове",
        "Photo Organization": "Организация на снимки",
        "Organize uploaded images": "Организирайте качените изображения",
        "Performance Monitoring": "Мониторинг на производителността",
        "Check for slow operations": "Проверете за бавни операции",
        "Update Dependencies": "Актуализирайте зависимости",
        "Keep Python packages current": "Поддържайте Python пакетите актуални",
        "Getting Help": "Получаване на помощ",
        "Documentation": "Документация",
        "Refer to this guide and inline help": "Обърнете се към това ръководство и вградена помощ",
        "Error Logs": "Дневници за грешки",
        "Check application logs for issues": "Проверете дневниците на приложението за проблеми",
        "Use export features to verify data integrity": "Използвайте функции за експорт, за да проверите целостта на данните",
        "Report Issues": "Докладвайте проблеми",
        "GitHub Issues - Report bugs and request features": "GitHub Issues - Докладвайте грешки и искайте функции",
        "Note": "Забележка",
        "This application stores all data locally in SQLite. For production use, consider additional security measures and regular backups.": "Това приложение съхранява всички данни локално в SQLite. За производствена употреба, обмислете допълнителни мерки за сигурност и редовни резервни копия.",
        "Overview": "Обзор",
        "The Karate Club Management System is a comprehensive web application designed to manage all aspects of a karate club's operations. It handles player registration, training session tracking, payment management, event organization, and reporting.": "Системата за управление на клуб по karate е цялостно уеб приложение, предназначено да управлява всички аспекти на операциите на клуб по karate. То обработва регистрация на спортисти, проследяване на тренировъчни сесии, управление на плащания, организация на събития и отчитане.",
        "Please enter your Personal Number (ЕГН).": "Моля, въведете вашия номер на спортист.",
        "Player with Personal Number {pn} not found.": "Спортист с номер {id} не е намерен.",
        "Player account is not active.": "Профилът на спортиста не е активен.",
        "Session for today already recorded for {name}.": "Сесията за днес вече е записана за {name}.",
        "Wrong Player Number! Please enter your own number.": "Грешен номер на спортист! Моля, въведете вашия собствен номер.",
        "Welcome {name}! Your training session has been recorded successfully. Keep up the great work!": "Добре дошъл {name}! 🎉 Твоята тренировъчна сесия е записана успешно! Ти си невероятен - продължавай да се бориш и постигай велики неща! 💪",
        "Session recording failed. Please try again.": "Записването на сесията е неуспешно. Моля, опитайте отново.",
        "Kiosk Mode - Record Training Session": "Режим Кiosk - Записване на тренировъчна сесия",
        "Enter your Personal Number (ЕГН)": "Въведете вашия номер на спортист",
        "Record Session": "Запиши тренировка",
        "Cancel": "Отказ",
        "Click on your name to record a training session": "Кликнете върху името си, за да запишете тренировъчна сесия",
        "Kiosk Mode": "Режим Kiosk",
        "Search by name...": "Търсене по име...",
        "All Belts": "Всички колани",
        "Search": "Търсене",
        "Admin View": "Админ изглед",
        "No players found": "Няма намерени спортисти",
        "Try adjusting your search criteria.": "Опитайте да коригирате критериите за търсене.",
        "Selected athlete:": "Избран спортист:",
        "Enter your 10-digit Bulgarian ID number to confirm and record the session.": "Въведете вашия номер на спортист, за да потвърдите и запишете сесията.",
        "For quick session recording without admin login, use Kiosk Mode: athletes click their name and enter their Personal Number (ЕГН) to record training sessions.": "За бързо записване на сесии без администраторски вход, използвайте режим Kiosk: спортистите кликват върху името си и въвеждат своя номер на спортист, за да запишат тренировъчни сесии.",
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
    # include WhiteYellow so users can filter 9 kyu
    "belt_colors": ["White", "WhiteYellow", "Yellow", "Orange", "Green", "Blue", "Purple", "Brown", "Black"],
    "grade_to_color": {
           "10 kyu": "White",
           "9 kyu": "WhiteYellow",
           "8 kyu": "Yellow",
           "7 kyu": "Orange",
           "6 kyu": "Orange",
           "5 kyu": "Green",
           "4 kyu": "Blue",
           "3 kyu": "Blue",
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
    # Centered yellow stripe on white background
    "WhiteYellow": "linear-gradient(90deg, #f8f9fa 0 40%, #ffd60a 40% 60%, #f8f9fa 60% 100%)",
}

# Medal color palette for icons
MEDAL_COLORS = {
    "gold":   "#ffd700",
    "silver": "#bfc1c2",
    "bronze": "#a97142",  # darker bronze
}

# Store short keys in DB; present localized labels in UI
DISCIPLINE_CHOICES = [
    ("All", "All Disciplines"),
    ("Kata", "Kata"),
    ("Kumite", "Kumite"),
    ("Makiwara", "Makiwara"),
]
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

def medal_icon_style(medal: Optional[str]) -> str:
    color = MEDAL_COLORS.get((medal or '').lower(), '#cccccc')
    return f"color: {color}; font-size: 1.2em;"

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

def scrape_bnfk_events():
    """Scrape events from BNFK calendar for informational display."""
    import json
    from datetime import datetime
    from dateutil import parser as date_parser
    import re
    
    cache_file = os.path.join(BASE_DIR, 'bnfk_cache.json')
    cache_duration_hours = 24
    
    # Check if we have a valid cache
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if (datetime.now() - cached_time).total_seconds() < (cache_duration_hours * 3600):
                # Cache is still valid, return cached events
                return cache_data['events']
        except (json.JSONDecodeError, KeyError, ValueError):
            # Cache is corrupted, continue to scrape
            pass
    
    # Scrape fresh data
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://www.bnfk.bg/calendar"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the calendar table
        events = []
        
        # Helper function to parse dates from various formats
        def parse_dates(date_str):
            date_str = date_str.strip()
            # Try to find date patterns using regex
            # Patterns: DD.MM.YYYY, DD/MM/YYYY, DD.MM, etc.
            date_pattern = re.compile(r'(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?')
            matches = date_pattern.findall(date_str)
            
            if not matches:
                # Try dateutil for other formats like "24 януари 2026"
                try:
                    parsed = date_parser.parse(date_str, fuzzy=True)
                    return parsed.date(), parsed.date()
                except:
                    return None, None
            
            dates = []
            for match in matches:
                day, month, year = match
                day = int(day)
                month = int(month)
                if year:
                    year = int(year)
                else:
                    year = date.today().year
                    # If month is before current, assume next year
                    current_month = date.today().month
                    if month < current_month:
                        year += 1
                try:
                    dates.append(date(year, month, day))
                except ValueError:
                    continue
            
            if len(dates) == 1:
                return dates[0], dates[0]
            elif len(dates) == 2:
                return dates[0], dates[1]
            else:
                return None, None
        
        # Look for table rows with event data
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    date_range = cols[0].get_text(strip=True)
                    title = cols[1].get_text(strip=True)
                    location = cols[2].get_text(strip=True)
                    
                    # Parse dates
                    start_date, end_date = parse_dates(date_range)
                    if not start_date:
                        app.logger.warning(f'Could not parse date: {date_range}')
                        continue
                    
                    events.append({
                        'title': f'🇧🇬 BNFK: {title}',
                        'start_date': start_date,
                        'end_date': end_date,
                        'location': location,
                        'url': url,  # Link back to BNFK calendar
                        'is_external': True
                    })
        
        # Cache the results
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'events': events
        }
        
        # Convert date objects to ISO strings for JSON serialization
        for event in cache_data['events']:
            event['start_date'] = event['start_date'].isoformat()
            event['end_date'] = event['end_date'].isoformat()
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            # If caching fails, just continue without caching
            pass
        
        return events
        
    except Exception as e:
        app.logger.warning(f'Failed to scrape BNFK events: {e}')
        # Try to return cached data even if expired
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                return cache_data.get('events', [])
            except Exception:
                pass
        return []

def parse_month_str(month_str: Optional[str]) -> Tuple[int, int]:
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
        exists = Payment.query.filter_by(player_pn=p.pn, year=year, month=month).first()
        if not exists:
            db.session.add(Payment(
                player_id=p.id,
                player_pn=p.pn,
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

# Preview a single training session
@app.route('/admin/training_session/<session_id>')
@admin_required
def preview_training_session(session_id):
    session = TrainingSession.query.filter_by(session_id=session_id).first()
    if not session:
        flash(_('Training session not found.'), 'danger')
        return redirect(url_for('players_list'))
    player = Player.query.get(session.player_id)
    return render_template('training_session_preview.html', session=session, player=player)

# -----------------------------
# Models
# -----------------------------
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), nullable=True)
    birthdate = db.Column(db.Date, nullable=True)
    pn = db.Column(db.String(10), nullable=False)  # Personal Number / ЕГН (mandatory, 10 digits)

    belt_rank = db.Column(db.String(20), nullable=False, default="White")
    grade_level = db.Column(db.String(20), nullable=True)
    grade_date = db.Column(db.Date, nullable=True)

    discipline = db.Column(db.String(10), nullable=False, default="All")
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
    player_id = db.Column(db.Integer, nullable=False, index=True)
    player_pn = db.Column(db.String(20), nullable=True, index=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1..12
    amount = db.Column(db.Integer, nullable=True)  # EUR
    paid = db.Column(db.Boolean, default=False)
    paid_on = db.Column(db.Date, nullable=True)

    player = db.relationship("Player", primaryjoin="Player.id==foreign(Payment.player_id)", foreign_keys=[player_id], backref=db.backref("payments", lazy="dynamic"))

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
    name = db.Column(db.String(120), nullable=False)  # Categories
    age_from = db.Column(db.Integer, nullable=True)
    age_to = db.Column(db.Integer, nullable=True)
    sex = db.Column(db.String(10), nullable=True)
    fee = db.Column(db.Integer, nullable=True)  # EUR
    team_size = db.Column(db.String(20), nullable=True)
    kyu = db.Column(db.String(20), nullable=True)
    dan = db.Column(db.String(20), nullable=True)
    other_cutoff_date = db.Column(db.String(40), nullable=True)
    limit_team = db.Column(db.String(20), nullable=True)
    limit = db.Column(db.String(20), nullable=True)

class EventRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False, index=True)
    player_id = db.Column(db.Integer, nullable=False, index=True)
    player_pn = db.Column(db.String(20), nullable=True, index=True)

    fee_override = db.Column(db.Integer, nullable=True)  # EUR
    paid = db.Column(db.Boolean, default=False)
    paid_on = db.Column(db.Date, nullable=True)

    player = db.relationship("Player", primaryjoin="Player.id==foreign(EventRegistration.player_id)", foreign_keys=[player_id], backref=db.backref("event_registrations", cascade="all, delete-orphan", lazy="dynamic"))

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

    player_id = db.Column(db.Integer, nullable=False, index=True)
    player_pn = db.Column(db.String(20), nullable=True, index=True)
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
    player = db.relationship("Player", primaryjoin="Player.id==foreign(PaymentRecord.player_id)", foreign_keys=[player_id])
    payment = db.relationship("Payment")
    event_registration = db.relationship("EventRegistration")
    related_receipt_id = db.Column(db.Integer, db.ForeignKey("payment_record.id"), nullable=True, index=True)
    related_receipt = db.relationship("PaymentRecord", remote_side=[id], backref="related_payments")

    def assign_receipt_no(self, do_commit: bool = True):
        if not self.id:
            return
        stamp = (self.paid_at or datetime.utcnow()).strftime("%Y%m%d")
        self.receipt_no = f"RCPT-{stamp}-{self.id:06d}"
        db.session.add(self)
        if do_commit:
            db.session.commit()

class Setting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(500), nullable=True)

# -----------------------------
# Forms
# -----------------------------
class PlayerForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    gender = SelectField("Gender", validators=[VOptional()], render_kw={"style": "max-width: 99px; display: inline-block;"})
    birthdate = DateField("Birthdate", validators=[VOptional()], render_kw={"style": "max-width: 132px; display: inline-block;"})
    pn = StringField("PN#", validators=[DataRequired(), Length(min=10, max=10), Regexp(r'^\d{10}$', message="PN must be exactly 10 digits")], render_kw={"style": "max-width: 120px; display: inline-block;"})
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

class SettingsForm(FlaskForm):
    logo = FileField("Logo", validators=[VOptional()])
    admin_password = PasswordField("Admin Password", validators=[VOptional(), Length(min=6)])
    background = FileField("Background Image", validators=[VOptional()])
    primary_color = StringField("Primary Color", validators=[VOptional(), Regexp(r'^#[0-9a-fA-F]{6}$', message="Invalid hex color")])
    secondary_color = StringField("Secondary Color", validators=[VOptional(), Regexp(r'^#[0-9a-fA-F]{6}$', message="Invalid hex color")])
    submit = SubmitField("Save Settings")

def set_localized_choices(form: PlayerForm):
    form.grade_level.choices = [(g, g) for g in GRADING_SCHEME["grades"]]
    # Display localized label, store short key in DB
    form.discipline.choices = [(value, _(label)) for (value, label) in DISCIPLINE_CHOICES]
    form.gender.choices = [("", _("—"))] + [(v, _(v)) for v in GENDER_VALUES]

# -----------------------------
@app.context_processor
def inject_settings():
    settings = {s.key: s.value for s in Setting.query.all()}
    return dict(
        app_logo=settings.get('logo_path', '/static/img/enso-logo.webp'),
        app_background=settings.get('background_image'),
        app_primary_color=settings.get('primary_color', '#007bff'),
        app_secondary_color=settings.get('secondary_color', '#6c757d'),
    )
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
        medal_icon_style=medal_icon_style,
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
        # Health/insurance badges via helper for consistent UX
        p.med_text, p.med_color = validity_badge(p.medical_expiry_date)
        p.ins_text, p.ins_color = validity_badge(p.insurance_expiry_date)

        sess_records = (PaymentRecord.query
                        .filter_by(player_pn=p.pn, kind='training_session')
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

        # Use TrainingSession for per-session logic
        all_sessions = TrainingSession.query.filter_by(player_pn=p.pn).all()
        paid_sessions = [s for s in all_sessions if s.paid]
        unpaid_sessions = [s for s in all_sessions if not s.paid]
        p.total_sessions_taken = len(all_sessions)
        p.total_sessions_paid = len(paid_sessions)
        p.total_sessions_unpaid = len(unpaid_sessions)
        per_session_price = float(p.monthly_fee_amount) if p.monthly_fee_amount and not p.monthly_fee_is_monthly else None
        p.per_session_price = per_session_price
        p.owed_amount = int(round(p.total_sessions_unpaid * per_session_price)) if per_session_price else 0

        # Ensure monthly_due_amount and monthly_due_paid are always set
        if not hasattr(p, 'monthly_due_amount'):
            p.monthly_due_amount = None
        if not hasattr(p, 'monthly_due_paid'):
            p.monthly_due_paid = None

        # monthly dues (optional, skip if month_year not set)
        p.monthly_due_amount = None
        p.monthly_due_paid = None
        if 'month_year' in locals() and month_year:
            try:
                yy, mm = month_year
                pay_row = Payment.query.filter_by(player_pn=p.pn, year=yy, month=mm).first()
                if pay_row:
                    p.monthly_due_amount = pay_row.amount or 0
                    p.monthly_due_paid = bool(pay_row.paid)
            except Exception:
                pass

        # Mark as having debt if session, monthly, or event debt exists
        p.has_debt = False
        if p.owed_amount > 0:
            p.has_debt = True
        if p.monthly_due_amount is not None and not p.monthly_due_paid and p.monthly_due_amount > 0:
            p.has_debt = True
        # Check for unpaid event registrations with a fee
        unpaid_regs = EventRegistration.query.filter_by(player_pn=p.pn, paid=False).all()
        for reg in unpaid_regs:
            fee = reg.fee_override if reg.fee_override is not None else reg.computed_fee()
            if fee and fee > 0:
                p.has_debt = True
                break

    return render_template(
        "players_list.html",
        players=players, q=q, belt=belt, active=active,
        belts=GRADING_SCHEME["belt_colors"]
    )
    regs = (EventRegistration.query
            .filter_by(player_pn=player.pn)
            .join(Event)
            .order_by(Event.start_date.desc())
            .all())
    return render_template(
        "player_detail_public.html",
        player=player,
        regs=regs,
    )

@app.route("/players/<int:player_id>")
def player_detail(player_id: int):
    if not session.get('is_admin'):
        abort(403)
    player = Player.query.get_or_404(player_id)
    today = date.today()
    try:
        ensure_payments_for_month(today.year, today.month)
    except Exception:
        pass

    # Use player PN when available, otherwise fall back to player_id for legacy rows
    pay_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
    current_payment = Payment.query.filter_by(**pay_filter, year=today.year, month=today.month).first()
    reg_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
    regs = (EventRegistration.query
        .filter_by(**reg_filter)
        .join(Event)
        .order_by(Event.start_date.desc())
        .all())

    # Use TrainingSession for session logic (unified with player list)
    sess_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
    all_sessions = TrainingSession.query.filter_by(**sess_filter).order_by(TrainingSession.date.desc()).all()
    paid_sessions = [s for s in all_sessions if s.paid]
    unpaid_sessions = [s for s in all_sessions if not s.paid]
    total_sessions_taken = len(all_sessions)
    total_sessions_paid = len(paid_sessions)
    total_sessions_unpaid = len(unpaid_sessions)
    per_session_price = float(player.monthly_fee_amount) if player.monthly_fee_amount and not player.monthly_fee_is_monthly else None
    owed_amount = int(round(total_sessions_unpaid * per_session_price)) if per_session_price else 0
    # Only show session receipts for sessions counted as paid
    # Filter PaymentRecords for kind='training_session' and limit to total_sessions_paid
    rec_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
    all_receipts = PaymentRecord.query.filter_by(**rec_filter, kind='training_session').order_by(PaymentRecord.paid_at.desc()).all()
    sess_records = all_receipts[:total_sessions_paid]
    
    # Prepare sessions data for calendar
    sessions_data = [{
        'id': s.id,
        'session_id': s.session_id,
        'date': s.date.isoformat() if s.date else None,
        'paid': s.paid,
        'created_at': s.created_at.isoformat() if s.created_at else None
    } for s in all_sessions]
    
    # Prepare events data for calendar
    events_data = []
    for reg in regs:
        event = reg.event
        if event.start_date:
            events_data.append({
                'id': event.id,
                'title': event.title,
                'start_date': event.start_date.isoformat(),
                'end_date': event.end_date.isoformat() if event.end_date else event.start_date.isoformat(),
                'location': event.location,
                'paid': reg.paid,
                'fee': reg.computed_fee()
            })
    
    return render_template(
        "player_detail.html",
        player=player,
        current_payment=current_payment,
        regs=regs,
        all_sessions=sessions_data,
        events_data=events_data,
        total_sessions_paid=total_sessions_paid,
        total_sessions_taken=total_sessions_taken,
        total_sessions_unpaid=total_sessions_unpaid,
        per_session_amount=per_session_price,
        owed_amount=owed_amount,
        payment_count=db.session.query(PaymentRecord).filter_by(**({'player_pn': player.pn} if player.pn else {'player_id': player.id})).count(),
        sess_records=sess_records,
    )

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):

    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)

# -------- Player CSV Export (Single) ----------
@app.route("/players/<int:player_id>/export_csv")
def export_player_csv(player_id):
    if not session.get('is_admin'):
        abort(403)
    import csv
    from io import StringIO
    player = Player.query.get_or_404(player_id)
    # Collect all Player fields for CSV
    fieldnames = [
        'id', 'first_name', 'last_name', 'gender', 'birthdate', 'pn',
        'belt_rank', 'grade_level', 'grade_date', 'discipline', 'weight_kg', 'height_cm',
        'email', 'phone', 'join_date', 'active_member', 'notes', 'photo_filename',
        'sportdata_wkf_url', 'sportdata_bnfk_url', 'sportdata_enso_url',
        'medical_exam_date', 'medical_expiry_date', 'insurance_expiry_date',
        'monthly_fee_amount', 'monthly_fee_is_monthly',
        'mother_name', 'mother_phone', 'father_name', 'father_phone'
    ]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    row = {k: getattr(player, k, '') for k in fieldnames}
    # Convert dates and booleans to string
    for k, v in row.items():
        if hasattr(v, 'isoformat'):
            row[k] = v.isoformat()
        elif isinstance(v, bool):
            row[k] = str(v)
    writer.writerow(row)
    output.seek(0)
    # Use ASCII-only fallback for filename, but provide UTF-8 version for browsers that support it
    ascii_filename = f"player_{player.id}.csv"
    utf8_filename = f"player_{player.id}_{player.last_name}.csv"
    headers = {
        'Content-Disposition': f'attachment; filename="{ascii_filename}"; filename*=UTF-8''{utf8_filename}'
    }
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers=headers
    )

# -------- Bulk Player CSV Export (ZIP) ----------
@app.route("/players/export_zip", endpoint="export_players_zip")
def export_players_zip():
    if not session.get('is_admin'):
        abort(403)
    import csv
    from io import StringIO, BytesIO
    import zipfile
    players = Player.query.order_by(Player.last_name.asc(), Player.first_name.asc()).all()
    fieldnames = [
        'id', 'first_name', 'last_name', 'gender', 'birthdate', 'pn',
        'belt_rank', 'grade_level', 'grade_date', 'discipline', 'weight_kg', 'height_cm',
        'email', 'phone', 'join_date', 'active_member', 'notes', 'photo_filename',
        'sportdata_wkf_url', 'sportdata_bnfk_url', 'sportdata_enso_url',
        'medical_exam_date', 'medical_expiry_date', 'insurance_expiry_date',
        'monthly_fee_amount', 'monthly_fee_is_monthly',
        'mother_name', 'mother_phone', 'father_name', 'father_phone'
    ]
    mem_zip = BytesIO()
    with zipfile.ZipFile(mem_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for player in players:
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            row = {k: getattr(player, k, '') for k in fieldnames}
            for k, v in row.items():
                if hasattr(v, 'isoformat'):
                    row[k] = v.isoformat()
                elif isinstance(v, bool):
                    row[k] = str(v)
            writer.writerow(row)
            output.seek(0)
            filename = f"player_{player.id}_{player.last_name}.csv"
            zf.writestr(filename, output.getvalue())
    mem_zip.seek(0)
    return Response(
        mem_zip.getvalue(),
        mimetype='application/zip',
        headers={
            'Content-Disposition': 'attachment; filename=players_profiles.zip'
        }
    )

# -------- Auth ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("list_players")
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        # Check settings first
        setting = Setting.query.filter_by(key='admin_password_hash').first()
        if setting:
            import hashlib
            hashed = hashlib.sha256(password.encode()).hexdigest()
            if username == ADMIN_USER and hashed == setting.value:
                session["is_admin"] = True
                flash(_("Logged in as admin."), "success")
                if next_url.endswith("/login") or next_url.startswith("/login?"):
                    next_url = url_for("list_players")
                return redirect(next_url)
        # Fallback to env
        elif username == ADMIN_USER and password == ADMIN_PASS:
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

@app.route("/help")
def help_page():
    return render_template("help.html", _=_ , current_lang=get_lang())

@app.route("/kiosk")
def kiosk():
    """Kiosk mode: Public player list for session recording without admin login."""
    q = request.args.get("q", "").strip()
    belt = request.args.get("belt", "")
    active = request.args.get("active", "")

    query = Player.query.filter_by(active_member=True)  # Only show active members

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Player.first_name.ilike(like), Player.last_name.ilike(like)))

    if belt:
        query = query.filter_by(belt_rank=belt)

    players = query.order_by(Player.last_name.asc(), Player.first_name.asc()).all()

    # Get belt colors for display
    belt_colors = {}
    for p in players:
        belt_colors[p.id] = BELT_PALETTE.get(p.belt_rank, "#f8f9fa")

    return render_template("kiosk.html", players=players, belt_colors=belt_colors, q=q, belt=belt, active=active)

@app.route("/kiosk/record_session", methods=["POST"])
def kiosk_record_session():
    """Kiosk mode: Record session by player ID."""
    player_id_str = request.form.get("player_id", "").strip()
    expected_player_id_str = request.form.get("expected_player_id", "").strip()
    
    if not player_id_str:
        flash(_("Please enter your Player Number."), "warning")
        return redirect(url_for("kiosk"))
    
    try:
        player_id = int(player_id_str)
        expected_player_id = int(expected_player_id_str)
    except ValueError:
        flash(_("Player Number must be a valid number."), "danger")
        return redirect(url_for("kiosk"))
    
    # Verify the entered ID matches the expected player
    if player_id != expected_player_id:
        flash(_("Wrong Player Number! Please enter your own number."), "danger")
        return redirect(url_for("kiosk"))
    
    # Find player by ID
    player = Player.query.get(player_id)
    if not player:
        flash(_("Player with number {id} not found.").format(id=player_id), "danger")
        return redirect(url_for("kiosk"))
    
    if not player.active_member:
        flash(_("Player account is not active."), "warning")
        return redirect(url_for("kiosk"))
    
    # Check if session already recorded today
    today = date.today()
    existing = TrainingSession.query.filter_by(player_pn=player.pn, date=today).first()
    if existing:
        flash(_("Session for today already recorded for {name}.").format(name=f"{player.first_name} {player.last_name}"), "info")
        return redirect(url_for("kiosk"))
    
    # For monthly payers, mark as paid since they pay monthly
    is_paid = player.monthly_fee_is_monthly
    
    session_id = f"{player.id}_{today.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S%f')}"
    ts = TrainingSession(player_id=player.id, player_pn=player.pn, date=today, session_id=session_id, paid=is_paid, created_at=datetime.now())
    db.session.add(ts)
    
    try:
        db.session.commit()
        flash(_("Welcome {name}! Your training session has been recorded successfully. Keep up the great work!").format(name=player.first_name), "success")
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to record TrainingSession from kiosk')
        flash(_("Session recording failed. Please try again."), "danger")
    
    return redirect(url_for("kiosk"))

# -------- CRUD Players ----------
@app.route("/admin/players/import_csv", methods=["POST"], endpoint='admin_players_import_csv')
@admin_required
def admin_players_import_csv():
    """Admin: import players from uploaded CSV file.

    Expected headers: first_name,last_name,gender,birthdate,pn,grade_level,join_date,
    email,phone,monthly_fee_amount,monthly_fee_is_monthly
    """
    if 'csv_file' not in request.files:
        flash(_('No file uploaded.'), 'danger')
        return redirect(request.referrer or url_for('list_players'))

    file = request.files.get('csv_file')
    if not file or not file.filename:
        flash(_('No file uploaded.'), 'danger')
        return redirect(request.referrer or url_for('list_players'))

    if not file.filename.lower().endswith('.csv'):
        flash(_('Please upload a .csv file.'), 'danger')
        return redirect(request.referrer or url_for('list_players'))

    import csv
    import io
    import datetime

    text_stream = io.TextIOWrapper(file.stream, encoding='utf-8-sig', errors='replace')
    reader = csv.DictReader(text_stream)
    created = 0
    errors = []
    for idx, row in enumerate(reader, start=1):
        try:
            first_name = (row.get('first_name') or '').strip()
            last_name = (row.get('last_name') or '').strip()
            if not first_name or not last_name:
                errors.append(f"Row {idx}: missing first_name/last_name")
                continue

            def get(k):
                return (row.get(k) or '').strip() or None

            player = Player(first_name=first_name, last_name=last_name)
            player.gender = get('gender')
            player.pn = (get('pn') or '')
            # Validate PN: must be exactly 10 digits
            if not re.match(r'^\d{10}$', player.pn):
                errors.append(f"Row {idx}: invalid or missing PN (must be exactly 10 digits): '{player.pn}'")
                continue
            player.email = get('email')
            player.phone = get('phone')
            player.grade_level = get('grade_level')

            def parse_date(s):
                if not s:
                    return None
                s = s.strip()
                try:
                    return datetime.date.fromisoformat(s)
                except Exception:
                    for fmt in ('%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d'):
                        try:
                            return datetime.datetime.strptime(s, fmt).date()
                        except Exception:
                            pass
                return None

            player.birthdate = parse_date(get('birthdate'))
            player.join_date = parse_date(get('join_date'))

            # Medical / insurance dates
            player.medical_exam_date = parse_date(get('medical_exam_date'))
            player.medical_expiry_date = parse_date(get('medical_expiry_date'))
            player.insurance_expiry_date = parse_date(get('insurance_expiry_date'))

            # Active member flag
            am = get('active_member')
            if am is not None:
                player.active_member = str(am).lower() in ('1', 'true', 'yes', 'y')

            # Misc fields
            player.notes = get('notes')
            player.photo_filename = get('photo_filename')
            player.sportdata_wkf_url = get('sportdata_wkf_url')
            player.sportdata_bnfk_url = get('sportdata_bnfk_url')
            player.sportdata_enso_url = get('sportdata_enso_url')
            try:
                player.weight_kg = int(get('weight_kg')) if get('weight_kg') else None
            except Exception:
                player.weight_kg = None
            try:
                player.height_cm = int(get('height_cm')) if get('height_cm') else None
            except Exception:
                player.height_cm = None

            player.discipline = get('discipline') or player.discipline

            # Parent contacts
            player.mother_name = get('mother_name')
            player.mother_phone = get('mother_phone')
            player.father_name = get('father_name')
            player.father_phone = get('father_phone')

            mfee = get('monthly_fee_amount')
            if mfee:
                try:
                    player.monthly_fee_amount = int(float(mfee))
                except Exception:
                    pass

            mflag = get('monthly_fee_is_monthly')
            if mflag is not None:
                player.monthly_fee_is_monthly = str(mflag).lower() in ('1', 'true', 'yes', 'y')

            # Prefer explicit belt_rank in CSV if provided, otherwise infer from grade
            csv_belt = get('belt_rank')
            if csv_belt:
                player.belt_rank = csv_belt
            elif player.grade_level and player.grade_level in GRADING_SCHEME.get('grade_to_color', {}):
                player.belt_rank = GRADING_SCHEME['grade_to_color'][player.grade_level]

            db.session.add(player)
            created += 1
        except Exception as e:
            errors.append(f"Row {idx}: {e}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(_('Import failed: ') + str(e), 'danger')
        return redirect(request.referrer or url_for('list_players'))

    msg = (_('%(count)s players imported.') % {'count': created}) if created else _('No players imported.')
    if errors:
        flash(msg + ' ' + _('Some rows had issues:') + ' ' + '; '.join(errors[:5]), 'warning')
    else:
        flash(msg, 'success')
    return redirect(url_for('list_players'))

@app.route("/admin/players/new", methods=["GET", "POST"])
@admin_required
def create_player():
    form = PlayerForm()
    set_localized_choices(form)
    if form.validate_on_submit():
        player = Player(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            pn=form.pn.data,
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

# Helper functions for debt checking
def player_has_outstanding_debts(player: Player) -> bool:
    """Check if a player has any outstanding debts."""
    today = date.today()
    
    # Check for unpaid monthly fees
    pay_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
    unpaid_monthly = Payment.query.filter_by(**pay_filter, year=today.year, month=today.month, paid=False).first()
    if unpaid_monthly:
        return True
    
    # Check for unpaid training sessions
    if player.monthly_fee_is_monthly is False and player.monthly_fee_amount:
        sess_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
        unpaid_sessions = TrainingSession.query.filter_by(**sess_filter, paid=False).count()
        if unpaid_sessions > 0:
            return True
    
    # Check for unpaid event registrations
    reg_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
    unpaid_regs = EventRegistration.query.filter_by(**reg_filter, paid=False).count()
    if unpaid_regs > 0:
        return True
    
    return False

def get_player_debts(player: Player) -> list:
    """Get detailed list of player's outstanding debts."""
    today = date.today()
    debts = []
    
    # Monthly due
    pay_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
    pay = Payment.query.filter_by(**pay_filter, year=today.year, month=today.month, paid=False).first()
    if pay:
        debts.append({
            "type": "monthly",
            "label": f"Monthly fee ({today.year}-{today.month:02d})",
            "amount": pay.amount or 0
        })
    
    # Owed session payments
    if player.monthly_fee_is_monthly is False and player.monthly_fee_amount:
        sess_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
        unpaid_sessions = TrainingSession.query.filter_by(**sess_filter, paid=False).count()
        if unpaid_sessions > 0:
            per_session_amount = player.monthly_fee_amount
            debts.append({
                "type": "sessions",
                "label": f"Owed sessions ({unpaid_sessions} x {per_session_amount} EUR)",
                "amount": unpaid_sessions * per_session_amount
            })
    
    # Unpaid event registrations
    reg_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
    regs = EventRegistration.query.filter_by(**reg_filter, paid=False).all()
    for r in regs:
        debts.append({
            "type": "event",
            "label": f"Event: {r.event.title if r.event else 'Event'}",
            "amount": r.computed_fee() or 0
        })
    
    return debts

@app.route("/admin/players/<int:player_id>/delete", methods=["POST"])
@admin_required
def delete_player(player_id: int):
    player = Player.query.get_or_404(player_id)
    
    # Check for outstanding debts
    has_debts = player_has_outstanding_debts(player)
    confirm_delete = request.form.get('confirm_delete_with_debts') == 'yes'
    
    if has_debts and not confirm_delete:
        # Show confirmation modal instead of deleting
        return render_template('player_delete_confirm.html', 
                             player=player, 
                             debts=get_player_debts(player))
    
    if player.photo_filename:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, player.photo_filename))
        except FileNotFoundError:
            pass
    try:
        # Preserve related records. Ensure their `player_pn` is set to this player's PN
        pn_val = player.pn
        if pn_val:
            PaymentRecord.query.filter_by(player_id=player.id).update({"player_pn": pn_val}, synchronize_session=False)
            Payment.query.filter_by(player_id=player.id).update({"player_pn": pn_val}, synchronize_session=False)
            TrainingSession.query.filter_by(player_id=player.id).update({"player_pn": pn_val}, synchronize_session=False)
            EventRegistration.query.filter_by(player_id=player.id).update({"player_pn": pn_val}, synchronize_session=False)
        # Soft-delete: keep the player row to preserve foreign key integrity, but mark inactive and anonymize contact info
        player.active_member = False
        # Optionally anonymize personal data while preserving PN as UID
        player.first_name = (player.first_name or '')
        player.last_name = (player.last_name or '')
        player.email = None
        player.phone = None
        player.photo_filename = None
        player.notes = (player.notes or '') + f"\n[DELETED on {date.today().isoformat()}]"
        db.session.add(player)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash(_("Failed to fully delete player and related records."), "danger")
        return redirect(url_for("player_detail", player_id=player.id))
    flash(_("Player deleted (soft). Related registrations and payments preserved and linked by PN#."), "info")
    return redirect(url_for("list_players"))


@app.route('/admin/players/<int:player_id>/purge', methods=['POST'])
@admin_required
def purge_player(player_id: int):
    """Permanently remove a player row after migrating related rows to use PN.

    This is destructive and irreversible. The form must include `confirm` field
    with the literal value 'PURGE' to proceed. Make a DB backup before running.
    """
    player = Player.query.get_or_404(player_id)
    
    # Check for outstanding debts
    has_debts = player_has_outstanding_debts(player)
    confirm_delete = request.form.get('confirm_delete_with_debts') == 'yes'
    
    if has_debts and not confirm_delete:
        # Show confirmation modal instead of purging
        return render_template('player_delete_confirm.html', 
                             player=player, 
                             debts=get_player_debts(player),
                             is_purge=True)
    
    confirm = (request.form.get('confirm') or '').strip()
    if confirm != 'PURGE':
        flash(_('Missing or incorrect confirmation token. To permanently delete, POST with confirm=PURGE'), 'danger')
        return redirect(url_for('player_detail', player_id=player.id))

    pn_val = player.pn
    try:
        # Backfill player_pn on related rows so history remains tied to PN
        if pn_val:
            PaymentRecord.query.filter_by(player_id=player.id).update({'player_pn': pn_val}, synchronize_session=False)
            Payment.query.filter_by(player_id=player.id).update({'player_pn': pn_val}, synchronize_session=False)
            TrainingSession.query.filter_by(player_id=player.id).update({'player_pn': pn_val}, synchronize_session=False)
            EventRegistration.query.filter_by(player_id=player.id).update({'player_pn': pn_val}, synchronize_session=False)

        # Remove photo file if present
        if player.photo_filename:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, player.photo_filename))
            except Exception:
                pass

        # Finally delete the player row
        db.session.delete(player)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.exception('Failed to purge player')
        flash(_(f'Purge failed: {e}'), 'danger')
        return redirect(url_for('player_detail', player_id=player.id))

    flash(_('Player permanently deleted and related rows backfilled with PN.'), 'success')
    return redirect(url_for('list_players'))

# --- Modal Dues Payment Backend ---
@app.route("/admin/players/<int:player_id>/pay_due_receipt", methods=["POST"])
@admin_required
def player_pay_due_receipt(player_id: int):
    import json as _json
    player = Player.query.get_or_404(player_id)
    data = request.get_json(force=True)
    due_ids = data.get("dues", [])
    created = []
    total_amount = 0
    today = date.today()
    bulk_note_parts = []

    # Helper: get due type and object by ID
    def get_due_obj(due_id):
        # Try Payment (monthly)
        p = Payment.query.filter_by(id=due_id, player_pn=player.pn, paid=False).first()
        if p:
            return ("monthly", p)
        # Try EventRegistration (event)
        r = EventRegistration.query.filter_by(id=due_id, player_pn=player.pn, paid=False).first()
        if r:
            return ("event", r)
        # Try PaymentRecord (debt)
        d = PaymentRecord.query.filter_by(id=due_id, player_pn=player.pn).first()
        if d and is_auto_debt_note(d.note) and "AUTO_DEBT_PAID" not in (d.note or ""):
            return ("debt", d)
        return (None, None)

    print('DEBUG: due_ids received:', due_ids)
    for due_id in due_ids:
        # Handle owed session payments (object with type and session_ids)
        if isinstance(due_id, dict) and due_id.get('type') == 'owed_sessions' and due_id.get('session_ids'):
            session_ids = due_id['session_ids']
            # Fetch the TrainingSession records
            sessions = TrainingSession.query.filter(TrainingSession.session_id.in_(session_ids), TrainingSession.player_pn == player.pn, TrainingSession.paid == False).all()
            if not sessions:
                continue
            per_session_amount = player.monthly_fee_amount
            amt = len(sessions) * per_session_amount
            # Mark sessions as paid
            for s in sessions:
                s.paid = True
                db.session.add(s)
            # For bulk receipt, just accumulate amount and note
            if len(session_ids) == 1:
                bulk_note_parts.append(f"Session ID: {session_ids[0]}")
            else:
                bulk_note_parts.append(f"Sessions: {', '.join(session_ids)}")
            total_amount += amt
            continue
        # Normal dues (int IDs)
        try:
            due_id_int = int(due_id)
        except Exception:
            continue
        kind, obj = get_due_obj(due_id_int)
        if kind == "monthly":
            # For bulk receipt, just accumulate amount and note
            amt = obj.amount or 0
            bulk_note_parts.append(f"Monthly fee {obj.year}-{obj.month:02d}")
            obj.paid = True
            obj.paid_on = today
            db.session.add(obj)
            total_amount += amt
        elif kind == "event":
            amt = obj.computed_fee() or 0
            event_name = obj.event.title if obj.event and hasattr(obj.event, 'title') else 'Event'
            bulk_note_parts.append(f"Event: {event_name}")
            obj.paid = True
            obj.paid_on = today
            db.session.add(obj)
            total_amount += amt
        elif kind == "debt":
            d_amt = int(obj.amount or 0)
            if d_amt <= 0:
                continue
            bulk_note_parts.append(f"Debt payment for receipt {obj.id}")
            obj.note = (obj.note or '') + ' | AUTO_DEBT_PAID'
            db.session.add(obj)
            total_amount += d_amt

    # Create a single bulk PaymentRecord
    if total_amount > 0:
        bulk_note = "Bulk payment: " + "; ".join(bulk_note_parts)
        rec = PaymentRecord(
            kind='bulk_payment', player_id=player.id, player_pn=player.pn,
            amount=total_amount, year=today.year, month=today.month,
            currency='EUR', note=bulk_note
        )
        db.session.add(rec)
        db.session.commit()
        try:
            rec.assign_receipt_no()
        except Exception:
            pass
        created.append(rec)

    print('DEBUG: created PaymentRecords:', [r.id for r in created])
    if created:
        ids = ",".join(str(r.id) for r in created)
        return _json.dumps({"redirect": url_for('receipts_print_batch') + f"?ids={ids}"})
    else:
        return _json.dumps({"redirect": url_for('player_detail', player_id=player.id)})
#-------------Rosen

# Outstanding dues JSON endpoint for modal
@app.route("/admin/players/<int:player_id>/dues_json")
@admin_required
def player_dues_json(player_id: int):
    player = Player.query.get_or_404(player_id)
    today = date.today()
    dues = []
    # Monthly due (unpaid Payment row for this month)
    pay_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
    pay = Payment.query.filter_by(**pay_filter, year=today.year, month=today.month, paid=False).first()
    if pay:
        dues.append({
            "id": pay.id,
            "label": f"Monthly fee ({today.year}-{today.month:02d})",
            "amount": pay.amount or 0,
            "type": "monthly"
        })

    # Owed session payments (per-session plan, sessions taken > sessions paid)
    if player.monthly_fee_is_monthly is False and player.monthly_fee_amount:
        # Get all unpaid TrainingSession records for this player (all time)
        sess_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
        unpaid_sessions = TrainingSession.query.filter_by(**sess_filter, paid=False).order_by(TrainingSession.date.asc()).all()
        per_session_amount = player.monthly_fee_amount
        owed_sessions = len(unpaid_sessions)
        if owed_sessions > 0:
            session_list = [
                {
                    "session_id": s.session_id,
                    "date": s.date.strftime('%Y-%m-%d') if s.date else "?"
                }
                for s in unpaid_sessions
            ]
            dues.append({
                "id": f"owed_sessions_all_time",
                "label": f"Owed sessions ({owed_sessions} x {per_session_amount} EUR)",
                "amount": owed_sessions * per_session_amount,
                "type": "owed_sessions",
                "sessions": owed_sessions,
                "session_list": session_list
            })
    # Unpaid event registrations
    reg_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
    regs = EventRegistration.query.filter_by(**reg_filter, paid=False).all()
    for r in regs:
        dues.append({
            "id": r.id,
            "label": f"Event: {r.event.title if r.event else 'Event'}",
            "amount": r.computed_fee() or 0,
            "type": "event"
        })
    # Debts (AUTO_DEBT)
    # Session debt is intentionally excluded from the dues modal
    print(f"DEBUG /dues_json for player {player_id}: {json.dumps(dues, indent=2)}")
    return {"dues": dues}
# Admin utility: Backfill missing TrainingSession records for all players

# Place this route after other admin routes
@app.route("/admin/backfill_training_sessions")
@admin_required
def backfill_training_sessions():
    from sqlalchemy.orm import load_only
    players = Player.query.options(load_only(Player.id)).all()
    created_total = 0
    for player in players:
        if player.monthly_fee_is_monthly or not player.monthly_fee_amount:
            continue  # Only per-session payers
        # Count sessions_taken from PaymentRecord
        total_taken = db.session.query(db.func.sum(PaymentRecord.sessions_taken)).filter_by(player_pn=player.pn, kind='training_session').scalar() or 0
        # Count existing TrainingSession rows
        existing_sessions = TrainingSession.query.filter_by(player_pn=player.pn).count()
        missing = total_taken - existing_sessions
        if missing > 0:
            # Find the latest session date, or use today
            last_date = db.session.query(db.func.max(TrainingSession.date)).filter_by(player_pn=player.pn).scalar() or date.today()
            for i in range(missing):
                sess_date = last_date  # Could randomize or increment if needed
                session_id = TrainingSession.generate_session_id(player.id, sess_date)
                ts = TrainingSession(player_id=player.id, player_pn=player.pn, date=sess_date, session_id=session_id, paid=False)
                db.session.add(ts)
                created_total += 1
    db.session.commit()
    flash(_(f"Backfilled {created_total} missing TrainingSession records."), "success")
    return redirect(request.referrer or url_for('list_players'))
@app.route("/reports/fees")
@admin_required
def fees_report():
    month_str = request.args.get("month")
    year, month = parse_month_str(month_str)
    ensure_payments_for_month(year, month)

    # Get all active players
    players = Player.query.filter_by(active_member=True).order_by(Player.last_name.asc(), Player.first_name.asc()).all()
    payments = {p.player_id: p for p in Payment.query.filter_by(year=year, month=month).all()}

    # Consolidate all payments per athlete
    from sqlalchemy import extract
    report_rows = []
    for player in players:
        # Monthly
        payment = payments.get(player.id)
        monthly_amount = payment.amount if payment else 0
        monthly_paid = payment.paid if payment else False
        monthly_id = payment.id if payment else None
        # Per-session
        # Count TrainingSession rows in the report month and use their paid flag to compute owed amount.
        per_session_amount = player.monthly_fee_amount if player.monthly_fee_is_monthly is False else None
        sessions_taken = 0
        sessions_paid = 0
        prepaid_amount = 0
        sessions_in_month = []
        sess_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
        if per_session_amount is not None:
            # Date range for month
            from calendar import monthrange
            month_start = date(year, month, 1)
            month_end = date(year, month, monthrange(year, month)[1])
            # Training sessions in the month (prefer player_pn for lookup)
            sessions_in_month = TrainingSession.query.filter_by(**sess_filter).filter(TrainingSession.date >= month_start, TrainingSession.date <= month_end).all()
            sessions_taken = len(sessions_in_month)
            sessions_paid = sum(1 for s in sessions_in_month if getattr(s, 'paid', False))
            # Fallback/prepaid amount: sum PaymentRecord amounts for training_session kind in the month
            session_pay_recs = PaymentRecord.query.filter_by(player_pn=player.pn, kind='training_session').filter(
                db.func.strftime('%Y', PaymentRecord.paid_at) == str(year),
                db.func.strftime('%m', PaymentRecord.paid_at) == f"{month:02d}"
            ).all()
            prepaid_amount = sum(r.amount or 0 for r in session_pay_recs)
            # For compatibility with previous logic, expose these as session_receipts
            session_receipts = session_pay_recs
            owed_amount = max(0, (sessions_taken - sessions_paid) * per_session_amount)
        else:
            owed_amount = 0
        # Build a lightweight session list for the UI (session_id, date, paid)
        session_list = [
            {
                'session_id': s.session_id,
                'date': s.date.isoformat() if s.date else None,
                'paid': bool(getattr(s, 'paid', False)),
                'amount': per_session_amount if per_session_amount is not None else None
            }
            for s in (locals().get('sessions_in_month') or [])
        ]
        # Events
        event_payments = PaymentRecord.query.filter_by(player_pn=player.pn, kind='event').filter(
            extract('year', PaymentRecord.paid_at) == year,
            extract('month', PaymentRecord.paid_at) == month
        ).all()
        event_total = sum(ep.amount or 0 for ep in event_payments)
        # Bulk payments
        bulk_payments = PaymentRecord.query.filter_by(player_pn=player.pn, kind='bulk_payment').filter(
            extract('year', PaymentRecord.paid_at) == year,
            extract('month', PaymentRecord.paid_at) == month
        ).all()
        bulk_total = sum(bp.amount or 0 for bp in bulk_payments)
        # Owed for events: sum of unpaid event registrations (per category) for this player
        # Event fees are due immediately upon registration, not based on event date
        event_owed = 0
        category_fees = 0
        # All unpaid event registrations for this player
        unpaid_regs = EventRegistration.query.filter_by(player_pn=player.pn, paid=False).all()
        for reg in unpaid_regs:
            # Sum all category fees for this registration
            for rc in reg.reg_categories:
                if rc.category and rc.category.fee is not None:
                    category_fees += int(rc.category.fee)
            # All unpaid registrations are owed
            for rc in reg.reg_categories:
                if rc.category and rc.category.fee is not None:
                    event_owed += int(rc.category.fee)
            # If no categories, fallback to registration fee
            if not reg.reg_categories and reg.computed_fee():
                event_owed += reg.computed_fee()
        # Details for expansion
        event_details = []
        for ep in event_payments:
            event_name = ep.event_registration.event.title if ep.event_registration and ep.event_registration.event else None
            event_details.append({
                'amount': ep.amount,
                'event_name': event_name,
                'receipt_no': ep.receipt_no,
                'paid_on': ep.paid_at.date() if ep.paid_at else None,
                'id': ep.id,
            })
        # Details for bulk payments expansion
        bulk_details = []
        for bp in bulk_payments:
            bulk_details.append({
                'amount': bp.amount,
                'receipt_no': bp.receipt_no,
                'paid_on': bp.paid_at.date() if bp.paid_at else None,
                'id': bp.id,
                'note': bp.note,
            })
        # Find monthly receipt (PaymentRecord)
        monthly_receipt = None
        if payment:
            monthly_receipt = PaymentRecord.query.filter_by(player_pn=player.pn, kind='training_month', year=year, month=month).first()
        monthly_receipt_no = monthly_receipt.receipt_no if monthly_receipt else None
        monthly_receipt_id = monthly_receipt.id if monthly_receipt else None
        # Collect all session receipts for the month
        session_receipt_nos = [r.receipt_no for r in (locals().get('session_receipts') or []) if r.receipt_no]
        session_receipt_ids = [r.id for r in (locals().get('session_receipts') or []) if r.receipt_no]
        report_rows.append({
            'player': player,
            'player_id': player.id,
            'monthly_amount': monthly_amount,
            'monthly_paid': monthly_paid,
            'monthly_id': monthly_id,
            'monthly_receipt_no': monthly_receipt_no,
            'monthly_receipt_id': monthly_receipt_id,
            'sessions_paid': sessions_paid,
            'sessions_taken': sessions_taken,
            'prepaid_amount': prepaid_amount,
            'per_session_amount': per_session_amount,
            'session_receipt_nos': session_receipt_nos,
            'session_receipt_ids': session_receipt_ids,
            'session_list': session_list,
            'owed_amount': (owed_amount or 0) + (event_owed or 0),
            'event_total': event_total,
            'event_owed': event_owed,
            'category_fees': category_fees,
            'event_details': event_details,
            'bulk_total': bulk_total,
            'bulk_details': bulk_details,
            'year': year,
            'month': month,
        })

    # Show due date as today if today is in the target month, else use first working day
    today_dt = date.today()
    if today_dt.year == year and today_dt.month == month:
        due = today_dt
    else:
        due = first_working_day(year, month)
    return render_template(
        "report_fees.html",
        payments=report_rows,
        year=year,
        month=month,
        due_date=due,
        today=date.today()
    )

@app.route("/admin/reports/fees/print/<int:year>/<int:month>")
@admin_required
def fees_report_print(year: int, month: int):
    """Print-friendly version of the monthly fees report."""
    month_str = f"{year:04d}-{month:02d}"
    ensure_payments_for_month(year, month)

    # Get all active players
    players = Player.query.filter_by(active_member=True).order_by(Player.last_name.asc(), Player.first_name.asc()).all()
    payments = {p.player_id: p for p in Payment.query.filter_by(year=year, month=month).all()}

    # Consolidate all payments per athlete (same logic as fees_report)
    from sqlalchemy import extract
    report_rows = []
    for player in players:
        # Monthly
        payment = payments.get(player.id)
        monthly_amount = payment.amount if payment else 0
        monthly_paid = payment.paid if payment else False
        monthly_id = payment.id if payment else None
        # Per-session
        per_session_amount = player.monthly_fee_amount if player.monthly_fee_is_monthly is False else None
        sessions_taken = 0
        sessions_paid = 0
        prepaid_amount = 0
        sessions_in_month = []
        sess_filter = {'player_pn': player.pn} if player.pn else {'player_id': player.id}
        if per_session_amount is not None:
            from calendar import monthrange
            month_start = date(year, month, 1)
            month_end = date(year, month, monthrange(year, month)[1])
            sessions_in_month = TrainingSession.query.filter_by(**sess_filter).filter(TrainingSession.date >= month_start, TrainingSession.date <= month_end).all()
            sessions_taken = len(sessions_in_month)
            sessions_paid = sum(1 for s in sessions_in_month if getattr(s, 'paid', False))
            session_pay_recs = PaymentRecord.query.filter_by(player_pn=player.pn, kind='training_session').filter(
                db.func.strftime('%Y', PaymentRecord.paid_at) == str(year),
                db.func.strftime('%m', PaymentRecord.paid_at) == f"{month:02d}"
            ).all()
            prepaid_amount = sum(r.amount or 0 for r in session_pay_recs)
            owed_amount = max(0, (sessions_taken - sessions_paid) * per_session_amount)
        else:
            owed_amount = 0
        
        session_list = [
            {
                'session_id': s.session_id,
                'date': s.date.isoformat() if s.date else None,
                'paid': bool(getattr(s, 'paid', False)),
                'amount': per_session_amount if per_session_amount is not None else None
            }
            for s in (locals().get('sessions_in_month') or [])
        ]
        
        # Events
        event_payments = PaymentRecord.query.filter_by(player_pn=player.pn, kind='event').filter(
            extract('year', PaymentRecord.paid_at) == year,
            extract('month', PaymentRecord.paid_at) == month
        ).all()
        event_total = sum(ep.amount or 0 for ep in event_payments)
        
        # Bulk payments
        bulk_payments = PaymentRecord.query.filter_by(player_pn=player.pn, kind='bulk_payment').filter(
            extract('year', PaymentRecord.paid_at) == year,
            extract('month', PaymentRecord.paid_at) == month
        ).all()
        bulk_total = sum(bp.amount or 0 for bp in bulk_payments)
        
        # Event owed calculation (same as main report)
        event_owed = 0
        category_fees = 0
        unpaid_regs = EventRegistration.query.filter_by(player_pn=player.pn, paid=False).all()
        for reg in unpaid_regs:
            for rc in reg.reg_categories:
                if rc.category and rc.category.fee is not None:
                    category_fees += int(rc.category.fee)
            for rc in reg.reg_categories:
                if rc.category and rc.category.fee is not None:
                    event_owed += int(rc.category.fee)
            if not reg.reg_categories and reg.computed_fee():
                event_owed += reg.computed_fee()
        
        # Event and bulk details for expandable sections
        event_details = []
        for ep in event_payments:
            event_name = ep.event_registration.event.title if ep.event_registration and ep.event_registration.event else None
            event_details.append({
                'amount': ep.amount,
                'event_name': event_name,
                'receipt_no': ep.receipt_no,
                'paid_on': ep.paid_at.date() if ep.paid_at else None,
                'id': ep.id,
            })
        
        bulk_details = []
        for bp in bulk_payments:
            bulk_details.append({
                'amount': bp.amount,
                'receipt_no': bp.receipt_no,
                'paid_on': bp.paid_at.date() if bp.paid_at else None,
                'id': bp.id,
                'note': bp.note,
            })
        
        # Find monthly receipt
        monthly_receipt = None
        if payment:
            monthly_receipt = PaymentRecord.query.filter_by(player_pn=player.pn, kind='training_month', year=year, month=month).first()
        monthly_receipt_no = monthly_receipt.receipt_no if monthly_receipt else None
        
        # Session receipts
        session_receipt_nos = [r.receipt_no for r in (locals().get('session_receipts') or []) if r.receipt_no]
        
        report_rows.append({
            'player': player,
            'player_id': player.id,
            'monthly_amount': monthly_amount,
            'monthly_paid': monthly_paid,
            'monthly_receipt_no': monthly_receipt_no,
            'sessions_paid': sessions_paid,
            'sessions_taken': sessions_taken,
            'prepaid_amount': prepaid_amount,
            'per_session_amount': per_session_amount,
            'session_receipt_nos': session_receipt_nos,
            'owed_amount': (owed_amount or 0) + (event_owed or 0),
            'event_total': event_total,
            'event_owed': event_owed,
            'category_fees': category_fees,
            'bulk_total': bulk_total,
            'year': year,
            'month': month,
        })

    # Calculate totals
    total_monthly = sum(p['monthly_amount'] for p in report_rows)
    total_session = sum(p['prepaid_amount'] for p in report_rows)
    total_event = sum(p['event_total'] for p in report_rows)
    total_bulk = sum(p['bulk_total'] for p in report_rows)
    total_category = sum(p['category_fees'] for p in report_rows)
    total_owed = sum(p['owed_amount'] for p in report_rows)
    
    # Show due date as today if today is in the target month, else use first working day
    today_dt = date.today()
    if today_dt.year == year and today_dt.month == month:
        due = today_dt
    else:
        due = first_working_day(year, month)
    
    return render_template(
        "report_fees_print.html",
        payments=report_rows,
        year=year,
        month=month,
        total_monthly=total_monthly,
        total_session=total_session,
        total_event=total_event,
        total_bulk=total_bulk,
        total_category=total_category,
        total_owed=total_owed,
        due_date=due,
        generated_at=datetime.now()
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
                .join(Player, Player.id == Payment.player_id)
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

    headers = {"Content-Disposition": f'attachment; filename="fees_{year:04d}-{month:02d}.csv"'}
    return Response(generate(), mimetype="text/csv", headers=headers)


@app.route("/admin/reports/payments/export_all")
@admin_required
def payments_export_all_csv():
    """Export all payment-related rows (Payment and PaymentRecord) as a single CSV for backup."""
    def generate():
        # Header: source,payment_id,record_id,player_id,player_pn,kind,year,month,amount,currency,paid,paid_on,paid_at,receipt_no,payment_id_ref,event_registration_id,sessions_paid,sessions_taken,note,method,created_at
        yield ("source,payment_id,record_id,player_id,player_pn,kind,year,month,amount,currency,paid,paid_on,paid_at,receipt_no,payment_id_ref,event_registration_id,sessions_paid,sessions_taken,note,method,created_at\n")
        # Payments (monthly bookkeeping)
        for p in Payment.query.order_by(Payment.id.asc()).all():
            src = 'payment'
            payment_id = p.id
            record_id = ''
            player_id = p.player_id
            player_pn = p.player_pn or ''
            kind = ''
            year = p.year
            month = p.month
            amount = p.amount if p.amount is not None else ''
            currency = ''
            paid = '1' if p.paid else '0'
            paid_on = p.paid_on.isoformat() if p.paid_on else ''
            paid_at = ''
            receipt_no = ''
            payment_id_ref = ''
            event_registration_id = ''
            sessions_paid = ''
            sessions_taken = ''
            note = ''
            method = ''
            created_at = ''
            row = [str(v) for v in [src, payment_id, record_id, player_id, player_pn, kind, year, month, amount, currency, paid, paid_on, paid_at, receipt_no, payment_id_ref, event_registration_id, sessions_paid, sessions_taken, note, method, created_at]]
            yield ",".join(row) + "\n"

        # PaymentRecords (receipts)
        for r in PaymentRecord.query.order_by(PaymentRecord.id.asc()).all():
            src = 'payment_record'
            payment_id = ''
            record_id = r.id
            player_id = r.player_id
            player_pn = r.player_pn or ''
            kind = r.kind
            year = r.year if r.year is not None else ''
            month = r.month if r.month is not None else ''
            amount = r.amount if r.amount is not None else ''
            currency = r.currency or ''
            paid = '1' if getattr(r, 'paid', None) else ''
            paid_on = ''
            paid_at = r.paid_at.isoformat() if r.paid_at else ''
            receipt_no = r.receipt_no or ''
            payment_id_ref = r.payment_id or ''
            event_registration_id = r.event_registration_id or ''
            sessions_paid = r.sessions_paid or ''
            sessions_taken = r.sessions_taken or ''
            note = (r.note or '').replace('\n', ' ').replace(',', ' ')
            method = r.method or ''
            created_at = r.created_at.isoformat() if r.created_at else ''
            row = [str(v) for v in [src, payment_id, record_id, player_id, player_pn, kind, year, month, amount, currency, paid, paid_on, paid_at, receipt_no, payment_id_ref, event_registration_id, sessions_paid, sessions_taken, note, method, created_at]]
            yield ",".join(row) + "\n"

    headers = {"Content-Disposition": 'attachment; filename="payments_all.csv"'}
    return Response(stream_with_context(generate()), mimetype='text/csv', headers=headers)


@app.route('/admin/exports')
@admin_required
def admin_exports():
    """Admin page listing all export/backup endpoints."""
    return render_template('admin_exports.html', _=_ , current_lang=get_lang())


@app.route('/admin/imports')
@admin_required
def admin_imports():
    """Admin page listing import/upload entry points."""
    return render_template('admin_imports.html', _=_ , current_lang=get_lang())


@app.route('/admin/events/export_zip_all')
@admin_required
def export_events_zip_all():
    """Export all events as a single ZIP containing per-event exports (no photos)."""
    events = Event.query.order_by(Event.start_date.asc()).all()
    import json
    import csv
    from io import StringIO, BytesIO
    import zipfile

    mem_zip = BytesIO()
    with zipfile.ZipFile(mem_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for ev in events:
            prefix = f'event_{ev.id}'
            # event JSON
            ev_dict = {
                'id': ev.id,
                'title': ev.title,
                'start_date': ev.start_date.isoformat() if ev.start_date else None,
                'end_date': ev.end_date.isoformat() if ev.end_date else None,
                'location': ev.location,
                'sportdata_url': ev.sportdata_url,
                'notes': ev.notes,
            }
            zf.writestr(f'{prefix}/{prefix}_detail.json', json.dumps(ev_dict, ensure_ascii=False, indent=2))

            # categories
            cats = EventCategory.query.filter_by(event_id=ev.id).order_by(EventCategory.name.asc()).all()
            cat_out = StringIO()
            cat_writer = csv.writer(cat_out)
            cat_writer.writerow(['id', 'name', 'age_from', 'age_to', 'sex', 'fee', 'team_size', 'kyu', 'dan', 'other_cutoff_date', 'limit_team', 'limit'])
            for c in cats:
                cat_writer.writerow([c.id, c.name, c.age_from, c.age_to, c.sex, c.fee, c.team_size, c.kyu, c.dan, c.other_cutoff_date, c.limit_team, c.limit])
            zf.writestr(f'{prefix}/{prefix}_categories.csv', cat_out.getvalue())

            # registrations
            regs = (EventRegistration.query
                    .filter_by(event_id=ev.id)
                    .join(Player, Player.id == EventRegistration.player_id)
                    .order_by(Player.last_name.asc(), Player.first_name.asc())
                    .all())
            reg_out = StringIO()
            reg_writer = csv.writer(reg_out)
            reg_writer.writerow(['id', 'player_id', 'player_name', 'fee_override', 'computed_fee', 'paid', 'paid_on', 'note', 'categories', 'medals'])
            for r in regs:
                cats_list = []
                medals_list = []
                for rc in r.reg_categories or []:
                    cats_list.append(rc.category.name if rc.category else '')
                    medals_list.append(rc.medal or '')
                computed = r.fee_override if r.fee_override is not None else (sum((rc.category.fee or 0) for rc in r.reg_categories) if r.reg_categories else '')
                reg_writer.writerow([r.id, r.player_id, r.player.full_name() if r.player else '', r.fee_override, computed, r.paid, (r.paid_on.isoformat() if r.paid_on else ''), '', '; '.join(cats_list), '; '.join(medals_list)])
            zf.writestr(f'{prefix}/{prefix}_registrations.csv', reg_out.getvalue())

            # per-player CSVs
            player_ids = {r.player_id for r in regs if r.player_id}
            players = Player.query.filter(Player.id.in_(player_ids)).all() if player_ids else []
            fieldnames = [
                'id', 'first_name', 'last_name', 'gender', 'birthdate', 'pn',
                'belt_rank', 'grade_level', 'grade_date', 'discipline', 'weight_kg', 'height_cm',
                'email', 'phone', 'join_date', 'active_member', 'notes', 'photo_filename',
                'sportdata_wkf_url', 'sportdata_bnfk_url', 'sportdata_enso_url',
                'medical_exam_date', 'medical_expiry_date', 'insurance_expiry_date',
                'monthly_fee_amount', 'monthly_fee_is_monthly',
                'mother_name', 'mother_phone', 'father_name', 'father_phone'
            ]
            for p in players:
                out = StringIO()
                dw = csv.DictWriter(out, fieldnames=fieldnames)
                dw.writeheader()
                row = {k: getattr(p, k, '') for k in fieldnames}
                for k, v in row.items():
                    if hasattr(v, 'isoformat'):
                        row[k] = v.isoformat()
                    elif isinstance(v, bool):
                        row[k] = str(v)
                zf.writestr(f'{prefix}/players/player_{p.id}_{(p.last_name or "").replace(" ","_")}.csv', out.getvalue())

    mem_zip.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="events_all_full_export.zip"'}
    return Response(mem_zip.getvalue(), mimetype='application/zip', headers=headers)


@app.route('/admin/payments/import_csv', methods=['POST'])
@admin_required
def admin_payments_import_csv():
    """Import payment/receipt rows from CSV into PaymentRecord."""
    if 'csv_file' not in request.files:
        flash(_('No file uploaded'), 'danger')
        return redirect(request.referrer or url_for('admin_imports'))
    file = request.files.get('csv_file')
    if not file or not file.filename:
        flash(_('No file uploaded'), 'danger')
        return redirect(request.referrer or url_for('admin_imports'))
    import io
    import csv
    import datetime

    text_stream = io.TextIOWrapper(file.stream, encoding='utf-8-sig', errors='replace')
    reader = csv.DictReader(text_stream)
    created = 0
    skipped = 0
    errors = []
    for idx, row in enumerate(reader, start=1):
        try:
            def g(k):
                return (row.get(k) or '').strip() or None

            player_pn = g('player_pn')
            player_id = g('player_id')
            player_obj = None
            if player_pn:
                player_obj = Player.query.filter_by(pn=player_pn).first()
            elif player_id:
                try:
                    player_obj = Player.query.get(int(player_id))
                except Exception:
                    player_obj = None

            if not player_obj:
                skipped += 1
                continue

            kind = g('kind') or 'training_session'
            amount_raw = g('amount') or '0'
            try:
                amount = int(float(amount_raw))
            except Exception:
                amount = 0

            paid_flag = g('paid')
            paid = True if str(paid_flag).strip() in ('1', 'true', 'yes', 'y') else False

            paid_at = None
            if g('paid_at'):
                try:
                    paid_at = datetime.datetime.fromisoformat(g('paid_at'))
                except Exception:
                    paid_at = None

            pr = PaymentRecord(
                kind=kind,
                player_id=player_obj.id,
                player_pn=player_obj.pn,
                year=int(g('year')) if g('year') else None,
                month=int(g('month')) if g('month') else None,
                sessions_paid=int(g('sessions_paid')) if g('sessions_paid') else 0,
                sessions_taken=int(g('sessions_taken')) if g('sessions_taken') else 0,
                amount=amount,
                currency=g('currency') or 'EUR',
                method=g('method'),
                note=g('note'),
                receipt_no=g('receipt_no') or None,
                paid_at=paid_at or datetime.datetime.utcnow(),
            )
            # Avoid duplicate receipt_no
            if pr.receipt_no:
                existing = PaymentRecord.query.filter_by(receipt_no=pr.receipt_no).first()
                if existing:
                    skipped += 1
                    continue

            db.session.add(pr)
            db.session.flush()
            # Assign generated receipt if none
            if not pr.receipt_no:
                pr.assign_receipt_no(do_commit=False)
            created += 1
        except Exception as e:
            app.logger.exception('Payments import row failed')
            errors.append(f'Row {idx}: {e}')

    db.session.commit()
    flash(f'Payments imported: {created}. Skipped: {skipped}. Errors: {len(errors)}', 'success' if not errors else 'warning')
    if errors:
        app.logger.warning('\n'.join(errors))
    return redirect(request.referrer or url_for('admin_imports'))

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
                            .filter_by(player_pn=p.pn, kind='training_session')
                            .all())
            explicit_sessions_paid = sum((r.sessions_paid or 0) for r in sess_records)
            sessions_taken = sum((r.sessions_taken or 0) for r in sess_records)
            prepaid_amount = sum((r.amount or 0) for r in sess_records)
            per_session_amount = int(p.monthly_fee_amount) if (p.monthly_fee_amount is not None and not p.monthly_fee_is_monthly) else ""
            owed_amount = ""
            sessions_paid = explicit_sessions_paid
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
@app.route("/events", endpoint="events_calendar")
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

    # Get registration counts for events
    event_reg_counts = {}
    for e in events:
        event_reg_counts[e.id] = EventRegistration.query.filter_by(event_id=e.id).count()

    # Scrape BNFK events
    bnfk_events = scrape_bnfk_events()
    
    # Convert string dates back to date objects if loaded from cache
    for event in bnfk_events:
        if isinstance(event['start_date'], str):
            event['start_date'] = date.fromisoformat(event['start_date'])
        if isinstance(event['end_date'], str):
            event['end_date'] = date.fromisoformat(event['end_date'])
    
    # Filter BNFK events for current month
    bnfk_events_filtered = [
        e for e in bnfk_events 
        if e['start_date'] <= last and (e['end_date'] or e['start_date']) >= first
    ]

    cal = calendar.monthcalendar(y, m)
    weeks = []
    
    # Get attendance data for the month
    first = date(y, m, 1)
    last = date(y, m, last_day)
    attendance_data = {}
    
    # Query all training sessions for this month
    sessions = TrainingSession.query.filter(
        TrainingSession.date >= first,
        TrainingSession.date <= last
    ).all()
    
    # Count sessions per day
    for session in sessions:
        date_key = session.date.isoformat()
        if date_key not in attendance_data:
            attendance_data[date_key] = 0
        attendance_data[date_key] += 1
    
    # Prepare events by date for JavaScript
    events_by_date = {}
    
    # Add local events
    for e in events:
        # For events spanning multiple days, add to each day
        event_start = e.start_date
        event_end = e.end_date or e.start_date
        current_date = event_start
        while current_date <= event_end:
            if first <= current_date <= last:
                date_key = current_date.isoformat()
                if date_key not in events_by_date:
                    events_by_date[date_key] = []
                events_by_date[date_key].append({
                    'title': e.title,
                    'url': url_for('event_detail', event_id=e.id),
                    'registrations_count': event_reg_counts[e.id]
                })
            current_date += timedelta(days=1)
    
    # Add BNFK events
    for e in bnfk_events_filtered:
        event_start = e['start_date']
        event_end = e['end_date']
        current_date = event_start
        while current_date <= event_end:
            if first <= current_date <= last:
                date_key = current_date.isoformat()
                if date_key not in events_by_date:
                    events_by_date[date_key] = []
                events_by_date[date_key].append({
                    'title': e['title'],
                    'url': e['url'],
                    'registrations_count': 0
                })
            current_date += timedelta(days=1)
    
    for wk in cal:
        row = []
        for d in wk:
            if d == 0:
                row.append({"day": None, "events": [], "attendance": 0})
            else:
                dt = date(y, m, d)
                day_events = [e for e in events if e.spans(dt)]
                day_attendance = attendance_data.get(dt, 0)
                row.append({"day": dt, "events": day_events, "attendance": day_attendance})
        weeks.append(row)

    prev_y, prev_m = (y - 1, 12) if m == 1 else (y, m - 1)
    next_y, next_m = (y + 1, 1) if m == 12 else (y, m + 1)

    return render_template(
        "events_calendar.html",
        year=y, month=m, month_name=calendar.month_name[m],
        weeks=weeks,
        events_by_date=events_by_date,
        attendance_by_date=attendance_data,
        prev_str=f"{prev_y:04d}-{prev_m:02d}",
        next_str=f"{next_y:04d}-{next_m:02d}",
        _=_,
        current_lang=get_lang(),
    )

@app.route("/event-list")
def event_list():
    events = Event.query.order_by(Event.start_date.asc()).all()
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
            .join(Player, Player.id == EventRegistration.player_id)
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
    # load existing categories early so we can re-render on validation errors
    cats = ev.categories.order_by(EventCategory.name.asc()).all()

    if form.validate_on_submit():
        # helper to parse integers from raw form
        def gf_int(key):
            v = request.form.get(key)
            try:
                return int(v) if v not in (None, '') else None
            except Exception:
                return None

        age_from_val = gf_int('age_from')
        age_to_val = gf_int('age_to')
        # Validate age range when both provided
        if age_from_val is not None and age_to_val is not None and age_to_val < age_from_val:
            flash(_('Age "to" must be greater than or equal to Age "from".'), 'danger')
            return render_template("event_categories.html", ev=ev, cats=cats, form=form)

        cat = EventCategory(
            event_id=ev.id,
            name=form.name.data,
            age_from=age_from_val,
            age_to=age_to_val,
            sex=request.form.get('sex') or None,
            fee=form.fee.data,
            team_size=request.form.get('team_size') or None,
            kyu=request.form.get('kyu') or None,
            dan=request.form.get('dan') or None,
            other_cutoff_date=request.form.get('other_cutoff_date') or None,
            limit=request.form.get('limit') or None,
            limit_team=request.form.get('limit_team') or None,
        )
        db.session.add(cat)
        db.session.commit()
        flash(_('Category added.'), 'success')
        return redirect(url_for('event_categories', event_id=ev.id))
    return render_template('event_categories.html', ev=ev, cats=cats, form=form)

@app.route("/admin/events/<int:event_id>/categories/<int:cat_id>/delete", methods=["POST"])
@admin_required
def event_category_delete(event_id: int, cat_id: int):
    ev = Event.query.get_or_404(event_id)
    cat = EventCategory.query.filter_by(id=cat_id, event_id=ev.id).first_or_404()
    db.session.delete(cat)
    db.session.commit()
    flash(_("Category deleted."), "info")
    return redirect(url_for("event_categories", event_id=ev.id))


@app.route("/admin/events/<int:event_id>/categories/<int:cat_id>/edit", methods=["GET", "POST"])
@admin_required
def event_category_edit(event_id: int, cat_id: int):
    ev = Event.query.get_or_404(event_id)
    cat = EventCategory.query.filter_by(id=cat_id, event_id=ev.id).first_or_404()
    form = EventCategoryForm(obj=cat)
    # If this is an AJAX GET (modal load), return a fragment without base layout
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_event_category_modal_fragment.html', ev=ev, form=form, cat=cat)

    if request.method == 'POST':
        # parse integer fields
        def gf_int(key):
            v = request.form.get(key)
            try:
                return int(v) if v not in (None, '') else None
            except Exception:
                return None

        age_from_val = gf_int('age_from')
        age_to_val = gf_int('age_to')
        if age_from_val is not None and age_to_val is not None and age_to_val < age_from_val:
            msg = _('Age "to" must be greater than or equal to Age "from".')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {'success': False, 'error': msg}, 400
            flash(msg, 'danger')
            return render_template('event_category_form.html', ev=ev, form=form, cat=cat)

        # update fields
        cat.name = request.form.get('name') or cat.name
        cat.age_from = age_from_val
        cat.age_to = age_to_val
        cat.sex = request.form.get('sex') or None
        cat.fee = gf_int('fee')
        cat.team_size = request.form.get('team_size') or None
        cat.kyu = request.form.get('kyu') or None
        cat.dan = request.form.get('dan') or None
        cat.other_cutoff_date = request.form.get('other_cutoff_date') or None
        cat.limit = request.form.get('limit') or None
        cat.limit_team = request.form.get('limit_team') or None
        db.session.add(cat)
        db.session.commit()
        flash(_('Category updated.'), 'success')
        # If AJAX request, return JSON so modal can close without redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {'success': True}
        return redirect(url_for('event_categories', event_id=ev.id))

    return render_template('event_category_form.html', ev=ev, form=form, cat=cat)

#-----------------------------
# Manually added
#-----------------------------
# --- Update medals for event registration categories ---
@app.route("/admin/events/registrations/<int:reg_id>/update_medals", methods=["POST"])
@admin_required
def event_reg_update_medals(reg_id):
    reg = EventRegistration.query.get_or_404(reg_id)
    changed = False
    for rc in reg.reg_categories:
        field = f"medal_{rc.category_id}"
        new_val = request.form.get(field)
        if new_val != (rc.medal or ""):
            rc.medal = new_val or None
            changed = True
    if changed:
        db.session.commit()
        flash("Medals updated.", "success")
    else:
        flash("No changes made.", "info")
    return redirect(request.referrer or url_for("event_registrations", event_id=reg.event_id))

# Bulk import endpoint for event categories
@app.route("/admin/events/<int:event_id>/categories/import", methods=["POST"])
@admin_required
def event_categories_import(event_id: int):
    ev = Event.query.get_or_404(event_id)
    data = request.get_json()
    rows = data.get("rows", [])
    imported = 0
    errors = []
    for idx, row in enumerate(rows):
        # Expect: name, age_from, age_to, sex, fee, team_size, kyu, dan, other_cutoff_date, limit, team_limit
        if not row or not row[0]:
            continue
        try:
            cat = EventCategory(
                event_id=ev.id,
                name=row[0],
                age_from=int(row[1]) if len(row) > 1 and row[1] else None,
                age_to=int(row[2]) if len(row) > 2 and row[2] else None,
                sex=row[3] if len(row) > 3 and row[3] else None,
                fee=int(row[4]) if len(row) > 4 and row[4] else None,
                team_size=row[5] if len(row) > 5 and row[5] else None,
                kyu=row[6] if len(row) > 6 and row[6] else None,
                dan=row[7] if len(row) > 7 and row[7] else None,
                other_cutoff_date=row[8] if len(row) > 8 and row[8] else None,
                limit=row[9] if len(row) > 9 and row[9] else None,
                limit_team=row[10] if len(row) > 10 and row[10] else None,
            )
            db.session.add(cat)
            imported += 1
        except Exception as e:
            errors.append(f"Row {idx+1}: {str(e)}")
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
    return {"success": True, "imported": imported, "errors": errors}

# -------- Registrations --------
@app.route("/admin/events/<int:event_id>/registrations", methods=["GET", "POST"])
@admin_required
def event_registrations(event_id: int):
    ev = Event.query.get_or_404(event_id)
    form = EventRegistrationForm()

    players = Player.query.filter_by(active_member=True).order_by(Player.last_name.asc(), Player.first_name.asc()).all()
    form.player_ids.choices = [(p.id, p.full_name()) for p in players]
    cats = ev.categories.order_by(EventCategory.name.asc()).all()

    # If a player is selected, filter categories for that player
    selected_player_id = None
    if request.method == "POST":
        # Try to get the first selected player (single or multi)
        if form.player_ids.data:
            selected_player_id = form.player_ids.data[0] if isinstance(form.player_ids.data, list) else form.player_ids.data
    elif request.method == "GET" and request.args.get("player_id"):
        selected_player_id = int(request.args.get("player_id"))
        # Pre-select the athlete in the form
        form.player_ids.data = [selected_player_id]

    filtered_cats = cats
    if selected_player_id:
        player = Player.query.get(selected_player_id)
        if player:
            today = date.today()
            age = None
            if player.birthdate:
                age = today.year - player.birthdate.year - ((today.month, today.day) < (player.birthdate.month, player.birthdate.day))
            weight = player.weight_kg
            sex_raw = (player.gender or '').strip().lower()
            # Map common values to 'm'/'f'
            sex_map = {'male': 'm', 'm': 'm', 'man': 'm', 'мъж': 'm', 'female': 'f', 'f': 'f', 'woman': 'f', 'жена': 'f', 'ж': 'f'}
            sex = sex_map.get(sex_raw, sex_raw)
            def cat_ok(cat):
                # Sex match (or not set)
                cat_sex = (cat.sex or '').strip().lower()
                if cat_sex and cat_sex not in (sex, '', None):
                    return False
                # Age match (within +2 years)
                if age is not None:
                    if cat.age_from is not None and age < cat.age_from:
                        return False
                    if cat.age_to is not None and age > (cat.age_to + 2):
                        return False
                # Weight match (under or equal to limit)
                if weight is not None and cat.limit is not None:
                    try:
                        if int(weight) > int(cat.limit):
                            return False
                    except Exception:
                        pass
                return True
            filtered_cats = [c for c in cats if cat_ok(c)]
    form.category_ids.choices = [(c.id, c.name) for c in filtered_cats]

    if form.validate_on_submit():
        selected_cats = [EventCategory.query.get(cid) for cid in form.category_ids.data]
        selected_cats = [c for c in selected_cats if c and c.event_id == ev.id]
        registration_added = False
        for pid in form.player_ids.data:
            # Check for existing registrations for this event/player
            existing_regs = EventRegistration.query.filter_by(event_id=ev.id, player_id=pid).all()
            existing_cat_ids = set()
            for reg in existing_regs:
                existing_cat_ids.update(rc.category_id for rc in reg.reg_categories)

            # Create separate registration for each selected category that isn't already registered
            player_obj = Player.query.get(pid)
            for cat in selected_cats:
                if cat.id not in existing_cat_ids:
                    reg = EventRegistration(
                        event_id=ev.id,
                        player_id=pid,
                        player_pn=(player_obj.pn if player_obj else None),
                        fee_override=form.fee_override.data,
                        paid=bool(form.paid.data),
                        paid_on=(date.today() if form.paid.data else None),
                    )
                    reg.reg_categories = [EventRegCategory(category_id=cat.id)]
                    db.session.add(reg)
                    registration_added = True
        db.session.commit()
        if registration_added:
            flash(_("Registration added."), "success")
        else:
            flash(_("Registration declined."), "danger")
        return redirect(url_for("event_registrations", event_id=ev.id))

    paid_filter = request.args.get("paid", "").strip().lower()
    q = request.args.get("q", "").strip()

    regs_query = (EventRegistration.query
                  .filter_by(event_id=ev.id)
                  .join(Player, Player.id == EventRegistration.player_id))

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
            .join(Player, Player.id == EventRegistration.player_id)
            .order_by(Player.last_name.asc(), Player.first_name.asc())
            .all())
    # Precompute CSV rows while the DB session is active to avoid detached-instance lazy loads
    csv_rows = []
    for r in regs:
        cats = "; ".join([rc.category.name for rc in r.reg_categories]) if r.reg_categories else ""
        medals = "; ".join([rc.medal or "" for rc in r.reg_categories]) if r.reg_categories else ""
        expected = r.fee_override if r.fee_override is not None else (
            sum((rc.category.fee or 0) for rc in r.reg_categories) if r.reg_categories else ""
        )
        paid = "yes" if r.paid else "no"
        paid_on = r.paid_on.isoformat() if r.paid_on else ""
        endd = (ev.end_date or ev.start_date).isoformat()
        full_name = r.player.full_name() if r.player else ''
        csv_rows.append((r.player_id, full_name, cats, medals, expected, paid, paid_on, ev.title, ev.start_date.isoformat(), endd, ev.location or ''))

    def generate():
        yield "player_id,full_name,categories,medals,fee_eur,paid,paid_on,event_title,start_date,end_date,location\n"
        for row in csv_rows:
            # Ensure values are CSV-safe (simple approach)
            vals = [str(v) for v in row]
            yield ",".join(vals) + "\n"

    headers = {"Content-Disposition": f'attachment; filename="event_{ev.id}_registrations.csv"'}
    return Response(generate(), mimetype="text/csv", headers=headers)


@app.route("/admin/events/<int:event_id>/export_full", endpoint='event_export_full')
@admin_required
def event_export_full(event_id: int):
    """Export full event data as a ZIP: event.json, categories.csv, registrations.csv,
    per-player CSVs and photos."""
    ev = Event.query.get_or_404(event_id)
    cats = EventCategory.query.filter_by(event_id=ev.id).order_by(EventCategory.name.asc()).all()
    regs = (EventRegistration.query
            .filter_by(event_id=ev.id)
            .join(Player, Player.id == EventRegistration.player_id)
            .order_by(Player.last_name.asc(), Player.first_name.asc())
            .all())

    import json
    import csv
    from io import StringIO, BytesIO
    import zipfile

    # Prepare per-player list
    player_ids = {r.player_id for r in regs if r.player_id}
    players = Player.query.filter(Player.id.in_(player_ids)).all() if player_ids else []

    mem_zip = BytesIO()
    with zipfile.ZipFile(mem_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        # event JSON
        ev_dict = {
            'id': ev.id,
            'title': ev.title,
            'start_date': ev.start_date.isoformat() if ev.start_date else None,
            'end_date': ev.end_date.isoformat() if ev.end_date else None,
            'location': ev.location,
            'sportdata_url': ev.sportdata_url,
            'notes': ev.notes,
        }
        zf.writestr(f'event_{ev.id}_detail.json', json.dumps(ev_dict, ensure_ascii=False, indent=2))

        # categories CSV
        cat_out = StringIO()
        cat_writer = csv.writer(cat_out)
        cat_writer.writerow(['id', 'name', 'age_from', 'age_to', 'sex', 'fee', 'team_size', 'kyu', 'dan', 'other_cutoff_date', 'limit_team', 'limit'])
        for c in cats:
            cat_writer.writerow([c.id, c.name, c.age_from, c.age_to, c.sex, c.fee, c.team_size, c.kyu, c.dan, c.other_cutoff_date, c.limit_team, c.limit])
        zf.writestr(f'event_{ev.id}_categories.csv', cat_out.getvalue())

        # registrations CSV
        reg_out = StringIO()
        reg_writer = csv.writer(reg_out)
        reg_writer.writerow(['id', 'player_id', 'player_name', 'fee_override', 'computed_fee', 'paid', 'paid_on', 'note', 'categories', 'medals'])
        for r in regs:
            cats_list = []
            medals_list = []
            for rc in r.reg_categories or []:
                # rc.category may be loaded; protect against None
                cats_list.append(rc.category.name if rc.category else '')
                medals_list.append(rc.medal or '')
            computed = r.fee_override if r.fee_override is not None else (sum((rc.category.fee or 0) for rc in r.reg_categories) if r.reg_categories else '')
            reg_writer.writerow([r.id, r.player_id, r.player.full_name() if r.player else '', r.fee_override, computed, r.paid, (r.paid_on.isoformat() if r.paid_on else ''), '', '; '.join(cats_list), '; '.join(medals_list)])
        zf.writestr(f'event_{ev.id}_registrations.csv', reg_out.getvalue())

        # per-player CSVs
        fieldnames = [
            'id', 'first_name', 'last_name', 'gender', 'birthdate', 'pn',
            'belt_rank', 'grade_level', 'grade_date', 'discipline', 'weight_kg', 'height_cm',
            'email', 'phone', 'join_date', 'active_member', 'notes', 'photo_filename',
            'sportdata_wkf_url', 'sportdata_bnfk_url', 'sportdata_enso_url',
            'medical_exam_date', 'medical_expiry_date', 'insurance_expiry_date',
            'monthly_fee_amount', 'monthly_fee_is_monthly',
            'mother_name', 'mother_phone', 'father_name', 'father_phone'
        ]
        for p in players:
            out = StringIO()
            dw = csv.DictWriter(out, fieldnames=fieldnames)
            dw.writeheader()
            row = {k: getattr(p, k, '') for k in fieldnames}
            for k, v in row.items():
                if hasattr(v, 'isoformat'):
                    row[k] = v.isoformat()
                elif isinstance(v, bool):
                    row[k] = str(v)
            dw.writerow(row)
            zf.writestr(f'players/player_{p.id}_{(p.last_name or "").replace(" ","_")}.csv', out.getvalue())

            # photos are intentionally omitted from full export

    mem_zip.seek(0)
    headers = {'Content-Disposition': f'attachment; filename="event_{ev.id}_full_export.zip"'}
    return Response(mem_zip.getvalue(), mimetype='application/zip', headers=headers)


@app.route('/admin/events/import_zip', methods=['POST'])
@admin_required
def import_event_zip():
    # Handle uploaded ZIP exported by the full-event export
    if 'zipfile' not in request.files:
        flash(_('No file uploaded'), 'danger')
        return redirect(request.referrer or url_for('events_calendar'))
    f = request.files['zipfile']
    if f.filename == '':
        flash(_('No file selected'), 'danger')
        return redirect(request.referrer or url_for('events_calendar'))
    try:
        import io
        import zipfile
        import re
        import csv
        import json as _json

        data = f.read()
        bio = io.BytesIO(data)
        with zipfile.ZipFile(bio) as z:
            app.logger.info(f"ZIP contents: {z.namelist()}")
            # Find event detail JSON matching export pattern: event_<id>_detail.json
            ev_json = None
            ev_prefix = None
            for name in z.namelist():
                m = re.match(r'^event_(\d+)_detail\.json$', os.path.basename(name))
                if m:
                    ev_prefix = f'event_{m.group(1)}'
                    with z.open(name) as ef:
                        ev_json = _json.load(io.TextIOWrapper(ef, encoding='utf-8'))
                    break

            # Determine categories filename (prefer event_{id}_categories.csv)
            cat_filename = None
            if ev_prefix:
                want = f'{ev_prefix}_categories.csv'
                if want in z.namelist():
                    cat_filename = want
            if not cat_filename:
                # fallback to any file that ends with categories.csv
                for name in z.namelist():
                    if name.endswith('categories.csv'):
                        cat_filename = name
                        break

            # Create or find Event record from the exported JSON
            ev = None
            if ev_json:
                try:
                    sd = ev_json
                    sd_start = None
                    sd_end = None
                    if sd.get('start_date'):
                        try:
                            sd_start = date.fromisoformat(sd.get('start_date'))
                        except Exception:
                            sd_start = None
                    if sd.get('end_date'):
                        try:
                            sd_end = date.fromisoformat(sd.get('end_date'))
                        except Exception:
                            sd_end = None
                    # Try to find an existing event by title+start_date
                    if sd.get('title') and sd_start:
                        ev = Event.query.filter_by(title=sd.get('title'), start_date=sd_start).first()
                    if not ev:
                        ev = Event(title=sd.get('title') or 'Imported event', start_date=sd_start, end_date=sd_end, location=sd.get('location'), sportdata_url=sd.get('sportdata_url'), notes=sd.get('notes'))
                        db.session.add(ev)
                        db.session.flush()
                except Exception:
                    ev = None

            created_cats = []
            if cat_filename:
                with z.open(cat_filename) as cf:
                    txt = io.TextIOWrapper(cf, encoding='utf-8')
                    reader = csv.DictReader(txt)
                    app.logger.info(f"Categories CSV headers: {reader.fieldnames}")
                    if reader.fieldnames:
                        for i, row in enumerate(reader):
                            if i < 5:
                                app.logger.info(f"Categories CSV row {i}: {row}")
                            try:
                                # Normalize keys and values
                                norm_row = { (k.strip().lower() if k else k): (v.strip() if isinstance(v, str) else v) for k, v in row.items() }
                                name = (norm_row.get('name') or '').strip()
                                if not name:
                                    continue
                                def parse_int_field(val):
                                    if val in (None, ''):
                                        return None
                                    try:
                                        return int(float(val))
                                    except Exception:
                                        return None
                                age_from = parse_int_field(norm_row.get('age_from'))
                                age_to = parse_int_field(norm_row.get('age_to'))
                                sex = norm_row.get('sex') or None
                                fee = None
                                if norm_row.get('fee'):
                                    try:
                                        fee = int(float(norm_row.get('fee')))
                                    except Exception:
                                        fee = None
                                team_size = norm_row.get('team_size') or None
                                kyu = norm_row.get('kyu') or None
                                dan = norm_row.get('dan') or None
                                other_cutoff_date = norm_row.get('other_cutoff_date') or None
                                limit_team = norm_row.get('limit_team') or None
                                limit = norm_row.get('limit') or None
                                if not EventCategory.query.filter_by(event_id=ev.id, name=name).first():
                                    cat = EventCategory(event_id=ev.id, name=name, age_from=age_from, age_to=age_to, sex=sex, fee=fee, team_size=team_size, kyu=kyu, dan=dan, other_cutoff_date=other_cutoff_date, limit=limit, limit_team=limit_team)
                                    db.session.add(cat)
                                    created_cats.append(cat)
                            except Exception:
                                app.logger.exception('Error parsing category row')
                                continue
            db.session.commit()

            # Build category lookup by name for registrations
            db.session.flush()
            cat_by_name = {c.name: c for c in EventCategory.query.filter_by(event_id=ev.id).all()}
            cats_created_count = len(created_cats)

            # Registrations
            regs_imported = 0
            regs_skipped = 0
            regs_duplicated = 0
            reg_name = f'{ev_prefix}_registrations.csv' if ev_prefix else 'registrations.csv'
            if reg_name in z.namelist():
                with z.open(reg_name) as rf:
                    txt = io.TextIOWrapper(rf, encoding='utf-8')
                    reader = csv.DictReader(txt)
                    for row in reader:
                        try:
                            orig_player_id = int(row.get('player_id') or 0)
                        except Exception:
                            orig_player_id = None
                        player = None
                        if orig_player_id:
                            player = Player.query.get(orig_player_id)
                        if not player:
                            regs_skipped += 1
                            continue
                        if EventRegistration.query.filter_by(event_id=ev.id, player_pn=player.pn).first():
                            regs_duplicated += 1
                            continue
                        fee_override = None
                        try:
                            fee_override = int(row.get('fee_override')) if row.get('fee_override') else None
                        except Exception:
                            fee_override = None
                        paid = (str(row.get('paid') or '').lower() in ('1','true','yes'))
                        reg = EventRegistration(event_id=ev.id, player_id=player.id, player_pn=player.pn, fee_override=fee_override, paid=paid, paid_on=(date.fromisoformat(row.get('paid_on')) if row.get('paid_on') else None))
                        db.session.add(reg)
                        db.session.flush()
                        regs_imported += 1
                        cats_field = row.get('categories') or ''
                        medals_field = row.get('medals') or ''
                        cats_list = [c.strip() for c in cats_field.split(';') if c.strip()]
                        medals_list = [m.strip() for m in medals_field.split(';') if m.strip()]
                        for idx, cname in enumerate(cats_list):
                            cat_obj = cat_by_name.get(cname)
                            if cat_obj:
                                if not EventRegCategory.query.filter_by(registration_id=reg.id, category_id=cat_obj.id).first():
                                    rc = EventRegCategory(registration_id=reg.id, category_id=cat_obj.id)
                                    if idx < len(medals_list) and medals_list[idx]:
                                        rc.medal = medals_list[idx]
                                    db.session.add(rc)
            db.session.commit()
            flash(f'Event imported. Categories created: {cats_created_count}. Registrations imported: {regs_imported}. Registrations skipped (no matching player): {regs_skipped}. Registrations skipped (duplicate): {regs_duplicated}.', 'success')
            return redirect(url_for('event_detail', event_id=ev.id))
    except zipfile.BadZipFile:
        flash('Uploaded file is not a valid ZIP archive', 'danger')
    except Exception as e:
        app.logger.exception('Import failed')
        flash(f'Import failed: {e}', 'danger')
    return redirect(request.referrer or url_for('events_calendar'))


# -------- Players ZIP import --------
@app.route('/admin/players/import_zip', methods=['POST'])
@admin_required
def import_players_zip():
    if 'zipfile' not in request.files:
        flash(_('No file uploaded'), 'danger')
        return redirect(request.referrer or url_for('list_players'))
    f = request.files['zipfile']
    if f.filename == '':
        flash(_('No file selected'), 'danger')
        return redirect(request.referrer or url_for('list_players'))
    try:
        import io
        import zipfile
        import csv

        data = f.read()
        bio = io.BytesIO(data)
        created = 0
        updated = 0
        skipped = 0
        errors = 0
        with zipfile.ZipFile(bio) as z:
            app.logger.info(f"Players ZIP contents: {z.namelist()}")
            # compute used ids to allocate first-available ids (include ones we create during this run)
            existing_ids = {r[0] for r in db.session.query(Player.id).all()}
            used_ids = set(existing_ids)

            def first_available_id():
                i = 1
                while i in used_ids:
                    i += 1
                used_ids.add(i)
                return i

            # Process files under players/ or any CSV files that look like player exports
            for name in z.namelist():
                base = os.path.basename(name)
                if not base.lower().endswith('.csv'):
                    continue
                # prefer files in players/ folder but accept any csv
                if ('players/' not in name) and (not base.startswith('player_')):
                    continue
                with z.open(name) as pf:
                    txt = io.TextIOWrapper(pf, encoding='utf-8')
                    reader = csv.DictReader(txt)
                    app.logger.info(f"Player CSV headers for {name}: {reader.fieldnames}")
                    if not reader.fieldnames:
                        continue
                    for i, row in enumerate(reader):
                        try:
                            # normalize keys
                            norm = { (k.strip().lower() if k else k): (v.strip() if isinstance(v, str) else v) for k, v in row.items() }

                            def parse_date(v):
                                if not v:
                                    return None
                                try:
                                    return date.fromisoformat(v)
                                except Exception:
                                    return None

                            def parse_int(v):
                                if not v:
                                    return None
                                try:
                                    return int(float(v))
                                except Exception:
                                    return None

                            fn = norm.get('first_name') or ''
                            ln = norm.get('last_name') or ''
                            if not (fn and ln):
                                skipped += 1
                                continue

                            # Always create a new Player; do NOT overwrite existing records.
                            # PN is required — skip rows without PN to avoid creating invalid records.
                            pn_val = norm.get('pn') or None
                            if not pn_val:
                                skipped += 1
                                continue
                            # Skip if PN already exists in DB
                            if Player.query.filter_by(pn=pn_val).first():
                                app.logger.info(f"Skipping import: PN already exists {pn_val}")
                                skipped += 1
                                continue
                            # Assign the first available numeric id (fill gaps) to the new player.
                            p = Player(
                                first_name=fn,
                                last_name=ln,
                                gender=norm.get('gender') or None,
                                birthdate=parse_date(norm.get('birthdate')),
                                pn=pn_val,
                                belt_rank=norm.get('belt_rank') or 'White',
                                grade_level=norm.get('grade_level') or None,
                                grade_date=parse_date(norm.get('grade_date')),
                                discipline=norm.get('discipline') or 'All',
                                weight_kg=parse_int(norm.get('weight_kg')),
                                height_cm=parse_int(norm.get('height_cm')),
                                email=norm.get('email') or None,
                                phone=norm.get('phone') or None,
                                join_date=parse_date(norm.get('join_date')),
                                active_member=(str(norm.get('active_member')).lower() in ('1','true','yes')) if norm.get('active_member') is not None else True,
                                notes=norm.get('notes') or None,
                                sportdata_wkf_url=norm.get('sportdata_wkf_url') or None,
                                sportdata_bnfk_url=norm.get('sportdata_bnfk_url') or None,
                                sportdata_enso_url=norm.get('sportdata_enso_url') or None,
                                medical_exam_date=parse_date(norm.get('medical_exam_date')),
                                medical_expiry_date=parse_date(norm.get('medical_expiry_date')),
                                insurance_expiry_date=parse_date(norm.get('insurance_expiry_date')),
                                monthly_fee_amount=parse_int(norm.get('monthly_fee_amount')),
                                monthly_fee_is_monthly=(str(norm.get('monthly_fee_is_monthly')).lower() in ('1','true','yes')) if norm.get('monthly_fee_is_monthly') is not None else True,
                                mother_name=norm.get('mother_name') or None,
                                mother_phone=norm.get('mother_phone') or None,
                                father_name=norm.get('father_name') or None,
                                father_phone=norm.get('father_phone') or None,
                            )
                            # allocate id
                            try:
                                p.id = first_available_id()
                            except Exception:
                                pass
                            db.session.add(p)
                            created += 1
                        except Exception:
                            app.logger.exception('Error importing player row')
                            errors += 1
            db.session.commit()
            # Ensure monthly payments exist for newly imported players so dues show up
            try:
                from datetime import date as _date
                ensure_payments_for_month(_date.today().year, _date.today().month)
            except Exception:
                app.logger.exception('Failed to ensure monthly payments after import')
        flash(f'Players import finished. Created: {created}. Updated: {updated}. Skipped: {skipped}. Errors: {errors}.', 'success')
        return redirect(url_for('list_players'))
    except zipfile.BadZipFile:
        flash('Uploaded file is not a valid ZIP archive', 'danger')
    except Exception as e:
        app.logger.exception('Players import failed')
        flash(f'Import failed: {e}', 'danger')
    return redirect(request.referrer or url_for('list_players'))

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
            # --- EventCategory columns migration ---
            result3 = conn.execute(text("PRAGMA table_info(event_category)"))
            existing3 = {row[1] for row in result3}
            eventcat_cols = [
                ("age_from", "INTEGER"),
                ("age_to", "INTEGER"),
                ("sex", "VARCHAR(10)"),
                ("team_size", "VARCHAR(20)"),
                ("kyu", "VARCHAR(20)"),
                ("dan", "VARCHAR(20)"),
                ("other_cutoff_date", "VARCHAR(40)"),
                ("limit_team", "VARCHAR(20)"),
                ("limit", "VARCHAR(20)")
            ]
            for col, t in eventcat_cols:
                col_sql = f'"{col}"' if col in ("limit", "limit_team") else col
                if col not in existing3:
                    conn.execute(text(f"ALTER TABLE event_category ADD COLUMN {col_sql} {t}"))
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
            if "pn" not in existing:
                conn.execute(text("ALTER TABLE player ADD COLUMN pn VARCHAR(20)"))
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
    # Add unique constraint on (player_id, date) for TrainingSession
    with db.engine.begin() as conn:
        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_player_session_date ON training_session (player_id, date)"))
        except Exception:
            pass
    with db.engine.begin() as conn:
        # --- EventCategory columns migration ---
        result3 = conn.execute(text("PRAGMA table_info(event_category)"))
        existing3 = {row[1] for row in result3}
        eventcat_cols = [
            ("age_from", "INTEGER"),
            ("age_to", "INTEGER"),
            ("sex", "VARCHAR(10)"),
            ("team_size", "VARCHAR(20)"),
            ("kyu", "VARCHAR(20)"),
            ("dan", "VARCHAR(20)"),
            ("other_cutoff_date", "VARCHAR(40)"),
            ("limit_team", "VARCHAR(20)"),
            ("limit", "VARCHAR(20)")
        ]
        for col, t in eventcat_cols:
            col_sql = f'"{col}"' if col in ("limit", "limit_team") else col
            if col not in existing3:
                conn.execute(text(f"ALTER TABLE event_category ADD COLUMN {col_sql} {t}"))

        result = conn.execute(text("PRAGMA table_info(player)"))
        existing = {row[1] for row in result}
        to_add = []
        for col, t in [
            ("pn", "VARCHAR(20)"),
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

        # Add player_pn columns to related tables to support PN-based relations
        for tbl in ("training_session", "payment", "event_registration", "payment_record"):
            info = conn.execute(text(f"PRAGMA table_info({tbl})"))
            cols = {row[1] for row in info}
            if "player_pn" not in cols:
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN player_pn VARCHAR(20)"))

        # Ensure Player.pn is unique (create unique index)
        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_player_pn ON player (pn)"))
        except Exception:
            pass

        # Backfill player_pn from existing player_id values
        try:
            conn.execute(text("UPDATE training_session SET player_pn = (SELECT pn FROM player WHERE player.id = training_session.player_id) WHERE player_pn IS NULL"))
            conn.execute(text("UPDATE payment SET player_pn = (SELECT pn FROM player WHERE player.id = payment.player_id) WHERE player_pn IS NULL"))
            conn.execute(text("UPDATE event_registration SET player_pn = (SELECT pn FROM player WHERE player.id = event_registration.player_id) WHERE player_pn IS NULL"))
            conn.execute(text("UPDATE payment_record SET player_pn = (SELECT pn FROM player WHERE player.id = payment_record.player_id) WHERE player_pn IS NULL"))
        except Exception:
            app.logger.exception('Backfill player_pn failed')

        # Add unique constraint on (player_id, date) for TrainingSession
        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_player_session_date ON training_session (player_id, date)"))
        except Exception:
            pass

with app.app_context():
    db.create_all()
    try:
        auto_migrate_on_startup()
    except Exception as e:
        app.logger.exception("Auto-migrate failed: %s", e)

# -----------------------------
# Admin Settings
# -----------------------------
@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    form = SettingsForm()
    if form.validate_on_submit():
        # Handle logo upload
        if form.logo.data:
            filename = secure_filename(form.logo.data.filename)
            if allowed_file(filename):
                filepath = os.path.join(app.root_path, 'static/img', filename)
                form.logo.data.save(filepath)
                setting = Setting.query.filter_by(key='logo_path').first()
                if not setting:
                    setting = Setting(key='logo_path')
                setting.value = f'/static/img/{filename}'
                db.session.add(setting)

        # Handle background upload
        if form.background.data:
            filename = secure_filename(form.background.data.filename)
            if allowed_file(filename):
                filepath = os.path.join(app.root_path, 'static/img', filename)
                form.background.data.save(filepath)
                setting = Setting.query.filter_by(key='background_image').first()
                if not setting:
                    setting = Setting(key='background_image')
                setting.value = f'/static/img/{filename}'
                db.session.add(setting)

        # Admin password
        if form.admin_password.data:
            import hashlib
            hashed = hashlib.sha256(form.admin_password.data.encode()).hexdigest()
            setting = Setting.query.filter_by(key='admin_password_hash').first()
            if not setting:
                setting = Setting(key='admin_password_hash')
            setting.value = hashed
            db.session.add(setting)

        # Colors
        if form.primary_color.data:
            setting = Setting.query.filter_by(key='primary_color').first()
            if not setting:
                setting = Setting(key='primary_color')
            setting.value = form.primary_color.data
            db.session.add(setting)

        if form.secondary_color.data:
            setting = Setting.query.filter_by(key='secondary_color').first()
            if not setting:
                setting = Setting(key='secondary_color')
            setting.value = form.secondary_color.data
            db.session.add(setting)

        db.session.commit()
        flash("Settings saved successfully.", "success")
        return redirect(url_for('admin_settings'))

    # Load current values
    logo_setting = Setting.query.filter_by(key='logo_path').first()
    background_setting = Setting.query.filter_by(key='background_image').first()
    primary_setting = Setting.query.filter_by(key='primary_color').first()
    secondary_setting = Setting.query.filter_by(key='secondary_color').first()

    return render_template(
        "admin_settings.html",
        form=form,
        current_logo=logo_setting.value if logo_setting else '/static/img/enso-logo.webp',
        current_background=background_setting.value if background_setting else None,
        current_primary=primary_setting.value if primary_setting else '#007bff',
        current_secondary=secondary_setting.value if secondary_setting else '#6c757d',
        _=_,
        current_lang=get_lang(),
    )

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

    # Uniqueness checks (except per-session)
    if kind == "training_month":
        pid = request.form.get("player_id", type=int)
        player = Player.query.get(pid)
        if not player:
            flash("Player is required for training payments.", "danger")
            return redirect(url_for("payment_new", player_id=player_id))
        month_str = request.form.get("month")
        y, m = parse_month_str(month_str)
        # Check for duplicate monthly payment
        exists = PaymentRecord.query.filter_by(kind="training_month", player_pn=player.pn, year=y, month=m).first()
        if exists:
            flash("Duplicate monthly payment for this player and month is not allowed.", "danger")
            return redirect(url_for("payment_new", player_id=player.id))
        record = PaymentRecord(kind=kind, amount=amount, currency=currency, method=method, note=note, player_id=player.id, player_pn=player.pn, year=y, month=m)
        pay = Payment.query.filter_by(player_pn=player.pn, year=y, month=m).first()
        record.payment_id = pay.id if pay else None
    elif kind == "event":
        rid = request.form.get("reg_id", type=int)
        reg = EventRegistration.query.get(rid)
        if not reg:
            flash("Event registration is required for event payments.", "danger")
            return redirect(url_for("payment_new", reg_id=reg_id))
        # Check for duplicate event payment for this registration
        reg_pn = (reg.player_pn or (reg.player.pn if getattr(reg, 'player', None) else None))
        exists = PaymentRecord.query.filter_by(kind="event", player_pn=reg_pn, event_registration_id=reg.id).first()
        if exists:
            flash("Duplicate event/category payment for this player and event registration is not allowed.", "danger")
            return redirect(url_for("payment_new", player_id=reg.player_id, reg_id=reg.id))
        record = PaymentRecord(kind=kind, amount=amount, currency=currency, method=method, note=note, player_id=reg.player_id, player_pn=(reg.player_pn or (reg.player.pn if getattr(reg, 'player', None) else None)), event_registration_id=reg.id)
    elif kind == "training_session":
        pid = request.form.get("player_id", type=int)
        player = Player.query.get(pid)
        if not player:
            flash("Player is required for training payments.", "danger")
            return redirect(url_for("payment_new", player_id=player_id))
        sessions_paid = request.form.get("sessions_paid", type=int) or 0
        record = PaymentRecord(kind=kind, amount=amount, currency=currency, method=method, note=note, player_id=player.id, player_pn=player.pn, sessions_paid=max(0, sessions_paid), sessions_taken=0)
        if player.monthly_fee_amount is not None and not player.monthly_fee_is_monthly:
            try:
                per_price = float(player.monthly_fee_amount)
                record.amount = int(round(record.sessions_paid * per_price))
            except Exception:
                pass

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
    pay = Payment.query.filter_by(player_pn=player.pn, year=year, month=month).first()

    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)

    regs_unpaid = (EventRegistration.query
                   .join(Event)
                   .filter(EventRegistration.player_pn == player.pn)
                   .filter(EventRegistration.paid.is_(False))
                   .filter(Event.start_date >= first, Event.start_date <= last)
                   .all())

    monthly_due = (pay.amount or 0) if (pay and not pay.paid and pay.amount is not None) else 0
    events_due = sum([(r.computed_fee() or 0) for r in regs_unpaid])
    due_date = first_working_day(year, month)

    # Use TrainingSession for session logic (unified with player_detail)
    all_sessions = TrainingSession.query.filter_by(player_pn=player.pn).all()
    paid_sessions = [s for s in all_sessions if s.paid]
    unpaid_sessions = [s for s in all_sessions if not s.paid]
    total_sessions_taken = len(all_sessions)
    total_sessions_paid = len(paid_sessions)
    total_sessions_unpaid = len(unpaid_sessions)
    per_session_amount = float(player.monthly_fee_amount) if player.monthly_fee_amount and not player.monthly_fee_is_monthly else None
    owed_amount = int(round(total_sessions_unpaid * per_session_amount)) if per_session_amount else 0
    # Only show session receipts for sessions counted as paid
    all_receipts = PaymentRecord.query.filter_by(player_pn=player.pn, kind='training_session').order_by(PaymentRecord.paid_at.desc()).all()
    sess_records = all_receipts[:total_sessions_paid]
    total_due = owed_amount + events_due
    return render_template(
        "player_due_print.html",
        player=player,
        year=year, month=month, due_date=due_date,
        pay=pay, regs_unpaid=regs_unpaid,
        monthly_due=owed_amount,
        events_due=events_due,
        total_due=total_due,
        sess_records=sess_records,
        total_sessions_paid=total_sessions_paid,
        total_sessions_taken=total_sessions_taken,
        total_sessions_unpaid=total_sessions_unpaid,
        total_prepaid_amount=sum((r.amount or 0) for r in sess_records),
        prepaid_credit=sum((r.amount or 0) for r in sess_records),
        per_session_amount=per_session_amount,
        owed_amount=owed_amount,
    )

@app.route("/reports/fees/period")
@admin_required
def fees_period_report():
    # Get date range parameters
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if not start_date_str or not end_date_str:
        flash("Please select both start and end dates.", "danger")
        return redirect(url_for("fees_report"))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid date format. Use YYYY-MM-DD.", "danger")
        return redirect(url_for("fees_report"))

    if start_date > end_date:
        flash("Start date cannot be after end date.", "danger")
        return redirect(url_for("fees_report"))

    # Get all active players
    players = Player.query.filter_by(active_member=True).order_by(Player.last_name.asc(), Player.first_name.asc()).all()

    # Aggregate data across the date range
    report_data = {
        'monthly_fees': {'total_income': 0, 'total_due': 0, 'details': []},
        'session_fees': {'total_income': 0, 'total_due': 0, 'details': []},
        'event_fees': {'total_income': 0, 'total_due': 0, 'details': []},
        'players': []
    }

    total_income = 0
    total_due = 0

    for player in players:
        player_data = {
            'player': player,
            'monthly_income': 0,
            'monthly_due': 0,
            'session_income': 0,
            'session_due': 0,
            'event_income': 0,
            'event_due': 0,
            'total_income': 0,
            'total_due': 0
        }

        # Monthly fees - get all payments in date range
        monthly_payments = PaymentRecord.query.filter_by(
            player_pn=player.pn, kind='training_month'
        ).filter(
            PaymentRecord.paid_at >= start_date,
            PaymentRecord.paid_at <= end_date
        ).all()

        monthly_income = sum(p.amount or 0 for p in monthly_payments)
        player_data['monthly_income'] = monthly_income
        report_data['monthly_fees']['total_income'] += monthly_income

        # Check for unpaid monthly fees in the period
        monthly_dues = Payment.query.filter_by(player_pn=player.pn, paid=False).filter(
            Payment.year >= start_date.year,
            Payment.month >= start_date.month,
            Payment.year <= end_date.year,
            Payment.month <= end_date.month
        ).all()
        monthly_due = sum(p.amount or 0 for p in monthly_dues)
        player_data['monthly_due'] = monthly_due
        report_data['monthly_fees']['total_due'] += monthly_due

        # Session fees - per session payments
        session_payments = PaymentRecord.query.filter_by(
            player_pn=player.pn, kind='training_session'
        ).filter(
            PaymentRecord.paid_at >= start_date,
            PaymentRecord.paid_at <= end_date
        ).all()

        session_income = sum(p.amount or 0 for p in session_payments)
        player_data['session_income'] = session_income
        report_data['session_fees']['total_income'] += session_income

        # Calculate owed session fees
        if not player.monthly_fee_is_monthly and player.monthly_fee_amount:
            # Count unpaid sessions in the date range
            unpaid_sessions = TrainingSession.query.filter_by(
                player_pn=player.pn, paid=False
            ).filter(
                TrainingSession.date >= start_date,
                TrainingSession.date <= end_date
            ).count()
            session_due = unpaid_sessions * player.monthly_fee_amount
            player_data['session_due'] = session_due
            report_data['session_fees']['total_due'] += session_due

        # Event fees - event payments
        event_payments = PaymentRecord.query.filter_by(
            player_pn=player.pn, kind='event'
        ).filter(
            PaymentRecord.paid_at >= start_date,
            PaymentRecord.paid_at <= end_date
        ).all()

        event_income = sum(p.amount or 0 for p in event_payments)
        player_data['event_income'] = event_income
        report_data['event_fees']['total_income'] += event_income

        # Calculate owed event fees
        # Event fees are due immediately upon registration, not based on event date
        event_dues = EventRegistration.query.filter_by(
            player_pn=player.pn, paid=False
        ).all()

        event_due = 0
        for reg in event_dues:
            event_due += reg.computed_fee() or 0
        player_data['event_due'] = event_due
        report_data['event_fees']['total_due'] += event_due

        # Calculate player totals
        player_data['total_income'] = player_data['monthly_income'] + player_data['session_income'] + player_data['event_income']
        player_data['total_due'] = player_data['monthly_due'] + player_data['session_due'] + player_data['event_due']
        # Calculate net income for each player: training income - event expenses
        player_data['net_income'] = player_data['monthly_income'] + player_data['session_income'] - (player_data['event_income'] + player_data['event_due'])

        total_income += player_data['total_income']
        total_due += player_data['total_due']

        report_data['players'].append(player_data)

    # Calculate net income: training income - event expenses (paid + due)
    # Event fees are pass-through, so subtract them from total income
    net_income = total_income - (report_data['event_fees']['total_income'] + report_data['event_fees']['total_due'])

    # Check if this is a print request
    if request.args.get('print') == '1':
        return render_template(
            "report_fees_period_print.html",
            report_data=report_data,
            start_date=start_date,
            end_date=end_date,
            total_income=total_income,
            total_due=total_due,
            net_income=net_income,
            generated_at=datetime.now()
        )

    # Default: render interactive version
    return render_template(
        "report_fees_period.html",
        report_data=report_data,
        start_date=start_date,
        end_date=end_date,
        total_income=total_income,
        total_due=total_due,
        net_income=net_income,
        today=date.today()
    )

@app.route("/admin/receipts/<int:rid>")
@admin_required
def receipt_view(rid: int):
    rec = db.session.get(PaymentRecord, rid)
    if not rec:
        abort(404)
    player = db.session.get(Player, rec.player_id)
    ev = None
    if rec.event_registration_id:
        reg = db.session.get(EventRegistration, rec.event_registration_id)
        ev = db.session.get(Event, reg.event_id) if reg else None
    return render_template("receipt.html", rec=rec, player=player, ev=ev)

# Dedicated print-friendly receipt view
@app.route("/admin/receipts/<int:rid>/print")
@admin_required
def receipt_print_view(rid: int):
    rec = db.session.get(PaymentRecord, rid)
    if not rec:
        abort(404)
    player = db.session.get(Player, rec.player_id)
    ev = None
    if rec.event_registration_id:
        reg = db.session.get(EventRegistration, rec.event_registration_id)
        ev = db.session.get(Event, reg.event_id) if reg else None
    return render_template("receipt_print.html", rec=rec, player=player, ev=ev)

@app.route("/admin/receipts/print_batch")
@admin_required
def receipts_print_batch():
    ids = request.args.get('ids', '')
    if not ids:
        flash('No receipts selected for printing.', 'info')
        return redirect(request.referrer or url_for('list_players'))
    id_list = [int(x) for x in ids.split(',') if x.strip().isdigit()]
    recs = (PaymentRecord.query
            .filter(PaymentRecord.id.in_(id_list))
            .order_by(PaymentRecord.paid_at.asc())
            .all())
    if not recs:
        flash('No receipts found.', 'info')
        return redirect(request.referrer or url_for('list_players'))
    return render_template('receipts_print_batch.html', recs=recs)

@app.route("/admin/receipts/print_batch_clean")
@admin_required
def receipts_print_batch_clean():
    ids = request.args.get('ids', '')
    if not ids:
        flash('No receipts selected for printing.', 'info')
        return redirect(request.referrer or url_for('list_players'))
    id_list = [int(x) for x in ids.split(',') if x.strip().isdigit()]
    recs = (PaymentRecord.query
            .filter(PaymentRecord.id.in_(id_list))
            .order_by(PaymentRecord.paid_at.asc())
            .all())
    if not recs:
        flash('No receipts found.', 'info')
        return redirect(request.referrer or url_for('list_players'))
    return render_template('receipts_print_batch_clean.html', recs=recs)

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

    # Always create a new TrainingSession row for this player
    today = date.today()
    # Avoid duplicate session for same player and date (unique constraint)
    existing = TrainingSession.query.filter_by(player_pn=player.pn, date=today).first()
    if existing:
        flash('Session for today already recorded.', 'info')
        return redirect(request.referrer or url_for('player_detail', player_id=player.id))
    
    # For monthly payers, mark as paid since they pay monthly
    is_paid = player.monthly_fee_is_monthly
    
    session_id = f"{player.id}_{today.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S%f')}"
    ts = TrainingSession(player_id=player.id, player_pn=player.pn, date=today, session_id=session_id, paid=is_paid, created_at=datetime.now())
    db.session.add(ts)
    try:
        db.session.commit()
        flash('Session recorded. New TrainingSession created.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to record TrainingSession (possible race or duplicate)')
        flash('Session recording failed (possibly already exists).', 'warning')

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

    # Monthly (pay only selected month, prevent duplicate receipts)
    if kind in ("monthly", "all"):
        # Get selected month from form (YYYY-MM), else default to current month
        month_str = request.form.get("month")
        if month_str:
            try:
                y, m = [int(x) for x in month_str.split("-")]
            except Exception:
                y, m = today.year, today.month
        else:
            y, m = today.year, today.month

        # Find unpaid Payment for that month
        p = Payment.query.filter_by(player_pn=player.pn, year=y, month=m, paid=False).first()
        if p:
            # Prevent duplicate PaymentRecord for this player/month
            exists = PaymentRecord.query.filter_by(kind='training_month', player_pn=player.pn, year=y, month=m).first()
            if exists:
                flash(f"Payment for {y}-{m:02d} already exists.", "warning")
            else:
                amt = p.amount or 0
                rec = PaymentRecord(kind='training_month', player_id=player.id, player_pn=player.pn,
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
        else:
            flash("No unpaid monthly fee for the selected month.", "warning")

    # Events
    if kind in ("events", "all"):
        regs = EventRegistration.query.filter_by(player_pn=player.pn, paid=False).all()
        for r in regs:
            amt = r.computed_fee() or 0
            rec = PaymentRecord(kind='event', player_id=player.id, player_pn=(r.player_pn or (r.player.pn if getattr(r, 'player', None) else None)),
                                amount=amt, event_registration_id=r.id,
                                currency='EUR', note='PAY_FROM_LIST')
            db.session.add(rec)
            db.session.flush()  # Ensure rec.id is available
            try:
                rec.assign_receipt_no()
            except Exception:
                pass
            r.paid = True
            r.paid_on = today
            db.session.add(r)
            db.session.commit()  # Commit after each registration to ensure status is saved
            total_amount += amt
            created.append(rec)

    # Debts (true AUTO_DEBT only)
    debts_to_pay = []
    if kind in ("debts", "all"):
        debts = (PaymentRecord.query
             .filter(PaymentRecord.player_pn == player.pn,
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
            kind=d.kind, player_id=player.id, player_pn=player.pn,
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
        sess_records_all = PaymentRecord.query.filter_by(player_pn=player.pn, kind='training_session').all()
        # Prepaid = all non-debt training receipts (MANUAL_OWED is prepaid, not debt)
        sess_receipts = [r for r in sess_records_all if not is_auto_debt_note(r.note)]
        total_sessions_taken = sum((r.sessions_taken or 0) for r in sess_records_all)
        total_prepaid_amount = sum((r.amount or 0) for r in sess_receipts)

        expected_cost = int(round(total_sessions_taken * unit_price))
        prepaid_credit_now = int(round(total_prepaid_amount))
        residual_owed = expected_cost - prepaid_credit_now

        if residual_owed > 0:
            rec = PaymentRecord(
                kind='training_session', player_id=player.id, player_pn=player.pn,
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
    # Optional hardening for cookies in production
    # app.config.update(
    #     SESSION_COOKIE_HTTPONLY=True,
    #     SESSION_COOKIE_SAMESITE="Lax",
    #     # SESSION_COOKIE_SECURE=True,  # enable if served over HTTPS
    # )
    app.run(host="0.0.0.0", port=5000)