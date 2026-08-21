# Glittering Field Academy — School Management System

A Django (server-side rendered) school management system for **Glittering
Field Academy** — Creche to Secondary, Suleja, Niger State. SQLite by
default, ZainPay for online fee payments (admission fees and termly school
fees), real fee-versioning so a price change never rewrites history.

This started as a static HTML/JS/LocalStorage frontend prototype and has
been rebuilt phase by phase into a real Django backend; the original
prototype's design system (`assets/css`, `assets/js/app.js`) is reused
directly as the template layer.

## Local development setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows — venv/bin/activate on macOS/Linux
pip install -r requirements.txt

copy .env.example .env         # cp on macOS/Linux — then fill in real values

python manage.py migrate
python manage.py seed_demo_users       # the 4 demo login accounts
python manage.py seed_academics        # sessions/terms/classes/sections/subjects
python manage.py seed_fee_structures   # the real 2025/2026 fee schedule
python manage.py seed_grade_boundaries # A–F grading
python manage.py seed_demo_people      # links demo accounts to real records
python manage.py seed_demo_data        # bulk realistic students/teachers/results/attendance/invoices

python manage.py runserver
```

Or, after the first `seed_demo_users`, `python manage.py reset_demo_data`
runs every seed step above (except `seed_demo_users`) in the correct order
in one go — this is also what the **Settings → Reset Demo Data** button in
the app calls.

## Demo logins

| Role          | Email               | Password     |
|---------------|----------------------|--------------|
| Administrator | admin@gfa.edu.ng     | admin123     |
| Teacher       | teacher@gfa.edu.ng   | teacher123   |
| Parent        | parent@gfa.edu.ng    | parent123    |
| Student       | student@gfa.edu.ng   | student123   |

## Running the tests

```bash
python manage.py test
```

37 tests cover: Zainpay webhook signature verification and idempotency,
the fee-structure snapshot/versioning guarantee (the core requirement —
changing fees must never alter an already-issued invoice), the admission
application wizard, attendance/results access control, and the demo-data
reset command's safety guarantees (never touches user accounts or school
configuration).

## Project layout

```
glittering/
├── manage.py
├── config/            # Django project settings/urls
├── accounts/          # custom User (role field), auth, role_required decorator
├── website/           # public site + SchoolSettings singleton + Contact form
├── admissions/        # Application wizard, admin review workflow, tracking
├── payments/          # ZainPay client (payments/services.py) + webhook — shared
│                         by admission fees and termly fees
├── academics/          # Sessions, Terms, Classes, Sections, Subjects, FeeBands
├── students/           # Student, Guardian
├── staff/               # Teacher
├── attendance/          # Mark attendance, records
├── results/              # Result entry (auto-graded), report cards
├── finance/              # FeeStructure (versioned), Invoice, Payment — termly fees
├── communication/        # Announcements, Events
├── portal/                # Role-based dashboard home, Reports, Settings
├── templates/              # base.html, base_public.html, base_dashboard.html + partials
└── assets/                  # the original prototype's CSS/JS, served as static files
```

## ZainPay configuration

Set these in `.env` (see `.env.example` for the full list with comments):

```
ZAINPAY_PUBLIC_KEY=
ZAINPAY_ZAINBOX_CODE=
ZAINPAY_BASE_URL=https://sandbox.zainpay.ng   # https://api.zainpay.ng in production
ZAINPAY_CALLBACK_URL=
ZAINPAY_SECRET_KEY=                            # verifies the webhook's HMAC signature
ZAINPAY_RECONCILE_LOOKBACK_HOURS=720
```

Create a **dedicated Zainpay merchant account/zainbox for this school** —
do not reuse credentials from another project. Both admission-fee and
termly-fee payments go through the same `payments/services.py` client and
the same webhook endpoint (`/payments/zainpay/callback/`).

Run `python manage.py reconcile_zainpay` on a schedule (every 5 minutes is
what ZainPay's own docs recommend) as a safety net for any payment whose
webhook never arrived:

```cron
*/5 * * * * /path/to/venv/bin/python /path/to/manage.py reconcile_zainpay >> reconcile_zainpay.log 2>&1
```

## Deployment checklist

1. **Environment**
   - `DEBUG=False`
   - `SECRET_KEY` — generate a fresh one (`django.core.management.utils.get_random_secret_key()`), never reuse the dev value
   - `ALLOWED_HOSTS` — your real domain(s), not `*`
   - `SITE_URL` — the public HTTPS URL (used to build links in emails/webhooks with no request object)
   - `ZAINPAY_BASE_URL=https://api.zainpay.ng`, `ZAINPAY_CALLBACK_URL` pointing at the live domain
2. **Database** — SQLite ships by default and is fine at this school's scale; swap `DATABASES` for Postgres in `config/settings.py` if concurrent-write load ever demands it. Either way, back up `db.sqlite3` (or the Postgres DB) regularly — it holds admissions, results, and payment records.
3. **Static & media files**
   ```bash
   python manage.py collectstatic --noinput
   ```
   WhiteNoise serves static files directly from the WSGI process (no separate static server needed); switch `STORAGES['staticfiles']` from `CompressedStaticFilesStorage` to `CompressedManifestStaticFilesStorage` once `collectstatic` is a standard part of your deploy, for cache-busted filenames. `MEDIA_ROOT` (student photos, application documents) needs its own backup — it's real user-uploaded data.
4. **Run with gunicorn behind a reverse proxy** (nginx/Caddy terminating TLS):
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
   ```
5. **HTTPS** — once TLS is confirmed working end-to-end, set `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True` in settings.
6. **Migrations**: `python manage.py migrate` on every deploy.
7. **First deploy only**: `seed_demo_users` (or create a real superuser with `createsuperuser` instead, if you don't want the demo accounts in production), `seed_academics`, `seed_fee_structures`, `seed_grade_boundaries` — then let the school's own admin staff take it from there through the app. Do **not** run `reset_demo_data` against a production database with real records — it deletes students, results, attendance, invoices and payments.
8. **Cron**: `reconcile_zainpay` as above.
