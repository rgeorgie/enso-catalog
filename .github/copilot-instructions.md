# Copilot instructions — enso-catalog

Purpose: concise, actionable guidance for AI coding agents working on this repository.

- **Big picture:** Single-file Flask monolith in `app.py` providing a small admin UI for a karate club: players, payments, events, registrations, receipts. Data stored in SQLite at `karate_club.db` (BASE_DIR). Templates are under `templates/`; static assets under `static/` and uploaded photos in `uploads/`.

- **Key models & relationships (edit here first):** defined in `app.py` near the top of the file: `Player`, `Payment`, `Event`, `EventCategory`, `EventRegistration`, `EventRegCategory`, and `PaymentRecord`. Use ORM fields there when changing DB shape.

- **Admin guard and credentials:** admin routes use `session['is_admin']` and the credentials come from env vars `ADMIN_USER` / `ADMIN_PASS`. To run tests or local debugging, set these env vars to known values.

- **Migrations / schema changes:** The app uses idempotent, ad-hoc migrations inside `app.py`:
  - `/admin/migrate` route runs ALTER TABLE to add missing `player` columns.
  - `auto_migrate_on_startup()` is invoked at app start to add the same set of columns.
  - When adding a column, update the ORM `Player` model and also add the column name/type to both `migrate()` and `auto_migrate_on_startup()` so migrations run correctly.

- **Uploads & file limits:** Uploaded files are stored in `uploads/`. Allowed extensions are in `ALLOWED_EXTENSIONS` and max upload size is `MAX_CONTENT_LENGTH` (2 MB). Use `allowed_file()` helper before saving.

- **Localization:** Simple in-file i18n via `translations` dictionary and `_()` helper; default language is Bulgarian (`bg`) stored in session via route `/lang/<code>`.

- **Forms & templates:** WTForms classes live in `app.py` (`PlayerForm`, `EventForm`, etc.). Routes pass context expected by templates (examples: `create_player` and `edit_player` pass `belt_colors_json=json.dumps(BELT_PALETTE)` to `player_form.html`). When modifying templates, update the corresponding route to ensure required context keys are provided.

- **Payments vs Receipts:** Two related concepts:
  - `Payment` — monthly bookkeeping row (year/month/player). Managed by `ensure_payments_for_month()` and toggled in `/admin/fees/<id>/toggle`.
  - `PaymentRecord` — receipt/receipt-numbered record used for receipts and printing; created in `/admin/payments/new` and stored separate from `Payment` (can link to it via `payment_id`).

- **CSV exports & reporting endpoints:** useful examples for data export and reporting: `/export/csv`, `/admin/reports/fees/export`, `/admin/events/<id>/export`, `/reports/medals`.

- **Local run / debug:** recommended commands:

  - Create virtualenv and install deps from `requirements.txt`.

    pip install -r requirements.txt

  - Run locally:

    python app.py

  - If you need deterministic admin access during development:

    export ADMIN_USER=admin; export ADMIN_PASS=admin123; export SECRET_KEY=dev

- **Common change patterns for AI edits:**
  - Adding a Player field: add a column to `Player` ORM, add to forms (PlayerForm), add to `migrate()` and `auto_migrate_on_startup()`, and update any templates that display or edit that field (e.g., `player_form.html`, `player_detail.html`).
  - Adding an endpoint: keep route handlers in `app.py` (this repo centralizes routes here). Expose template variables in `render_template()` as the last step.
  - Updating exports/reports: follow the streaming `Response(generate(), mimetype='text/csv')` pattern used in existing CSV endpoints.

- **Conventions & idioms:**
  - Single-file app: prefer minimal invasive changes — keep helpers and templates consistent.
  - Use helpers declared in `app.py` (e.g., `belt_chip_style`, `validity_badge`) rather than reimplementing logic in templates.
  - Avoid changing DB filenames or moving DB out of BASE_DIR without also updating `app.config['SQLALCHEMY_DATABASE_URI']`.

- **Integration points / external dependencies:**
  - Dependencies in `requirements.txt`: `Flask`, `Flask-WTF`, `Flask-SQLAlchemy`, `email-validator`.
  - No external APIs are required at runtime; `sportdata_*` URLs are stored as fields but not fetched automatically.

- **What NOT to change without checking the user:**
  - The ad-hoc migration approach (ALTER TABLE + `db.create_all()`) — changing it affects upgrade path for existing users.
  - The upload path (`uploads/`) or SQL file name unless you update config and docs.

If anything above is unclear or you want this file expanded with CI, tests, or deploy notes, tell me which area to expand. I will iterate.
