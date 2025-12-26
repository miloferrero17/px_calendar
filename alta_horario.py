import argparse
from services.connection import ConnectionService, load_config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--dia", type=int, required=True, help="0=Lun, 1=Mar, 2=Mie, 3=Jue, 4=Vie")
    parser.add_argument("--inicio", required=True, help="HH:MM")
    parser.add_argument("--fin", required=True, help="HH:MM")
    args = parser.parse_args()

    conn = ConnectionService(load_config())
    medico = conn.get_medico_by_email(args.email)
    
    # Buscamos el consultorio del médico
    res_cons = conn.supabase.table("consultorios").select("id, nombre").eq("medico_id", medico["id"]).execute()
    
    if not res_cons.data:
        print("❌ Error: Primero debés dar de alta un consultorio.")
        return

    consultorio_id = res_cons.data[0]["id"]
    
    nuevo_horario = {
        "consultorio_id": consultorio_id,
        "dia_semana": args.dia,
        "hora_inicio": args.inicio,
        "hora_fin": args.fin
    }

    conn.supabase.table("horarios_atencion").insert(nuevo_horario).execute()
    print(f"✅ Horario cargado en '{res_cons.data[0]['nombre']}' para el día {args.dia} ({args.inicio} a {args.fin}).")

if __name__ == "__main__":
    main()