from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user
from config import UPLOAD_FOLDER, LOG_FOLDER
from database.models import collection_users
from instagrapi import Client
from instagram.follow import  procesar_usuarios, generar_mensaje_combinado
from instagram.session import verificar_autenticacion, manejar_2fa
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
from instagrapi.exceptions import LoginRequired
import time
from functools import wraps
from openai_utils import generar_mensaje_ia
from instagram.config_bot import PAUSAS_POR_ACCION
from datetime import datetime, timedelta

os.environ['FLASK_ENV'] = 'development'  # Simula el entorno local en producción



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



from instagrapi.exceptions import ChallengeRequired

@app.route('/instagram-login', methods=['POST'])
def instagram_login():
    username = request.form.get('instagram_username')
    password = request.form.get('instagram_password')

    if not username or not password:
        return jsonify({"success": False, "error": "Debes proporcionar un usuario y contraseña de Instagram."})

    try:
        cl = Client()

        # Intentar restaurar sesión previa
        if 'instagram_client' in session:
            cl.set_settings(session['instagram_client'])
            print("🔄 [DEBUG] Se restauró la sesión guardada en Railway.")

        cl.login(username, password)

        # Guardar sesión para futuros logins sin 2FA
        session['instagram_user'] = username
        session['instagram_password'] = password
        session['instagram_client'] = cl.get_settings()

        print("✅ Inicio de sesión en Instagram exitoso")
        return jsonify({"success": True, "message": "Inicio de sesión exitoso.", "redirect": "/acciones"})

    except ChallengeRequired as e:
        print(f"⚠️ [DEBUG] Instagram requiere verificación para {username}")

        # Intentar obtener el método de verificación (correo, SMS, etc.)
        challenge = cl.challenge_resolve()
        if challenge.get("step_name") == "select_verify_method":
            return jsonify({"2fa_required": True, "message": "Instagram requiere verificación. Ingresa el código que recibirás por email."})

        return jsonify({"success": False, "error": "Se requiere verificación adicional en Instagram."})

    except Exception as e:
        print(f"❌ [ERROR] al iniciar sesión en Instagram: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/verify-2fa', methods=['POST'])
def verificar_2fa():
    username = session.get('instagram_user')
    password = session.get('instagram_password')
    code = request.json.get('code')

    if not username or not password:
        return jsonify({"success": False, "error": "Usuario no autenticado para verificar 2FA."}), 400

    if not code:
        return jsonify({"success": False, "error": "Debes ingresar un código de 2FA."}), 400

    try:
        cl = Client()
        cl.login(username, password, verification_code=code)

        # Guardar la sesión para evitar pedir 2FA en futuros logins
        session['instagram_client'] = cl.get_settings()
        session['two_fa_pending'] = False

        return jsonify({"success": True, "message": "Autenticación 2FA exitosa.", "redirect": "/acciones"})

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
    
@app.route('/acciones', methods=['GET', 'POST'])
def acciones():
    print("[DEBUG] Iniciando la función /acciones")
    
    if 'user' not in session:
        print("[DEBUG] Usuario no autenticado. Redirigiendo a /login")
        return redirect('/login')
    
    if request.method == 'POST':
        try:
            # Capturar y limpiar valores del formulario
            competidores_raw = request.form.get('competidores', '').strip()
            competidores = [c.strip() for c in competidores_raw.split(',') if c.strip()]
            
            try:
                duracion_horas = int(request.form.get('duracion', 6))
                cantidad = int(request.form.get('cantidad', 120))
            except ValueError:
                print("❌ [ERROR] Los valores de duración y cantidad no son números válidos.")
                return jsonify({"success": False, "error": "Los valores de duración y cantidad deben ser números válidos."}), 400

            rol = request.form.get('rol', 'amigable')

            print(f"[DEBUG] Ejecutando procesamiento para los siguientes competidores: {competidores}")
            print(f"[DEBUG] Duración: {duracion_horas} horas, Cantidad de seguidores a procesar: {cantidad}")
            print(f"[DEBUG] Rol seleccionado para mensajes: {rol}")

            # Validaciones
            if not competidores:
                print("❌ [ERROR] No se proporcionaron usuarios de competencia.")
                return jsonify({"success": False, "error": "Debe proporcionar al menos un usuario de competencia."}), 400
            if duracion_horas <= 0 or cantidad <= 0:
                print("❌ [ERROR] La duración y cantidad deben ser mayores a 0.")
                return jsonify({"success": False, "error": "La duración y la cantidad deben ser mayores a 0."}), 400

            # Verificar sesión antes de procesar seguidores
            if not verificar_autenticacion():
                print("❌ [ERROR] Sesión de Instagram inválida. No se puede ejecutar el proceso.")
                return jsonify({"success": False, "error": "Sesión de Instagram inválida."}), 400

            # Procesar seguidores
            errores_procesamiento = []
            for competencia in competidores:
                print(f"🚀 [DEBUG] Obteniendo seguidores para {competencia}...")

                try:
                    respuesta = procesar_usuarios(competencia, duracion_horas=duracion_horas, cantidad=cantidad)

                    if not isinstance(respuesta, dict) or not respuesta.get("success"):
                        print(f"⚠️ [ERROR] No se pudieron obtener seguidores de {competencia}")
                        errores_procesamiento.append({
                            "competencia": competencia, 
                            "error": respuesta.get("error", "Error desconocido")
                        })
                        continue

                except Exception as e:
                    print(f"❌ [ERROR] Error al obtener seguidores de {competencia}: {e}")
                    errores_procesamiento.append({
                        "competencia": competencia, 
                        "error": str(e)
                    })

            print("✅ [DEBUG] Procesamiento de acciones completado.")

            return jsonify({
                "success": True,
                "message": "Acciones iniciadas correctamente.",
                "errors": errores_procesamiento
            })

        except Exception as e:
            print(f"❌ [ERROR] Error en el procesamiento de /acciones: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    return render_template('Acciones.html')


@app.route('/cargar_mensajes', methods=['POST'])
def cargar_mensajes():
    try:
        mensajes_dm = []
        mensajes_comentarios = []

        # Diccionario para registrar qué archivos fueron subidos
        session['archivos_subidos'] = session.get('archivos_subidos', {})

        for file_key in request.files:
            for file in request.files.getlist(file_key):
                contenido = file.read().decode('utf-8').splitlines()

                # Verificar qué campo del formulario subió el archivo
                if file_key == "mensajes_dm":
                    mensajes_dm.extend(contenido)
                    session['archivos_subidos']['dm'] = file.filename
                elif file_key == "mensajes_comentarios":
                    mensajes_comentarios.extend(contenido)
                    session['archivos_subidos']['comentarios'] = file.filename
                else:
                    print(f"⚠️ [ADVERTENCIA] Archivo {file.filename} subido en un campo no identificado.")

        # Guardamos los mensajes en la sesión asegurándonos de no sobrescribir erróneamente
        session['mensajes_dm'] = mensajes_dm if mensajes_dm else []
        session['mensajes_comentarios'] = mensajes_comentarios if mensajes_comentarios else []

        print(f"✅ Archivos subidos correctamente: {session['archivos_subidos']}")
        print(f"✅ Mensajes DM: {len(mensajes_dm)}, Mensajes Comentarios: {len(mensajes_comentarios)}")

        return jsonify({
            "success": True,
            "mensajes_dm": len(mensajes_dm),
            "mensajes_comentarios": len(mensajes_comentarios),
            "archivos_subidos": session['archivos_subidos']
        })
    except Exception as e:
        print(f"❌ [ERROR] al cargar los archivos de mensajes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route("/chatgpt", methods=["POST"])
def chatgpt():
    """
    Procesa un mensaje de usuario y genera una respuesta breve y personalizada con ChatGPT,
    priorizando nombres reales y asegurando mensajes concisos.
    """
    datos = request.json
    mensaje_usuario = datos.get("mensaje", "").strip()
    rol = datos.get("rol", "amigable")  # Valor por defecto
    nombre = datos.get("nombre")  # Obtener el nombre real si está disponible
    username = datos.get("username")  # Obtener el username si está disponible

    if not mensaje_usuario:
        return jsonify({"respuesta": "No se recibió ningún mensaje."}), 400

    try:
        # Construcción de saludo con alternancia para evitar repetición
        if nombre:
            saludo = nombre
        elif username:
            saludo = username
        else:
            saludo = "friend"

        if random.random() > 0.7:  # 30% de los mensajes no incluirán saludo
            saludo = ""

        # Generar mensaje personalizado con el rol proporcionado y priorización de brevedad
        respuesta = generar_mensaje_ia(
            username=username,
            bio=None,
            intereses=None,
            ultima_publicacion=mensaje_usuario,
            rol=rol,
            nombre=saludo
        )
        return jsonify({"respuesta": respuesta})
    except Exception as e:
        return jsonify({"respuesta": f"Error al procesar el mensaje: {e}"}), 500


if __name__ == "__main__":
    try:
        app.run(debug=False, use_reloader=False)
    except Exception as e:
    
        print(f"Error al iniciar la aplicación: {e}")
