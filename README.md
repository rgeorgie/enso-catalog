# enso-catalog
a clean, cross‑platform (Linux/Windows) web app you can run locally for a karate club player catalog. It includes a simple web UI, search &amp; filters, admin login for CRUD, and optional photo uploads.

Tech stack: Python 3, Flask, SQLite (no external DB needed)
Features:

List/search/filter players
View player profile
Add/Edit/Delete players (admin only)
Upload player photo (optional)
Export list as CSV


Security:

Simple admin login (env-configurable credentials)
CSRF-protected forms
File upload validation (size & extension)

Runs on Linux and Windows. No internet required once dependencies are installed.

```Project structure
karate-club/
├─ app.py
├─ requirements.txt
├─ .gitignore
├─ uploads/             # auto-created on first run
└─ templates/
   ├─ base.html
   ├─ players_list.html
   ├─ player_form.html
   ├─ player_detail.html
   └─ login.html
```
How to run
A) Linux/macOS (Bash/Zsh)
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(16))')"
export ADMIN_USER="admin"
export ADMIN_PASS="change_me"

python app.py
# Open http://127.0.0.1:5000
```
B) Windows (PowerShell)
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(16))")
$env:ADMIN_USER = "admin"
$env:ADMIN_PASS = "change_me"

python app.py
# Open http://127.0.0.1:5000
```

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
