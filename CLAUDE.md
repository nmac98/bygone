# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

**Bygone** is a Flask web app for exploring Dublin's heritage — locations, historical photos, guided walking/running tours, and plaque identification via AI. It is deployed on Render with a PostgreSQL database and Supabase for image storage.

## Environment setup

Required environment variables (in `.env` locally; provided by Render in production):

```
DATABASE_URL=postgresql://...
SECRET_KEY=...
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_BUCKET=bygone-images
ANTHROPIC_API_KEY=...
```

## Running locally

```bash
source venv/bin/activate
flask run
```

Production server (as used by Render):
```bash
gunicorn app:app
```

## Database migrations

```bash
flask db migrate -m "description"
flask db upgrade
```

Migrations live in `migrations/versions/`. The database schema is also snapshotted in `render.dump`.

## Architecture

### Application structure

- **`app.py`** — Flask app factory: loads config, registers extensions (SQLAlchemy, Flask-Migrate, Flask-Login), registers blueprints.
- **`models.py`** — All SQLAlchemy models in a single file.
- **`config.py`** — Single `Config` class; requires `DATABASE_URL` env var; handles the `postgres://` → `postgresql://` Render quirk.
- **`extensions/`** — Thin wrappers: `__init__.py` holds `db` and `migrate` instances; `login.py` holds the `LoginManager`.
- **`auth/`** — Login/logout routes and a `User` model (separate from main models).
- **`utils/`** — `supabase_storage.py` (upload/delete/URL helpers), `decorators.py` (`@admin_required`), `ids.py` (ULID generation).

### Blueprints

| Blueprint | Prefix | Purpose |
|---|---|---|
| `main_bp` | `/` | Home, explore map, tours list, plaque analyser |
| `locations_bp` | `/gallery` | Location detail page (gallery + chapters) |
| `routes_bp` | `/route` | Walking/running route viewer |
| `auth` | `/login` | Authentication |
| `admin_bp` | `/admin` | Full CRUD for locations, routes, images, chapters, topics |

### Data model

The core hierarchy is:

```
Location
  ├── LocationImage → ImageAsset → ImageFile   (carousel photos, stored in Supabase)
  └── LocationChapter (ordered)
        ├── ChapterBlock (ordered: text | image | link | divider | people)
        └── ChapterTopic → Topic               (reusable "find out more" links)

Route
  └── RouteStop (ordered) → Location
        waypoints: JSON [{lat, lon, after_stop}]  (GPS path between stops)
```

`ImageAsset` is the metadata record (title, date, lat/lon); `ImageFile` holds the actual Supabase storage key and public URL. The `variant` field on `ImageFile` is always `"original"` currently.

Location IDs are human-readable strings (e.g. `"trinity-college"`). Image IDs are ULIDs. Route IDs are strings.

### Image storage

Images are stored in Supabase Storage (`bygone-images` bucket) under the key `original/<ulid>.<ext>`. The public URL is constructed directly from `SUPABASE_URL` — see `utils/supabase_storage.py:22`. Uploads use the service role key, not the anon key.

### AI features

Two endpoints call the Anthropic API (`claude-sonnet-4-6`):

- `POST /plaques/analyze` — identifies a plaque from an uploaded photo; resizes to <4 MB before sending.
- `POST /admin/ai/draft` — drafts content for admin forms: `location_description`, `chapter_summary`, `text_block`, `people_cards`, `stop_dialogue`.

### Admin access

All `/admin/*` routes require `@admin_required` (Flask-Login + `user.is_admin` flag). Unauthenticated users are redirected to `/login`; authenticated non-admins get 403.

### Frontend

Static assets are in `static/` — `main.css`, `map.css`, `main.js`, `map.js`, `components.css/js`. The interactive map on `/explore` uses Leaflet (loaded from `static/vendor/`). The running route page has GPS tracking and turn-by-turn navigation built in JS.

Templates use Jinja2 with a `base.html` layout and `components/` partials (`top_nav.html`, `bottom_nav.html`, `map_container.html`).

A custom Jinja filter `from_json` is registered in `app.py` for deserialising JSON stored in template variables.
