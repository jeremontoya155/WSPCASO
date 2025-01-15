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
    print(f"Cargando usuario con ID: {user_id}")
    user = collection_users.find_one({"username": user_id})
    if user:
        print(f"Usuario encontrado: {user}")
        return User(id=user["username"])
    print("Usuario no encontrado")
    return None

# Ruta principal
@app.route('/index')
def index():
    print("Accediendo a la ruta /index")
    if 'user' not in session:
        print("Usuario no autenticado, redirigiendo a /login")
        return redirect('/login')
    print(f"Usuario autenticado: {session['user']}")
    return render_template('index.html', username=session['user'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
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

if __name__ == "__main__":
    print("Iniciando la aplicación Flask...")
    app.run(debug=True)
