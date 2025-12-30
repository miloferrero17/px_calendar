from __future__ import annotations

import argparse
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.google_calendar.connection import ConnectionService, load_config
from backend.services.google_calendar.setup_availability import configurar_disponibilidad_recurrente

router = APIRouter()

# Mapeo desde tu frontend (mondayStart, mondayEnd, etc.) a dia_semana (0=lun ... 6=dom)
DAY_FIELDS = [
    (0, "mondayStart", "mondayEnd"),
    (1, "tuesdayStart", "tuesdayEnd"),
    (2, "wednesdayStart", "wednesdayEnd"),
    (3, "thursdayStart", "thursdayEnd"),
    (4, "fridayStart", "fridayEnd"),
    # si mañana agregás sábado/domingo en UI:
    # (5, "saturdayStart", "saturdayEnd"),
    # (6, "sundayStart", "sundayEnd"),
]


class CreateSedeRequest(BaseModel):
    email: str
    nombre: str
    direccion: Optional[str] = None
    horarios: Optional[Dict[str, Any]] = None  # viene el objeto clinicInfo completo (MVP)


def crear_sede(email: str, nombre_sede: str, direccion: Optional[str] = None) -> dict:
    """
    Crea un calendario para la sede en Google Calendar y guarda el consultorio en Supabase.
    Devuelve: { consultorio_id, google_calendar_id }
    """
    config = load_config()
    conn = ConnectionService(config)
    service = conn.build_calendar_service(email)

    # 1) Crear calendario en Google
    calendar_metadata = {
        "summary": f"Sede: {nombre_sede}",
        "description": "Calendario de atención gestionado por PX Calendar",
        "timeZone": "America/Argentina/Buenos_Aires",
    }
    created_calendar = service.calendars().insert(body=calendar_metadata).execute()
    google_id = created_calendar["id"]

    # 2) Buscar médico en Supabase
    medico = conn.get_medico_by_email(email)
    if not medico:
        raise ValueError(f"El médico con email {email} no existe en la base de datos.")

    # 3) Insertar consultorio en Supabase y recuperar ID
    data = {
        "medico_id": medico["id"],
        "nombre": nombre_sede,
        "google_calendar_id": google_id,
    }
    if direccion:
        data["direccion"] = direccion

    inserted = conn.supabase.table("consultorios").insert(data).execute()

    # Supabase suele devolver filas insertadas en inserted.data
    consultorio_id = None
    if inserted.data and len(inserted.data) > 0:
        consultorio_id = inserted.data[0].get("id")

    # Fallback: si tu config no devuelve inserted rows, lo buscamos por google_id
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


@router.post("/sedes")
def crear_sede_endpoint(payload: CreateSedeRequest):
    """
    POST /api/sedes
    Body: { email, nombre, direccion, horarios }
    """
    try:
        result = crear_sede(payload.email, payload.nombre, payload.direccion)

        # Si vienen horarios, los persistimos + creamos bloqueos recurrentes en Google
        if payload.horarios:
            consultorio_id = result["consultorio_id"]

            for dia_semana, start_key, end_key in DAY_FIELDS:
                apertura = payload.horarios.get(start_key) if isinstance(payload.horarios, dict) else None
                cierre = payload.horarios.get(end_key) if isinstance(payload.horarios, dict) else None

                # Llama a tu servicio (guarda en horarios_atencion + crea bloqueos mañana/noche)
                configurar_disponibilidad_recurrente(
                    email=payload.email,
                    consultorio_id=consultorio_id,
                    dia_semana=dia_semana,
                    apertura_str=apertura or "",
                    cierre_str=cierre or "",
                )

        return {"ok": True, **result}

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- MODO SCRIPT (opcional) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gestionar sedes y calendarios de Google.")
    parser.add_argument("--email", required=True, help="Email del médico")
    parser.add_argument("--nombre", required=True, help="Nombre de la nueva sede")
    parser.add_argument("--direccion", required=False, help="Dirección de la sede")
    args = parser.parse_args()

    out = crear_sede(args.email, args.nombre, args.direccion)
    print(f"✅ OK. Consultorio ID: {out['consultorio_id']} | Google Calendar ID: {out['google_calendar_id']}")
