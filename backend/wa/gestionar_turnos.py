'''
python3 ./backend/wa/gestionar_turnos.py --email milonguitaferrero@gmail.com --dni "12345678"
'''
# backend/wa/gestionar_turnos.py
import argparse
import os
import sys
import re
from datetime import datetime

# Ajuste de ruta para alcanzar la carpeta 'services'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.connection import ConnectionService, load_config
from services.calendar_logic import WEEKDAYS_ES, list_calendars

def extraer_nombre_y_dni(summary):
    """
    Extrae el nombre y DNI del título del evento:
    'Paciente: Juan Perez (DNI: 12345678) - Niño Sano'
    """
    match = re.search(r"Paciente:\s*(.*?)\s*\(DNI:\s*(\d+)\)", summary)
    if match:
        return match.group(1), match.group(2)
    return None, None

def eliminar_evento(service, calendar_id, event_id):
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except Exception as e:
        print(f"❌ Error al eliminar: {e}")
        return False

def obtener_turnos(email_medico, dni):
    cfg = load_config()
    conn = ConnectionService(cfg)
    service = conn.build_calendar_service(email_medico)
    ahora = datetime.utcnow().isoformat() + "Z"
    
    try:
        cals = list_calendars(email_medico)
        calendar_ids = [c['id'] for c in cals if c.get("accessRole") in ("owner", "writer")]
    except Exception as e:
        print(f"Error al listar calendarios: {e}")
        return [], None

    turnos_encontrados = []
    for cal_id in calendar_ids:
        events = service.events().list(calendarId=cal_id, q=dni, timeMin=ahora, singleEvents=True).execute()
        for item in events.get("items", []):
            item['calendar_id_origin'] = cal_id 
            turnos_encontrados.append(item)

    return sorted(turnos_encontrados, key=lambda x: x['start'].get('dateTime', '')), service

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Email del médico")
    parser.add_argument("--dni", help="DNI del paciente para búsqueda directa") # Nuevo argumento
    args = parser.parse_args()

    # Si el DNI no viene por terminal, lo pide por teclado
    dni_busqueda = args.dni if args.dni else input("\nIngrese su DNI para gestionar sus turnos: ").strip()
    
    if not dni_busqueda:
        print("DNI requerido para la consulta.")
        return

    turnos, service = obtener_turnos(args.email, dni_busqueda)

    if not turnos:
        print(f"\nNo se encontraron turnos para el DNI: {dni_busqueda}")
        return

    print(f"\nSus turnos actuales (DNI: {dni_busqueda}):")
    for i, t in enumerate(turnos, start=1):
        start_str = t['start'].get('dateTime', t['start'].get('date'))
        dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        print(f"{i}) {WEEKDAYS_ES[dt.weekday()]} {dt.strftime('%d/%m %H:%M')} - {t.get('summary')}")

    try:
        choice_raw = input("\nSeleccione el número de turno para gestionar (o 0 para salir): ").strip()
        if not choice_raw or choice_raw == "0": return
        idx = int(choice_raw) - 1
        turno_sel = turnos[idx]
    except (ValueError, IndexError):
        print("Opción inválida.")
        return

    print(f"\n¿Qué desea hacer con el turno del {turno_sel['start'].get('dateTime')}?")
    print("1) Cancelar (Eliminar)")
    print("2) Re-agendar (Cambiar fecha)")
    accion = input("Opción: ").strip()

    if accion == "1":
        if eliminar_evento(service, turno_sel['calendar_id_origin'], turno_sel['id']):
            print("\n✅ Turno cancelado con éxito.")
        
    elif accion == "2":
        # Intentamos extraer el nombre para pasarlo al siguiente script
        nombre_ext, dni_ext = extraer_nombre_y_dni(turno_sel.get('summary', ''))
        
        # Si no se pudo extraer del título, usamos el DNI de la búsqueda
        if not dni_ext: dni_ext = dni_busqueda

        print(f"\nIniciando proceso de re-agendamiento para DNI: {dni_ext}...")
        
        if eliminar_evento(service, turno_sel['calendar_id_origin'], turno_sel['id']):
            print("✅ Turno anterior liberado.")
            
            # Importamos dinámicamente el script de solicitud
            import solicitar_turno
            
            # Configuramos sys.argv para que solicitar_turno tome los datos automáticamente
            sys.argv = [sys.argv[0], "--email", args.email, "--dni", dni_ext]
            if nombre_ext:
                sys.argv.extend(["--nombre", nombre_ext])
            
            print("Redirigiendo a búsqueda de nuevos horarios...\n")
            solicitar_turno.main()
        else:
            print("❌ No se pudo liberar el turno actual. Intente nuevamente.")

if __name__ == "__main__":
    main()