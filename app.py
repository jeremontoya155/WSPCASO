<<<<<<< HEAD
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, session
from flask_login import LoginManager, UserMixin, current_user
from config import UPLOAD_FOLDER, LOG_FOLDER
from instagrapi import Client
from database.models import db, registrar_usuario, collection_users, verificar_accion, registrar_accion 
from datetime import datetime
from instagrapi.exceptions import TwoFactorRequired
import os
from fpdf import FPDF
import csv
from io import StringIO
from werkzeug.security import generate_password_hash, check_password_hash
from instagram.filters import filtrar_usuarios
from instagram.follow import procesar_usuario, obtener_seguidores_de_competencia, procesar_seguidores
from celery_app import celery
from instagram.session import autenticar_bot, autenticar_con_2fa,validar_codigo_2fa
from tasks.celery_tasks import seguir_cuenta, comentar_perfil, procesar_usuario_completo
import random
import time
=======
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user
from config import UPLOAD_FOLDER, LOG_FOLDER
from database.models import collection_users, db
from instagrapi import Client
from instagram.follow import obtener_seguidores_de_competencia, seguir_usuario, dar_me_gusta_a_publicaciones, comentar_publicacion, enviar_dm
from instagram.filters import aplicar_filtros_individual
from instagram.session import autenticar_con_2fa
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from json.decoder import JSONDecodeError
from instagrapi.exceptions import LoginRequired, TwoFactorRequired
import time
from functools import wraps

>>>>>>> 3f8b5aa (mejoras)


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
<<<<<<< HEAD
    print(f"Cargando usuario con ID: {user_id}")
    user = collection_users.find_one({"username": user_id})
    if user:
        print(f"Usuario encontrado: {user}")
        return User(id=user["username"])
    print("Usuario no encontrado")
=======
    print(f"[DEBUG] Cargando usuario con ID: {user_id}")
    user = collection_users.find_one({"username": user_id})
    if user:
        print(f"[DEBUG] Usuario encontrado: {user}")
        return User(id=user["username"])
    print("[DEBUG] Usuario no encontrado")
>>>>>>> 3f8b5aa (mejoras)
    return None

# Ruta principal
@app.route('/index')
<<<<<<< HEAD
def index():
    print("Accediendo a la ruta /index")
    if 'user' not in session:
        print("Usuario no autenticado, redirigiendo a /login")
        return redirect('/login')
    print(f"Usuario autenticado: {session['user']}")
    return render_template('index.html', username=session['user'])
=======
@login_required
def index():
    print("[DEBUG] Usuario autenticado accediendo al bot.")
    return render_template('index.html', username=current_user.id)

>>>>>>> 3f8b5aa (mejoras)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
<<<<<<< HEAD
        print("Procesando solicitud POST en /login")
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            print("Campos de login incompletos")
            return render_template('login.html', error="Todos los campos son obligatorios")

        user = collection_users.find_one({"username": username})

        if user and 'password' in user:
            if check_password_hash(user['password'], password):
                session['user'] = username
                print(f"Inicio de sesión exitoso para: {username}")
                return redirect('/index')
            else:
                print("Contraseña incorrecta")
        else:
            print("Usuario no encontrado o datos incompletos")

        return render_template('login.html', error="Credenciales incorrectas")

    print("Accediendo al formulario de login (GET)")
    return render_template('login.html')


@app.route('/verify-2fa', methods=['POST'])
def verificar_2fa():
    """
    Verifica el código 2FA enviado desde el frontend y completa la autenticación en Instagram.
    """
    username = session.get('instagram_user')  # Recupera el usuario almacenado en la sesión
    code = request.form.get('code')  # Código enviado desde el frontend

    if not username:
        return jsonify({"error": "⚠️ No hay usuario en sesión para verificar 2FA."}), 400

    try:
        # Validar el código 2FA
        result = validar_codigo_2fa(code)
        if result["authenticated"]:
            return jsonify({"message": "✅ Sesión iniciada correctamente con 2FA."}), 200
        else:
            return jsonify({"error": result["error"]}), 400
    except Exception as e:
        print(f"❌ Error al verificar el código 2FA: {e}")
        return jsonify({"error": f"❌ Error al verificar el código 2FA: {str(e)}"}), 400



def validar_codigo_2fa(code):
    """
    Valida el código 2FA proporcionado por el usuario.
    """
    try:
        print(f"🔑 Verificando código 2FA: {code}")
        cl.two_factor_login(code)  # Validar el código 2FA con Instagram
        print("✅ Código 2FA verificado correctamente.")
        return {"authenticated": True, "message": "Sesión iniciada correctamente con 2FA."}
    except Exception as e:
        print(f"❌ Error al verificar el código 2FA: {e}")
        return {"authenticated": False, "error": str(e)}




@app.route('/', methods=['GET', 'POST'])
def home():
    print("Accediendo a la ruta /")
    if current_user.is_authenticated:
        print("Usuario autenticado, redirigiendo a /bot")
        return redirect(url_for('iniciar_bot'))

    if request.method == 'POST':
        print("Solicitud POST recibida en /")
        return redirect(url_for('login'))

    print("Redirigiendo a /login desde /")
    return redirect(url_for('login'))



def autenticar_bot(username, password):
    """
    Maneja la autenticación inicial en Instagram, incluyendo el caso de 2FA.
    """
    try:
        print(f"🔐 Iniciando sesión en Instagram para @{username}...")
        cl.login(username, password)  # Intenta iniciar sesión
        return {"authenticated": True, "message": "✅ Sesión iniciada correctamente."}

    except TwoFactorRequired as e:
        print("⚠️ Se requiere 2FA para este usuario.")
        return {"2fa_required": True, "message": "⚠️ Se requiere autenticación 2FA. Ingresa el código."}

    except Exception as e:
        print(f"❌ Error al autenticar: {e}")
        raise

@app.route('/bot', methods=['POST'])
def iniciar_bot():
    """
    Maneja el inicio de sesión en Instagram desde el frontend.
    """
    try:
        username_instagram = request.form.get("username", "").strip()
        password_instagram = request.form.get("password", "").strip()

        if not username_instagram or not password_instagram:
            return jsonify({"error": "⚠️ Debes proporcionar las credenciales de Instagram."}), 400

        # Autenticación inicial
        result = autenticar_bot(username_instagram, password_instagram)

        if result.get("2fa_required"):
            session['instagram_user'] = username_instagram  # Guarda el usuario en sesión
            return jsonify({
                "2fa_required": True,
                "message": "⚠️ Se requiere autenticación 2FA. Ingresa el código."
            }), 200

        return jsonify({"message": "✅ Sesión iniciada correctamente en Instagram."}), 200

    except Exception as e:
        error_message = str(e)
        print(f"❌ Error al iniciar sesión en Instagram: {error_message}")
        return jsonify({"error": f"❌ Error al iniciar sesión: {error_message}"}), 400


@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        print("Accediendo a la ruta /register")
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            print(f"Registrando usuario: {username}")

            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

            if collection_users.find_one({"username": username}):
                print("El usuario ya existe")
                return render_template('register.html', error="El usuario ya existe")

            collection_users.insert_one({"username": username, "password": hashed_password})
            print("Registro exitoso")
            return redirect(url_for('login'))

        return render_template('register.html')
    except Exception as e:
        print(f"Error en /register: {e}")
        return render_template('register.html', error="Error interno del servidor.")

@app.route("/filtros", methods=["POST"])
def actualizar_filtros():
    try:
        data = request.get_json()
        print("Filtros recibidos:", data)
        db["filters"].update_one({}, {"$set": data}, upsert=True)
        return jsonify({"success": True, "message": "Filtros actualizados correctamente."})
    except Exception as e:
        print(f"Error al actualizar los filtros: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route("/iniciar_tarea", methods=["POST"])
def iniciar_tarea():
    try:
        # Extraer datos enviados en la solicitud
        datos = request.get_json()

        user_id = datos.get("user_id")
        username = datos.get("username")
        bio = datos.get("bio")  # Ya no es relevante para las tareas actuales
        intereses = datos.get("intereses")  # Ya no es relevante para las tareas actuales
        ultima_publicacion = datos.get("ultima_publicacion")
        tipo_tarea = datos.get("tipo_tarea")  # Tipo de tarea a ejecutar

        # Verificar los parámetros obligatorios
        if not user_id or not username or not tipo_tarea:
            return jsonify({"mensaje": "Faltan parámetros obligatorios."}), 400

        # Seleccionar y ejecutar la tarea correspondiente
        if tipo_tarea == "seguir_cuenta":
            tarea = seguir_cuenta.apply_async(args=[user_id, username])
        elif tipo_tarea == "comentar_perfil":
            tarea = comentar_perfil.apply_async(args=[user_id, username, ultima_publicacion])
        elif tipo_tarea == "procesar_usuario_completo":
            tarea = procesar_usuario_completo.apply_async(args=[user_id, username])
        else:
            return jsonify({"mensaje": "Tipo de tarea no válido."}), 400

        return jsonify({"mensaje": "Tarea iniciada", "id_tarea": tarea.id})
    except Exception as e:
        return jsonify({"mensaje": "Error al iniciar tarea", "error": str(e)}), 500




@app.route("/estado_tarea/<task_id>")
def estado_tarea(task_id):
    tarea = celery.AsyncResult(task_id)
    if tarea.state == "PENDING":
        return {"estado": "En espera"}
    elif tarea.state == "SUCCESS":
        return {"estado": "Completada", "resultado": tarea.result}
    elif tarea.state == "FAILURE":
        return {"estado": "Fallida", "error": str(tarea.info)}
    else:
        return {"estado": tarea.state}



# Función para leer mensajes desde los archivos
def obtener_mensaje_aleatorio(directorio):
    """
    Selecciona un mensaje aleatorio desde los archivos en un directorio.
    """
    mensajes = []
    try:
        for archivo in os.listdir(directorio):
            if archivo.endswith(".txt"):
                ruta_archivo = os.path.join(directorio, archivo)
                with open(ruta_archivo, "r", encoding="utf-8") as f:
                    mensajes.extend([linea.strip() for linea in f if linea.strip()])
        if mensajes:
            return random.choice(mensajes)
        else:
            raise ValueError("No se encontraron mensajes en los archivos.")
    except Exception as e:
        print(f"❌ Error al leer mensajes: {e}")
        raise

# Función para pausas aleatorias
def pausar_aleatorio(min_seg=45, max_seg=90):
    """
    Introduce una pausa aleatoria entre acciones para simular un comportamiento humano.
    """
    tiempo_espera = random.uniform(min_seg, max_seg)
    print(f"⏳ Pausando por {tiempo_espera:.2f} segundos...")
    time.sleep(tiempo_espera)

def generar_mensaje_personalizado(nombre, genero=None, bio=None, intereses=None, ultima_publicacion=None):
    """
    Genera un mensaje personalizado basado en los datos del destinatario.

    Args:
        nombre (str): Nombre real del destinatario.
        genero (str): Género del destinatario ('hombre' o 'mujer') (opcional).
        bio (str): Biografía del destinatario (opcional).
        intereses (list): Lista de intereses del destinatario (opcional).
        ultima_publicacion (str): Descripción o título de la última publicación del destinatario (opcional).

    Returns:
        str: Mensaje personalizado.
    """
    # Saludo basado en género
    if genero == "hombre":
        saludo = f"¡Hola, amigo {nombre}! 😊"
    elif genero == "mujer":
        saludo = f"¡Hola, amiga {nombre}! 😊"
    else:
        saludo = f"¡Hola, {nombre}! 😊"  # Saludo neutral

    # Construcción del mensaje
    mensaje = saludo + " "
    if bio:
        mensaje += f"Leí tu biografía y me parece interesante: '{bio}'. "
    if intereses:
        intereses_formateados = ", ".join(intereses)
        mensaje += f"¡Qué genial que estés interesado/a en {intereses_formateados}! "
    if ultima_publicacion:
        mensaje += f"Vi tu última publicación y me encantó: '{ultima_publicacion}'. "
    mensaje += "Espero que podamos conectar y compartir ideas. ¡Saludos! 🚀"

    return mensaje


def enviar_dm(instagram_username, instagram_password, user_id, nombre, genero=None, bio=None, intereses=None, ultima_publicacion=None):
    """
    Envía un mensaje directo (DM) personalizado a un usuario de Instagram.

    Args:
        instagram_username (str): Nombre de usuario de la cuenta que enviará el DM.
        instagram_password (str): Contraseña de la cuenta que enviará el DM.
        user_id (str): ID del usuario al que se enviará el DM.
        nombre (str): Nombre real del destinatario.
        genero (str): Género del destinatario ('hombre' o 'mujer') (opcional).
        bio (str): Biografía del usuario (opcional).
        intereses (list): Lista de intereses del usuario (opcional).
        ultima_publicacion (str): Descripción de la última publicación del usuario (opcional).

    Returns:
        dict: Resultado de la operación (éxito o fallo).
    """
    try:
        # Iniciar sesión en Instagram
        cl = Client()
        print("Intentando iniciar sesión en Instagram...")
        cl.login(instagram_username, instagram_password)
        print(f"✅ Sesión iniciada correctamente como {instagram_username}")

        # Generar mensaje personalizado
        mensaje = generar_mensaje_personalizado(nombre, genero, bio, intereses, ultima_publicacion)
        print(f"📝 Mensaje generado: {mensaje}")

        # Enviar el mensaje
        print(f"Intentando enviar mensaje directo a {nombre} (ID: {user_id})...")
        cl.direct_send(mensaje, [user_id])
        print(f"✅ Mensaje enviado exitosamente a {nombre} (ID: {user_id})")

        return {"status": "éxito", "mensaje": mensaje}
    except Exception as e:
        print(f"❌ Error al enviar DM a {nombre} (ID: {user_id}): {e}")
        return {"status": "fallo", "error": str(e)}



@app.route("/sugerencias", methods=["GET"])
def obtener_sugerencias_diarias():
    """
    Obtiene las sugerencias del día actual desde la base de datos.
    """
    try:
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        sugerencias = list(db["sugerencias_diarias"].find({"fecha": fecha_hoy}, {"_id": 0}))
        return jsonify({"success": True, "sugerencias": sugerencias})
    except Exception as e:
        print(f"Error al obtener sugerencias diarias: {e}")
        return jsonify({"success": False, "error": str(e)}), 5000


@app.route("/reportes", methods=["GET"])
def obtener_reportes():
    """
    Devuelve todos los reportes generados.
    """
    try:
        reportes = list(db["reportes"].find({}, {"_id": 0}))
        return jsonify({"success": True, "reportes": reportes})
    except Exception as e:
        print(f"Error al obtener reportes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/descargar_reporte_pdf')
def descargar_reporte_pdf():
    """
    Genera y descarga un reporte en formato PDF.
    """
    # Crear el contenido del PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte de Rendimiento", ln=True, align='C')

    # Agrega los datos del reporte (ejemplo)
    reportes = list(db["reportes"].find({}, {"_id": 0}))
    for reporte in reportes:
        pdf.cell(0, 10, txt=f"Fecha: {reporte['fecha']}", ln=True)
        pdf.cell(0, 10, txt=f"Usuarios Seguidos: {reporte['usuarios_seguidos']}", ln=True)
        pdf.cell(0, 10, txt=f"Mensajes Enviados: {reporte['mensajes_enviados']}", ln=True)
        pdf.cell(0, 10, txt=f"Respuestas Recibidas: {reporte['respuestas_recibidas']}", ln=True)
        pdf.cell(0, 10, txt=f"Tasa de Respuesta: {reporte['tasa_respuesta'] * 100:.2f}%", ln=True)
        pdf.cell(0, 10, txt=f"Seguidores Obtenidos: {reporte['seguidores_obtenidos']}", ln=True)
        pdf.cell(0, 10, txt="-----------------------------------", ln=True)

    # Devuelve el PDF como respuesta
    response = Response(pdf.output(dest='S').encode('latin1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=reporte_rendimiento.pdf'
    return response

@app.route('/descargar_reporte_csv')
def descargar_reporte_csv():
    """
    Genera y descarga un reporte en formato CSV.
    """
    # Crear el contenido del CSV
    output = StringIO()
    writer = csv.writer(output)

    # Encabezados del archivo CSV
    writer.writerow(['Fecha', 'Usuarios Seguidos', 'Mensajes Enviados', 'Respuestas Recibidas', 'Tasa de Respuesta (%)', 'Seguidores Obtenidos'])

    # Agregar los datos del reporte
    reportes = list(db["reportes"].find({}, {"_id": 0}))
    for reporte in reportes:
        writer.writerow([
            reporte['fecha'],
            reporte['usuarios_seguidos'],
            reporte['mensajes_enviados'],
            reporte['respuestas_recibidas'],
            f"{reporte['tasa_respuesta'] * 100:.2f}",
            reporte['seguidores_obtenidos']
        ])

    # Devuelve el CSV como respuesta
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=reporte_rendimiento.csv'
    return response

=======
        print("[DEBUG] Procesando solicitud POST en /login")

        username = request.form.get('username')
        password = request.form.get('password')

        print(f"[DEBUG] Credenciales recibidas: username={username}, password={'*' * len(password) if password else None}")

        if not username or not password:
            print("[DEBUG] Campos de login incompletos")
            return render_template('login.html', error="Todos los campos son obligatorios")

        # Buscar usuario en la base de datos
        user = collection_users.find_one({"username": username})
        if user and 'password' in user:
            if check_password_hash(user['password'], password):  # Contraseña correcta
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

    print("[DEBUG] Accediendo al formulario de login (GET)")
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            print(f"[DEBUG] Intentando registrar usuario: {username}")

            if not username or not password:
                return render_template('register.html', error="Todos los campos son obligatorios")

            if collection_users.find_one({"username": username}):
                print("[DEBUG] Usuario ya existe en la base de datos")
                return render_template('register.html', error="El usuario ya existe")

            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
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
                try:
                    seguidores_ids = obtener_seguidores_de_competencia(competencia, cantidad=10)
                    for seguidor_id in seguidores_ids:
                        info = cl.user_info(seguidor_id)
                        usuarios_seguidores.append({
                            "username": info.username,
                            "biography": info.biography or "Sin biografía",
                        })
                except Exception as e:
                    print(f"[DEBUG] Error al obtener seguidores de {competencia}: {e}")

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
        print("[DEBUG] Iniciando la función /procesar_accion")
        data = request.get_json()
        print(f"[DEBUG] Datos recibidos: {data}")

        user_id = data.get('user_id')  # ID del usuario
        action = data.get('action')   # Acción solicitada

        # Validar parámetros obligatorios
        if not user_id or not action:
            print("[DEBUG] Faltan parámetros obligatorios.")
            return jsonify({"success": False, "error": "Faltan parámetros obligatorios (user_id, action)."}), 400

        print(f"[DEBUG] Ejecutando acción '{action}' para el usuario {user_id}")

        # Validar y ejecutar la acción correspondiente
        if action == "like":
            print(f"[DEBUG] Ejecutando 'Dar Me Gusta' para {user_id}")
            dar_me_gusta_a_publicaciones(user_id)
        elif action == "comment":
            comentario = "Comentario automático"  # Personalizar mensaje si es necesario
            print(f"[DEBUG] Ejecutando 'Comentar' con mensaje: {comentario}")
            comentar_publicacion(user_id, comentario)
        elif action == "dm":
            mensaje = "Hola, gracias por seguirme. 😊"  # Personalizar mensaje si es necesario
            print(f"[DEBUG] Ejecutando 'Enviar DM' con mensaje: {mensaje}")
            enviar_dm(user_id, mensaje)
        elif action == "follow":
            print(f"[DEBUG] Ejecutando 'Seguir usuario' para {user_id}")
            seguir_usuario(user_id)
        else:
            print(f"[DEBUG] Acción no reconocida: {action}")
            return jsonify({"success": False, "error": "Acción no reconocida."}), 400

        # Responder con éxito
        return jsonify({"success": True, "message": f"Acción '{action}' realizada con éxito para @{user_id}."})

    except Exception as e:
        # Manejo de errores
        print(f"[DEBUG] Error al procesar la acción: {e}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500

@app.route('/aplicar_filtros', methods=['POST'])
def aplicar_filtros():
    try:
        print("[DEBUG] Procesando filtros enviados desde el frontend")

        competencias = request.form.get('competidores', '').split(',')
        competencias = [c.strip() for c in competencias if c.strip()]
        filtros = {
            "ubicaciones": request.form.get('ubicaciones', '').split(','),
            "palabras_clave": request.form.get('palabras_clave', '').split(','),
            "min_publicaciones": int(request.form.get('min_publicaciones', 0)),
            "min_seguidores": int(request.form.get('min_seguidores', 0)),
            "tipo_cuenta": request.form.get('tipo_cuenta', 'publica'),
        }

        usuarios_filtrados = []
        usuarios_con_errores = []

        if not competencias:
            print("[DEBUG] No se proporcionaron competencias válidas.")
            return jsonify({"success": False, "error": "Debes proporcionar al menos una competencia válida."}), 400

        print(f"[DEBUG] Competencias recibidas: {competencias}")
        print(f"[DEBUG] Filtros enviados: {filtros}")

        for competencia in competencias:
            print(f"[DEBUG] Procesando la competencia: {competencia}")
            try:
                seguidores_ids = obtener_seguidores_de_competencia(competencia, cantidad=1)
                print(f"[DEBUG] IDs de seguidores obtenidos para {competencia}: {seguidores_ids}")

                for seguidor_id in seguidores_ids:
                    try:
                        info = obtener_informacion_usuario(seguidor_id)
                        print(f"[DEBUG] Información obtenida del usuario {seguidor_id}: {info}")

                        if not info or "error" in info:
                            error_msg = info.get("error", "Información no disponible")

                            if "Please wait a few minutes before you try again" in error_msg:
                                print(f"[DEBUG] Bloqueo temporal detectado. Pausando 5 minutos.")
                                time.sleep(300)  # Esperar 5 minutos
                                usuarios_con_errores.append({"id": seguidor_id, "error": error_msg})
                                continue

                            print(f"[DEBUG] Error en usuario {seguidor_id}: {error_msg}")
                            usuarios_con_errores.append({"id": seguidor_id, "error": error_msg})
                            continue

                        if aplicar_filtros_individual(info, filtros):
                            print(f"[DEBUG] Usuario {info['username']} pasa los filtros.")
                            usuarios_filtrados.append(info)
                        else:
                            print(f"[DEBUG] Usuario {info['username']} no cumple los filtros.")
                            usuarios_con_errores.append({"id": seguidor_id, "error": "No cumple los filtros"})

                    except Exception as e:
                        print(f"[DEBUG] Error inesperado al procesar el usuario {seguidor_id}: {e}")
                        usuarios_con_errores.append({"id": seguidor_id, "error": str(e)})

            except Exception as e:
                print(f"[DEBUG] Error al obtener seguidores de la competencia {competencia}: {e}")
                usuarios_con_errores.append({"competencia": competencia, "error": str(e)})

        print(f"[DEBUG] Usuarios filtrados: {len(usuarios_filtrados)}")
        print(f"[DEBUG] Usuarios con errores: {len(usuarios_con_errores)}")

        return jsonify({
            "success": True,
            "users": usuarios_filtrados,
            "errors": usuarios_con_errores,
        })

    except Exception as e:
        print(f"[DEBUG] Error inesperado en aplicar_filtros: {e}")
        return jsonify({"success": False, "error": f"Error inesperado: {str(e)}"})


def obtener_informacion_usuario(user_id):
    try:
        # Obtener información básica del usuario desde el ID directamente
        print(f"[DEBUG] Obteniendo información básica para el ID: {user_id}")
        user_info = cl.user_info(user_id)  # Esto devuelve información básica del usuario

        # Validar que se obtuvo información
        if not user_info:
            print(f"[DEBUG] No se pudo obtener información para el ID: {user_id}")
            return None

        # Retornar la información del usuario
        return {
            "username": user_info.username,
            "biography": user_info.biography,
            "follower_count": user_info.follower_count,
            "media_count": user_info.media_count,
            "is_private": user_info.is_private,
        }
    except Exception as e:
        error_message = str(e)
        print(f"[DEBUG] Error inesperado al procesar el ID {user_id}: {error_message}")
        return {"id": user_id, "error": error_message}


@app.route('/cargar_mas_usuarios', methods=['POST'])
def cargar_mas_usuarios():
    try:
        competencia = request.form.get('competencia')
        if not competencia:
            return jsonify({"success": False, "error": "No se proporcionó una cuenta de competencia."})

        filtros = {
            "ubicaciones": request.form.get('ubicaciones', '').split(','),
            "palabras_clave": request.form.get('palabras_clave', '').split(','),
            "min_publicaciones": int(request.form.get('min_publicaciones', 0)),
            "min_seguidores": int(request.form.get('min_seguidores', 0)),
            "tipo_cuenta": request.form.get('tipo_cuenta', 'publica'),
        }

        usuarios_filtrados = []
        cantidad_procesada = 0
        cantidad_necesaria = 5

        while len(usuarios_filtrados) < cantidad_necesaria and cantidad_procesada < 100:
            seguidores_ids = obtener_seguidores_de_competencia(competencia, cantidad=10)
            cantidad_procesada += len(seguidores_ids)

            for seguidor_id in seguidores_ids:
                try:
                    info = cl.user_info(seguidor_id)
                    usuario = {
                        "username": info.username,
                        "biography": info.biography or "Sin biografía",
                        "follower_count": info.follower_count,
                        "media_count": info.media_count,
                        "is_private": info.is_private,
                    }
                    if aplicar_filtros_individual(usuario, filtros):
                        usuarios_filtrados.append(usuario)
                        if len(usuarios_filtrados) >= cantidad_necesaria:
                            break
                except Exception as e:
                    print(f"[DEBUG] Error al procesar usuario {seguidor_id}: {e}")

        return jsonify({"success": True, "users": usuarios_filtrados})

    except Exception as e:
        print(f"[DEBUG] Error al cargar más usuarios: {e}")
        return jsonify({"success": False, "error": str(e)})


>>>>>>> 3f8b5aa (mejoras)
if __name__ == "__main__":
    print("Iniciando la aplicación Flask...")
    app.run(debug=True)
