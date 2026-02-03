# enso-catalog

enso-catalog is a small single-file Flask application for managing a karate club: players, training sessions, monthly/per-session payments, events, registrations and receipts. It's designed to run locally with SQLite and a lightweight admin UI.

## Tech Stack
- Python 3
- Flask (single-file app)
- SQLite (local DB, no server required)
- WTForms (forms & validation)
 - JavaScript (small client-side helpers + DataTables for some reports)

## Features

- **Players**: List, search, filter, add, edit, delete. Each player has a mandatory 10-digit PN (ЕГН) as stable UID. Photos, contact info, medical/insurance data, and parent contacts are supported.
- **Training Sessions**: Track attendance for all players (monthly and per-session payers). Interactive calendar view and detailed list view in player profiles. Record sessions with automatic payment status based on player type. Calendar shows training sessions, event participations, and external BNFK federation events (informational only, cached daily) with clickable event details. Events with registered players display a club logo and participant count.
- **Kiosk Mode**: Public interface (`/kiosk`) for athletes to record training sessions without admin login. Click on name, enter Player Number in modal to confirm and record session.
- **Payments & Receipts**:
  - Track monthly bookkeeping rows (`Payment`) and receipt records (`PaymentRecord`).
  - Export all payments/receipts as CSV (`/admin/reports/payments/export_all`).
  - Per-session support via `TrainingSession` rows (mark paid/unpaid and create receipts).
- **Events & Registrations**:
  - Create/edit/delete events with categories and fees.
  - Register players for events and mark event payments.
  - Track medals per event/category.
  - **Event Payment Report**: Grouped by player showing all categories, total fees, and payment status.
- **Reports & Exports**:
  - Admin export/import pages: `/admin/exports` and `/admin/imports` provide CSV/ZIP import-export endpoints.
  - Export players (ZIP/CSV), events (ZIP without photos), registrations and full payment backups as CSV.
- **Photo Uploads**: Store player photos in `uploads/` (max 2MB, jpg/png/gif/webp).
- **Localization**: Simple i18n (BG/EN) with in-app language switch.
- **Admin UI**: All CRUD and sensitive actions require admin login (credentials via env vars).
- **Admin Settings**: Customize app appearance and security via `/admin/settings` - upload custom logo, background image, set primary/secondary colors, and change admin password (stored securely as hash).

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
│   ├─ admin_settings.html
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

Notes:
- For development set `ADMIN_USER`/`ADMIN_PASS` to known values (e.g. `admin`/`admin123`).
- The app auto-creates the DB and runs safe, idempotent ad-hoc migrations on startup (non-destructive column additions).
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
- Training sessions are tracked for all players regardless of payment type - monthly payers have sessions automatically marked as paid, while per-session payers can have paid or unpaid sessions.
- The calendar widget in player profiles provides an intuitive view of training attendance and event participations over time, with clickable event details.
- Admin settings allow customization of the app's appearance (logo, background, colors) and security (admin password).
- For more, see comments in `app.py` and the `.github/copilot-instructions.md` file.

Important operational notes
- PN is mandatory: when creating players via the UI or CSV import, `pn` must be exactly 10 digits. The CSV importer validates and rejects invalid/duplicate PN rows.
- UID migration: the app maintains `player_pn` on related rows to preserve historical relations. A non-destructive backfill runs on startup for missing fields; if you plan a destructive purge or DB-level FK changes, back up `karate_club.db` and `uploads/` first.
- Import/Export endpoints: use `/admin/imports` and `/admin/exports` (admin-only) for bulk operations. Event exports are ZIPs (photos excluded) and players export/import supports ZIP/CSV.
- Purge: there is an admin `purge` endpoint that permanently deletes a player after backfilling related rows with the PN — this is irreversible; use the confirmation token to trigger.
- Watermark: templates include a centered faint watermark of the site logo (in `static/img/enso-logo.webp`). If you print pages, consider hiding the watermark via CSS @media print rules.

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
