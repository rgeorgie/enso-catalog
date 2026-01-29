# enso-catalog
here’s a clean, cross‑platform (Linux/Windows) web app you can run locally for a karate club player catalog. It includes a simple web UI, search &amp; filters, admin login for CRUD, and optional photo uploads.

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

Project structure
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
