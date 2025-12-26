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
    n: int = 5,
    minutes: int = 30,
    work_start_hour: int = 9,
    work_end_hour: int = 18,
    max_days_ahead: int = 14,
    calendar_id: str = "primary",
) -> list[Slot]:
    """
    Devuelve los próximos N slots libres, redondeando al próximo bloque de 30 min 
    para que los turnos empiecen en horario en punto o media hora (ej: 12:00, 12:30).
    """
    cfg = load_config()
    conn = ConnectionService(cfg)
    service = conn.build_calendar_service(email)

    tz = ZoneInfo(tz_str)
    now = datetime.now(tz)

    # --- LÓGICA DE REDONDEO (Ej: 12:13 -> 12:30 | 12:45 -> 13:00) ---
    if now.minute < 30:
        now = now.replace(minute=30, second=0, microsecond=0)
    else:
        now = now + timedelta(hours=1)
        now = now.replace(minute=0, second=0, microsecond=0)

    results: list[Slot] = []

    for day_offset in range(0, max_days_ahead + 1):
        target_day = (now + timedelta(days=day_offset)).date()
        day_start, day_end = _day_range_local(tz, target_day, work_start_hour, work_end_hour)

        # Si es hoy, empezar desde 'now' ya redondeado
        if day_offset == 0 and day_start < now:
            day_start = now

        if day_start >= day_end:
            continue

        busy = _freebusy_busy_intervals(service, calendar_id, day_start, day_end)
        candidates = _iter_slots(day_start, day_end, minutes)

        for s in candidates:
            if s.start < now:
                continue
            if _slot_is_free(busy, s):
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
    """Crea un evento en Google Calendar para el usuario especificado."""
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

    created = service.events().insert(calendarId=calendar_id, body=body).execute()
    return created


def create_meeting_from_strings(
    email: str,
    tz_str: str,
    date_ddmmyyyy: str,
    start_hhmm: str,
    minutes: int,
    location: str,
    summary: str = "Turno",
    description: str = "",
    calendar_id: str = "primary",
) -> dict:
    """Versión simplificada para crear reuniones desde strings de fecha y hora."""
    tz = ZoneInfo(tz_str)
    day, month, year = [int(x) for x in date_ddmmyyyy.split("/")]
    hh, mm = [int(x) for x in start_hhmm.split(":")]

    start = datetime(year, month, day, hh, mm, tzinfo=tz)
    end = start + timedelta(minutes=minutes)

    return create_meeting(
        email=email,
        tz_str=tz_str,
        start=start,
        end=end,
        location=location,
        summary=summary,
        description=description,
        calendar_id=calendar_id,
    )


def list_calendars(email: str) -> list[dict]:
    """Lista los calendarios disponibles para el usuario."""
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


def pick_best_calendar_id(email: str, preferred_names: list[str] | None = None) -> str:
    """Selecciona el calendario más adecuado para escribir (propietario o editor)."""
    preferred_names = preferred_names or []
    cals = list_calendars(email)
    writable = [c for c in cals if c.get("accessRole") in ("owner", "writer")]

    for name in preferred_names:
        name_l = name.strip().lower()
        for c in writable:
            if (c.get("summary") or "").strip().lower() == name_l:
                return c["id"]

    for c in writable:
        if c.get("primary"):
            return c["id"]

    if writable:
        return writable[0]["id"]

    for c in cals:
        if c.get("primary"):
            return c["id"]

    return "primary"


def get_calendar_name(email: str, calendar_id: str) -> str:
    """Obtiene el nombre (summary) de un calendario específico."""
    cfg = load_config()
    conn = ConnectionService(cfg)
    service = conn.build_calendar_service(email)

    c = service.calendarList().get(calendarId=calendar_id).execute()
    return c.get("summary") or "(sin nombre)"


def create_calendar(
    email: str,
    summary: str,
    tz_str: str = "America/Argentina/Buenos_Aires",
    description: str = "",
) -> dict:  
    """Crea un nuevo calendario en la cuenta del usuario."""
    cfg = load_config()
    conn = ConnectionService(cfg)
    service = conn.build_calendar_service(email)

    body = {
        "summary": summary,
        "timeZone": tz_str,
        "description": description,
    }

    created = service.calendars().insert(body=body).execute()
    return created


# services/calendar_logic.py (Añadir esta función)

def bloquear_horas_no_laborales(email, tz_str, calendar_id="primary"):
    """
    Lee los horarios de atención de Supabase y crea eventos en Google Calendar
    para bloquear el tiempo donde el médico NO atiende.
    """
    from services.connection import ConnectionService, load_config
    from datetime import datetime, timedelta
    
    conn = ConnectionService(load_config())
    medico = conn.get_medico_by_email(email)
    service = conn.build_calendar_service(email)
    
    # 1. Obtener horarios de atención permitidos
    res = conn.supabase.table("horarios_atencion").select("*").execute()
    horarios = res.data # Lista de {dia_semana, hora_inicio, hora_fin}

    # 2. Definir el rango a bloquear (ej: hoy y mañana)
    now = datetime.now(ZoneInfo(tz_str))
    
    # Lógica simplificada: Bloquear de 00:00 a 23:59 y luego 
    # borrar/ajustar según los huecos de atención.
    # Alternativa Pro: Crear un evento que dure todo el día y 
    # usar "Free/Busy" para que el sistema lo ignore.
    
    print(f"Sincronizando bloqueos de agenda para {email}...")
    
    # Por ahora, para no saturar tu calendario, vamos a crear un evento
    # de prueba que marque el fin de jornada.
    create_meeting(
        email=email,
        tz_str=tz_str,
        start=now.replace(hour=20, minute=0), 
        end=now.replace(hour=23, minute=59),
        summary="⛔ Fuera de Horario de Atención",
        location="Sistema Automático",
        calendar_id=calendar_id
    )
def setup_medico_calendar(email: str, medico_id: str):
    """
    1. Crea el calendario en Google.
    2. Guarda el ID resultante en la tabla 'medicos' de Supabase.
    """
    cfg = load_config()
    conn = ConnectionService(cfg)
    
    # 1. Crear el calendario
    # Usamos la función que ya tienes en calendar_logic.py
    calendar_name = f"Consultorio - {email}"
    new_cal = create_calendar(email, calendar_name)
    new_id = new_cal.get("id")

    if new_id:
        # 2. Actualizar la tabla 'medicos' en Supabase
        # Usamos la instancia de supabase que ya tiene ConnectionService
        conn.supabase.table("medicos") \
            .update({"google_calendar_id": new_id}) \
            .eq("id", medico_id) \
            .execute()
            
        print(f"✅ Calendario vinculado al médico {medico_id}")
        return new_id
    return None