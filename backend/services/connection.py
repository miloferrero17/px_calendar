#!/usr/bin/env python3
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from dotenv import load_dotenv
from cryptography.fernet import Fernet
from supabase import create_client, Client

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Nombre de la tabla de tokens por defecto
USERS_TABLE = "users_tokens"

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _split_csv(raw: str) -> List[str]:
    return [x.strip() for x in (raw or "").split(",") if x.strip()]

@dataclass
class AppConfig:
    google_client_id: str
    google_client_secret: str
    fernet_key: str
    supabase_url: str
    supabase_service_role: str
    users_table: str = USERS_TABLE

def load_config() -> AppConfig:
    """Carga la configuración desde el entorno."""
    load_dotenv()
    cfg = AppConfig(
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
        google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "").strip(),
        fernet_key=os.environ.get("FERNET_KEY", "").strip(),
        supabase_url=os.environ.get("SUPABASE_URL", "").strip(),
        supabase_service_role=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
        users_table=os.environ.get("USERS_TABLE", USERS_TABLE).strip() or USERS_TABLE,
    )

    missing = []
    for k, v in [
        ("GOOGLE_CLIENT_ID", cfg.google_client_id),
        ("GOOGLE_CLIENT_SECRET", cfg.google_client_secret),
        ("FERNET_KEY", cfg.fernet_key),
        ("SUPABASE_URL", cfg.supabase_url),
        ("SUPABASE_SERVICE_ROLE_KEY", cfg.supabase_service_role),
    ]:
        if not v:
            missing.append(k)
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")
    return cfg

class ConnectionService:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.fernet = Fernet(cfg.fernet_key)
        self.supabase: Client = create_client(cfg.supabase_url, cfg.supabase_service_role)

    def get_user_row(self, email: str) -> Optional[Dict[str, Any]]:
        """Busca el token en la tabla users_tokens."""
        res = self.supabase.table(self.cfg.users_table).select("*").eq("email", email).execute()
        data = getattr(res, "data", None)
        return data[0] if data else None

    # En services/connection.py, localiza esta función:
    def get_medico_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        res_medico = self.supabase.table("medicos").select("*").eq("email", email).execute()
        if not res_medico.data:
            return None
        
        medico_data = res_medico.data[0]
        token_data = self.get_user_row(email)
        if token_data:
            # En lugar de medico_data.update(token_data)
            # Solo pasamos los tokens, sin tocar el ID del médico
            medico_data["access_token"] = token_data.get("access_token")
            medico_data["refresh_token_encrypted"] = token_data.get("refresh_token_encrypted")
            # ... agregar otros campos necesarios si hace falta
        return medico_data

    def update_user_row(self, email: str, fields: Dict[str, Any]) -> None:
        """Actualiza tokens en Supabase."""
        fields = {**fields, "updated_at": _utc_now_iso()}
        self.supabase.table(self.cfg.users_table).update(fields).eq("email", email).execute()

    def decrypt(self, encrypted: str) -> str:
        """Desencripta el refresh token."""
        return self.fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")

    def build_credentials(self, email: str) -> Credentials:
        """Gestiona credenciales y refresco automático."""
        row = self.get_user_row(email)
        if not row:
            raise RuntimeError(f"No existe el usuario {email}.")

        enc_refresh = row.get("refresh_token_encrypted")
        if not enc_refresh:
            raise RuntimeError(f"El usuario {email} no tiene refresh_token.")

        creds = Credentials(
            token=row.get("access_token"),
            refresh_token=self.decrypt(enc_refresh),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.cfg.google_client_id,
            client_secret=self.cfg.google_client_secret,
            scopes=_split_csv(row.get("scopes", ""))
        )

        if not creds.valid:
            creds.refresh(Request())
            self.update_user_row(email, {
                "access_token": creds.token,
                "token_expiry": creds.expiry.isoformat() if getattr(creds, "expiry", None) else None,
            })
        return creds

    def get_valid_access_token(self, email: str) -> str:
        """Retorna token válido."""
        return self.build_credentials(email).token

    def build_calendar_service(self, email: str):
        """Cliente Google Calendar."""
        creds = self.build_credentials(email)
        return build("calendar", "v3", credentials=creds, cache_discovery=False)