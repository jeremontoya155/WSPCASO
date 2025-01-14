from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, session
from flask_login import LoginManager, UserMixin, current_user
from config import UPLOAD_FOLDER, LOG_FOLDER
from instagrapi import Client
from database.models import db, registrar_usuario, collection_users, verificar_accion, registrar_accion 
from datetime import datetime
import os
from fpdf import FPDF
import csv
from io import StringIO
from werkzeug.security import generate_password_hash, check_password_hash
from instagram.filters import filtrar_usuarios
from instagram.follow import procesar_usuario, obtener_seguidores_de_competencia, procesar_seguidores
from celery_app import celery
from instagram.session import autenticar_bot
from tasks.celery_tasks import seguir_cuenta, enviar_dm_personalizado, comentar_perfil, procesar_usuario_completo

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

@app.route('/bot', methods=['POST'])
def iniciar_bot():
    try:
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("index.html", error="Debe proporcionar credenciales de Instagram.")

        autenticar_bot(username, password)

        competencia_raw = request.form.get("competencia", "").strip()
        cantidad_seguidores = int(request.form.get("cantidad_seguidores", "10").strip())
        competencia = [usuario.strip() for usuario in competencia_raw.split(",") if usuario.strip()]

        for usuario_competencia in competencia:
            print(f"Obteniendo seguidores de la competencia: {usuario_competencia}")
            seguidores = obtener_seguidores_de_competencia(usuario_competencia, cantidad_seguidores)

            for seguidor_id in seguidores:
                print(f"Procesando seguidor con ID: {seguidor_id}")

                if verificar_accion(seguidor_id, "procesado"):
                    print(f"ℹ️ El seguidor con ID {seguidor_id} ya fue procesado. Saltando.")
                    continue

                procesar_usuario(seguidor_id)

                registrar_accion(seguidor_id, "procesado", {"detalles": "Seguidor procesado por el bot."})

        return render_template("index.html", success="El bot procesó los seguidores correctamente.")
    except Exception as e:
        print(f"❌ Error al iniciar el bot: {e}")
        return render_template("index.html", error=f"Error: {e}")

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
        bio = datos.get("bio")
        intereses = datos.get("intereses")
        ultima_publicacion = datos.get("ultima_publicacion")
        tipo_tarea = datos.get("tipo_tarea")  # Tipo de tarea a ejecutar

        # Verificar los parámetros obligatorios
        if not user_id or not username or not tipo_tarea:
            return jsonify({"mensaje": "Faltan parámetros obligatorios."}), 400

        # Seleccionar y ejecutar la tarea correspondiente
        if tipo_tarea == "seguir_cuenta":
            tarea = seguir_cuenta.apply_async(args=[user_id, username])
        elif tipo_tarea == "enviar_dm_personalizado":
            tarea = enviar_dm_personalizado.apply_async(args=[user_id, username, bio, intereses, ultima_publicacion])
        elif tipo_tarea == "comentar_perfil":
            tarea = comentar_perfil.apply_async(args=[user_id, username, ultima_publicacion])
        elif tipo_tarea == "procesar_usuario_completo":
            tarea = procesar_usuario_completo.apply_async(args=[user_id, username, bio, intereses, ultima_publicacion])
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
