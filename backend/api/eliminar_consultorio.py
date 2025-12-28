from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.connection import ConnectionService, load_config

router = APIRouter()


class DeleteClinicRequest(BaseModel):
    email: str
    consultorio_id: str


def eliminar_consultorio_total(email: str, consultorio_id: str) -> dict:
    cfg = load_config()
    conn = ConnectionService(cfg)

    # 1) Obtener google_calendar_id antes de borrar el registro
    res = (
        conn.supabase.table("consultorios")
        .select("google_calendar_id")
        .eq("id", consultorio_id)
        .single()
        .execute()
    )

    if not res.data:
        raise ValueError("El consultorio no existe en Supabase.")

    google_id = res.data["google_calendar_id"]

    # 2) Eliminar calendario en Google Calendar (best-effort)
    try:
        service = conn.build_calendar_service(email)
        service.calendars().delete(calendarId=google_id).execute()
    except Exception:
        # no frenamos el proceso si Google falla (puede ya no existir)
        pass

    # 3) Eliminar en Supabase
    conn.supabase.table("consultorios").delete().eq("id", consultorio_id).execute()

    return {"ok": True, "deleted_consultorio_id": consultorio_id, "deleted_calendar_id": google_id}


@router.delete("/consultorios")
def eliminar_consultorio_endpoint(payload: DeleteClinicRequest):
    """
    DELETE /api/consultorios
    Body: { "email": "...", "consultorio_id": "..." }
    """
    try:
        return eliminar_consultorio_total(payload.email, payload.consultorio_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- MODO SCRIPT (opcional) ---
if __name__ == "__main__":
    # Ejemplo manual
    print(eliminar_consultorio_total("milonguitaferrero@gmail.com", "5d31392d-31a6-485a-af9e-c5765489eb48"))
