from services.connection import load_config, ConnectionService

# 1. Preparar la conexión
cfg = load_config()
conn = ConnectionService(cfg)

# 2. El email que quieres consultar
DOCTOR_EMAIL = "milonguitaferrero@gmail.com"

# 3. Obtener el token (limpio y actualizado)
token = conn.get_valid_access_token(DOCTOR_EMAIL)
print(f"Tu Access Token es: {token}")