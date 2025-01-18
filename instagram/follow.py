import random
import time
<<<<<<< HEAD
from datetime import datetime
from database.models import collection_seguidos
from instagram.session import cl
from json.decoder import JSONDecodeError
from database.models import registrar_accion


# Configuración de límites y horarios
LIMITES_ACCIONES = {
    "likes": 30  # Máximo "me gusta" diarios
=======
import os
from datetime import datetime
from database.models import registrar_accion
from instagram.session import cl
from json.decoder import JSONDecodeError
from openai_utils import extraer_nombre_apodo
from instagram.session import autenticar_bot, reautenticar_sesion, verificar_autenticacion
from instagrapi.exceptions import LoginRequired

# Configuración de límites y horarios
LIMITES_ACCIONES = {
    "likes": 30,  # Máximo "me gusta" diarios
    "comments": 20,  # Máximo comentarios diarios
    "follows": 50,  # Máximo seguimientos diarios
>>>>>>> 3f8b5aa (mejoras)
}
HORA_INICIO = 9
HORA_FIN = 23

<<<<<<< HEAD
tiempo_pausa_prolongada = 3600  # 1 hora después de 10 "me gusta"
likes_realizados = 0

=======
tiempo_pausa_prolongada = 3600  # 1 hora después de ciertas acciones
UPLOAD_FOLDER = "./uploads"
>>>>>>> 3f8b5aa (mejoras)
# Funciones auxiliares
def delay_aleatorio(min_seg=30, max_seg=60):
    """Introduce un delay más largo para evitar bloqueos."""
    tiempo = random.uniform(min_seg, max_seg)
    print(f"Esperando {tiempo:.2f} segundos...")
    time.sleep(tiempo)

def dentro_de_horario():
    """Verifica si la hora actual está dentro del horario permitido."""
    hora_actual = datetime.now().hour
    return HORA_INICIO <= hora_actual < HORA_FIN

<<<<<<< HEAD
def verificar_limite_likes():
    """Verifica si el límite de likes se ha alcanzado."""
    return likes_realizados < LIMITES_ACCIONES["likes"]

def registrar_like():
    """Registra un like realizado."""
    global likes_realizados
    likes_realizados += 1

=======
def verificar_limite_accion(accion):
    """Verifica si el límite de una acción específica se ha alcanzado."""
    return registrar_accion.cuenta_acciones(accion) < LIMITES_ACCIONES[accion]

# Funciones principales de acciones
>>>>>>> 3f8b5aa (mejoras)
def dar_me_gusta_a_publicaciones(user_id):
    try:
        publicaciones = cl.user_medias(user_id, amount=1)
        if publicaciones:
            publicacion_id = publicaciones[0].id
            cl.media_like(publicacion_id)
            registrar_accion(user_id, "me_gusta", {"publicacion_id": publicacion_id})
            print(f"✅ 'Me gusta' dado a la publicación {publicacion_id}.")
    except Exception as e:
        print(f"❌ Error al dar 'me gusta': {e}")

<<<<<<< HEAD

def ver_historias_de_usuario(user_id):
    try:
        historias = cl.user_stories(user_id)
        if historias:
            for historia in historias:
                historia_id = historia.id

                # Verificar y registrar la acción
                cl.story_view(historia_id)
                registrar_accion(user_id, "ver_historia", {"historia_id": historia_id})
                print(f"✅ Historia {historia_id} vista.")
    except Exception as e:
        print(f"❌ Error al ver historias: {e}")

def procesar_usuario(user_id):
    """
    Procesa un usuario para dar 'me gusta' a sus publicaciones y ver sus historias.
    Args:
        user_id (str): ID del usuario a procesar.
    """
    try:
        if dentro_de_horario() and verificar_limite_likes():
            # Introducir pausa antes de procesar el usuario
            delay_aleatorio(30, 60)

            # Dar "me gusta" a las publicaciones
            dar_me_gusta_a_publicaciones(user_id)

            # Introducir pausa antes de ver historias
            delay_aleatorio(10, 30)

            # Ver historias del usuario
            ver_historias_de_usuario(user_id)
        else:
            print(f"⏳ Fuera del horario permitido o se alcanzaron los límites. Usuario {user_id} no procesado.")
    except Exception as e:
        print(f"❌ Error al procesar el usuario {user_id}: {e}")

def procesar_seguidores(seguidores):
    """
    Procesa una lista de seguidores para dar 'me gusta' y ver historias.
    Args:
        seguidores (list): Lista de `user_id` de los seguidores.
    """
    for user_id in seguidores:
        try:
            print(f"Procesando seguidor con ID: {user_id}")
            procesar_usuario(user_id)  # Utiliza la función para dar "me gusta" y ver historias
        except Exception as e:
            print(f"❌ Error al procesar seguidor {user_id}: {e}")

def obtener_seguidores_de_competencia(username, cantidad=10):
    """
    Obtiene una lista de seguidores de un usuario de la competencia.
    """
    try:
        user_id = cl.user_id_from_username(username)
        print(f"Obtenido user_id para la competencia {username}: {user_id}")

        seguidores = cl.user_followers(user_id, amount=cantidad)
        print(f"Seguidores obtenidos de {username}: {len(seguidores)} usuarios.")
        return list(seguidores.keys())

    except JSONDecodeError:
        print(f"❌ Error: Instagram devolvió una respuesta no válida (posiblemente HTML).")
    except Exception as e:
        print(f"❌ Error al obtener seguidores de {username}: {e}")
        return []

=======
def comentar_publicacion(user_id, comentario):
    try:
        publicaciones = cl.user_medias(user_id, amount=1)
        if publicaciones:
            publicacion_id = publicaciones[0].id
            cl.media_comment(publicacion_id, comentario)
            registrar_accion(user_id, "comentario", {"publicacion_id": publicacion_id, "comentario": comentario})
            print(f"✅ Comentario realizado en la publicación {publicacion_id}.")
    except Exception as e:
        print(f"❌ Error al comentar: {e}")

def enviar_dm(user_id, mensaje):
    try:
        cl.direct_send(mensaje, [user_id])
        registrar_accion(user_id, "dm", {"mensaje": mensaje})
        print(f"✅ Mensaje enviado a {user_id}.")
    except Exception as e:
        print(f"❌ Error al enviar DM: {e}")

def seguir_usuario(user_id):
    try:
        cl.user_follow(user_id)
        registrar_accion(user_id, "seguir", {})
        print(f"✅ Usuario {user_id} seguido correctamente.")
    except Exception as e:
        print(f"❌ Error al seguir usuario: {e}")
def leer_mensajes_desde_txt():
    """Lee los mensajes desde los archivos TXT en la carpeta configurada."""
    mensajes = []
    try:
        for archivo in os.listdir(UPLOAD_FOLDER):
            if archivo.endswith(".txt"):
                ruta = os.path.join(UPLOAD_FOLDER, archivo)
                with open(ruta, "r", encoding="utf-8") as f:
                    mensajes.extend([linea.strip() for linea in f if linea.strip()])
        return mensajes
    except Exception as e:
        print(f"Error al leer mensajes desde TXT: {e}")
        return ["Espero que estés bien 😊."]

def generar_mensaje_personalizado(username, bio=None):
    """Genera un mensaje personalizado comenzando por el nombre del usuario."""
    nombre, genero = extraer_nombre_apodo(username, bio)

    # Si no hay nombre, usar el nombre de usuario como referencia
    if not nombre:
        nombre = username

    # Seleccionar mensaje aleatorio
    mensajes = leer_mensajes_desde_txt()
    mensaje_aleatorio = random.choice(mensajes)

    # Construir mensaje personalizado
    mensaje_personalizado = f"{nombre}, {mensaje_aleatorio}"
    print(f"Mensaje personalizado generado: {mensaje_personalizado}")
    return mensaje_personalizado

def enviar_mensaje_personalizado(user_id, username, bio=None):
    """Envía un mensaje personalizado a un usuario de Instagram."""
    try:
        mensaje = generar_mensaje_personalizado(username, bio)
        cl.direct_send(mensaje, [user_id])
        registrar_accion(user_id, "dm", {"mensaje": mensaje})
        print(f"✅ Mensaje enviado exitosamente a @{username}: {mensaje}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar mensaje a @{username}: {e}")
        return False


# Función genérica para ejecutar acciones
def ejecutar_accion(user_id, accion, **kwargs):
    if not dentro_de_horario():
        return {"success": False, "error": "Fuera del horario permitido."}

    if not verificar_limite_accion(accion):
        return {"success": False, "error": f"Límite diario alcanzado para {accion}."}

    try:
        if accion == "like":
            dar_me_gusta_a_publicaciones(user_id)
        elif accion == "comment":
            comentario = kwargs.get("comentario", "Comentario genérico.")
            comentar_publicacion(user_id, comentario)
        elif accion == "dm":
            enviar_mensaje_personalizado(user_id, kwargs.get("username"), kwargs.get("bio"))
        elif accion == "follow":
            seguir_usuario(user_id)
        else:
            return {"success": False, "error": "Acción no reconocida."}

        return {"success": True, "message": f"Acción '{accion}' ejecutada correctamente."}

    except Exception as e:
        return {"success": False, "error": str(e)}

def obtener_seguidores_de_competencia(username, cantidad=1):  # Por defecto 1 seguidor
    try:
        if not verificar_autenticacion():
            print("⚠️ Sesión no válida. Reautenticando...")
            reautenticar_sesion()

        user_id = cl.user_id_from_username(username)
        print(f"🔍 User ID obtenido para la competencia {username}: {user_id}")

        seguidores = cl.user_followers(user_id, amount=cantidad)
        print(f"✅ {len(seguidores)} seguidores obtenidos de {username}.")
        return list(seguidores.keys())[:1]  # Retorna solo el primer seguidor
    except Exception as e:
        print(f"❌ Error al obtener seguidores de {username}: {e}")
        return []
>>>>>>> 3f8b5aa (mejoras)
