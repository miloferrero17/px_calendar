import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.connection import ConnectionService, load_config

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
    eliminar_consultorio_total("milonguitaferrero@gmail.com", "0022504c-2db7-42eb-bbf3-ac8744f69d2f")