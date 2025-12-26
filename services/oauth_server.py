#!/usr/bin/env python3
"""
oauth_server.py
Actualizado para integrarse con la tabla 'medicos' y 'users_tokens'.
"""

import os
# Para localhost (http)
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

import json
from datetime import datetime, timezone
from dotenv import load_dotenv

from flask import Flask, request, redirect, jsonify
from cryptography.fernet import Fernet
import requests

from google_auth_oauthlib.flow import Flow
from supabase import create_client

# -----------------------
# Config
# -----------------------
load_dotenv()

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "http://localhost:5000/oauth/callback")

OAUTH_SCOPES = os.environ.get(
    "OAUTH_SCOPES",
    "openid,email,profile,https://www.googleapis.com/auth/calendar",
)
SCOPES = [s.strip() for s in OAUTH_SCOPES.split(",") if s.strip()]

FERNET_KEY = os.environ.get("FERNET_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
# IMPORTANTE: Cambiamos a la variable que corregimos en el .env
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
FLASK_SECRET = os.environ.get("FLASK_SECRET", os.urandom(24).hex())

# -----------------------
# Setup services
# -----------------------
app = Flask(__name__)
app.secret_key = FLASK_SECRET

fernet = Fernet(FERNET_KEY)
# Usamos la KEY corregida
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# -----------------------
# Helpers
# -----------------------
def encrypt_token(plain: str) -> str:
    return fernet.encrypt(plain.encode()).decode()

def get_user_info(access_token: str) -> dict | None:
    """Obtiene email y nombre real del usuario."""
    r = requests.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    return r.json() if r.ok else None

def sync_medico_profile(email: str, name: str):
    """
    Asegura que el médico exista en la tabla 'medicos'.
    Si no existe, lo crea. Si existe, no hace nada (evita pisar 'usa_secretaria').
    """
    res = supabase.table("medicos").select("id").eq("email", email).execute()
    if not res.data:
        print(f"Creando perfil inicial para médico: {email}")
        supabase.table("medicos").insert({
            "email": email,
            "nombre_completo": name,
            "usa_secretaria": False, # Por defecto False
            "google_calendar_id": "primary"
        }).execute()

def upsert_tokens(email: str, fields: dict):
    """Guarda o actualiza los tokens en la tabla 'users_tokens'."""
    payload = {**{"email": email}, **fields}
    supabase.table("users_tokens").upsert(payload, on_conflict="email").execute()

def build_flow(state: str | None):
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        state=state,
        redirect_uri=OAUTH_REDIRECT_URI,
    )

# -----------------------
# Routes
# -----------------------
@app.route("/auth/start")
def auth_start():
    email_hint = request.args.get("email")
    state = json.dumps({"email_hint": email_hint}) if email_hint else None
    flow = build_flow(state)
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return redirect(auth_url)

@app.route("/oauth/callback")
def oauth_callback():
    state = request.args.get("state")
    flow = build_flow(state)
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    # 1. Obtener info real de Google
    user_info = get_user_info(creds.token)
    if not user_info or "email" not in user_info:
        return "Error obteniendo info de usuario", 400

    email = user_info["email"]
    name = user_info.get("name", email)

    # 2. Sincronizar Perfil de Médico (Tabla 'medicos')
    sync_medico_profile(email, name)

    # 3. Guardar Tokens (Tabla 'users_tokens')
    refresh_token = getattr(creds, "refresh_token", None)
    fields = {
        "access_token": creds.token,
        "token_expiry": creds.expiry.isoformat() if getattr(creds, "expiry", None) else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if refresh_token:
        fields["refresh_token_encrypted"] = encrypt_token(refresh_token)

    upsert_tokens(email, fields)

    return f"¡Listo! Dr/a {name}, su cuenta ha sido vinculada. Ya puede usar la turnera."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)