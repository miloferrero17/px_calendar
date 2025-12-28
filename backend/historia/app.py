#!/usr/bin/env python3
"""
app.py
Flask app que gestiona OAuth2 con Google Calendar y persiste tokens en Supabase (Data API).
- No usa conexión Postgres directa: usa supabase-py (REST).
- Guarda refresh_token encriptado con Fernet.
"""

import os
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from flask import Flask, request, redirect, jsonify
from cryptography.fernet import Fernet

# Google libs
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Supabase
from supabase import create_client

# Load env
load_dotenv()

# Config required in .env
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "http://localhost:5000/oauth/callback")
SCOPES = os.environ.get("OAUTH_SCOPES", "https://www.googleapis.com/auth/calendar.events").split(',')
FERNET_KEY = os.environ.get("FERNET_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE")
FLASK_SECRET = os.environ.get("FLASK_SECRET", os.urandom(24).hex())

# Basic validations
missing = []
for k, v in [
    ("GOOGLE_CLIENT_ID", CLIENT_ID),
    ("GOOGLE_CLIENT_SECRET", CLIENT_SECRET),
    ("FERNET_KEY", FERNET_KEY),
    ("SUPABASE_URL", SUPABASE_URL),
    ("SUPABASE_SERVICE_ROLE", SUPABASE_SERVICE_ROLE),
]:
    if not v:
        missing.append(k)
if missing:
    raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}. Revisa tu .env")

# Setup
app = Flask(__name__)
app.secret_key = FLASK_SECRET
fernet = Fernet(FERNET_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)

# Helpers para Supabase table users_tokens
USERS_TABLE = "users_tokens"

def supabase_get_user(email: str):
    """Devuelve fila (dict) o None"""
    res = supabase.table(USERS_TABLE).select("*").eq("email", email).execute()
    # supabase-py returns an object with .data (list) or .error
    data = getattr(res, "data", None)
    if not data:
        return None
    return data[0]

def supabase_insert_or_update_user(email: str, update_fields: dict):
    """Inserta o updatea (upsert) por email. Devuelve row final."""
    # Usamos upsert behavior: insert with on_conflict if supabase configured. Simpler: try insert, on conflict update via RPC not available here.
    # supabase REST can do upsert via .upsert().execute() in newer SDKs. We'll attempt upsert.
    try:
        res = supabase.table(USERS_TABLE).upsert({**{"email": email}, **update_fields}).execute()
    except Exception:
        # Fallback: try insert (may error) then update
        try:
            res = supabase.table(USERS_TABLE).insert({**{"email": email}, **update_fields}).execute()
        except Exception:
            res = supabase.table(USERS_TABLE).update(update_fields).eq("email", email).execute()
    return getattr(res, "data", None)

def encrypt_token(plain: str) -> str:
    return fernet.encrypt(plain.encode()).decode()

def decrypt_token(enc: str) -> str:
    return fernet.decrypt(enc.encode()).decode()

# OAuth start
@app.route("/auth/start")
def auth_start():
    # optional state param: ?email=...
    email = request.args.get("email")
    state = json.dumps({"email": email}) if email else None

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
    return redirect(auth_url)

# OAuth callback
@app.route("/oauth/callback")
def oauth_callback():
    state = request.args.get("state")
    saved_state = json.loads(state) if state else {}
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    # Exchange code
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    # Try to obtain user's email
    email = None
    # Prefer state email if provided
    if saved_state.get("email"):
        email = saved_state.get("email")
    # If id_token present, attempt to extract email
    if not email and getattr(creds, "id_token", None):
        try:
            # id_token may be a decoded dict or JWT string; google-auth may supply id_token as str.
            if isinstance(creds.id_token, dict):
                email = creds.id_token.get("email")
            else:
                # safe fallback: call tokeninfo
                import requests
                rr = requests.get("https://oauth2.googleapis.com/tokeninfo", params={"access_token": creds.token})
                if rr.ok:
                    email = rr.json().get("email")
        except Exception:
            pass

    if not email:
        return "No pudimos obtener el email del usuario. Incluye ?email=... en /auth/start o reintenta.", 400

    # Save tokens in Supabase (encrypt refresh token)
    refresh_token = getattr(creds, "refresh_token", None)
    enc = None
    if refresh_token:
        enc = encrypt_token(refresh_token)

    # Prepare fields to save
    fields = {}
    if enc:
        fields["refresh_token_encrypted"] = enc
    fields["access_token"] = creds.token
    fields["token_expiry"] = creds.expiry.isoformat() if getattr(creds, "expiry", None) else None
    fields["scopes"] = ",".join(getattr(creds, "scopes", SCOPES))
    fields["revoked"] = False
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    inserted = supabase_insert_or_update_user(email, fields)
    return f"Autorización completada para {email}. Puedes cerrar esta ventana."

# Helper to build calendar service for user email
def get_calendar_service_for(email: str):
    # Fetch row
    row = supabase_get_user(email)
    if not row:
        raise Exception("Usuario no encontrado o no autorizado")

    enc_refresh = row.get("refresh_token_encrypted")
    if not enc_refresh:
        raise Exception("Usuario no tiene refresh_token almacenado")

    refresh_token = decrypt_token(enc_refresh)
    access_token = row.get("access_token")
    expiry_iso = row.get("token_expiry")
    expiry = None
    if expiry_iso:
        try:
            expiry = datetime.fromisoformat(expiry_iso)
        except Exception:
            expiry = None

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=row.get("scopes", SCOPES).split(",")
    )

    # Refresh if needed
    if not creds.valid:
        try:
            creds.refresh(Request())
        except Exception as e:
            # Mark revoked in supabase to force reauth
            try:
                supabase.table(USERS_TABLE).update({"revoked": True}).eq("email", email).execute()
            except Exception:
                pass
            raise Exception("No se pudo refrescar el token; requiere re-autorización") from e

        # Save new access_token & expiry back to supabase
        update_fields = {
            "access_token": creds.token,
            "token_expiry": creds.expiry.isoformat() if getattr(creds, "expiry", None) else None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            supabase.table(USERS_TABLE).update(update_fields).eq("email", email).execute()
        except Exception:
            pass

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return service

# Endpoint: listar próximos eventos (ejemplo)
@app.route("/events/list")
def events_list():
    email = request.args.get("email")
    if not email:
        return jsonify({"error":"email param required"}), 400
    try:
        service = get_calendar_service_for(email)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    now = datetime.utcnow().isoformat() + "Z"
    events_result = service.events().list(calendarId="primary", timeMin=now, maxResults=10,
                                          singleEvents=True, orderBy="startTime").execute()
    items = events_result.get("items", [])
    return jsonify(items)

# Endpoint optional: revoke (mark revoked + call google revocation)
@app.route("/auth/revoke", methods=["POST"])
def revoke():
    payload = request.json or {}
    email = payload.get("email")
    if not email:
        return jsonify({"error":"email required"}), 400
    row = supabase_get_user(email)
    if not row:
        return jsonify({"error":"user not found"}), 404
    access_token = row.get("access_token")
    if access_token:
        import requests
        try:
            requests.post("https://oauth2.googleapis.com/revoke", params={"token": access_token})
        except Exception:
            pass
    # mark revoked
    supabase.table(USERS_TABLE).update({"revoked": True, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("email", email).execute()
    return jsonify({"status":"revoked"})

# --- chequeo de disponibilidad para un intervalo ---
from dateutil import parser as dateparser  # pip install python-dateutil si no lo tenés

@app.route("/events/is_free")
def events_is_free():
    """
    GET /events/is_free?email=...&start=2025-12-23T10:00:00-03:00&duration=60
    Devuelve si el usuario está libre en ese intervalo.
    """
    email = request.args.get("email")
    start_str = request.args.get("start")
    duration_min = int(request.args.get("duration", 60))

    if not email or not start_str:
        return jsonify({"error": "params required: email, start (ISO8601)"}), 400

    try:
        start_dt = dateparser.isoparse(start_str)
    except Exception as e:
        return jsonify({"error": "start must be ISO8601 (e.g. 2025-12-23T10:00:00-03:00)", "detail": str(e)}), 400

    end_dt = start_dt + timedelta(minutes=duration_min)

    # RFC3339 strings with zone (google wants something like 2025-12-23T10:00:00-03:00)
    time_min = start_dt.isoformat()
    time_max = end_dt.isoformat()

    try:
        service = get_calendar_service_for(email)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "items": [{"id": "primary"}],  # pregunta por el calendario primary del usuario
    }

    try:
        fb = service.freebusy().query(body=body).execute()
        # fb example: {'calendars': {'primary': {'busy': [ { 'start':..., 'end':... }, ... ] } }, ...}
        busy = fb.get("calendars", {}).get("primary", {}).get("busy", [])
        free = len(busy) == 0

        # Opcional: obtener más detalles de los eventos (resumen) si hay conflictos
        conflicts = []
        if not free:
            # Si querés detalles, podemos pedir eventos list entre timeMin/timeMax y devolver resumen
            evs = service.events().list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime"
            ).execute().get("items", [])
            for e in evs:
                conflicts.append({
                    "id": e.get("id"),
                    "summary": e.get("summary"),
                    "start": e.get("start"),
                    "end": e.get("end"),
                    "organizer": e.get("organizer", {}).get("email")
                })

        return jsonify({
            "free": free,
            "start": time_min,
            "end": time_max,
            "conflicts": conflicts
        })
    except Exception as e:
        return jsonify({"error": "freebusy query failed", "detail": str(e)}), 500



if __name__ == "__main__":
    # dev server
    app.run(host="0.0.0.0", port=5000, debug=True)
