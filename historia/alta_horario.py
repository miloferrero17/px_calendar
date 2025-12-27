import argparse
import os
import sys
import datetime  # Importa el módulo completo
from datetime import datetime, time, timedelta # Mantiene las referencias directas

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


# Importamos build para una llamada personalizada si create_meeting no soporta recurrence
from googleapiclient.discovery import build 

def get_proximo_dia(dia_semana_objetivo):
    """Encuentra la fecha del próximo día de la semana (0=Lunes, 6=Domingo)"""
    hoy = datetime.now()
    dias_de_diferencia = (dia_semana_objetivo - hoy.weekday() + 7) % 7
    return (hoy + timedelta(days=dias_de_diferencia)).date()

def configurar_disponibilidad_recurrente(email, consultorio_id, dia_semana, apertura_str, cierre_str):
    try:
        cfg = load_config()
        conn = ConnectionService(cfg)
        
        # Obtener el ID de Google Calendar del consultorio
        res = conn.supabase.table("consultorios").select("google_calendar_id").eq("id", consultorio_id).single().execute()
        if not res.data:
            print("❌ No se encontró el consultorio.")
            return
        
        target_calendar_id = res.data["google_calendar_id"]

        # Persistir en Supabase
        conn.supabase.table("horarios_atencion").insert({
            "consultorio_id": consultorio_id,
            "dia_semana": dia_semana,
            "hora_inicio": apertura_str,
            "hora_fin": cierre_str
        }).execute()

        fecha_objetivo = get_proximo_dia(dia_semana)
        tz = "America/Argentina/Buenos_Aires"
        
        t_apertura = datetime.strptime(apertura_str, "%H:%M").time()
        t_cierre = datetime.strptime(cierre_str, "%H:%M").time()

        # Definir los bloques de tiempo
        bloques = []
        if t_apertura > time(0, 0):
            bloques.append({
                "start": datetime.combine(fecha_objetivo, time(0, 0)),
                "end": datetime.combine(fecha_objetivo, t_apertura),
                "summary": "⛔ CERRADO (Mañana)"
            })
        if t_cierre < time(23, 59):
            bloques.append({
                "start": datetime.combine(fecha_objetivo, t_cierre),
                "end": datetime.combine(fecha_objetivo, time(23, 59)),
                "summary": "⛔ CERRADO (Noche)"
            })

        # Mapeo de días para Google (RRULE usa MO, TU, WE, TH, FR, SA, SU)
        days_map = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        rrule = f"RRULE:FREQ=WEEKLY;BYDAY={days_map[dia_semana]}" # Se repite semanalmente este día

        service = conn.build_calendar_service(email)

        for b in bloques:
            event_body = {
                "summary": b["summary"],
                "location": "Bloqueo Automático",
                "description": "Horario no laboral configurado por el sistema",
                "start": {"dateTime": b["start"].isoformat(), "timeZone": tz},
                "end": {"dateTime": b["end"].isoformat(), "timeZone": tz},
                "recurrence": [rrule], # <--- ESTO HACE QUE SEA ETERNO
                "transparency": "opaque", # Aparece como 'Ocupado'
            }
            
            service.events().insert(calendarId=target_calendar_id, body=event_body).execute()
            print(f"✅ Bloqueo RECURRENTE creado para los {days_map[dia_semana]} en: {target_calendar_id}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    # Ejemplo: Bloquear todos los Lunes (0) para siempre
    configurar_disponibilidad_recurrente(
        email="milonguitaferrero@gmail.com",
        consultorio_id="ab10af79-9f46-470d-bc67-7f6ee5cbf450", # Tu UUID de médico/consultorio
        dia_semana=5, 
        apertura_str="14:00",
        cierre_str="18:00"
    )