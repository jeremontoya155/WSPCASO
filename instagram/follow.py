import random
import time
from datetime import datetime
from database.models import collection_seguidos
from instagram.session import cl
from json.decoder import JSONDecodeError
from database.models import registrar_accion


# Configuración de límites y horarios
LIMITES_ACCIONES = {
    "likes": 30  # Máximo "me gusta" diarios
}
HORA_INICIO = 9
HORA_FIN = 23

tiempo_pausa_prolongada = 3600  # 1 hora después de 10 "me gusta"
likes_realizados = 0

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

def verificar_limite_likes():
    """Verifica si el límite de likes se ha alcanzado."""
    return likes_realizados < LIMITES_ACCIONES["likes"]

def registrar_like():
    """Registra un like realizado."""
    global likes_realizados
    likes_realizados += 1

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

