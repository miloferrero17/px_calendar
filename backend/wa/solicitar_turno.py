'''
python3 ./backend/wa/solicitar_turno.py --email milonguitaferrero@gmail.com
'''
# backend/wa/solicitar_turno.py
import argparse
import os
import sys
from datetime import timedelta

# Ajuste de ruta para alcanzar la carpeta 'services' desde 'backend/wa'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.calendar_logic import next_n_slots, create_meeting, WEEKDAYS_ES, list_calendars
from services.connection import ConnectionService, load_config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Email del médico registrado")
    args = parser.parse_args()

    conn = ConnectionService(load_config())
    medico = conn.get_medico_by_email(args.email)

    if not medico:
        print(f"\n❌ Error: No se encontró ningún médico con el email: {args.email}")
        return

    try:
        cals = list_calendars(args.email)
        consultorios = [c for c in cals if c.get("accessRole") in ("owner", "writer") and not c.get("primary")]
    except Exception:
        consultorios = []

    if not consultorios:
        print(f"\n--- Turnera Médica: Dr/a {medico['nombre_completo']} ---")
        print("\nMuchas gracias por su consulta. En algunos minutos la secretaria se contactará con usted.")
        return

    # Selección de sede (Automática si es única)
    if len(consultorios) == 1:
        selected_cal = consultorios[0]
        print(f"\nSede: {selected_cal['summary']}")
    else:
        print(f"\n--- Turnera Médica: Dr/a {medico['nombre_completo']} ---")
        for i, cal in enumerate(consultorios, start=1):
            print(f"{i}) {cal['summary']}")
        selected_cal = consultorios[int(input("\nSeleccione la sede: ")) - 1]

    # Selección de tipo de turno
    print("\nSeleccione el tipo de turno:\n1) Niño Sano (30 min)\n2) Demanda espontánea (20 min)")
    tipo_raw = input("Elija una opción: ").strip()
    minutes = 30 if tipo_raw == "1" else 20
    title_suffix = "Niño Sano" if tipo_raw == "1" else "Demanda espontánea"

    # --- BUCLE DE NAVEGACIÓN ---
    last_slot_end = None 

    while True:
        slots = next_n_slots(
            email=args.email,
            tz_str="America/Argentina/Buenos_Aires",
            calendar_id=selected_cal['id'],
            minutes=minutes,
            n=5,
            start_from=last_slot_end 
        )

        if not slots:
            print("\nNo se encontraron más turnos disponibles. Derivando a la secretaria...")
            break

        print("\nEstos son los turnos más rápidos disponibles:")
        for i, s in enumerate(slots, start=1):
            nombre_dia = WEEKDAYS_ES[s.start.weekday()]
            print(f"{i}) {nombre_dia} {s.start.strftime('%d/%m - %H:%M')}")
        
        idx_siguientes = len(slots) + 1
        idx_secre = len(slots) + 2
        print(f"{idx_siguientes}) Ver los 5 turnos siguientes")
        print(f"{idx_secre}) Llamar a la secretaria")

        try:
            choice_raw = input("\nSeleccione una opción: ").strip()
            if not choice_raw: break
            choice = int(choice_raw)
        except ValueError: break

        if choice == idx_secre:
            print("\n📞 Derivando a la secretaria... ¡Muchas gracias!")
            break
        
        if choice == idx_siguientes:
            # PRECISIÓN: El nuevo inicio es exactamente el fin del último slot mostrado
            last_slot_end = slots[-1].end 
            continue 

        if 1 <= choice <= len(slots):
            selected_slot = slots[choice - 1]
            create_meeting(
                email=args.email,
                tz_str="America/Argentina/Buenos_Aires",
                start=selected_slot.start,
                end=selected_slot.end,
                summary=f"Turno Paciente: Milo - {title_suffix}",
                location=f"Sede: {selected_cal['summary']}",
                calendar_id="primary"
            )
            print(f"\n✅ ¡Turno agendado con éxito el {selected_slot.start.strftime('%d/%m')} a las {selected_slot.start.strftime('%H:%M')} hs!")
            break

if __name__ == "__main__":
    main()