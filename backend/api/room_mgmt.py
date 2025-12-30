'''
python3 -m backend.api.room_mgmt \
  --email "emilio.ferrero@mercadolibre.com" \
  --nombre "Sede Centro" \
  --direccion "Av. Corrientes 1234, CABA"
'''

from __future__ import annotations

import argparse
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.google_calendar.connection import ConnectionService, load_config
from backend.services.google_calendar.setup_availability import configurar_disponibilidad_recurrente

router = APIRouter()

# Map from frontend keys (mondayStart, mondayEnd, etc.) to dia_semana (0=Mon ... 6=Sun)
DAY_FIELDS = [
    (0, "mondayStart", "mondayEnd"),
    (1, "tuesdayStart", "tuesdayEnd"),
    (2, "wednesdayStart", "wednesdayEnd"),
    (3, "thursdayStart", "thursdayEnd"),
    (4, "fridayStart", "fridayEnd"),
    (5, "saturdayStart", "saturdayEnd"),
    (6, "sundayStart", "sundayEnd"),
]


class CreateRoomRequest(BaseModel):
    email: str
    nombre: str
    direccion: Optional[str] = None
    horarios: Optional[Dict[str, Any]] = None  # full clinicInfo object from the UI (MVP)


def create_room(email: str, room_name: str, direccion: Optional[str] = None) -> dict:
    """
    Creates a Google Calendar for the room and persists a `consultorio` row in Supabase.
    Returns: { consultorio_id, google_calendar_id }
    """
    config = load_config()
    conn = ConnectionService(config)
    service = conn.build_calendar_service(email)

    # 1) Create Google Calendar
    calendar_metadata = {
        "summary": f"Sede: {room_name}",
        "description": "Calendario de atención gestionado por PX Calendar",
        "timeZone": "America/Argentina/Buenos_Aires",
    }
    created_calendar = service.calendars().insert(body=calendar_metadata).execute()
    google_id = created_calendar["id"]

    # (Optional) Ensure it appears and is selected in user's calendar list
    try:
        service.calendarList().insert(body={"id": google_id, "selected": True}).execute()
    except Exception:
        pass

    # 2) Find doctor in Supabase
    medico = conn.get_medico_by_email(email)
    if not medico:
        raise ValueError(f"El médico con email {email} no existe en la base de datos.")

    # 3) Insert consultorio in Supabase and get ID
    data = {
        "medico_id": medico["id"],
        "nombre": room_name,
        "google_calendar_id": google_id,
    }
    if direccion:
        data["direccion"] = direccion

    inserted = conn.supabase.table("consultorios").insert(data).execute()

    consultorio_id = None
    if inserted.data and len(inserted.data) > 0:
        consultorio_id = inserted.data[0].get("id")

    # Fallback: search by google_id if DB didn't return rows
    if not consultorio_id:
        res = (
            conn.supabase.table("consultorios")
            .select("id")
            .eq("google_calendar_id", google_id)
            .single()
            .execute()
        )
        consultorio_id = res.data["id"] if res.data else None

    if not consultorio_id:
        raise RuntimeError("No se pudo obtener el consultorio_id luego de crear la sede.")

    return {"consultorio_id": consultorio_id, "google_calendar_id": google_id}


@router.post("/rooms")
def create_room_endpoint(payload: CreateRoomRequest):
    """
    POST /api/rooms
    Body: { email, nombre, direccion, horarios }
    """
    try:
        result = create_room(payload.email, payload.nombre, payload.direccion)

        # If schedules are provided, persist them and create recurring busy blocks in Google
        if payload.horarios:
            consultorio_id = result["consultorio_id"]
            horarios = payload.horarios if isinstance(payload.horarios, dict) else {}

            for dia_semana, start_key, end_key in DAY_FIELDS:
                apertura = (horarios.get(start_key) or "").strip()
                cierre = (horarios.get(end_key) or "").strip()

                # Optional: allow FE to send mondayClosed/tuesdayClosed/etc.
                closed_key = start_key.replace("Start", "Closed")
                if bool(horarios.get(closed_key)):
                    apertura = ""
                    cierre = ""

                # Validate: both filled or both empty
                if (apertura and not cierre) or (cierre and not apertura):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Horario inválido en día {dia_semana}: "
                            "completá inicio y cierre, o dejá ambos vacíos para bloquear todo el día."
                        ),
                    )

                # UX rule: empty/empty => setup_availability creates ALL-DAY blocks
                configurar_disponibilidad_recurrente(
                    email=payload.email,
                    consultorio_id=consultorio_id,
                    dia_semana=dia_semana,
                    apertura_str=apertura,
                    cierre_str=cierre,
                )

        return {"ok": True, **result}

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Backwards-compatible alias: keep `/sedes` path working for existing clients
@router.post("/sedes")
def create_sede_alias(payload: CreateRoomRequest):
    return create_room_endpoint(payload)


# --- SCRIPT MODE (optional) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage rooms and Google calendars.")
    parser.add_argument("--email", required=True, help="Doctor email")
    parser.add_argument("--nombre", required=True, help="New room name")
    parser.add_argument("--direccion", required=False, help="Room address")
    args = parser.parse_args()

    out = create_room(args.email, args.nombre, args.direccion)
    print(f"✅ OK. Consultorio ID: {out['consultorio_id']} | Google Calendar ID: {out['google_calendar_id']}")