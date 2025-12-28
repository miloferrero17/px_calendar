from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Optional

from backend.services.connection import ConnectionService, load_config

TZ = "America/Argentina/Buenos_Aires"
DAYS_MAP = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]  # 0=Lun ... 6=Dom


def get_next_weekday_date(target_weekday: int):
    """Devuelve la fecha del próximo día de la semana (0=Lun, 6=Dom)."""
    today = datetime.now()
    delta_days = (target_weekday - today.weekday() + 7) % 7
    return (today + timedelta(days=delta_days)).date()


def configurar_disponibilidad_recurrente(
    email: str,
    consultorio_id: str,
    dia_semana: int,
    apertura_str: Optional[str],
    cierre_str: Optional[str],
):
    """
    - Persiste el horario en Supabase (horarios_atencion)
    - Crea bloqueos recurrentes en Google Calendar (mañana/noche)
    """

    if dia_semana < 0 or dia_semana > 6:
        raise ValueError("dia_semana debe estar entre 0 (Lun) y 6 (Dom).")

    cfg = load_config()
    conn = ConnectionService(cfg)

    # 1) Obtener google_calendar_id del consultorio
    res = (
        conn.supabase.table("consultorios")
        .select("google_calendar_id")
        .eq("id", consultorio_id)
        .single()
        .execute()
    )
    if not res.data:
        raise ValueError("No se encontró el consultorio.")

    target_calendar_id = res.data["google_calendar_id"]

    # 2) Persistir en Supabase
    conn.supabase.table("horarios_atencion").insert(
        {
            "consultorio_id": consultorio_id,
            "dia_semana": dia_semana,
            "hora_inicio": apertura_str or "",
            "hora_fin": cierre_str or "",
        }
    ).execute()

    # Si no hay horario, no creamos bloqueos (MVP). Podés cambiar esto a “cerrado todo el día”.
    if not apertura_str or not cierre_str:
        return

    fecha_objetivo = get_next_weekday_date(dia_semana)

    t_apertura = datetime.strptime(apertura_str, "%H:%M").time()
    t_cierre = datetime.strptime(cierre_str, "%H:%M").time()

    bloques = []
    if t_apertura > time(0, 0):
        bloques.append(
            {
                "start": datetime.combine(fecha_objetivo, time(0, 0)),
                "end": datetime.combine(fecha_objetivo, t_apertura),
                "summary": "⛔ CERRADO (Mañana)",
            }
        )

    if t_cierre < time(23, 59):
        bloques.append(
            {
                "start": datetime.combine(fecha_objetivo, t_cierre),
                "end": datetime.combine(fecha_objetivo, time(23, 59)),
                "summary": "⛔ CERRADO (Noche)",
            }
        )

    rrule = f"RRULE:FREQ=WEEKLY;BYDAY={DAYS_MAP[dia_semana]}"
    service = conn.build_calendar_service(email)

    for b in bloques:
        event_body = {
            "summary": b["summary"],
            "location": "Automatic Block",
            "description": "Non-working hours configured by the system",
            "start": {"dateTime": b["start"].isoformat(), "timeZone": TZ},
            "end": {"dateTime": b["end"].isoformat(), "timeZone": TZ},
            "recurrence": [rrule],
            "transparency": "opaque",  # Busy
        }

        service.events().insert(calendarId=target_calendar_id, body=event_body).execute()