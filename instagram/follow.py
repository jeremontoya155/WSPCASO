import random
import time
import os
from datetime import datetime
from database.models import registrar_accion
from instagram.session import cl
from json.decoder import JSONDecodeError
from openai_utils import extraer_nombre_apodo, enviar_mensaje_personalizado
from instagram.session import autenticar_bot, reautenticar_sesion, verificar_autenticacion
from instagrapi.exceptions import LoginRequired

# Configuración de límites y horarios
LIMITES_ACCIONES = {
    "likes": 30,  # Máximo "me gusta" diarios
    "comments": 20,  # Máximo comentarios diarios
    "follows": 50,  # Máximo seguimientos diarios
}
HORA_INICIO = 9
HORA_FIN = 23

tiempo_pausa_prolongada = 3600  # 1 hora después de ciertas acciones
UPLOAD_FOLDER = "./uploads"
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

def verificar_limite_accion(accion):
    """Verifica si el límite de una acción específica se ha alcanzado."""
    return registrar_accion.cuenta_acciones(accion) < LIMITES_ACCIONES[accion]

# Funciones principales de acciones
def dar_me_gusta_a_publicaciones(user_id):
    if not user_id:
        print("❌ Error: ID de usuario no válido para dar 'me gusta'.")
        return
    try:
        publicaciones = cl.user_medias(user_id, amount=1)
        if publicaciones:
            publicacion_id = publicaciones[0].id
            cl.media_like(publicacion_id)
            registrar_accion(user_id, "me_gusta", {"publicacion_id": publicacion_id})
            print(f"✅ 'Me gusta' dado a la publicación {publicacion_id}.")
        else:
            print(f"❌ No se encontraron publicaciones para el usuario {user_id}.")
    except Exception as e:
        print(f"❌ Error al dar 'me gusta' al usuario {user_id}: {e}")


def comentar_publicacion(user_id, username=None, bio=None):
    if not user_id:
        print("❌ Error: ID de usuario no válido para comentar.")
        return
    try:
        publicaciones = cl.user_medias(user_id, amount=1)
        if publicaciones:
            publicacion_id = publicaciones[0].id
            comentario = generar_mensaje_personalizado(username, bio)
            cl.media_comment(publicacion_id, comentario)
            registrar_accion(user_id, "comentario", {"publicacion_id": publicacion_id, "comentario": comentario})
            print(f"✅ Comentario realizado en la publicación {publicacion_id}: {comentario}")
        else:
            print(f"❌ No se encontraron publicaciones para el usuario {user_id}.")
    except Exception as e:
        print(f"❌ Error al comentar en la publicación del usuario {user_id}: {e}")


def enviar_dm(user_id, username=None, bio=None):
    if not user_id:
        print("❌ Error: ID de usuario no válido para enviar DM.")
        return
    try:
        mensaje = generar_mensaje_personalizado(username, bio)
        cl.direct_send(mensaje, [user_id])
        registrar_accion(user_id, "dm", {"mensaje": mensaje})
        print(f"✅ Mensaje enviado a {user_id}: {mensaje}")
    except Exception as e:
        print(f"❌ Error al enviar DM al usuario {user_id}: {e}")


def generar_mensaje_personalizado(username, bio=None):
    try:
        nombre, genero = extraer_nombre_apodo(username, bio)
        nombre = nombre or username  # Si no hay nombre, usar el username.

        mensajes = leer_mensajes_desde_txt()
        if not mensajes:
            mensajes = ["Espero que estés bien 😊."]

        mensaje_aleatorio = random.choice(mensajes)
        mensaje_personalizado = f"{nombre}, {mensaje_aleatorio}"
        print(f"Mensaje personalizado generado: {mensaje_personalizado}")
        return mensaje_personalizado
    except Exception as e:
        print(f"❌ Error al generar mensaje personalizado: {e}")
        return "Espero que estés bien 😊."


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

def seguir_usuario(user_id):
    """Sigue a un usuario en Instagram y registra la acción."""
    try:
        cl.user_follow(user_id)
        registrar_accion(user_id, "seguir", {})
        print(f"✅ Usuario {user_id} seguido correctamente.")
    except Exception as e:
        print(f"❌ Error al seguir al usuario {user_id}: {e}")


def obtener_seguidores_de_competencia(username, cantidad=1):
    if not username:
        print("❌ Error: Username no válido para obtener seguidores.")
        return []
    try:
        if not verificar_autenticacion():
            print("⚠️ Sesión no válida. Reautenticando...")
            reautenticar_sesion()

        user_id = cl.user_id_from_username(username)
        print(f"🔍 User ID obtenido para {username}: {user_id}")

        seguidores = cl.user_followers(user_id, amount=cantidad)
        seguidores_ids = list(seguidores.keys())
        print(f"✅ {len(seguidores_ids)} seguidores obtenidos de {username}.")
        return seguidores_ids[:cantidad]
    except JSONDecodeError as e:
        print(f"❌ Error al decodificar JSON para {username}: {e}")
    except Exception as e:
        print(f"❌ Error al obtener seguidores de {username}: {e}")
    return []


def ver_historias(user_id):
    if not user_id:
        print("❌ Error: ID de usuario no válido para ver historias.")
        return
    try:
        historias = cl.user_stories(user_id)
        if historias:
            for historia in historias:
                cl.story_view(historia.pk)
                registrar_accion(user_id, "view_story", {"story_id": historia.pk})
                print(f"✅ Historia vista: {historia.pk}")
        else:
            print(f"❌ No se encontraron historias para el usuario {user_id}.")
    except Exception as e:
        print(f"❌ Error al ver historias del usuario {user_id}: {e}")
