import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    print(f"Intentando conectar a: {url}")
    
    try:
        supabase = create_client(url, key)
        # Intentamos una operación mínima: pedir la versión o una tabla vacía
        res = supabase.table("medicos").select("count", count="exact").limit(1).execute()
        print("✅ Conexión exitosa. Supabase respondió correctamente.")
        print(f"Total de médicos en tabla: {res.count}")
    except Exception as e:
        print("❌ Error de conexión:")
        print(e)

if __name__ == "__main__":
    test_connection()