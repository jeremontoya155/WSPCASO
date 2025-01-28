from flask import Blueprint, request, jsonify
from instagram.session import cl, iniciar_sesion

# Crear el blueprint para las rutas de login
login_routes = Blueprint('login_routes', __name__)

@login_routes.route('/login', methods=['POST'])
def login():
    """
    Maneja el inicio de sesión desde el frontend.
    """
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"success": False, "error": "Credenciales incompletas."}), 400

        # Llamar a iniciar_sesion
        iniciar_sesion(username, password)
        return jsonify({"success": True, "message": "Inicio de sesión exitoso."})
    except Exception as e:
        print(f"Error en el login: {e}")
        return jsonify({"success": False, "error": str(e)}), 500