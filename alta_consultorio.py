import argparse
from services.connection import ConnectionService, load_config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Email del médico")
    parser.add_argument("--nombre", required=True, help="Ej: Consultorio Palermo")
    parser.add_argument("--direccion", required=True, help="Ej: Av. Santa Fe 1234")
    args = parser.parse_args()

    conn = ConnectionService(load_config())
    # 1. Obtenemos el médico (con el UUID real que ya arreglamos)
    medico = conn.get_medico_by_email(args.email)

    if not medico:
        print(f"❌ Error: No se encontró al médico con email {args.email}")
        return

    # 2. CREAR EL CALENDARIO REAL EN GOOGLE
    print(f"Creando calendario en Google para: {args.nombre}...")
    try:
        service = conn.build_calendar_service(args.email)
        
        calendar_metadata = {
            'summary': f"Consultorio: {args.nombre}",
            'description': f"Sede: {args.direccion}",
            'timeZone': 'America/Argentina/Buenos_Aires'
        }
        
        created_calendar = service.calendars().insert(body=calendar_metadata).execute()
        google_calendar_id = created_calendar['id']
        print(f"✅ Calendario de Google creado con ID: {google_calendar_id}")

    except Exception as e:
        print(f"❌ Error al crear en Google Calendar: {e}")
        return

    # 3. PERSISTIR EN SUPABASE (con el ID de Google incluido)
    nuevo_consultorio = {
        "medico_id": medico["id"],
        "nombre": args.nombre,
        "direccion": args.direccion,
        "google_calendar_id": google_calendar_id
    }

    try:
        res = conn.supabase.table("consultorios").insert(nuevo_consultorio).execute()
        print(f"✅ Consultorio '{args.nombre}' persistido en Supabase para el Dr/a {medico['nombre_completo']}.")
    except Exception as e:
        print(f"❌ Error al insertar en Supabase: {e}")

if __name__ == "__main__":
    main()