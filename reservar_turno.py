#!/usr/bin/env python3
"""
solicitar_turno.py (CLI - SIN Flask)

Uso:
  python solicitar_turno.py --email doctor@gmail.com --title "Paciente: Milo"
  python solicitar_turno.py --email doctor@gmail.com --title "Paciente: Milo" --json
"""

import argparse
import json
import os

from services.calendar_logic import next_n_slots, create_meeting


TZ_DEFAULT = "America/Argentina/Buenos_Aires"
MINUTES_DEFAULT = 30
DESCRIPTION_DEFAULT = ""


def _print(obj, as_json: bool):
    if as_json:
        print(json.dumps(obj, ensure_ascii=False))
        return

    if obj.get("screen") == "offer":
        print("\nElegí un turno:")
        for o in obj["options"]:
            print(f"{o['id']}) {o['label']}")
    elif obj.get("screen") == "confirm":
        print("\nConfirmación")
        print(obj["selected"]["label"])
        if obj.get("location"):
            print(f"Ubicación: {obj['location']}")
        for o in obj["options"]:
            print(f"{o['id']}) {o['label']}")
    else:
        print(obj)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--email", required=True, help="Email del doctor (dueño del calendar)")
    p.add_argument("--title", required=True, help='Título del evento (ej: "Paciente: Milo")')
    p.add_argument("--json", action="store_true", help="Imprime pantallas en JSON")

    # defaults desde env (sin preguntar)
    p.add_argument("--location", default=os.getenv("DEFAULT_LOCATION", "").strip())

    args = p.parse_args()

    tz = TZ_DEFAULT
    minutes = MINUTES_DEFAULT
    title = args.title.strip()
    description = DESCRIPTION_DEFAULT
    location = (args.location or "").strip()

    # TOP 5 slots
    slots = next_n_slots(
        email=args.email,
        tz_str=tz,
        n=5,
        minutes=minutes,
        work_start_hour=9,
        work_end_hour=18,
        max_days_ahead=14,
    )

    if not slots:
        _print({"screen": "end", "result": "no_slots", "message": "No hay turnos disponibles."}, args.json)
        return

    # ---------- Pantalla 1: OFFER ----------
    options = []
    for i, s in enumerate(slots, start=1):
        label = f"{s.start.strftime('%a')} {s.start.strftime('%d/%m')} — {s.start.strftime('%H:%M')}"
        options.append({
            "type": "slot",
            "id": i,
            "label": label,
            "start": s.start.isoformat(),
            "end": s.end.isoformat(),
        })

    options.append({"type": "secretary", "id": 6, "label": "Hablar con secretaria"})

    offer = {
        "screen": "offer",
        "location": location,
        "minutes": minutes,
        "title": title,
        "options": options,
    }
    _print(offer, args.json)

    raw = input("Respondé con un número (1..6) o Enter para salir: ").strip()
    if not raw:
        _print({"screen": "end", "result": "cancel", "message": "Sin selección."}, args.json)
        return

    try:
        choice = int(raw)
    except ValueError:
        _print({"screen": "end", "result": "invalid", "message": "Opción inválida."}, args.json)
        return

    if choice == 6:
        _print({"screen": "end", "result": "secretary", "message": "Derivar a secretaria."}, args.json)
        return

    if choice < 1 or choice > 5:
        _print({"screen": "end", "result": "invalid", "message": "Opción fuera de rango."}, args.json)
        return

    chosen = slots[choice - 1]
    chosen_label = f"{chosen.start.strftime('%a %d/%m/%Y — %H:%M')} a {chosen.end.strftime('%H:%M')}"

    # ---------- Pantalla 2: CONFIRM ----------
    confirm = {
        "screen": "confirm",
        "location": location,
        "title": title,
        "selected": {
            "label": chosen_label,
            "start": chosen.start.isoformat(),
            "end": chosen.end.isoformat(),
        },
        "options": [
            {"type": "confirm", "id": 1, "label": "Confirmar"},
            {"type": "change", "id": 2, "label": "Cambiar turno"},
            {"type": "secretary", "id": 3, "label": "Hablar con secretaria"},
        ],
    }
    _print(confirm, args.json)

    raw2 = input("Respondé (1..3) o Enter para salir: ").strip()
    if not raw2:
        _print({"screen": "end", "result": "cancel", "message": "Sin confirmar."}, args.json)
        return

    try:
        c2 = int(raw2)
    except ValueError:
        _print({"screen": "end", "result": "invalid", "message": "Opción inválida."}, args.json)
        return

    if c2 == 2:
        _print({"screen": "end", "result": "change", "message": "Volvé a correr para elegir otro turno."}, args.json)
        return

    if c2 == 3:
        _print({"screen": "end", "result": "secretary", "message": "Derivar a secretaria."}, args.json)
        return

    if c2 != 1:
        _print({"screen": "end", "result": "invalid", "message": "Opción inválida."}, args.json)
        return

    # ---------- RESERVA REAL ----------
    try:
        created = create_meeting(
            email=args.email,
            tz_str=tz,
            start=chosen.start,
            end=chosen.end,
            location=location,
            summary=title,
            description=description,
            calendar_id="primary",
        )
    except Exception as e:
        _print({"screen": "end", "result": "error", "message": str(e)}, args.json)
        return

    out = {
        "screen": "end",
        "result": "created",
        "message": "Turno reservado.",
        "event": {
            "id": created.get("id"),
            "htmlLink": created.get("htmlLink"),
            "summary": created.get("summary"),
            "location": created.get("location"),
            "start": (created.get("start") or {}).get("dateTime"),
            "end": (created.get("end") or {}).get("dateTime"),
        }
    }
    _print(out, args.json)


if __name__ == "__main__":
    main()
