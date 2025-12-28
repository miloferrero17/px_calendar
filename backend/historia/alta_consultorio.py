'''
python3 backend/web/alta_consultorio.py --email milonguitaferrero@gmail.com --nombre "Consultorio Palermo" --direccion "Av. Santa Fe 1234"

'''

import argparse
import os
import sys

# 1. Localizamos la carpeta del archivo actual (.../backend/web)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Subimos dos niveles para llegar a la raíz (../..)
# De 'backend/web' a 'backend' y luego a 'raiz'
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))

# 3. Verificamos si la ruta ya está en sys.path para evitar duplicados y la agregamos al inicio
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Ahora intentamos importar
try:
    from services.connection import ConnectionService, load_config
    print("✅ Módulos cargados correctamente desde:", project_root)
except ModuleNotFoundError as e:
    print(f"❌ Error: No se encontró la carpeta 'services'.")
    print(f"Buscando en: {project_root}")
    print(f"Contenido de esa carpeta: {os.listdir(project_root) if os.path.exists(project_root) else 'Ruta no existe'}")
    sys.exit(1)


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
            'summary': f"Consultorio: {args.nombre}", # Corregido: f-string estándar
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