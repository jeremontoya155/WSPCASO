import random
import time
from database.models import registrar_accion
from instagram.session import cl
from openai_utils import generar_mensaje_ia, construir_prompt
from instagram.session import  reautenticar_sesion, verificar_autenticacion
from database.models import collection_mensajes
import json
from datetime import datetime
import random
import time
from instagram.config_bot import verificar_limite_accion, registrar_error, pausa_por_accion, registro_acciones, acciones_aleatorias, guardar_usuarios_procesados


# follow.py
usuarios_procesados = set()  # Define la variable como un conjunto global
def procesar_seguidores_por_lotes(username, cantidad_por_lote=120, pausa_min_usuario=600, pausa_max_usuario=900, duracion_horas=6):
    """
    Procesa un lote grande de seguidores y maneja pausas entre usuarios,
    optimizando las solicitudes para reducir problemas con la API.
    """
    from datetime import datetime, timedelta
    import random
    import time

    hora_inicio = datetime.now()
    tiempo_limite = hora_inicio + timedelta(hours=duracion_horas)

    # Verificar y renovar la sesión al inicio
    if not verificar_autenticacion():
        print("⚠️ Sesión no válida. Intentando reautenticación...")
        if not reautenticar_sesion():
            print("❌ Error: No se pudo reautenticar la sesión.")
            return

    try:
        # Convertir el username al user_id
        user_id = cl.user_id_from_username(username)
        print(f"🔍 User ID obtenido para {username}: {user_id}")
    except Exception as e:
        print(f"❌ Error al obtener el User ID para {username}: {e}")
        return

    try:
        # Obtener solo los IDs de los seguidores
        seguidores = cl.user_followers(user_id, amount=cantidad_por_lote)
        print(f"✅ {len(seguidores)} IDs de seguidores obtenidos para {username}.")
    except Exception as e:
        print(f"❌ Error al obtener IDs de seguidores de {username}: {e}")
        return

    usuarios_fallidos = []  # Lista para registrar usuarios que no se pudieron procesar

    for follower_id in seguidores.keys():
        if datetime.now() >= tiempo_limite:
            print("⏰ Tiempo límite alcanzado. Deteniendo procesamiento.")
            break

        if follower_id in usuarios_procesados:  # Ignorar usuarios ya procesados
            print(f"⚠️ Usuario ya procesado detectado: {follower_id}. Saltando...")
            continue

        try:
            # Intentar obtener información detallada del usuario bajo demanda
            try:
                info = cl.user_info(follower_id)
                usuario = {
                    "id": follower_id,
                    "username": info.username if hasattr(info, "username") else f"Usuario_{follower_id}",
                    "biography": getattr(info, "biography", "No disponible"),
                    "follower_count": getattr(info, "follower_count", 0),
                    "media_count": getattr(info, "media_count", 0),
                    "is_private": getattr(info, "is_private", False)
                }
            except Exception as e:
                print(f"⚠️ Error al obtener información detallada de usuario {follower_id}: {e}")
                usuario = {"id": follower_id, "username": f"Usuario_{follower_id}"}  # Fallback con ID
                usuarios_fallidos.append(usuario)
                continue

            print(f"✅ Información obtenida del usuario: {usuario['username']}")

            # Aplicar acciones al usuario
            acciones = acciones_aleatorias()
            print(f"✅ Ejecutando acciones para {usuario['username']}: {acciones}")
            ejecutar_acciones_para_usuario(usuario)

            # Registrar usuario como procesado
            usuarios_procesados.add(follower_id)
            guardar_usuarios_procesados()  # Persistir los usuarios procesados

            # Pausa entre usuarios
            pausa_usuario = random.uniform(pausa_min_usuario, pausa_max_usuario)
            print(f"⏳ Pausando {pausa_usuario / 60:.2f} minutos antes del próximo usuario...")
            time.sleep(pausa_usuario)

        except Exception as e:
            print(f"❌ Error al procesar usuario {follower_id}: {e}")
            usuarios_fallidos.append({"id": follower_id, "username": usuario.get("username", "Desconocido")})

    print("✅ [DEBUG] Proceso completado. Todos los seguidores del lote fueron procesados.")
    if usuarios_fallidos:
        print(f"⚠️ Usuarios fallidos: {len(usuarios_fallidos)}")
        for usuario in usuarios_fallidos:
            print(f"- ID: {usuario['id']}, Username: {usuario['username']}")






def ejecutar_acciones_para_usuario(usuario):
    if "id" not in usuario or "username" not in usuario:
        print(f"❌ [DEBUG] Usuario inválido: {usuario}. Saltando...")
        return

    print(f"🚀 [DEBUG] Iniciando acciones para el usuario: {usuario['username']} | Hora: {datetime.now()}")

    # Generar acciones aleatorias
    acciones_disponibles = ["follow", "like", "comment", "view_story", "direct_message"]
    cantidad_acciones = random.randint(1, 3)  # Generar entre 2 y 5 acciones
    acciones = random.sample(acciones_disponibles, cantidad_acciones)

    print(f"✅ [DEBUG] Acciones aleatorias asignadas: {acciones}")

    # Mezclar el orden de las acciones
    random.shuffle(acciones)

    for accion in acciones:
        if not verificar_limite_accion(accion):
            print(f"⚠️ Límite alcanzado para '{accion}'. No se ejecutará esta acción.")
            continue

        try:
            print(f"⚙️ [DEBUG] Ejecutando acción '{accion}' para {usuario['username']}...")
            if accion == "follow":
                seguir_usuario(usuario["id"])
            elif accion == "like":
                dar_me_gusta_a_publicaciones(usuario["id"])
            elif accion == "comment":
                comentar_publicacion(usuario["username"])
            elif accion == "view_story":
                ver_historias(usuario["id"])
            elif accion == "direct_message":
                enviar_dm(usuario["username"])
            print(f"✅ [DEBUG] Acción '{accion}' completada para {usuario['username']} | Hora: {datetime.now()}.")

            # Registrar la acción ejecutada
            registro_acciones[accion].append(datetime.now())

        except Exception as e:
            print(f"❌ [DEBUG] Error al realizar '{accion}' para {usuario['username']}: {e}")
            registrar_error(usuario["id"], accion, str(e))

        # Pausa específica por acción
        pausa_por_accion(accion)



def obtener_seguidores_con_acciones(username, cantidad=3):
    seguidores_info = procesar_seguidores_por_lotes(username, cantidad=cantidad)
    for usuario in seguidores_info:
        usuario["acciones"] = generar_acciones_aleatorias()
    return seguidores_info


def generar_acciones_aleatorias():
    """Genera una lista de acciones aleatorias para un usuario."""
    acciones_posibles = ["follow", "like", "comment", "view_story", "direct_message"]
    cantidad_acciones = random.randint(1, len(acciones_posibles))
    return random.sample(acciones_posibles, cantidad_acciones)

def dar_me_gusta_a_publicaciones(user_id):
    """
    Intenta dar 'me gusta' a la primera publicación de un usuario,
    verificando si la cuenta es privada.
    """
    try:
        # Verificar autenticación de la sesión de Instagram
        verificar_autenticacion_instagram()

        if not user_id:
            print("❌ [DEBUG] ID de usuario no proporcionado.")
            return

        # Obtener información del usuario
        user_info = cl.user_info(user_id)
        if user_info.is_private:
            print(f"⚠️ La cuenta del usuario {user_id} es privada. No se puede acceder a las publicaciones.")
            return

        # Obtener publicaciones del usuario
        publicaciones = cl.user_medias(user_id, amount=1)
        if publicaciones:
            publicacion_id = publicaciones[0].id
            cl.media_like(publicacion_id)  # Dar 'me gusta'
            registrar_accion(user_id, "me_gusta", {"publicacion_id": publicacion_id})
            print(f"✅ 'Me gusta' dado a la publicación {publicacion_id}.")
        else:
            print(f"❌ No se encontraron publicaciones para el usuario {user_id}.")
    except Exception as e:
        registrar_error_instagram(user_id, "me_gusta", str(e))
        print(f"❌ Error al dar 'me gusta' al usuario {user_id}: {e}")

def registrar_error_instagram(user_id, accion, error):
    """Registra los errores en un archivo de logs."""
    with open("errores_instagram.log", "a") as archivo:
        archivo.write(f"{datetime.now()} | Usuario: {user_id} | Acción: {accion} | Error: {error}\n")
    print(f"❌ [ERROR] Registrado en errores_instagram.log: {error}")


def ver_historias(user_id):
    try:
        print(f"🔍 [DEBUG] Intentando ver historias del usuario: {user_id}")
        verificar_autenticacion()  # Verifica que el cliente esté autenticado
        historias = cl.user_stories(user_id)
        if historias:
            for historia in historias:
                cl.story_seen([historia.pk])
                registrar_accion(user_id, "view_story", {"story_id": historia.pk})
                print(f"✅ Historia vista: {historia.pk}")
        else:
            print(f"⚠️ No se encontraron historias para el usuario: {user_id}")
    except Exception as e:
        print(f"❌ Error al ver historias del usuario {user_id}: {e}")


def cargar_mensajes_txt(rutas_txt):
    """
    Carga mensajes desde múltiples archivos TXT y los combina en una lista.
    """
    mensajes = []
    for ruta in rutas_txt:
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                contenido = archivo.read()
                mensajes.extend([linea.strip() for linea in contenido.split(";") if linea.strip()])
        except Exception as e:
            print(f"❌ Error al leer {ruta}: {e}")
    return mensajes



def cargar_mensajes_json(ruta):
    """
    Carga mensajes desde un archivo JSON.
    """
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            bloques = json.load(archivo)
            mensajes = []
            for bloque in bloques.values():
                if isinstance(bloque, list):
                    mensajes.extend(bloque)
            return mensajes
    except Exception as e:
        print(f"❌ Error al cargar mensajes desde JSON ({ruta}): {e}")
        return []


# Rutas de los archivos
RUTA_MENSAJES_JSON_COMENTARIOS = "./mensajes/mensajes_dm.json"
RUTA_MENSAJES_JSON_DM = "./mensajes/mensajes_dm.json"
RUTA_MENSAJES_TXT_COMENTARIOS = "./mensajes/Hola como estas;.txt"
RUTA_MENSAJES_TXT_DM = "./mensajes/primeros mensajes.txt"

# Cargar los mensajes
mensajes_comentarios = cargar_mensajes_json(RUTA_MENSAJES_JSON_COMENTARIOS)
mensajes_dm = cargar_mensajes_json(RUTA_MENSAJES_JSON_DM)
mensajes_txt_comentarios = cargar_mensajes_txt([RUTA_MENSAJES_TXT_COMENTARIOS])
mensajes_txt_dm = cargar_mensajes_txt([RUTA_MENSAJES_TXT_DM])

# Validar que sean listas
for nombre, lista in [("mensajes_comentarios", mensajes_comentarios), 
                      ("mensajes_dm", mensajes_dm), 
                      ("mensajes_txt_comentarios", mensajes_txt_comentarios), 
                      ("mensajes_txt_dm", mensajes_txt_dm)]:
    if not isinstance(lista, list):
        print(f"❌ Error: {nombre} no es una lista. Valor actual: {lista}")
        lista = []


def generar_mensaje_combinado(tipo, username, nombre=None, bio=None, intereses=None, ultima_publicacion=None, rol="friendly"):
    """
    Genera un mensaje combinando un mensaje base con uno personalizado generado por IA.
    """
    try:
        # Seleccionar la base de mensajes según el tipo
        if tipo == "comentario":
            mensajes_base = mensajes_comentarios + mensajes_txt_comentarios
        elif tipo == "dm":
            mensajes_base = mensajes_dm + mensajes_txt_dm
        else:
            print(f"❌ Tipo desconocido: {tipo}")
            return "Espero que tengas un gran día. 😊 ¿Qué tal van tus proyectos?"

        if not mensajes_base:
            print(f"⚠️ No se encontraron mensajes base para el tipo {tipo}. Generando mensaje por IA...")
            # Generar mensaje dinámico en caso de falta de mensajes base
            return generar_mensaje_ia(
                username=username,
                bio=bio,
                intereses=intereses,
                ultima_publicacion=ultima_publicacion,
                rol=rol,
                nombre=nombre
            )

        # Generar un mensaje base aleatorio
        mensaje_base = random.choice(mensajes_base)

        # Generar un mensaje personalizado con IA
        prompt = construir_prompt(
            username=username,
            bio=bio,
            intereses=intereses,
            ultima_publicacion=ultima_publicacion,
            rol=rol,
            nombre=nombre
        )
        mensaje_personalizado = generar_mensaje_ia(
            username=username,
            bio=bio,
            intereses=intereses,
            ultima_publicacion=ultima_publicacion,
            rol=rol,
            prompt=prompt,
            nombre=nombre
        )

        # Combinar los mensajes
        mensaje_completo = f"{mensaje_base} {mensaje_personalizado}".strip()
        print(f"[DEBUG] Mensaje generado: {mensaje_completo}")
        return mensaje_completo
    except Exception as e:
        print(f"❌ Error en generar_mensaje_combinado: {e}")
        return "Algo salió mal al generar el mensaje, pero aquí estoy para ayudarte. 😊"




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

def comentar_publicacion(username, bio=None, intereses=None, ultima_publicacion=None, rol="amigable"):
    try:
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

        # Generar comentario usando el nombre de usuario como prioridad
        comentario = generar_mensaje_combinado(
            tipo="comentario", username=username, bio=bio, 
            intereses=intereses, ultima_publicacion=ultima_publicacion, rol=rol
        )

        if "Error" in comentario:
            print(f"❌ Error al generar el comentario para @{username}. Mensaje: {comentario}")
            return

        cl.media_comment(publicacion_id, comentario)
        print(f"✅ Comentario publicado para @{username}: {comentario}")
        registrar_conversacion(username, "comentario", comentario)
    except Exception as e:
        print(f"❌ Error al comentar en la publicación de @{username}: {e}")
        registrar_error_instagram(user_id, "comment", str(e))


def enviar_dm(username, bio=None, intereses=None, ultima_publicacion=None, rol="amigable"):
    """
    Envía un mensaje directo personalizado basado en el perfil del usuario.
    """
    try:
        # Obtener el user_id y la información del usuario
        user_id = obtener_user_id_por_username(username)
        if not user_id:
            print(f"❌ Error: No se pudo obtener el ID de usuario para @{username}.")
            return "Error: No se pudo obtener el ID de usuario."

        # Generar mensaje con prioridad al nombre de usuario
        mensaje_contextual = generar_mensaje_combinado(
            tipo="dm",
            username=username,
            bio=bio,
            intereses=intereses,
            ultima_publicacion=ultima_publicacion,
            rol=rol
        )

        # Enviar mensaje directo
        cl.direct_send(mensaje_contextual, [user_id])
        print(f"✅ Mensaje enviado a @{username}: {mensaje_contextual}")
        return "Mensaje enviado exitosamente."
    except Exception as e:
        print(f"❌ Error al enviar DM al usuario @{username}: {e}")
        return "Error al enviar el mensaje."


def procesar_respuesta(user_id, mensaje_usuario, tipo="dm", rol="amigable"):
    """
    Procesa una respuesta y genera un mensaje de seguimiento.
    """
    try:
        # Generar una respuesta con contexto
        respuesta_bot = generar_respuesta_con_contexto(user_id, mensaje_usuario, rol)

        # Enviar respuesta según el tipo
        if tipo == "dm":
            cl.direct_send(respuesta_bot, [user_id])
        elif tipo == "comentario":
            # Asegúrate de que mensaje_usuario contenga el ID de la publicación y del comentario
            if "publicacion_id" in mensaje_usuario and "comentario_id" in mensaje_usuario:
                cl.media_comment_reply(
                    mensaje_usuario["publicacion_id"], 
                    mensaje_usuario["comentario_id"], 
                    respuesta_bot
                )
            else:
                print(f"❌ Datos incompletos para responder al comentario: {mensaje_usuario}")
                return

        # Registrar la conversación actualizada
        actualizar_conversacion(user_id, mensaje_usuario, respuesta_bot)
        print(f"✅ Respuesta procesada y enviada: {respuesta_bot}")
    except Exception as e:
        print(f"❌ Error al procesar la respuesta del usuario {user_id}: {e}")
        registrar_error_instagram(user_id, "procesar_respuesta", str(e))



# **7. Registro y actualización en la base de datos**
def registrar_conversacion(username, tipo, mensaje_inicial):
    """
    Registra una nueva conversación en la base de datos.
    """
    try:
        collection_mensajes.insert_one({
            "username": username,
            "tipo": tipo,
            "mensaje_inicial": mensaje_inicial,
            "respuestas": [],
            "estado": "abierta",
            "fecha_creacion": datetime.utcnow(),
            "fecha_actualizacion": datetime.utcnow()
        })
        print(f"✅ Conversación registrada para el usuario @{username}.")
    except Exception as e:
        print(f"❌ Error al registrar la conversación para @{username}: {e}")


def actualizar_conversacion(user_id, mensaje_usuario, mensaje_bot):
    """
    Actualiza la conversación existente con nuevas respuestas.
    """
    try:
        actualizacion = {
            "$push": {
                "respuestas": {
                    "mensaje_usuario": mensaje_usuario,
                    "mensaje_bot": mensaje_bot
                }
            },
            "$set": {
                "fecha_actualizacion": datetime.utcnow()
            }
        }
        collection_mensajes.update_one({"user_id": user_id, "estado": "abierta"}, actualizacion)
        print(f"✅ Conversación actualizada para el usuario {user_id}.")
    except Exception as e:
        print(f"❌ Error al actualizar la conversación: {e}")

def generar_respuesta_con_contexto(user_id, mensaje_usuario, rol="amigable"):
    """
    Genera una respuesta utilizando el historial de la conversación.
    """
    try:
        mensaje_inicial, contexto = obtener_contexto_conversacion(user_id)
        historial = "\n".join([f"Usuario: {r['mensaje_usuario']}\nBot: {r['mensaje_bot']}" for r in contexto])

        prompt = f"""
        Actúa como un {rol}. Sigue el contexto de la conversación y genera una respuesta adecuada:
        Mensaje inicial: {mensaje_inicial}
        Historial de conversación:
        {historial}
        Usuario: {mensaje_usuario}
        """
        respuesta_bot = generar_mensaje_ia(username="Usuario", bio=None, intereses=None, ultima_publicacion=mensaje_usuario, rol=rol, prompt=prompt)
        return respuesta_bot
    except Exception as e:
        print(f"❌ Error al generar respuesta con contexto: {e}")
        return "Hubo un error al generar la respuesta."



def obtener_contexto_conversacion(user_id):
    """
    Obtiene el contexto de la conversación desde la base de datos.
    """
    try:
        conversacion = collection_mensajes.find_one({"user_id": user_id, "estado": "abierta"})
        if conversacion:
            mensaje_inicial = conversacion.get("mensaje_inicial", "")
            contexto = conversacion.get("respuestas", [])
            return mensaje_inicial, contexto
        return None, []
    except Exception as e:
        print(f"❌ Error al obtener el contexto de la conversación: {e}")
        return None, []

def verificar_autenticacion_instagram():
    """Verifica si el cliente de Instagram está autenticado."""
    try:
        if not cl.user_id:
            print("⚠️ Cliente de Instagram no autenticado. Reautenticando...")
            reautenticar_sesion()
        else:
            print("✅ Cliente de Instagram autenticado.")
    except Exception as e:
        print(f"❌ Error al verificar la autenticación: {e}")


def seguir_usuario(user_id):
    """Sigue a un usuario en Instagram y registra la acción."""
    try:
        verificar_autenticacion_instagram()
        cl.user_follow(user_id)
        registrar_accion(user_id, "seguir", {})
        print(f"✅ Usuario {user_id} seguido correctamente.")
    except Exception as e:
        print(f"❌ Error al seguir al usuario {user_id}: {e}")
        raise e
