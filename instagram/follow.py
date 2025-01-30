import random
import time
from datetime import datetime
from instagram.config_bot import PAUSAS_POR_ACCION
from openai_utils import generar_mensaje_ia, construir_prompt
from instagram.session import  reautenticar_sesion, verificar_autenticacion, cl
from instagram.filters import filtrar_usuarios
import json
from flask import session, jsonify
from datetime import datetime, timedelta
from instagram.config_bot import PAUSAS_POR_ACCION, acciones_aleatorias


def obtener_seguidores(username, cantidad=120):
    """
    Obtiene una lista de seguidores de un usuario.
    """
    try:
        user_id = cl.user_id_from_username(username)
        seguidores = cl.user_followers(user_id, amount=cantidad)
        return list(seguidores.values())
    except Exception as e:
        print(f"❌ Error al obtener seguidores de @{username}: {e}")
        return []

def procesar_usuarios(username, duracion_horas=6, cantidad=120, pausa_entre_usuarios=(100, 450)):
    """
    Obtiene seguidores y ejecuta acciones con pausas.
    """
    print(f"[DEBUG] Iniciando procesamiento de seguidores para @{username}...")

    if not verificar_autenticacion():
        print("⚠️ Sesión no válida. Reintentando autenticación...")
        if not reautenticar_sesion():
            print("❌ Error: No se pudo reautenticar la sesión.")
            return {"success": False, "error": "No se pudo autenticar en Instagram."}

    tiempo_limite = datetime.now() + timedelta(hours=duracion_horas)

    seguidores = obtener_seguidores(username, cantidad)
    if not seguidores:
        print(f"⚠️ No se encontraron seguidores para @{username}.")
        return {"success": False, "error": "No se encontraron seguidores."}

    print(f"✅ [DEBUG] Total de seguidores obtenidos: {len(seguidores)}")

    for idx, usuario in enumerate(seguidores):
        if datetime.now() >= tiempo_limite:
            print("⏳ Tiempo límite alcanzado. Deteniendo procesamiento.")
            break

        print(f"✅ [DEBUG] Procesando seguidor {idx + 1}/{len(seguidores)}: {usuario.username}")

        try:
            acciones, _ = acciones_aleatorias(cantidad=1)
        except ValueError as e:
            print(f"❌ [ERROR] Formato inesperado en acciones_aleatorias: {e}")
            continue  

        for accion in acciones:
            if not isinstance(accion, str):  
                print(f"❌ [ERROR] Acción inválida detectada: {accion}. No se ejecutará.")
                continue  

            if not verificar_autenticacion():  
                print(f"❌ [ERROR] Sesión inválida. No se ejecutará '{accion}' para @{usuario.username}.")
                continue  

            ejecutar_accion(usuario, accion)  # 🔥 Aquí ya se hace la pausa después de la acción

        # ⏳ Mantener solo la pausa general entre usuarios
        pausa_usuario = random.uniform(*pausa_entre_usuarios)
        print(f"⏳ Pausando {pausa_usuario:.2f} segundos antes del siguiente usuario...")
        time.sleep(pausa_usuario)

    print("✅ Procesamiento finalizado.")
    return {"success": True, "message": "Procesamiento finalizado."}


def ejecutar_accion(usuario, accion):
    """
    Ejecuta la acción especificada para un usuario sin repetir lógica innecesaria.
    """
    try:
        if not isinstance(accion, str):
            print(f"❌ [ERROR] Tipo de dato inválido en acción: {accion} para @{usuario.username}. Se espera un string.")
            return

        print(f"⚙️ [DEBUG] Ejecutando '{accion}' para @{usuario.username}...")

        if not verificar_autenticacion():
            print(f"❌ [ERROR] No se puede ejecutar '{accion}' para @{usuario.username}: Sesión no válida.")
            return

        if accion == "like":
            dar_me_gusta_a_publicaciones(usuario.pk)

        elif accion == "comment":
            comentar_publicacion(usuario.username)

        elif accion == "direct_message":
            enviar_dm(usuario.username)

        # ⏳ Aplicar pausa después de cada acción
        if accion in PAUSAS_POR_ACCION:
            pausa = random.uniform(*PAUSAS_POR_ACCION[accion])
            print(f"⏳ Pausando {pausa:.2f} segundos después de ejecutar '{accion}'...")
            time.sleep(pausa)

    except Exception as e:
        print(f"❌ [ERROR] Falló la ejecución de '{accion}' para @{usuario.username}: {e}")



def generar_mensaje_combinado(tipo, username, nombre=None, bio=None, intereses=None, ultima_publicacion=None, rol="friendly", mensajes_usuario=[], max_caracteres=60):
    """
    Genera un mensaje combinando un mensaje de usuario con IA sin agregar saludos innecesarios.
    :param tipo: Tipo de mensaje (dm o comentario).
    :param username: Nombre de usuario de destino.
    :param nombre: Nombre real del usuario (si está disponible).
    :param bio: Biografía del usuario.
    :param intereses: Intereses del usuario.
    :param ultima_publicacion: Última publicación del usuario.
    :param rol: Estilo del mensaje.
    :param mensajes_usuario: Lista de mensajes proporcionados desde el frontend.
    :param max_caracteres: Límite de caracteres para el mensaje.
    """
    try:
        # 🔹 Usar mensajes del usuario si están disponibles, de lo contrario generar con IA
        if mensajes_usuario:
            mensaje_base = random.choice(mensajes_usuario)
        else:
            mensaje_base = ""  # ✅ Se elimina el mensaje base innecesario

        # 🔹 Decidir si usar nombre o username
        if nombre:
            saludo = nombre
        elif username:
            saludo = username
        else:
            saludo = "friend"

        # 🔹 Controlar la repetición del saludo (50% de los casos sin saludo)
        if random.random() > 0.5:
            saludo = ""

        # 🔹 Generar mensaje personalizado con IA
        prompt = construir_prompt(
            username=username,
            bio=bio,
            intereses=intereses,
            ultima_publicacion=ultima_publicacion,
            rol=rol,
            nombre=saludo
        )
        mensaje_personalizado = generar_mensaje_ia(
            username=username,
            bio=bio,
            intereses=intereses,
            ultima_publicacion=ultima_publicacion,
            rol=rol,
            prompt=prompt,
            nombre=saludo
        )

        # 🔹 Combinar mensajes sin agregar saludos innecesarios
        if mensaje_base:
            mensaje_completo = f"{mensaje_base} {mensaje_personalizado}".strip()
        else:
            mensaje_completo = mensaje_personalizado.strip()

        # 🔹 Limitar la longitud del mensaje
        if len(mensaje_completo) > max_caracteres:
            mensaje_completo = mensaje_completo[:max_caracteres].rstrip(".")

        print(f"[DEBUG] Mensaje generado para @{username}: {mensaje_completo}")
        return mensaje_completo

    except Exception as e:
        print(f"❌ [ERROR] en generar_mensaje_combinado: {e}")
        return "Error en la generación del mensaje."


def dar_me_gusta_a_publicaciones(user_id):
    if not user_id:
        print("❌ Error: ID de usuario no válido para dar 'me gusta'.")
        return
    try:
        # Verificar si la cuenta es privada antes de interactuar
        user_info = cl.user_info(user_id)
        if user_info.is_private:
            print(f"⚠️ La cuenta del usuario {user_id} es privada. No se puede dar 'me gusta'.")
            return

        publicaciones = cl.user_medias(user_id, amount=1)
        if publicaciones:
            publicacion_id = publicaciones[0].id
            cl.media_like(publicacion_id)
            print(f"✅ 'Me gusta' dado a la publicación {publicacion_id}.")
        else:
            print(f"❌ No se encontraron publicaciones para el usuario {user_id}.")
    except Exception as e:
        print(f"❌ Error al dar 'me gusta' al usuario {user_id}: {e}")




def enviar_dm(username, bio=None, intereses=None, ultima_publicacion=None, rol="amigable"):
    """
    Envía un mensaje directo personalizado basado en el perfil del usuario, 
    combinando los mensajes cargados desde el frontend con los generados por IA.
    """
    try:
        # Obtener los mensajes cargados desde el frontend
        mensajes_usuario = session.get('mensajes_dm', [])
        
        user_id = obtener_user_id_por_username(username)
        if not user_id:
            print(f"❌ Error: No se pudo obtener el ID de usuario para @{username}.")
            return "Error: No se pudo obtener el ID de usuario."

        # Generar mensaje con combinación de frontend e IA
        mensaje_contextual = generar_mensaje_combinado(
            tipo="dm",
            username=username,
            bio=bio,
            intereses=intereses,
            ultima_publicacion=ultima_publicacion,
            rol=rol,
            mensajes_usuario=mensajes_usuario
        )

        # Enviar mensaje directo
        cl.direct_send(mensaje_contextual, [user_id])
        print(f"✅ Mensaje enviado a @{username}: {mensaje_contextual}")
        return "Mensaje enviado exitosamente."
    except Exception as e:
        print(f"❌ Error al enviar DM al usuario @{username}: {e}")
        return "Error al enviar el mensaje."

def comentar_publicacion(username, bio=None, intereses=None, ultima_publicacion=None, rol="amigable"):
    """
    Publica un comentario en la publicación más reciente del usuario, verificando si los comentarios están permitidos.
    """
    try:
        mensajes_usuario = session.get('mensajes_comentarios', [])

        user_id = obtener_user_id_por_username(username)
        if not user_id:
            print(f"❌ Error: No se pudo obtener el ID de usuario para @{username}.")
            return

        user_info = cl.user_info(user_id)
        if user_info.is_private:
            print(f"⚠️ La cuenta de @{username} es privada. Saltando comentarios.")
            return

        publicaciones = cl.user_medias(user_id, amount=1)
        if not publicaciones:
            print(f"⚠️ No se encontraron publicaciones para @{username}.")
            return

        publicacion_id = publicaciones[0].id
        print(f"[DEBUG] Publicación seleccionada para @{username}: {publicacion_id}")

        # 🔍 **Verificar si los comentarios están restringidos**
        if hasattr(publicaciones[0], "commenting_disabled") and publicaciones[0].commenting_disabled:
            print(f"⚠️ Los comentarios están restringidos en la publicación de @{username}. Saltando acción.")
            return

        # Generar comentario usando el mensaje del frontend + IA
        comentario = generar_mensaje_combinado(
            tipo="comentario",
            username=username,
            bio=bio,
            intereses=intereses,
            ultima_publicacion=ultima_publicacion,
            rol=rol,
            mensajes_usuario=mensajes_usuario
        )

        if "Error" in comentario:
            print(f"❌ Error al generar el comentario para @{username}. Mensaje: {comentario}")
            return

        # Publicar el comentario
        cl.media_comment(publicacion_id, comentario)
        print(f"✅ Comentario publicado para @{username}: {comentario}")

    except Exception as e:
        if "feedback_required" in str(e) and "Comments on this post have been limited" in str(e):
            print(f"⚠️ No se pudo comentar en la publicación de @{username}. Los comentarios están restringidos.")
        else:
            print(f"❌ Error al comentar en la publicación de @{username}: {e}")




def obtener_user_id_por_username(username):
    """
    Busca el user_id correspondiente a un username utilizando el cliente de Instagram.
    """
    try:
        usuario = cl.user_info_by_username(username)  # Verifica si tu cliente tiene esta función
        return usuario.pk  # Esto devuelve el user_id (primary key)
    except Exception as e:
        print(f"❌ Error al obtener el user_id para @{username}: {e}")
        return None
