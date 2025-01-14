import random
import time
from datetime import datetime
from celery_app import celery
from openai_utils import enviar_mensaje_personalizado, generar_mensaje_ia
from instagrapi import Client
from instagrapi.exceptions import ClientError

# Instancia del cliente de Instagram
cl = Client()

# Configuración de límites diarios y horarios
LIMITES_DIARIOS = {
    "seguir": 200,
    "dm": 50,
    "comentar": 30
}
acciones_realizadas = {
    "seguir": 0,
    "dm": 0,
    "comentar": 0
}

HORA_INICIO = 9
HORA_FIN = 23

def dentro_de_horario():
    """Verifica si la hora actual está dentro del horario permitido."""
    hora_actual = datetime.now().hour
    return HORA_INICIO <= hora_actual < HORA_FIN

def pausar_aleatorio(min_seg=30, max_seg=60):
    """Introduce una pausa aleatoria entre acciones."""
    tiempo_espera = random.uniform(min_seg, max_seg)
    print(f"Esperando {tiempo_espera:.2f} segundos...")
    time.sleep(tiempo_espera)

@celery.task(name="seguir_cuenta")
def seguir_cuenta(user_id, username):
    """
    Tarea para seguir a un usuario en Instagram, respetando límites diarios.
    """
    if acciones_realizadas["seguir"] >= LIMITES_DIARIOS["seguir"]:
        print("Límite diario de seguimientos alcanzado. No se realizarán más acciones hoy.")
        return {"username": username, "status": "fallo", "error": "Límite diario alcanzado."}

    if not dentro_de_horario():
        print("⏳ Fuera del horario permitido. No se realizarán acciones.")
        return {"username": username, "status": "fallo", "error": "Fuera del horario permitido."}

    try:
        cl.user_follow(user_id)
        acciones_realizadas["seguir"] += 1
        print(f"✅ Se siguió exitosamente a @{username}.")

        # Pausa aleatoria
        pausar_aleatorio()
        return {"username": username, "status": "éxito"}
    except ClientError as e:
        return {"username": username, "status": "fallo", "error": f"Error en la API de Instagram: {e}"}
    except Exception as e:
        return {"username": username, "status": "fallo", "error": f"Error inesperado: {e}"}

@celery.task(name="enviar_dm_personalizado")
def enviar_dm_personalizado(user_id, username, bio=None, intereses=None, ultima_publicacion=None):
    """
    Tarea para enviar un mensaje directo personalizado a un usuario de Instagram.
    """
    if acciones_realizadas["dm"] >= LIMITES_DIARIOS["dm"]:
        print("Límite diario de mensajes directos alcanzado.")
        return {"username": username, "status": "fallo", "error": "Límite diario alcanzado."}

    if not dentro_de_horario():
        print("⏳ Fuera del horario permitido. No se realizarán acciones.")
        return {"username": username, "status": "fallo", "error": "Fuera del horario permitido."}

    try:
        resultado = enviar_mensaje_personalizado(user_id, username, bio, intereses, ultima_publicacion)
        acciones_realizadas["dm"] += 1
        pausar_aleatorio()
        return {"username": username, "status": "éxito" if resultado else "fallo"}
    except Exception as e:
        return {"username": username, "status": "fallo", "error": f"Error inesperado: {e}"}

@celery.task(name="comentar_perfil")
def comentar_perfil(user_id, username, ultima_publicacion=None):
    """
    Tarea para realizar un comentario en el perfil de un usuario.
    """
    if acciones_realizadas["comentar"] >= LIMITES_DIARIOS["comentar"]:
        print("Límite diario de comentarios alcanzado.")
        return {"username": username, "status": "fallo", "error": "Límite diario alcanzado."}

    if not dentro_de_horario():
        print("⏳ Fuera del horario permitido. No se realizarán acciones.")
        return {"username": username, "status": "fallo", "error": "Fuera del horario permitido."}

    try:
        comentario = generar_mensaje_ia(username, ultima_publicacion=ultima_publicacion)
        print(f"Generando comentario para @{username}: {comentario}")

        publicaciones = cl.user_medias(user_id, amount=1)
        if not publicaciones:
            return {"username": username, "status": "fallo", "error": "No se encontraron publicaciones."}

        media_id = publicaciones[0].id
        cl.media_comment(media_id, comentario)
        acciones_realizadas["comentar"] += 1
        pausar_aleatorio()
        return {"username": username, "status": "éxito", "comentario": comentario}
    except Exception as e:
        return {"username": username, "status": "fallo", "error": f"Error inesperado: {e}"}

@celery.task(name="procesar_usuario_completo")
def procesar_usuario_completo(user_id, username, bio=None, intereses=None, ultima_publicacion=None):
    """
    Tarea combinada para procesar a un usuario: seguir, enviar DM y comentar.
    """
    if not all([user_id, username]):
        return {"error": "Faltan parámetros obligatorios."}

    # Lista de tareas posibles para ejecutar
    tareas = [
        seguir_cuenta,
        enviar_dm_personalizado,
        comentar_perfil
    ]

    # Verificar límites antes de seleccionar una tarea
    if acciones_realizadas["seguir"] >= LIMITES_DIARIOS["seguir"]:
        tareas.remove(seguir_cuenta)
    if acciones_realizadas["dm"] >= LIMITES_DIARIOS["dm"]:
        tareas.remove(enviar_dm_personalizado)
    if acciones_realizadas["comentar"] >= LIMITES_DIARIOS["comentar"]:
        tareas.remove(comentar_perfil)

    if not tareas:
        return {"error": "Límites diarios alcanzados para todas las acciones."}

    # Seleccionar una tarea aleatoria
    tarea_seleccionada = random.choice(tareas)
    print(f"Ejecutando tarea: {tarea_seleccionada.__name__} para @{username}")

    # Ejecutar la tarea seleccionada
    if tarea_seleccionada == seguir_cuenta:
        return tarea_seleccionada(user_id, username)
    elif tarea_seleccionada == enviar_dm_personalizado:
        return tarea_seleccionada(user_id, username, bio, intereses, ultima_publicacion)
    elif tarea_seleccionada == comentar_perfil:
        return tarea_seleccionada(user_id, username, ultima_publicacion)
