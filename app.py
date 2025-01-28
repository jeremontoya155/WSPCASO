from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, has_request_context
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user
from config import UPLOAD_FOLDER, LOG_FOLDER
from database.models import collection_users, collection_acciones
from instagrapi import Client
from instagram.follow import ejecutar_acciones_para_usuario, procesar_respuesta, usuarios_procesados, procesar_seguidores_por_lotes
from instagram.session import autenticar_con_2fa, reautenticar_sesion
from instagram.config_bot import  PAUSA_ENTRE_USUARIOS, acciones_aleatorias, cargar_usuarios_privados, guardar_usuarios_privados, guardar_usuarios_procesados
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
from json.decoder import JSONDecodeError
from instagrapi.exceptions import LoginRequired, TwoFactorRequired
import time
from functools import wraps
from openai_utils import generar_mensaje_ia, detectar_genero
from instagram.filters import filtrar_usuarios
from datetime import datetime, timedelta

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
        from datetime import datetime, timedelta
        import random
        import time

        print("[DEBUG] Iniciando el procesamiento de usuarios con un límite de tiempo...")

        # Cargar usuarios de la sesión
        usuarios = session.get('usuarios_seguidores', [])
        print(f"[DEBUG] Usuarios en la sesión antes del procesamiento: {len(usuarios)}")

        if not usuarios:
            return jsonify({"success": False, "error": "No hay usuarios para procesar."})

        # Configuración para el tiempo límite
        duracion_horas = 6  # Tiempo total de procesamiento
        tiempo_limite = datetime.now() + timedelta(hours=duracion_horas)

        usuarios_procesados = []
        usuarios_fallidos = []  # Lista para registrar usuarios que fallaron

        while datetime.now() < tiempo_limite:
            if not usuarios:
                print("[DEBUG] No quedan usuarios por procesar.")
                break

            # Procesar usuarios uno por uno
            usuario = usuarios.pop(0)

            try:
                user_id = usuario.get("id", None)
                username = usuario.get("username", f"Usuario_{user_id if user_id else 'desconocido'}")
                print(f"🔍 [DEBUG] Procesando usuario: {username}")

                # Validar si el usuario tiene un ID válido
                if not user_id:
                    print(f"⚠️ Usuario sin ID detectado: {username}. Saltando...")
                    continue

                # Asignar acciones aleatorias al usuario
                usuario["acciones"] = acciones_aleatorias()
                print(f"✅ Acciones asignadas al usuario {username}: {usuario['acciones']}")

                # Ejecutar las acciones para el usuario
                ejecutar_acciones_para_usuario(usuario)
                usuarios_procesados.append(usuario)

                # Actualizar la sesión con los usuarios restantes
                session['usuarios_seguidores'] = usuarios
                session.modified = True  # Asegurar que los cambios en la sesión se guarden

                # Pausa entre usuarios
                pausa_usuario = random.uniform(600, 900)  # 10-15 minutos
                print(f"⏳ Pausando {pausa_usuario / 60:.2f} minutos antes del próximo usuario...")
                time.sleep(pausa_usuario)

            except Exception as e:
                print(f"❌ [DEBUG] Error al procesar usuario {username}: {e}")
                usuarios_fallidos.append({"id": user_id, "username": username, "error": str(e)})
                continue  # Continuar con el siguiente usuario en caso de error

            # Verificar tiempo restante
            tiempo_restante = (tiempo_limite - datetime.now()).total_seconds()
            print(f"[DEBUG] Tiempo restante para procesar: {tiempo_restante / 3600:.2f} horas.")
            if tiempo_restante <= 0:
                print("[DEBUG] Tiempo límite alcanzado. Finalizando procesamiento.")
                break

        # Guardar usuarios procesados en el archivo
        guardar_usuarios_procesados()
        print("[DEBUG] Proceso finalizado. Usuarios procesados guardados.")

        # Log de usuarios fallidos (opcional)
        if usuarios_fallidos:
            print(f"⚠️ Usuarios fallidos: {len(usuarios_fallidos)}")
            with open("usuarios_fallidos.log", "a") as log_file:
                for usuario in usuarios_fallidos:
                    log_file.write(f"{datetime.now()} | {usuario}\n")

        return jsonify({
            "success": True,
            "processed_users": [u['username'] for u in usuarios_procesados],
            "failed_users": len(usuarios_fallidos),
            "remaining_users": len(usuarios),
            "message": f"Se procesaron {len(usuarios_procesados)} usuarios. {len(usuarios_fallidos)} fallaron. {len(usuarios)} restantes."
        })

    except Exception as e:
        print(f"❌ [DEBUG] Error durante el procesamiento: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/acciones', methods=['GET', 'POST'])
def acciones():
    print("[DEBUG] Iniciando la función /acciones")

    # Verificar si el usuario está autenticado al inicio
    if 'user' not in session:
        print("[DEBUG] Usuario no autenticado. Redirigiendo a /login")
        return redirect('/login')

    if request.method == 'POST':
        try:
            from datetime import datetime, timedelta
            import random
            import time

            # Obtener usuarios de competencia y configuración inicial
            competencias = request.form.get('competencia', '')
            print(f"[DEBUG] Competencias recibidas en el formulario: {competencias}")

            competencias = [c.strip() for c in competencias.split(',') if c.strip()]
            if not competencias:
                print("[DEBUG] No se proporcionaron competencias válidas.")
                return jsonify({"success": False, "error": "Debes proporcionar al menos un usuario de competencia."}), 400

            duracion_horas = 6  # Tiempo máximo de ejecución
            tiempo_limite = datetime.now() + timedelta(hours=duracion_horas)
            usuarios_procesados = set()

            # Generar respuesta progresiva
            def generar_respuesta():
                usuarios_seguidores = []
                for competencia in competencias:
                    print(f"[DEBUG] Procesando la competencia: {competencia}")

                    # Usar la versión mejorada de procesar_seguidores_por_lotes
                    seguidores = procesar_seguidores_por_lotes(competencia, cantidad_por_lote=120)

                    if not seguidores:
                        print(f"[DEBUG] No se encontraron seguidores para {competencia}.")
                        continue

                    for seguidor_id, _ in seguidores.items():
                        if datetime.now() >= tiempo_limite:
                            print("⏰ Tiempo límite alcanzado. Deteniendo procesamiento.")
                            break

                        if seguidor_id in usuarios_procesados:
                            print(f"⚠️ Usuario ya procesado detectado: {seguidor_id}. Saltando...")
                            continue

                        try:
                            # Obtener información detallada del usuario
                            info = obtener_informacion_usuario(seguidor_id)
                            usuario = {
                                "id": seguidor_id,
                                "username": info.get("username", f"Usuario_{seguidor_id}"),
                                "biography": info.get("biography", "No disponible"),
                                "follower_count": info.get("follower_count", 0),
                                "media_count": info.get("media_count", 0),
                                "is_private": info.get("is_private", False)
                            }

                            # Filtrar cuentas privadas o incompletas
                            if usuario["is_private"]:
                                print(f"⚠️ Usuario privado detectado: {usuario['username']}. Saltando...")
                                continue

                            # Asignar acciones aleatorias
                            usuario["acciones"] = acciones_aleatorias()
                            print(f"✅ Acciones asignadas a {usuario['username']}: {usuario['acciones']}")

                            # Ejecutar acciones para el usuario
                            ejecutar_acciones_para_usuario(usuario)
                            usuarios_seguidores.append(usuario)
                            usuarios_procesados.add(seguidor_id)

                            # Enviar datos parciales al cliente
                            yield f"✅ Procesado usuario: {usuario['username']} con acciones: {usuario['acciones']}<br>"

                            # Pausa entre usuarios
                            pausa_usuario = random.uniform(600, 900)  # 10-15 minutos
                            print(f"⏳ Pausando {pausa_usuario / 60:.2f} minutos antes del próximo usuario...")
                            time.sleep(pausa_usuario)

                        except Exception as e:
                            print(f"❌ Error al procesar usuario {seguidor_id}: {e}")
                            yield f"❌ Error al procesar usuario: {seguidor_id}<br>"

                print("[DEBUG] Procesamiento completo.")
                yield "✅ Procesamiento completado.<br>"

            return Response(generar_respuesta(), content_type='text/html')

        except Exception as e:
            print(f"[DEBUG] Error en el procesamiento de /acciones: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # Renderizar la página si es una solicitud GET
    usuarios_seguidores = session.get('usuarios_seguidores', [])
    print(f"[DEBUG] Usuarios seguidores en sesión: {len(usuarios_seguidores)}")
    return render_template('Acciones.html', users=usuarios_seguidores)

@app.route('/aplicar_filtros', methods=['POST'])
def aplicar_filtros():
    """
    Procesa usuarios según los filtros enviados desde el frontend y ajusta el tiempo de trabajo del bot.
    """
    try:
        from datetime import datetime, timedelta
        import random
        import time

        print("[DEBUG] Procesando filtros enviados desde el frontend")

        # Obtener los datos del formulario
        competencias_raw = request.form.get('competidores', '')
        duracion_horas = int(request.form.get('duracion', 6))  # Duración por defecto: 6 horas
        min_publicaciones = int(request.form.get('min_publicaciones', 1))
        min_seguidores = int(request.form.get('min_seguidores', 0))  # Ahora opcional

        competencias = [c.strip() for c in competencias_raw.split(',') if c.strip()]

        if not competencias:
            return jsonify({"success": False, "error": "Debes proporcionar al menos una competencia válida."}), 400

        # Configuración del tiempo límite
        tiempo_limite = datetime.now() + timedelta(hours=duracion_horas)
        print(f"[DEBUG] Tiempo límite configurado: {tiempo_limite}")

        usuarios_procesados = set()  # Almacenar IDs de usuarios procesados

        # Procesamiento de usuarios
        while datetime.now() < tiempo_limite:
            print("[DEBUG] Iniciando procesamiento de usuarios...")

            for competencia in competencias:
                print(f"[DEBUG] Procesando competencia: {competencia}")

                # Usar la versión mejorada de procesar_seguidores_por_lotes
                seguidores = procesar_seguidores_por_lotes(competencia, cantidad_por_lote=120)

                if not seguidores:
                    print(f"[DEBUG] No se encontraron seguidores para {competencia}.")
                    continue

                # Usar la función filtrar_usuarios optimizada
                usuarios_filtrados = filtrar_usuarios(seguidores, min_publicaciones=min_publicaciones)
                print(f"[DEBUG] Usuarios filtrados: {len(usuarios_filtrados)}")

                for usuario in usuarios_filtrados:
                    user_id = usuario.get("id")
                    username = usuario.get("username", f"Usuario_{user_id if user_id else 'desconocido'}")

                    if user_id in usuarios_procesados:
                        print(f"⚠️ Usuario ya procesado: {username}. Saltando...")
                        continue

                    try:
                        # Asignar acciones aleatorias al usuario
                        usuario["acciones"] = acciones_aleatorias()
                        print(f"✅ Acciones asignadas a {username}: {usuario['acciones']}")

                        # Ejecutar acciones para el usuario
                        ejecutar_acciones_para_usuario(usuario)
                        usuarios_procesados.add(user_id)
                        print(f"✅ Usuario procesado: {username}")

                        # Pausa entre usuarios
                        pausa_usuario = random.uniform(10 * 60, 15 * 60)  # 10-15 minutos
                        print(f"⏳ Pausando {pausa_usuario / 60:.2f} minutos antes del próximo usuario...")
                        time.sleep(pausa_usuario)

                    except Exception as e:
                        print(f"❌ Error al procesar usuario {username}: {e}")

            # Verificar tiempo restante en cada iteración
            if datetime.now() >= tiempo_limite:
                print("[DEBUG] Tiempo límite alcanzado. Finalizando procesamiento.")
                break

        print("[DEBUG] Procesamiento completo.")
        return jsonify({"success": True, "message": "Procesamiento completo."})

    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/responder', methods=['POST'])
def responder():
    try:
        datos = request.json
        user_id = datos.get("user_id")
        mensaje_usuario = datos.get("mensaje_usuario")
        tipo = datos.get("tipo", "dm")
        rol = datos.get("rol", "amigable")

        if not user_id or not mensaje_usuario:
            return jsonify({"success": False, "error": "Datos incompletos para procesar la respuesta."}), 400

        procesar_respuesta(user_id, mensaje_usuario, tipo, rol)
        return jsonify({"success": True, "message": "Respuesta procesada correctamente."})
    except Exception as e:
        print(f"❌ Error en el endpoint /responder: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def obtener_informacion_usuario(user_id):
    """
    Obtiene información de un usuario de Instagram por su ID y maneja errores.
    """
    try:
        print(f"🔍 Obteniendo información del usuario {user_id}")
        user_info = cl.user_info(user_id)
        return {
            "id": user_id,
            "username": user_info.get("username", f"Usuario_{user_id}"),
            "biography": user_info.get("biography", "No disponible"),
            "follower_count": user_info.get("follower_count", 0),
            "media_count": user_info.get("media_count", 0),
            "is_private": user_info.get("is_private", False),
        }
    except Exception as e:
        print(f"❌ Error al obtener información del usuario {user_id}: {e}")
        # Intentar reautenticar si es un problema de sesión
        if "LoginRequired" in str(e):
            print("⚠️ La sesión no es válida. Intentando reautenticación...")
            if reautenticar_sesion():
                return obtener_informacion_usuario(user_id)
        return {"id": user_id, "username": f"Usuario_{user_id}", "error": str(e)}

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



@app.route('/metrics', methods=['GET'])
def get_metrics():
    """
    Devuelve métricas desglosadas por tipo de acción realizada.
    """
    import logging

    # Deshabilitar logs temporalmente
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    try:
        # Recuperar los conteos de cada acción desde la base de datos
        acciones = {
            "seguir_usuario": collection_acciones.count_documents({"accion": "seguir"}),
            "dar_me_gusta_a_publicaciones": collection_acciones.count_documents({"accion": "me_gusta"}),
            "comentar_publicacion": collection_acciones.count_documents({"accion": "comentario"}),
            "enviar_dm": collection_acciones.count_documents({"accion": "dm"}),
            "ver_historias": collection_acciones.count_documents({"accion": "view_story"})
        }

        # Estado del bot
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

    finally:
        # Volver a habilitar logs
        logging.getLogger('werkzeug').setLevel(logging.INFO)

    
@app.route("/chatgpt", methods=["POST"])
def chatgpt():
    datos = request.json
    mensaje_usuario = datos.get("mensaje", "")
    rol = datos.get("rol", "amigable")  # Valor por defecto
    nombre = datos.get("nombre")  # Obtener el nombre si está disponible
    username = datos.get("username")  # Obtener el username si está disponible

    if not mensaje_usuario:
        return jsonify({"respuesta": "No se recibió ningún mensaje."}), 400

    try:
        # Construir saludo personalizado
        saludo = nombre if nombre else detectar_genero(username)

        # Generar mensaje con el rol proporcionado
        respuesta = generar_mensaje_ia(
            username=saludo,  # Usar el nombre o "amigo/amiga"
            bio=None,
            intereses=None,
            ultima_publicacion=mensaje_usuario,
            rol=rol
        )
        return jsonify({"respuesta": respuesta})
    except Exception as e:
        return jsonify({"respuesta": f"Error al procesar el mensaje: {e}"}), 500


if __name__ == "__main__":
    cargar_usuarios_privados()
    try:
        # Código principal
        app.run(debug=True)
    finally:
        guardar_usuarios_privados()
