# backend/web/gestionar_sedes.py
import argparse
import os
import sys

# Ajuste de ruta para llegar a la raíz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from services.connection import ConnectionService, load_config

def crear_sede(email, nombre_sede):
    """Crea un calendario para la sede y lo vincula al médico."""
    conn = ConnectionService(load_config())
    service = conn.build_calendar_service(email)
    
    # 1. Crear el calendario en Google
    calendar_metadata = {
        'summary': f"Sede: {nombre_sede}",
        'description': "Calendario de atención gestionado por PX Calendar",
        'timeZone': 'America/Argentina/Buenos_Aires'
    }
    
    try:
        created_calendar = service.calendars().insert(body=calendar_metadata).execute()
        google_id = created_calendar['id']
        print(f"✅ Sede '{nombre_sede}' creada en Google Calendar.")
        print(f"🆔 ID: {google_id}")
        
        # 2. (Opcional) Guardar referencia en Supabase 
        # para que el sistema sepa que esta sede existe
        medico = conn.get_medico_by_email(email)
        if medico:
            conn.supabase.table("consultorios").insert({
                "medico_id": medico["id"],
                "nombre": nombre_sede,
                "google_calendar_id": google_id
            }).execute()
            print("✅ Referencia guardada en base de datos.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--nombre", required=True, help="Nombre de la sede (ej: Palermo)")
    args = parser.parse_args()
    
    crear_sede(args.email, args.nombre)