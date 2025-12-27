import os
from datetime import datetime, time, timedelta
from services.connection import ConnectionService, load_config
from services.calendar_logic import create_meeting

def sincronizar_bloqueos(email):
    conn = ConnectionService(load_config())
    medico = conn.get_medico_by_email(email)
    
    # Supongamos que queremos bloquear el día de hoy
    hoy = datetime.now().date()
    
    # 1. Traer horarios de atención de este médico
    # (Suponiendo que ya cargaste alguno con alta_horario.py)
    res = conn.supabase.table("horarios_atencion").select("*").execute()
    
    # Lógica de bloqueo: Si no hay atención antes de las 14:00, bloqueamos mañana
    # Esto es un ejemplo de "Bloqueo de mañana"
    inicio_bloqueo = datetime.combine(hoy, time(0, 0))
    fin_bloqueo = datetime.combine(hoy, time(14, 0)) # Bloquea hasta que empezás a atender
    
    print(f"Bloqueando agenda de {inicio_bloqueo} a {fin_bloqueo}...")
    
    create_meeting(
        email=email,
        tz_str="America/Argentina/Buenos_Aires",
        start=inicio_bloqueo,
        end=fin_bloqueo,
        summary="⛔ NO DISPONIBLE (Sistema)",
        location="Automático",
        calendar_id="primary"
    )

if __name__ == "__main__":
    sincronizar_bloqueos("milonguitaferrero@gmail.com")