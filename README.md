a clean, cross‑platform (Linux/Windows) web app you can run locally for a karate club player catalog. It includes a simple web UI, search &amp; filters, admin login for CRUD, and optional photo uploads.
# enso-catalog

enso-catalog is a cross-platform (Linux/macOS/Windows) web app for managing a karate club's players, payments, events, and receipts. It provides a modern admin UI, search/filtering, CSV export, and photo uploads—all running locally with no external dependencies beyond Python.

## Tech Stack
- Python 3
- Flask (single-file app)
- SQLite (local DB, no server required)
- WTForms (forms & validation)

## Features

- **Players**: List, search, filter, add, edit, delete. Each player can have a photo, contact info, medical/insurance data, and parent contacts.
- **Payments & Receipts**:
    - Track monthly and per-session training fees.
    - Mark payments as paid/unpaid; print or export receipts.
    - Per-session logic: pay for a number of sessions, track sessions taken, and show remaining/prepaid balance.
    - Admin can record payments for monthly dues, events, or session debts directly from the player profile.
- **Events & Registrations**:
    - Create/edit/delete events with categories and fees.
    - Register players for events and mark event payments.
    - Track medals per event/category.
- **Reports & Exports**:
    - Export player list, event registrations, and payment reports as CSV.
    - Medals and fee reports for club bookkeeping.
- **Photo Uploads**: Store player photos in `uploads/` (max 2MB, jpg/png/gif/webp).
- **Localization**: Simple i18n (BG/EN) with in-app language switch.
- **Admin UI**: All CRUD and sensitive actions require admin login (credentials via env vars).

## Security
- Admin login (username/password from environment variables)
- CSRF-protected forms
- File upload validation (type & size)

## Project Structure

```
enso-catalog/
├─ app.py                # Main Flask app (all logic/models/routes)
├─ requirements.txt      # Python dependencies
├─ uploads/              # Uploaded player photos
├─ static/               # CSS, images
├─ templates/            # Jinja2 HTML templates
│   ├─ base.html
│   ├─ players_list.html
│   ├─ player_form.html
│   ├─ player_detail.html
│   ├─ event_form.html
│   ├─ event_detail.html
│   ├─ event_categories.html
│   ├─ event_registrations.html
│   ├─ payment_new.html
│   ├─ report_fees.html
│   ├─ report_medals.html
│   └─ login.html
└─ karate_club.db        # SQLite database (auto-created)
```

## How to Run

### A) Linux/macOS (Bash/Zsh)
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(16))')"
export ADMIN_USER="admin"
export ADMIN_PASS="change_me"

python app.py
# Open http://127.0.0.1:5000
```

### B) Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(16))")
$env:ADMIN_USER = "admin"
$env:ADMIN_PASS = "change_me"

python app.py
# Open http://127.0.0.1:5000
```

## Notes
- All data is stored locally in `karate_club.db`.
- To reset, delete the DB and uploads folder.
- For more, see comments in `app.py` and the `.github/copilot-instructions.md` file.

7) Optional: Docker
Create Dockerfile:
```
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV SECRET_KEY=change_me \
    ADMIN_USER=admin \
    ADMIN_PASS=change_me
EXPOSE 5000
CMD ["python", "app.py"]
```
Build & Run:
```
docker build -t karate-club .
docker run --rm -p 5000:5000 -e SECRET_KEY=prod_secret -e ADMIN_USER=admin -e ADMIN_PASS=change_me -v "$PWD/uploads:/app/uploads" karate-club
```
Notes & next steps

Security: The admin login uses env vars. For production, consider hashing passwords and using Flask-Login with user records.
Backups: The app stores data in karate_club.db (SQLite). Back up the file and the uploads/ directory.
Extensibility ideas:

Roles (viewer vs admin)
Belt history and grading dates
Competition results (kata/kumite), medals, ranks
CSV import for bulk data
Localization (Bulgarian UI)
Deploy behind a reverse proxy (nginx) with HTTPS
