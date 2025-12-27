# solicitar_turno.py
import argparse
import os
import sys

# Agregamos la carpeta raíz al sistema de búsqueda de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ahora las importaciones funcionarán correctamente
from services.calendar_logic import next_n_slots, create_meeting, WEEKDAYS_ES
from services.connection import ConnectionService, load_config

from services.calendar_logic import next_n_slots, create_meeting, WEEKDAYS_ES
from services.connection import ConnectionService, load_config

def main():
    parser = argparse.ArgumentParser()
    # El email es la llave para encontrar al médico en la tabla 'medicos'
    parser.add_argument("--email", required=True, help="Email del médico registrado")
    args = parser.parse_args()

    # 1. Conectar y buscar datos del médico
    conn = ConnectionService(load_config())
    medico = conn.get_medico_by_email(args.email)

    if not medico:
        print(f"\n❌ Error: No se encontró ningún médico con el email: {args.email}")
        print("Asegúrate de haberlo dado de alta en la tabla 'medicos' de Supabase.")
        return

    # 2. Interfaz inicial
    print(f"\n--- Turnera Médica: Dr/a {medico['nombre_completo']} ---")
    print("Seleccione el tipo de turno:")
    print("1) Niño Sano")
    print("2) Demanda espontánea")
    
    tipo_raw = input("Elija una opción (1 o 2): ").strip()
    
    if tipo_raw == "1":
        minutes = 30
        title_suffix = "Niño Sano"
    elif tipo_raw == "2":
        minutes = 20
        title_suffix = "Demanda espontánea"
    else:
        print("Opción inválida.")
        return

    # 3. Buscar turnos disponibles
    # Usamos el google_calendar_id que está guardado en la tabla para ese médico
    print("\nBuscando turnos disponibles...")
    slots = next_n_slots(
        email=args.email,
        tz_str="America/Argentina/Buenos_Aires",
        n=5,
        minutes=minutes,
        calendar_id=medico.get("google_calendar_id", "primary")
    )

    if not slots:
        print("No hay turnos disponibles para los próximos días.")
        return

    # 4. Mostrar opciones al usuario
    print("\nElegí un turno:")
    for i, s in enumerate(slots, start=1):
        # s.start.weekday() devuelve 0 para Lunes, 1 para Martes, etc.
        nombre_dia = WEEKDAYS_ES[s.start.weekday()]
        
        # Ahora armamos el print usando esa variable
        print(f"{i}) {nombre_dia} {s.start.strftime('%d/%m - %H:%M')}")
        
    
    # OPCIÓN DINÁMICA: Solo aparece si 'usa_secretaria' es TRUE en la DB
    idx_secretaria = len(slots) + 1
    if medico.get("usa_secretaria"):
        print(f"{idx_secretaria}) Hablar con secretaria")

    choice_raw = input("\nRespondé con un número o Enter para salir: ").strip()
    if not choice_raw.isdigit():
        return

    choice = int(choice_raw)

    # Lógica si elige hablar con secretaria
    if medico.get("usa_secretaria") and choice == idx_secretaria:
        print(f"\n📞 Derivando consulta al equipo del Dr/a {medico['nombre_completo']}...")
        return

    # 5. Confirmar y agendar
    if 1 <= choice <= len(slots):
        selected_slot = slots[choice - 1]
        
        create_meeting(
            email=args.email,
            tz_str="America/Argentina/Buenos_Aires",
            start=selected_slot.start,
            end=selected_slot.end,
            summary=f"Paciente: Milo - {title_suffix}",
            location="Consultorio a confirmar", # Esto vendrá de la tabla consultorios pronto
            calendar_id=medico.get("google_calendar_id", "primary")
        )
        print(f"\n✅ ¡Turno agendado correctamente para las {selected_slot.start.strftime('%H:%M')} hs!")
    else:
        print("Opción no válida.")

if __name__ == "__main__":
    main()