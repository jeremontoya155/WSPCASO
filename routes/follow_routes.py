from flask import Blueprint, request, jsonify
from instagram.session import cl, iniciar_sesion, manejar_login
from instagrapi.exceptions import LoginRequired

# Crear el blueprint para las rutas de seguimiento
follow_routes = Blueprint('follow_routes', __name__)

@follow_routes.route('/seguir', methods=['POST'])
def seguir():
    """
    Ruta para realizar seguimientos con manejo explícito de LoginRequired.
    """
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        cuentas_competencia = data.get('cuentas_competencia', [])

        if not username or not password:
            return jsonify({"success": False, "error": "Credenciales incompletas."}), 400

        # Manejo de sesión
        manejar_login(username, password)

        # Obtener seguidores
        log = []
        for cuenta in cuentas_competencia:
            try:
                user_id = cl.user_id_from_username(cuenta)
                seguidores = cl.user_followers(user_id, amount=10)
                log.append(f"Seguidores obtenidos de @{cuenta}.")
            except LoginRequired as e:
                log.append(f"Error: Se requiere login para @{cuenta}: {e}")
            except Exception as e:
                log.append(f"Error al obtener seguidores de @{cuenta}: {e}")

        return jsonify({"success": True, "log": log})
    except Exception as e:
        print(f"Error en /seguir: {e}")
        return jsonify({"success": False, "error": str(e)}), 500