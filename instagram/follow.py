import random
import time
from datetime import datetime
from database.models import registrar_accion
from instagram.session import cl
from openai_utils import generar_mensaje_ia, construir_prompt
from instagram.session import  reautenticar_sesion, verificar_autenticacion
from database.models import collection_mensajes
import json
# Configuración de límites y horarios
LIMITES_ACCIONES = {
    "likes": 30,  # Máximo "me gusta" diarios
    "comments": 20,  # Máximo comentarios diarios
    "follows": 50,  # Máximo seguimientos diarios
}
HORA_INICIO = 9
HORA_FIN = 23

tiempo_pausa_prolongada = 3600  # 1 hora después de ciertas acciones

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

def obtener_seguidores_de_competencia(username, cantidad=3, pausa_min=1, pausa_max=3):
    """
    Obtiene la información completa (o parcial) de los seguidores de un usuario de competencia,
    con pausas aleatorias entre las solicitudes.
    
    Args:
        username (str): Nombre de usuario de la competencia.
        cantidad (int): Cantidad de seguidores a obtener.
        pausa_min (int): Tiempo mínimo de pausa entre solicitudes (en segundos).
        pausa_max (int): Tiempo máximo de pausa entre solicitudes (en segundos).
    
    Returns:
        list: Lista de diccionarios con la información de los seguidores.
    """
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
        seguidores_info = []

        for idx, follower_id in enumerate(seguidores.keys(), start=1):
            try:
                # Intentar obtener información completa del usuario
                info = cl.user_info(follower_id)
                seguidores_info.append({
                    "id": follower_id,
                    "username": info.username,
                    "biography": info.biography or "",
                    "follower_count": info.follower_count or 0,
                    "media_count": info.media_count or 0,
                    "is_private": info.is_private
                })
                print(f"✅ Información obtenida del seguidor {idx}/{cantidad}: {info.username}")

            except Exception as e:
                # En caso de error, agregar datos mínimos disponibles
                print(f"❌ Error al obtener información completa del seguidor {follower_id}: {e}")
                seguidores_info.append({
                    "id": follower_id,
                    "username": "Usuario desconocido",
                    "biography": "No disponible",
                    "follower_count": 0,
                    "media_count": 0,
                    "is_private": None
                })

            # Generar pausa aleatoria entre solicitudes
            if idx < cantidad:  # No pausar después del último usuario
                pausa = random.uniform(pausa_min, pausa_max)  # Generar pausa aleatoria
                print(f"⏳ Pausando {pausa:.2f} segundos antes de la próxima solicitud...")
                time.sleep(pausa)

        print(f"✅ Información obtenida de {len(seguidores_info)} seguidores (completa o parcial).")
        return seguidores_info

    except Exception as e:
        print(f"❌ Error al obtener seguidores de {username}: {e}")
        return []


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



def cargar_mensajes_txt(rutas_txt):
    """
    Carga mensajes desde múltiples archivos TXT y los combina en una lista.
    """
    mensajes = []
    for ruta in rutas_txt:
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                mensajes.extend([linea.strip() for linea in archivo if linea.strip()])
        except Exception as e:
            print(f"❌ Error al leer {ruta}: {e}")
    return mensajes


# **1. Funciones para cargar mensajes**

def cargar_mensajes_json(ruta):
    """
    Carga mensajes desde un archivo JSON.
    """
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception as e:
        print(f"❌ Error al cargar mensajes desde JSON ({ruta}): {e}")
        return {}

# Cargar mensajes desde JSON y TXT
RUTA_MENSAJES = "./mensajes/"
mensajes_comentarios = cargar_mensajes_json(f"{RUTA_MENSAJES}mensajes_comentarios.json")
mensajes_dm = cargar_mensajes_json(f"{RUTA_MENSAJES}mensajes_dm.json")["mensajes_dm"]

mensajes_txt_comentarios = cargar_mensajes_txt([f"{RUTA_MENSAJES}Hola como estas;.txt"])
mensajes_txt_dm = cargar_mensajes_txt([f"{RUTA_MENSAJES}primeros mensajes.txt"])

# **2. Función para detectar idioma**
def detectar_idioma(texto):
    """
    Detecta el idioma del texto basándose en palabras clave.
    """
    if any(palabra in texto.lower() for palabra in ["hola", "día", "interesante"]):
        return "es"
    return "en"


def generar_mensaje_combinado(tipo, username, nombre=None, bio=None, intereses=None, ultima_publicacion=None, rol="friendly"):
    """
    Genera un mensaje combinando un mensaje base desde TXT/JSON con un mensaje personalizado generado por IA.
    """
    # Seleccionar la base de mensajes según el tipo
    if tipo == "comentario":
        mensajes_base = mensajes_comentarios + mensajes_txt_comentarios
    elif tipo == "dm":
        mensajes_base = mensajes_dm + mensajes_txt_dm
    else:
        print(f"❌ Tipo desconocido: {tipo}")
        return "Error: Tipo de mensaje no válido."

    # Construir el prompt dinámico
    prompt = construir_prompt(
        username=username,
        bio=bio,
        intereses=intereses,
        ultima_publicacion=ultima_publicacion,
        rol=rol,
        nombre=nombre
    )

    # Generar mensaje personalizado con IA
    mensaje_generado = generar_mensaje_ia(
        username=username,
        bio=bio,
        intereses=intereses,
        ultima_publicacion=ultima_publicacion,
        rol=rol,
        prompt=prompt,
        nombre=nombre
    )

    # Seleccionar un mensaje base aleatorio como respaldo
    mensaje_base = random.choice(mensajes_base)

    # Combinar el mensaje generado con el mensaje base
    mensaje_final = f"{mensaje_base} {mensaje_generado}".strip()

    return mensaje_final



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
            return "Error: No se pudo obtener el ID de usuario."

        user_info = cl.user_info(user_id)

        # Ajustar el acceso a is_private según el tipo de user_info
        if hasattr(user_info, "is_private") and user_info.is_private:
            print(f"❌ La cuenta de @{username} es privada. No se puede publicar comentarios.")
            return "Error: No se puede comentar en cuentas privadas."

        publicaciones = cl.user_medias(user_id, amount=1)
        if not publicaciones:
            print(f"❌ No se encontraron publicaciones para @{username}.")
            return "Error: No se encontraron publicaciones."

        publicacion_id = publicaciones[0].id
        comentario = generar_mensaje_combinado(
            tipo="comentario",
            username=username,
            bio=bio,
            intereses=intereses,
            ultima_publicacion=ultima_publicacion,
            rol=rol
        )

        cl.media_comment(publicacion_id, comentario)
        print(f"✅ Comentario publicado para @{username}: {comentario}")
        registrar_conversacion(username, "comentario", comentario)
    except Exception as e:
        print(f"❌ Error al comentar en la publicación de @{username}: {e}")


def enviar_dm(username, bio=None, intereses=None, ultima_publicacion=None, rol="amigable"):
    """
    Envía un mensaje directo personalizado basado en el perfil del usuario usando exclusivamente `generar_mensaje_combinado`.
    """
    try:
        # Obtener el user_id y la información del usuario
        user_id = obtener_user_id_por_username(username)
        if not user_id:
            print(f"❌ Error: No se pudo obtener el ID de usuario para @{username}.")
            return "Error: No se pudo obtener el ID de usuario."

        user_info = cl.user_info(user_id)

        # Generar siempre el mensaje usando `generar_mensaje_combinado`
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


# **6. Procesar respuestas del usuario**
def procesar_respuesta(user_id, mensaje_usuario, tipo="dm", rol="amigable"):
    """
    Procesa una respuesta y genera un mensaje de seguimiento.
    """
    try:
        respuesta_bot = generar_respuesta_con_contexto(user_id, mensaje_usuario, rol)

        if tipo == "dm":
            cl.direct_send(respuesta_bot, [user_id])
        elif tipo == "comentario":
            cl.media_comment_reply(mensaje_usuario["publicacion_id"], mensaje_usuario["comentario_id"], respuesta_bot)

        print(f"✅ Respuesta procesada y enviada: {respuesta_bot}")
        actualizar_conversacion(user_id, mensaje_usuario, respuesta_bot)
    except Exception as e:
        print(f"❌ Error al procesar la respuesta del usuario {user_id}: {e}")


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
    # Obtener el historial de la conversación y el mensaje inicial
    mensaje_inicial, contexto = obtener_contexto_conversacion(user_id)

    # Construir el historial en formato de texto para el prompt
    historial = "\n".join([f"Usuario: {r['mensaje_usuario']}\nBot: {r['mensaje_bot']}" for r in contexto])

    # Construir el prompt
    prompt = f"""
    Actúa como un {rol}. Sigue el contexto de la conversación y genera una respuesta adecuada:
    Mensaje inicial: {mensaje_inicial}
    Historial de conversación:
    {historial}
    Usuario: {mensaje_usuario}
    """

    # Generar respuesta con OpenAI
    try:
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


# Función genérica para ejecutar acciones
def ejecutar_accion(user_id, accion, rol="amigable", **kwargs):
    """
    Ejecuta una acción específica en función del tipo y los datos proporcionados.
    """
    if not dentro_de_horario():
        return {"success": False, "error": "Fuera del horario permitido."}

    if not verificar_limite_accion(accion):
        return {"success": False, "error": f"Límite diario alcanzado para {accion}."}

    try:
        if accion == "like":
            dar_me_gusta_a_publicaciones(user_id)
        elif accion == "comment":
            comentario = generar_mensaje_combinado(
                username=kwargs.get("username"),
                bio=kwargs.get("bio"),
                intereses=kwargs.get("intereses"),
                ultima_publicacion=kwargs.get("ultima_publicacion"),
                idioma=kwargs.get("idioma", "es"),
                rol=rol  # Aplicar el rol seleccionado
            )
            comentar_publicacion(user_id, comentario)
        elif accion == "dm":
            enviar_dm(
                user_id=user_id,
                username=kwargs.get("username"),
                bio=kwargs.get("bio"),
                intereses=kwargs.get("intereses"),
                ultima_publicacion=kwargs.get("ultima_publicacion"),
                rol=rol  # Aplicar el rol seleccionado
            )
        elif accion == "follow":
            seguir_usuario(user_id)
        elif accion == "view_story":
            ver_historias(user_id)
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


