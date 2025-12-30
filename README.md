## Quick orientation

This repo is a small two-tier app: a Python FastAPI backend (server) that integrates with Supabase and Google Calendar, and a Next.js frontend in `apps/web` that communicates with the backend via cookie-based sessions.

High-level components
- Backend: `backend/` — FastAPI app, Google OAuth + Calendar integration, Supabase access.
- Frontend: `apps/web/` — Next 13 app directory UI, talks to backend at `http://localhost:8000` during dev.

## How to run locally

- Install backend deps: `python -m pip install -r requirements.txt` (use a venv).
- Backend dev server: `uvicorn backend.main:app --reload --port 8000` (this is the canonical command used in the repo).
- Frontend dev server: `cd apps/web && npm run dev` (or `pnpm dev` / `yarn dev` depending on your package manager; scripts defined in `apps/web/package.json`).

Notes:
- The frontend calls backend endpoints with `credentials: 'include'` and expects cookies to be set by the backend (see `apps/web/app/page.tsx`).
- For local OAuth testing, the backend sets `OAUTHLIB_INSECURE_TRANSPORT=1` in the environment; secure flags should be enabled in production.

## Required environment variables (backend)

- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY (server-side/key with permissions to read/write tables)
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- FERNET_KEY (used to encrypt refresh tokens; `ConnectionService` uses it)
- OAUTH_REDIRECT_URI (default: `http://localhost:8000/api/auth/callback`) / FRONTEND_URL (default `http://localhost:3000`)

Files that read env: `backend/main.py`, `backend/services/google_calendar/connection.py`, `backend/services/google_calendar/oauth_server.py`.

## Key data model / Supabase tables used (expect these to exist)

- `medicos` (doctors) — created or looked up during OAuth (`sync_medico_profile`)
- `users_tokens` — stores `email`, `access_token`, `refresh_token_encrypted`, `token_expiry`, `scopes`
- `consultorios` — stores consultorio entries created when a new site/clinic is created
- `horarios_atencion` — stores recurring schedule rows
- `auth_sessions` — session rows used to map browser cookie sessions to an email / oauth_state

Search for these tables in `backend/` to see where they are read/written (e.g., `ConnectionService.get_medico_by_email`, `room_mgmt.py`, `setup_availability.py`).

## Important behavior & patterns (examples to follow)

- OAuth flow: The server generates a Flow (`obtener_flujo_google`), stores `oauth_state` in `auth_sessions`, and finalizes the callback in `/api/auth/callback` (see `backend/main.py` and `oauth_server.py`). Keep `OAUTH_REDIRECT_URI` in sync with Google console.

- Tokens: Refresh tokens are encrypted with `FERNET_KEY` and saved in `users_tokens`. Use `ConnectionService.build_credentials(email)` to obtain a valid access token (it auto-refreshes and persists new access tokens).

- Calendar ops: `calendar_logic.next_n_slots` uses Google FreeBusy and expects timezone-aware datetimes (raises if tz-naive). Working timezone is often `America/Argentina/Buenos_Aires` in scheduling helpers.

-- Creating a new clinic (sede): POST `/api/rooms` -> `room_mgmt.create_room` creates a Google Calendar, inserts a `consultorio`, and optionally creates recurring busy events via `setup_availability.configurar_disponibilidad_recurrente`.

## Debugging tips

- Check printed env values and startup logs in the backend; `oauth_server.py` prints `GOOGLE_CLIENT_ID` and `OAUTH_REDIRECT_URI` at import-time.
- If OAuth fails: confirm `oauth_state` is saved to `auth_sessions`, check `OAUTH_REDIRECT_URI` and that your Google Console has the callback registered.
- For token issues, verify `FERNET_KEY` matches the one used to encrypt entries in Supabase; `ConnectionService.decrypt` uses it.

## Coding conventions / patterns

- Python: type hints are used widely and `dataclasses` used in scheduling logic (`Slot` in `calendar_logic.py`). Prefer timezone-aware datetimes when interacting with Google API.
- API: FastAPI for backend; routers live under `backend/api/*` and are included from `backend/main.py`.
- Frontend: Next.js app with `app/` directory; UI components are in `apps/web/components` and expect backend to be available at `http://localhost:8000` by default.

## Useful examples (copy/paste)

- Check auth session status:
  curl -v -c cookies.txt http://localhost:8000/api/auth/status

- Kick off OAuth (browser is expected): open `http://localhost:3000` and click the "Conectar Google Calendar" button in the UI (it calls `GET /api/auth/google`).

- Create a sede via API (example payload):
  POST http://localhost:8000/api/rooms
  Body: { "email": "doc@example.com", "nombre": "Sede Centro", "direccion": "Av X 123", "horarios": { "mondayStart": "08:00", "mondayEnd": "12:00", "fridayStart": "08:00", "fridayEnd": "16:00" } }

## When in doubt

- Inspect `backend/services/google_calendar/*` for authentication, token and calendar usage patterns.
- If you need to modify resource ownership or DB schema, update the Supabase table usage sites (search for `.table("...")` calls) and keep token encryption aligned with `FERNET_KEY`.

---

If anything here is unclear or you want more detail (CI, test strategy, db migrations), tell me which section to expand and I'll iterate. ✅
