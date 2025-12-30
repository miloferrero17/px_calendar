"""
backend/main.py
Servidor principal FastAPI para el consultorio pediátrico.
Ejecución: uvicorn backend.main:app --reload --port 8000
"""
import traceback
import os
from uuid import uuid4
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from supabase import create_client, Client

load_dotenv()

# Permitir HTTP para desarrollo local (OAuthlib)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# --- CONFIGURACIÓN ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan las credenciales de Supabase en el archivo .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- IMPORTACIONES DE SERVICIOS ---
from backend.services.google_calendar.oauth_server import (
    obtener_flujo_google,
    sync_medico_profile,
    upsert_tokens,
    get_user_info,
    encrypt_token,
)
from backend.api.gestionar_sedes import router as sedes_router

app = FastAPI(title="API Consultorio Pediátrico")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- RUTAS EXTRA ---
app.include_router(sedes_router, prefix="/api")

# -----------------------------
# SESIÓN (cookie) + auth_sessions
# -----------------------------
SESSION_COOKIE_NAME = "consultorio_session"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 días

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _get_or_create_session_id(request: Request) -> tuple[str, bool]:
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    if sid:
        return sid, False
    return str(uuid4()), True

def _ensure_session_row(session_id: str) -> None:
    supabase.table("auth_sessions").upsert(
        {"session_id": session_id, "updated_at": _now_iso()},
        on_conflict="session_id",
    ).execute()

def _set_session_cookie(resp, session_id: str) -> None:
    resp.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=False,      # True en prod con https
        samesite="lax",
        max_age=SESSION_COOKIE_MAX_AGE,
        path="/",
    )

# -----------------------------
# ENDPOINTS
# -----------------------------

@app.get("/api/auth/status")
async def get_auth_status(request: Request):
    """
    Status por sesión (cookie). No requiere email.
    connected=true si la sesión ya quedó asociada a un email.
    """
    try:
        session_id, created = _get_or_create_session_id(request)
        _ensure_session_row(session_id)

        result = supabase.table("auth_sessions").select("email").eq("session_id", session_id).execute()
        email = result.data[0].get("email") if result.data else None

        payload = {"connected": bool(email), "email": email} if email else {"connected": False}
        resp = JSONResponse(content=payload)

        if created:
            _set_session_cookie(resp, session_id)

        return resp
    except Exception as e:
        print(f"Error status session: {e}")
        raise HTTPException(status_code=500, detail="Error en status de autenticación")

@app.get("/api/auth/google")
async def get_auth_url(request: Request):
    try:
        session_id, created = _get_or_create_session_id(request)
        _ensure_session_row(session_id)

        # IMPORTANTE: dejar que la lib genere el state y guardar el que retorna
        flow = obtener_flujo_google(state=None)
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )

        supabase.table("auth_sessions").update(
            {"oauth_state": state, "updated_at": _now_iso()}
        ).eq("session_id", session_id).execute()

        resp = JSONResponse(content={"url": authorization_url})

        # yo lo setearía siempre, no solo si created, para evitar edge cases
        _set_session_cookie(resp, session_id)
        return resp

    except Exception as e:
        print(f"Error auth google: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/callback")
async def oauth_callback(request: Request):
    """
    Callback OAuth: valida state contra auth_sessions, procesa token
    y asocia la sesión al email.
    """
    try:
        state = request.query_params.get("state")
        if not state:
            return RedirectResponse(url=f"{FRONTEND_URL}/?status=error")

        session_res = supabase.table("auth_sessions").select("session_id").eq("oauth_state", state).execute()
        if not session_res.data:
            return RedirectResponse(url=f"{FRONTEND_URL}/?status=error")

        session_id = session_res.data[0]["session_id"]

        flow = obtener_flujo_google(state=state)
        flow.fetch_token(authorization_response=str(request.url))
        creds = flow.credentials

        user_info = get_user_info(creds.token)
        if not user_info:
            return RedirectResponse(url=f"{FRONTEND_URL}/?status=error")

        email = user_info["email"]
        name = user_info.get("name", email)

        # 1) Perfil del médico
        sync_medico_profile(email, name)

        # 2) Tokens
        fields = {
            "access_token": creds.token,
            "token_expiry": creds.expiry.isoformat() if creds.expiry else None,
        }
        if creds.refresh_token:
            fields["refresh_token_encrypted"] = encrypt_token(creds.refresh_token)

        upsert_tokens(email, fields)

        # 3) Asociar sesión a email y limpiar oauth_state
        supabase.table("auth_sessions").update(
            {"email": email, "oauth_state": None, "updated_at": _now_iso()}
        ).eq("session_id", session_id).execute()

        resp = RedirectResponse(url=f"{FRONTEND_URL}/?status=success")
        _set_session_cookie(resp, session_id)
        return resp

    except Exception as e:
        print("Error en callback:", e)
        traceback.print_exc()
        return RedirectResponse(url=f"{FRONTEND_URL}/?status=error")



@app.get("/api/health")
async def health_check():
    return {"status": "online", "database": "connected via python"}
    