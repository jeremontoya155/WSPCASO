from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user
from config import UPLOAD_FOLDER, LOG_FOLDER
from database.models import collection_users, collection_acciones
from instagrapi import Client
from instagram.follow import obtener_seguidores_de_competencia, seguir_usuario, dar_me_gusta_a_publicaciones, comentar_publicacion, enviar_dm, ver_historias, generar_mensaje_personalizado
from instagram.session import autenticar_con_2fa
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
from json.decoder import JSONDecodeError
from instagrapi.exceptions import LoginRequired, TwoFactorRequired
import time
from functools import wraps
from openai_utils import generar_mensaje_ia




# Configurar la aplicación Flask
app = Flask(__name__)
app.secret_key = 'clave-secreta-super-segura'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['LOG_FOLDER'] = LOG_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['LOG_FOLDER'], exist_ok=True)

cl = Client()

# Configura Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelo de usuario
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    print(f"[DEBUG] Cargando usuario con ID: {user_id}")
    user = collection_users.find_one({"username": user_id})
    if user:
        print(f"[DEBUG] Usuario encontrado: {user}")
        return User(id=user["username"])
    print("[DEBUG] Usuario no encontrado")
    return None

# Ruta principal
@app.route('/index')
@login_required
def index():
    print("[DEBUG] Usuario autenticado accediendo al bot.")
    return render_template('index.html', username=current_user.id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            username = request.form.get('username')
            password = request.form.get('password')

            print(f"[DEBUG] Credenciales recibidas: username={username}, password={'*' * len(password) if password else None}")

            # Validar que ambos campos estén completos
            if not username or not password:
                print("[DEBUG] Campos de login incompletos")
                return render_template('login.html', error="Todos los campos son obligatorios")

            # Buscar usuario en la base de datos
            user = collection_users.find_one({"username": username})
            if user and 'password' in user:
                # Validar la contraseña
                if check_password_hash(user['password'], password):
                    print(f"[DEBUG] Contraseña correcta para el usuario: {username}")
                    user_obj = User(id=username)
                    login_user(user_obj)
                    session['user'] = username
                    return redirect('/index')
                else:
                    print("[DEBUG] Contraseña incorrecta")
            else:
                print("[DEBUG] Usuario no encontrado o datos incompletos")
            return render_template('login.html', error="Credenciales incorrectas")
        except Exception as e:
            print(f"[DEBUG] Error durante el login: {e}")
            return render_template('login.html', error="Error interno del servidor.")
    print("[DEBUG] Accediendo al formulario de login (GET)")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            username = request.form['username']
            password = request.form['password']
            print(f"[DEBUG] Intentando registrar usuario: {username}")

            # Validar que ambos campos estén completos
            if not username or not password:
                return render_template('register.html', error="Todos los campos son obligatorios")

            # Verificar si el usuario ya existe
            if collection_users.find_one({"username": username}):
                print("[DEBUG] Usuario ya existe en la base de datos")
                return render_template('register.html', error="El usuario ya existe")

            # Generar hash de la contraseña
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

            # Guardar el usuario en la base de datos
            collection_users.insert_one({"username": username, "password": hashed_password})
            print("[DEBUG] Usuario registrado exitosamente")
            return redirect('/login')
        except Exception as e:
            print(f"[DEBUG] Error en registro: {e}")
            return render_template('register.html', error="Error interno del servidor.")
    return render_template('register.html')


@app.route('/instagram-login', methods=['POST'])
@login_required
def instagram_login():
    username = request.form.get('instagram_username')
    password = request.form.get('instagram_password')

    if not username or not password:
        return render_template('index.html', error="Debes proporcionar un usuario y contraseña de Instagram.")

    try:
        # Intentar iniciar sesión
        result = autenticar_con_2fa(username, password)
        if result.get("2fa_required"):
            # Si se requiere 2FA, guardar información en la sesión
            session['instagram_user'] = username
            session['instagram_password'] = password
            return jsonify({"2fa_required": True, "message": "Se requiere autenticación 2FA. Ingresa el código."})

        # Inicio de sesión exitoso
        session['instagram_user'] = username
        session['instagram_password'] = password
        session['instagram_client'] = cl.get_settings()
        print("✅ Inicio de sesión en Instagram exitoso")
        return jsonify({"success": True, "message": "Inicio de sesión exitoso.", "redirect": "/acciones"})
    except Exception as e:
        print(f"❌ Error al iniciar sesión en Instagram: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/verify-2fa', methods=['POST'])
def verificar_2fa():
    username = session.get('instagram_user')
    code = request.json.get('code')

    if not username:
        return jsonify({"success": False, "error": "Usuario no autenticado para verificar 2FA."}), 400

    if not code:
        return jsonify({"success": False, "error": "Debes ingresar un código de 2FA."}), 400

    try:
        # Manejar el desafío de 2FA
        result = cl.challenge_code(code)  # Cambia esto según la librería que estés usando
        if result:
            session['two_fa_pending'] = False  # Marcar que el 2FA ha sido completado
            return jsonify({"success": True, "message": "Autenticación 2FA exitosa.", "redirect": "/acciones"})
        else:
            return jsonify({"success": False, "error": "Código 2FA incorrecto."})
    except Exception as e:
        print(f"❌ Error al verificar el código 2FA: {e}")
        return jsonify({"success": False, "error": str(e)})

def validar_codigo_2fa(code):
    try:
        print(f"🔑 Verificando código 2FA: {code}")
        cl.two_factor_login(code)
        print("✅ Código 2FA verificado correctamente")
        return {"authenticated": True, "message": "Sesión iniciada correctamente con 2FA"}
    except LoginRequired:
        print("⚠️ Sesión expirada. Reintentando autenticación...")
        username = session.get('instagram_user')
        password = session.get('instagram_password')
        if username and password:
            try:
                cl.login(username, password)
                return {"authenticated": False, "error": "La sesión fue renovada. Por favor, ingresa el código nuevamente."}
            except Exception as e:
                return {"authenticated": False, "error": f"Error al reautenticar: {e}"}
    except Exception as e:
        print(f"❌ Error al verificar el código 2FA: {e}")
        return {"authenticated": False, "error": str(e)}

def verificar_2fa_completado(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'instagram_user' not in session:
            print("[DEBUG] Usuario no autenticado. Redirigiendo a /login.")
            return redirect('/login')  # Redirigir al formulario de login

        if session.get('two_fa_pending', True):  # Si el 2FA está pendiente
            print("[DEBUG] 2FA pendiente. Redirigiendo a /")
            return redirect('/login')  # Redirigir al formulario de inicio de sesión

        return func(*args, **kwargs)
    return wrapper


@app.route('/', methods=['GET', 'POST'])
def home():
    print("[DEBUG] Accediendo a la ruta /")
    if current_user.is_authenticated:
        print("[DEBUG] Usuario autenticado, redirigiendo a /bot")
        return redirect(url_for('iniciar_bot'))

    if request.method == 'POST':
        print("[DEBUG] Solicitud POST recibida en /")
        return redirect(url_for('login'))

    print("[DEBUG] Redirigiendo a /login desde /")
    return redirect(url_for('login'))


@app.route('/bot', methods=['GET', 'POST'])
def iniciar_bot():
    if request.method == 'GET':
        if session.get('two_fa_pending', True):
            print("[DEBUG] Intento de acceso a /bot sin completar 2FA.")
            return redirect('/login')
        return render_template('index.html')

    print("[DEBUG] Procesando solicitud POST en /bot")
    from instagram.session import autenticar_bot
    try:
        username = request.form.get("username")
        password = request.form.get("password")
        result = autenticar_bot(username, password)

        # Si se requiere 2FA, no completar la autenticación
        if result.get("2fa_required"):
            session['instagram_user'] = username
            session['two_fa_pending'] = True  # Marcar que el 2FA está pendiente
            return jsonify({"2fa_required": True, "message": result["message"]})

        # Si la autenticación es exitosa
        session['instagram_user'] = username
        session['two_fa_pending'] = False  # Marcar que no hay 2FA pendiente
        return jsonify({"message": "Autenticación exitosa", "redirect": "/acciones"})
    except Exception as e:
        print(f"[DEBUG] Error al procesar la autenticación: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/procesar_usuarios', methods=['POST'])
def procesar_usuarios():
    try:
        print("[DEBUG] Procesando usuarios con retraso...")
        usuarios = session.get('usuarios_seguidores', [])
        if not usuarios:
            return jsonify({"success": False, "error": "No hay usuarios para procesar."})
        
        # Aquí se puede agregar lógica si es necesaria para procesar los usuarios manualmente
        return jsonify({"success": True, "message": "Usuarios procesados con retraso."})
    except Exception as e:
        print(f"[DEBUG] Error al procesar usuarios: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/acciones', methods=['GET', 'POST'])
def acciones():
    print("[DEBUG] Iniciando la función /acciones")

    if 'user' not in session:
        print("[DEBUG] Usuario no autenticado. Redirigiendo a /login")
        return redirect('/login')

    if request.method == 'POST':
        try:
            # Obtener los usuarios de competencia desde el formulario
            competencias = request.form.get('competencia', '')
            print(f"[DEBUG] Competencias recibidas en el formulario: {competencias}")

            # Procesar las competencias como lista
            competencias = [c.strip() for c in competencias.split(',') if c.strip()]
            if not competencias:
                print("[DEBUG] No se proporcionaron competencias válidas.")
                return jsonify({"success": False, "error": "Debes proporcionar al menos un usuario de competencia."}), 400

            # Obtener seguidores de cada cuenta de competencia
            usuarios_seguidores = []
            for competencia in competencias:
                print(f"[DEBUG] Procesando la competencia: {competencia}")
                try:
                    seguidores_ids = obtener_seguidores_de_competencia(competencia, cantidad=10)
                    print(f"[DEBUG] IDs de seguidores obtenidos para {competencia}: {seguidores_ids}")
                    
                    for seguidor_id in seguidores_ids:
                        try:
                            info = obtener_informacion_usuario(seguidor_id)
                            usuarios_seguidores.append({
                                "username": info.get("username", "Usuario desconocido"),
                                "biography": info.get("biography", "Sin biografía"),
                                "follower_count": info.get("follower_count", 0),
                                "media_count": info.get("media_count", 0),
                            })
                        except Exception as e:
                            print(f"[DEBUG] Error al obtener información del seguidor {seguidor_id}: {e}")
                except Exception as e:
                    print(f"[DEBUG] Error al obtener seguidores de la competencia {competencia}: {e}")

            if not usuarios_seguidores:
                print("[DEBUG] No se encontraron seguidores para las cuentas especificadas.")
                return jsonify({"success": False, "error": "No se encontraron seguidores para las cuentas especificadas."}), 404

            # Guardar usuarios en la sesión para usarlos en la plantilla
            session['usuarios_seguidores'] = usuarios_seguidores

            return jsonify({"success": True, "users": usuarios_seguidores})

        except Exception as e:
            print(f"[DEBUG] Error en el procesamiento de /acciones: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # Si la solicitud es GET, renderizar la página con los usuarios guardados
    usuarios_seguidores = session.get('usuarios_seguidores', [])
    print(f"[DEBUG] Usuarios seguidores en sesión: {len(usuarios_seguidores)}")
    return render_template('Acciones.html', users=usuarios_seguidores)

@app.route('/procesar_accion', methods=['POST'])
def procesar_accion():
    try:
        data = request.get_json()
        user = data.get("user")  # Ahora recibimos los datos completos del usuario
        action = data.get("action")

        if not user or not action:
            return jsonify({"success": False, "error": "Faltan datos para procesar la acción."}), 400

        if action == "comment":
            comentario = generar_mensaje_personalizado(user["username"], user.get("biography"))
            comentar_publicacion(user["id"], comentario)
        elif action == "dm":
            mensaje = generar_mensaje_personalizado(user["username"], user.get("biography"))
            enviar_dm(user["id"], mensaje)
        elif action == "follow":
            seguir_usuario(user["id"])
        elif action == "like":
            dar_me_gusta_a_publicaciones(user["id"])
        elif action == "view_story":
            ver_historias(user["id"])

        return jsonify({"success": True, "message": f"Acción '{action}' realizada con éxito."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/aplicar_filtros', methods=['POST'])
def aplicar_filtros():
    try:
        print("[DEBUG] Procesando filtros enviados desde el frontend")

        # Obtener y procesar los datos enviados desde el formulario
        competencias = request.form.get('competidores', '').split(',')
        competencias = [c.strip() for c in competencias if c.strip()]
        
        usuarios_filtrados = []
        usuarios_con_errores = []

        # Validación de competencias
        if not competencias:
            print("[DEBUG] No se proporcionaron competencias válidas.")
            return jsonify({"success": False, "error": "Debes proporcionar al menos una competencia válida."}), 400

        print(f"[DEBUG] Competencias recibidas: {competencias}")

        # Procesar cada competencia
        for competencia in competencias:
            print(f"[DEBUG] Procesando la competencia: {competencia}")
            try:
                # Obtener seguidores con información completa
                seguidores_info = obtener_seguidores_de_competencia(competencia, cantidad=3)
                print(f"[DEBUG] Información de seguidores obtenida para {competencia}: {seguidores_info}")

                # Agregar usuarios filtrados
                usuarios_filtrados.extend(seguidores_info)

            except Exception as e:
                print(f"[DEBUG] Error al obtener seguidores de la competencia {competencia}: {e}")
                usuarios_con_errores.append({"competencia": competencia, "error": str(e)})

        # Validar si se encontraron usuarios
        if not usuarios_filtrados:
            print("[DEBUG] No se encontraron usuarios filtrados.")
            return jsonify({"success": False, "error": "No se encontraron usuarios para las competencias proporcionadas."}), 404

        # Procesar acciones seleccionadas (si las hay)
        acciones_seleccionadas = request.form.getlist('acciones')
        if acciones_seleccionadas:
            print(f"[DEBUG] Acciones seleccionadas: {acciones_seleccionadas}")
            for usuario in usuarios_filtrados:
                for accion in acciones_seleccionadas:
                    try:
                        # Ejecutar acciones según el tipo
                        if accion == "follow":
                            seguir_usuario(usuario['id'])
                        elif accion == "view_story":
                            ver_historias(usuario['id'])
                        print(f"✅ Acción '{accion}' realizada con éxito para el usuario ID: {usuario['id']}.")
                    except Exception as e:
                        print(f"❌ Error al realizar la acción '{accion}' para el usuario ID: {usuario['id']}: {e}")
                        usuarios_con_errores.append({
                            "id": usuario['id'],
                            "action": accion,
                            "error": str(e),
                        })

        # Construir la respuesta final
        return jsonify({
            "success": True,
            "users": usuarios_filtrados,
            "errors": usuarios_con_errores,
        })

    except Exception as e:
        print(f"[DEBUG] Error inesperado en aplicar_filtros: {e}")
        return jsonify({"success": False, "error": f"Error inesperado: {str(e)}"}), 500


def obtener_informacion_usuario(user_id):
    """
    Obtiene información de un usuario de Instagram por su ID y maneja errores.
    """
    try:
        print(f"🔍 Obteniendo información del usuario {user_id}")
        user_info = cl.user_info(user_id)

        # Retorna la información si la solicitud es exitosa
        return {
            "id": user_id,
            "username": user_info.get("username", "No disponible"),
            "biography": user_info.get("biography", "No disponible"),
            "follower_count": user_info.get("follower_count", 0),
            "media_count": user_info.get("media_count", 0),
            "is_private": user_info.get("is_private", False),
        }

    except KeyError as ke:
        # Si falta información clave, devolver solo el ID y un mensaje de error
        print(f"❌ Error al obtener información del usuario {user_id}: {ke}")
        return {
            "id": user_id,
            "username": "No disponible",
            "error": f"Información incompleta: {str(ke)}"
        }

    except Exception as e:
        # Manejo genérico de otros errores
        print(f"❌ Error inesperado al obtener información del usuario {user_id}: {e}")
        return {
            "id": user_id,
            "username": "No disponible",
            "error": "Error desconocido al procesar el usuario"
        }
@app.route('/procesar_acciones_lote', methods=['POST'])
def procesar_acciones_lote():
    try:
        data = request.get_json()
        acciones = data.get("actions", [])
        user_ids = data.get("user_ids", [])

        if not acciones:
            return jsonify({"success": False, "error": "No se seleccionaron acciones."}), 400

        if not user_ids:
            return jsonify({"success": False, "error": "No se enviaron IDs de usuarios."}), 400

        errores = []
        for user_id in user_ids:
            for accion in acciones:
                try:
                    if accion == "follow":
                        seguir_usuario(user_id)
                    elif accion == "like":
                        dar_me_gusta_a_publicaciones(user_id)
                    elif accion == "comment":
                        comentario = generar_mensaje_ia("", "")  # Personalizar si es necesario
                        comentar_publicacion(user_id, comentario)
                    elif accion == "dm":
                        mensaje = generar_mensaje_ia("", "")  # Personalizar si es necesario
                        enviar_dm(user_id, mensaje)
                    elif accion == "view_story":
                        ver_historias(user_id)
                except Exception as e:
                    errores.append({"id": user_id, "action": accion, "error": str(e)})

        if errores:
            return jsonify({"success": False, "error": "Algunas acciones fallaron.", "details": errores}), 207

        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/cargar_mas_usuarios', methods=['POST'])
def cargar_mas_usuarios():
    competencia = request.form.get('competencia')
    if not competencia:
        return jsonify({"success": False, "error": "No se proporcionó una cuenta de competencia."})

    try:
        usuarios = obtener_seguidores_de_competencia(competencia, cantidad=10)
        return jsonify({"success": True, "users": usuarios})
    except Exception as e:
        print(f"❌ Error al cargar más usuarios: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """
    Devuelve métricas desglosadas por tipo de acción realizada.
    """
    try:
        # Recuperar los conteos de cada acción desde la base de datos
        acciones = {
            "seguir_usuario": collection_acciones.count_documents({"accion": "seguir"}),
            "dar_me_gusta_a_publicaciones": collection_acciones.count_documents({"accion": "me_gusta"}),
            "comentar_publicacion": collection_acciones.count_documents({"accion": "comentario"}),
            "enviar_dm": collection_acciones.count_documents({"accion": "dm"}),
            "ver_historias": collection_acciones.count_documents({"accion": "view_story"})
        }

        # Estado del bot (puedes ajustarlo dinámicamente si es necesario)
        estado_bot = "activo"

        # Métricas finales
        metrics = {
            "acciones_realizadas": sum(acciones.values()),
            "desglose_acciones": acciones,
            "estado_bot": estado_bot
        }

        return jsonify(metrics)

    except Exception as e:
        print(f"❌ Error al generar métricas: {e}")
        return jsonify({"error": "No se pudieron obtener las métricas."}), 500

if __name__ == "__main__":
    print("Iniciando la aplicación Flask...")
    app.run(debug=True)

