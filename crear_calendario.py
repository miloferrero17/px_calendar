from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from services.connection import load_config, ConnectionService

def crear_calendario_google(access_token):
    # Configuramos las credenciales usando el token que ya tienes
    creds = Credentials(token=access_token)
    
    # Construimos el servicio de Google Calendar
    service = build('calendar', 'v3', credentials=creds)

    # Definimos los detalles del nuevo calendario
    calendar_details = {
        'summary': 'Consultorio - Turnos Médicos',
        'timeZone': 'America/Argentina/Buenos_Aires'
    }

    try:
        # Ejecutamos la creación
        created_calendar = service.calendars().insert(body=calendar_details).execute()
        
        print(f"¡Calendario creado con éxito!")
        print(f"ID del Calendario: {created_calendar['id']}")
        
        return created_calendar['id']

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return None

# Ejemplo de uso:
# token_de_supabase = "tu_access_token_aqui"
# id_nuevo = crear_calendario_google(token_de_supabase)
# --- AÑADE ESTO AL FINAL DE TU ARCHIVO ---

# 1. Preparar la conexión
cfg = load_config()
conn = ConnectionService(cfg)

# 2. El email que quieres consultar
DOCTOR_EMAIL = "milonguitaferrero@gmail.com"

# 3. Obtener el token (limpio y actualizado)
mi_token = conn.get_valid_access_token(DOCTOR_EMAIL)
print(f"Tu Access Token es: {mi_token}")
# Llamamos a la función pasándole ese token
crear_calendario_google(mi_token)