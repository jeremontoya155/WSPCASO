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
    try:
        user_id = cl.user_id_from_username(username)
        seguidores = cl.user_followers(user_id, amount=cantidad)
        return list(seguidores.values())
    except Exception as e:
        print(f"❌ Error al obtener seguidores de @{username}: {e}")
        return []


def procesar_usuarios(username, duracion_horas=6, cantidad=120, pausa_entre_usuarios=(90, 350)):
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
        
        user_info = cl.user_info(usuario.pk)
        if user_info.is_private:
            print(f"⏭️ [INFO] Saltando usuario @{usuario.username} porque la cuenta es privada.")
            continue
        
        publicaciones = cl.user_medias(usuario.pk, amount=1)
        if not publicaciones:
            print(f"⏭️ [INFO] Saltando usuario @{usuario.username} porque no tiene publicaciones.")
            continue
        
        print(f"✅ [DEBUG] Procesando seguidor {idx + 1}/{len(seguidores)}: {usuario.username}")
        
        try:
            acciones, _ = acciones_aleatorias(cantidad=2)
        except ValueError as e:
            print(f"❌ [ERROR] Formato inesperado en acciones_aleatorias: {e}")
            continue  
        
        user_id = usuario.pk
        for accion in acciones:
            if not isinstance(accion, str):  
                print(f"❌ [ERROR] Acción inválida detectada: {accion}. No se ejecutará.")
                continue  
            
            if not verificar_autenticacion():  
                print(f"❌ [ERROR] Sesión inválida. No se ejecutará '{accion}' para @{usuario.username}.")
                continue  
            
            ejecutar_accion(usuario, accion, user_id)
        
        pausa_usuario = random.uniform(*pausa_entre_usuarios)
        print(f"⏳ Pausando {pausa_usuario:.2f} segundos antes del siguiente usuario...")
        time.sleep(pausa_usuario)
    
    print("✅ Procesamiento finalizado.")
    return {"success": True, "message": "Procesamiento finalizado."}

def ejecutar_accion(usuario, accion, user_id):
    try:
        if not isinstance(accion, str):
            print(f"❌ [ERROR] Tipo de dato inválido en acción: {accion} para @{usuario.username}. Se espera un string.")
            return

        print(f"⚙️ [DEBUG] Ejecutando '{accion}' para @{usuario.username}...")

        if not verificar_autenticacion():
            print(f"❌ [ERROR] No se puede ejecutar '{accion}' para @{usuario.username}: Sesión no válida.")
            return

        if accion == "like":
            dar_me_gusta_a_publicaciones(user_id)
        elif accion == "comment":
            comentar_publicacion(usuario.username)
        elif accion == "direct_message":
            mensajes_usuario = session.get('mensajes_dm', [])
            if mensajes_usuario:
                enviar_dm(usuario.username, mensajes_usuario, user_id)
            else:
                print(f"⚠️ No hay mensajes disponibles para enviar a @{usuario.username}.")

        if accion in PAUSAS_POR_ACCION:
            pausa = random.uniform(*PAUSAS_POR_ACCION[accion])
            print(f"⏳ Pausando {pausa:.2f} segundos después de ejecutar '{accion}'...")
            time.sleep(pausa)
    except Exception as e:
        print(f"❌ [ERROR] Falló la ejecución de '{accion}' para @{usuario.username}: {e}")

def generar_mensaje_combinado(tipo, username, nombre=None, mensajes_usuario=None, max_caracteres=150, historial_mensajes=None):
    """Genera un mensaje combinando texto de usuario y mejora con IA para mayor naturalidad."""
    try:
        if mensajes_usuario is None or not mensajes_usuario:
            print("❌ [ERROR] No hay mensajes disponibles.")
            return "No hay mensajes disponibles."

        if historial_mensajes is None:
            historial_mensajes = set()

        mensajes_disponibles = [m for m in mensajes_usuario if m not in historial_mensajes]

        if not mensajes_disponibles:
            print("[DEBUG] Todos los mensajes han sido usados. Reiniciando historial.")
            historial_mensajes.clear()
            mensajes_disponibles = mensajes_usuario[:]

        mensaje_base = random.choice(mensajes_disponibles)
        historial_mensajes.add(mensaje_base)

        try:
            mensaje_ia = generar_mensaje_ia(
                username=username,
                prompt=f"Improve this message while keeping its essence and making it sound more natural: {mensaje_base}"
            )
        except Exception as e:
            print(f"❌ [ERROR] en generar_mensaje_ia: {e}")
            mensaje_ia = mensaje_base

        saludos_alternativos = ["Hello!", "Hey!", "Greetings!", "What's up!", "Hi, nice to see you!"]
        saludo = random.choice(saludos_alternativos)
        mensaje_completo = f"{saludo} {mensaje_ia}".strip()

        if len(mensaje_completo) > max_caracteres:
            mensaje_completo = mensaje_completo[:max_caracteres].rsplit(' ', 1)[0] + "..."

        print(f"✅ [DEBUG] Message generated: {mensaje_completo}")
        return mensaje_completo

    except Exception as e:
        print(f"❌ [ERROR] en generar_mensaje_combinado: {e}")
        return "Error generating the message."


ultimos_intentos_dm = {}
def enviar_dm(username, mensajes_usuario, user_id, bio=None, intereses=None, ultima_publicacion=None, rol="amigable"):
    mensaje_contextual = generar_mensaje_combinado(
        tipo="dm",
        username=username,
        nombre=username,
        mensajes_usuario=mensajes_usuario
    )

    if not mensaje_contextual.strip():
        return "Error: El mensaje generado está vacío."

    ahora = datetime.now()

    if username in ultimos_intentos_dm:
        ultimo_intento = ultimos_intentos_dm[username]
        tiempo_transcurrido = ahora - ultimo_intento
        if tiempo_transcurrido < timedelta(hours=24):
            tiempo_restante = timedelta(hours=24) - tiempo_transcurrido
            print(f"⚠️ Ya se intentó enviar un DM a @{username} recientemente. Tiempo restante: {tiempo_restante}")
            return f"Error: DM a @{username} bloqueado por límite de tiempo."

    intentos = 0
    tiempo_espera_base = 60
    tiempo_espera_maximo = 3600

    while intentos < 3:
        try:
            cl.direct_send(mensaje_contextual, [user_id])
            print(f"✅ Mensaje enviado a @{username}: {mensaje_contextual}")
            ultimos_intentos_dm[username] = ahora
            return "Mensaje enviado exitosamente."
        except Exception as e:
            error_str = str(e).lower()
            if "limit" in error_str or "can't be delivered" in error_str or "403" in error_str:
                intentos += 1
                tiempo_espera = min(tiempo_espera_base * (2**(intentos-1)), tiempo_espera_maximo) + random.randint(0,30)
                print(f"❌ [ALERTA] Instagram bloqueó el mensaje a @{username}. Esperando {tiempo_espera} segundos (intento {intentos}).")
                time.sleep(tiempo_espera)
                ultimos_intentos_dm[username] = ahora
            else:
                print(f"❌ Error al enviar DM al usuario @{username}: {e}")
                return f"Error al enviar el mensaje: {e}"

    print(f"❌ No se pudo enviar el mensaje a @{username} después de varios intentos. Límite alcanzado.")
    return "Error: No se pudo enviar el mensaje (límite alcanzado)."

def comentar_publicacion(username, bio=None, intereses=None, ultima_publicacion=None, rol="amigable"):
    """Publica un comentario en la publicación más reciente del usuario."""
    try:
        mensajes_usuario = session.get('mensajes_comentarios', [])

        if not mensajes_usuario:
            archivo_subido = session.get('archivos_subidos', {}).get('comentarios', 'Ninguno')
            print(f"⚠️ No hay mensajes de comentarios disponibles. Último archivo subido: {archivo_subido}")
            return f"Error: No hay mensajes disponibles. Último archivo subido: {archivo_subido}"

        user_id = obtener_user_id_por_username(username)
        if not user_id:
            return "Error: No se pudo obtener el ID de usuario."

        user_info = cl.user_info(user_id)
        if user_info.is_private:
            print(f"⚠️ La cuenta @{username} es privada. No se puede comentar en sus publicaciones.")
            return f"Error: No se puede comentar en la publicación de @{username} porque la cuenta es privada."

        publicaciones = cl.user_medias(user_id, amount=1)

        # Lógica para manejar el caso de que no haya publicaciones
        if not publicaciones:
            # Opción 1: Comentar en el perfil (si es posible)
            try:
                comentario_perfil = generar_mensaje_combinado(
                    tipo="comentario",
                    username=username,
                    nombre=username,
                    mensajes_usuario=mensajes_usuario
                )
                cl.user_comment(user_id, comentario_perfil)  # Comentar en el perfil
                print(f"✅ Comentario publicado en el perfil de @{username}: {comentario_perfil}")
                return "Comentario publicado en el perfil exitosamente."
            except Exception as e:
                print(f"⚠️ La cuenta @{username} no tiene publicaciones y no se pudo comentar en su perfil: {e}")
                return f"Error: La cuenta @{username} no tiene publicaciones disponibles."

            # Opción 2: Devolver un mensaje específico
            # return f"La cuenta @{username} es pública, pero no tiene publicaciones disponibles."

        publicacion_id = publicaciones[0].id
        print(f"[DEBUG] Publicación seleccionada para @{username}: {publicacion_id}")

        if hasattr(publicaciones[0], "commenting_disabled") and publicaciones[0].commenting_disabled:
            print(f"⚠️ Los comentarios están restringidos en la publicación de @{username}.")
            return f"Error: No se puede comentar en la publicación de @{username} porque los comentarios están restringidos."

        comentario = generar_mensaje_combinado(
            tipo="comentario",
            username=username,
            nombre=username,
            mensajes_usuario=mensajes_usuario
        )

        if not comentario.strip():
            return "Error: El comentario generado está vacío."

        cl.media_comment(publicacion_id, comentario)
        print(f"✅ Comentario publicado en la cuenta de @{username}: {comentario}")
        return "Comentario publicado exitosamente."

    except Exception as e:
        print(f"❌ Error al comentar en la publicación de @{username}: {e}")
        return f"Error al comentar: {e}"
    
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
