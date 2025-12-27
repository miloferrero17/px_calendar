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

def eliminar_consultorio_total(email, consultorio_id):
    try:
        cfg = load_config()
        conn = ConnectionService(cfg)
        
        # 1. Obtener el ID del calendario antes de borrar el registro
        res = conn.supabase.table("consultorios").select("google_calendar_id")\
            .eq("id", consultorio_id).single().execute()
        
        if not res.data:
            print("❌ El consultorio no existe en Supabase.")
            return

        google_id = res.data["google_calendar_id"]

        # 2. Eliminar en Google Calendar
        try:
            service = conn.build_calendar_service(email)
            service.calendars().delete(calendarId=google_id).execute()
            print(f"✅ Calendario {google_id} eliminado en Google.")
        except Exception as ge:
            print(f"⚠️ No se pudo eliminar en Google (quizás ya no existía): {ge}")

        # 3. Eliminar en Supabase (esto borrará horarios_atencion por cascada si está configurado)
        conn.supabase.table("consultorios").delete().eq("id", consultorio_id).execute()
        print(f"✅ Registro {consultorio_id} eliminado en Supabase.")

    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    eliminar_consultorio_total("milonguitaferrero@gmail.com", "5d31392d-31a6-485a-af9e-c5765489eb48")