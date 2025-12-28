# services/calendar_logic.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo

from services.connection import load_config, ConnectionService

@dataclass(frozen=True)
class Slot:
    start: datetime
    end: datetime

WEEKDAYS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

def _to_rfc3339(dt: datetime) -> str:
    """Convierte un datetime a formato RFC3339 para la API de Google."""
    if dt.tzinfo is None:
        raise ValueError("datetime sin tzinfo. Pasá datetimes timezone-aware.")
    return dt.isoformat()

def _day_range_local(tz: ZoneInfo, day: date, start_hour: int, end_hour: int) -> tuple[datetime, datetime]:
    """Define el inicio y fin de la jornada laboral para un día específico."""
    start_dt = datetime.combine(day, time(hour=start_hour, minute=0), tzinfo=tz)
    end_dt = datetime.combine(day, time(hour=end_hour, minute=0), tzinfo=tz)
    return start_dt, end_dt

def _iter_slots(day_start: datetime, day_end: datetime, minutes: int) -> list[Slot]:
    """Genera una lista de slots potenciales de duración X dentro de un rango."""
    slots: list[Slot] = []
    cur = day_start
    step = timedelta(minutes=minutes)
    while cur + step <= day_end:
        slots.append(Slot(start=cur, end=cur + step))
        cur += step
    return slots

def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Verifica si dos intervalos de tiempo se superponen."""
    return a_start < b_end and b_start < a_end

def _freebusy_busy_intervals(service, calendar_id: str, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Consulta la API de FreeBusy de Google para obtener intervalos ocupados."""
    body = {
        "timeMin": _to_rfc3339(start),
        "timeMax": _to_rfc3339(end),
        "items": [{"id": calendar_id}],
    }
    resp = service.freebusy().query(body=body).execute()
    cal = resp.get("calendars", {}).get(calendar_id, {})
    busy = cal.get("busy", [])
    out: list[tuple[datetime, datetime]] = []
    for b in busy:
        bs = datetime.fromisoformat(b["start"].replace("Z", "+00:00"))
        be = datetime.fromisoformat(b["end"].replace("Z", "+00:00"))
        out.append((bs, be))
    return out

def _slot_is_free(busy_intervals: list[tuple[datetime, datetime]], slot: Slot) -> bool:
    """Comprueba si un slot específico está libre comparándolo con los intervalos ocupados."""
    for bs, be in busy_intervals:
        if _overlaps(slot.start, slot.end, bs, be):
            return False
    return True

def next_n_slots(
    email: str,
    tz_str: str,
    calendar_id: str,
    n: int = 5,
    minutes: int = 30,
    work_start_hour: int = 8,
    work_end_hour: int = 21,
    max_days_ahead: int = 14,
    start_from: datetime | None = None,
) -> list[Slot]:
    """
    Busca los próximos N slots LIBRES. 
    Cruza el calendario 'primary' (personal) y el 'calendar_id' de la sede.
    """
    cfg = load_config()
    conn = ConnectionService(cfg)
    service = conn.build_calendar_service(email)

    tz = ZoneInfo(tz_str)
    
    # PRECISIÓN: Si no hay start_from, aplicamos redondeo inicial.
    # Si HAY start_from, lo usamos tal cual para no saltar turnos en la paginación.
    if start_from is None:
        now = datetime.now(tz)
        if now.minute < 30:
            now = now.replace(minute=30, second=0, microsecond=0)
        else:
            now = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    else:
        now = start_from.astimezone(tz)

    calendars_to_check = ["primary"]
    if calendar_id != "primary":
        calendars_to_check.append(calendar_id)

    results: list[Slot] = []

    for day_offset in range(0, max_days_ahead + 1):
        target_day = (now + timedelta(days=day_offset)).date()
        day_start, day_end = _day_range_local(tz, target_day, work_start_hour, work_end_hour)

        if day_start < now:
            day_start = now
        
        if day_start >= day_end:
            continue

        combined_busy = []
        for cal_id in calendars_to_check:
            combined_busy.extend(_freebusy_busy_intervals(service, cal_id, day_start, day_end))

        candidates = _iter_slots(day_start, day_end, minutes)

        for s in candidates:
            if s.start < now:
                continue
            if _slot_is_free(combined_busy, s):
                results.append(s)
                if len(results) >= n:
                    return results

    return results

def create_meeting(
    email: str,
    tz_str: str,
    start: datetime,
    end: datetime,
    location: str,
    summary: str = "Turno",
    description: str = "",
    calendar_id: str = "primary",
) -> dict:
    cfg = load_config()
    conn = ConnectionService(cfg)
    service = conn.build_calendar_service(email)

    tz = ZoneInfo(tz_str)
    start = start.astimezone(tz)
    end = end.astimezone(tz)

    body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start.isoformat(), "timeZone": tz_str},
        "end": {"dateTime": end.isoformat(), "timeZone": tz_str},
    }

    return service.events().insert(calendarId=calendar_id, body=body).execute()

def list_calendars(email: str) -> list[dict]:
    cfg = load_config()
    conn = ConnectionService(cfg)
    service = conn.build_calendar_service(email)

    calendars: list[dict] = []
    page_token = None
    while True:
        resp = service.calendarList().list(pageToken=page_token).execute()
        for c in resp.get("items", []):
            calendars.append({
                "id": c.get("id"),
                "summary": c.get("summary"),
                "primary": bool(c.get("primary", False)),
                "accessRole": c.get("accessRole"),
                "timeZone": c.get("timeZone"),
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return calendars

def list_patient_appointments(email_doctor, patient_query):
    """
    Busca eventos en el calendario del doctor que coincidan 
    con el nombre o email del paciente.
    """
    cfg = load_config()
    conn = ConnectionService(cfg)
    service = conn.build_calendar_service(email_doctor)
    
    now = datetime.utcnow().isoformat() + "Z"
    # Buscamos eventos futuros que contengan el nombre del paciente
    events_result = service.events().list(
        calendarId="primary", 
        timeMin=now,
        q=patient_query, # Filtro de búsqueda
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    return events_result.get("items", [])