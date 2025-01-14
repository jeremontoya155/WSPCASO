import openai
from openai import AuthenticationError, RateLimitError, APIConnectionError

import random
from config import OPENAI_API_KEY
from genderize import Genderize
from instagrapi import Client
# Configurar la clave de API de OpenAI
openai.api_key = OPENAI_API_KEY
cl = Client()
# Mensajes predefinidos en caso de error o como alternativa
MENSAJES_PREDEFINIDOS = [
    "Hola, ¡me encanta tu contenido!",
    "¡Qué gran trabajo estás haciendo!",
    "Saludos, sigue creando cosas tan inspiradoras.",
    "¡Tu perfil es muy interesante, felicidades!"
]

def generar_mensaje_ia(username, bio=None, intereses=None, ultima_publicacion=None):
    """
    Genera un mensaje personalizado para un usuario.
    """
    try:
        # Construir el prompt
        prompt = f"Genera un mensaje amigable para el usuario @{username}. {bio or ''} Intereses: {intereses or ''}. Última publicación: {ultima_publicacion or ''}."

        # Realizar la solicitud a OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        mensaje = response["choices"][0]["message"]["content"].strip()
        print(f"Mensaje generado para @{username}: {mensaje}")
        return mensaje

    except AuthenticationError:
        print("❌ Error: Problema de autenticación con la API de OpenAI.")
        return "Error de autenticación con la API."
    except RateLimitError:
        print("❌ Error: Límite de solicitudes alcanzado en la API de OpenAI.")
        return "Límite de solicitudes alcanzado. Por favor, inténtalo más tarde."
    except APIConnectionError:
        print("❌ Error: No se pudo conectar con la API de OpenAI.")
        return "Error de conexión con OpenAI."
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return "Error desconocido al generar el mensaje."


def extraer_nombre_apodo(username, bio):
    """
    Intenta extraer el nombre o apodo de la biografía del usuario.
    Si no se encuentra un nombre, usa el username como referencia.
    Además, intenta identificar el género basándose en el nombre.

    Args:
        username (str): Username del usuario de Instagram.
        bio (str): Biografía del usuario.

    Returns:
        tuple: (nombre, genero), donde:
            - nombre (str): Nombre o apodo extraído.
            - genero (str): 'hombre', 'mujer' o 'desconocido'.
    """
    # Palabras clave comunes en biografías para nombres
    posibles_nombres = bio.split() if bio else []

    # Intentar identificar un nombre válido
    nombre = None
    for palabra in posibles_nombres:
        if palabra.istitle():  # Palabra que comienza con mayúscula (posible nombre)
            nombre = palabra
            break

    # Si no se encuentra nombre, usar el username
    if not nombre:
        nombre = username.split('_')[0].capitalize()

    # Intentar identificar género usando Genderize
    try:
        genero = Genderize().get([nombre])[0]['gender']
        if genero == 'male':
            genero = 'hombre'
        elif genero == 'female':
            genero = 'mujer'
        else:
            genero = 'desconocido'
    except Exception as e:
        print(f"Error al intentar determinar género: {e}")
        genero = 'desconocido'

    return nombre, genero

def enviar_mensaje_personalizado(user_id, username, bio=None, intereses=None, ultima_publicacion=None):
    """
    Envía un mensaje personalizado a un usuario de Instagram.

    Args:
        user_id (str): ID del usuario en Instagram.
        username (str): Nombre de usuario del usuario.
        bio (str, opcional): Biografía del usuario.
        intereses (list, opcional): Lista de intereses del usuario.
        ultima_publicacion (str, opcional): Descripción de la última publicación del usuario.

    Returns:
        bool: True si el mensaje fue enviado con éxito, False en caso de error.
    """
    print(f"Iniciando el envío de mensaje a @{username}...")

    # Generar mensaje personalizado
    mensaje = generar_mensaje_ia(username, bio=bio, intereses=intereses, ultima_publicacion=ultima_publicacion)

    # Intentar enviar el mensaje
    try:
        cl.direct_send(mensaje, [user_id])
        print(f"✅ Mensaje enviado exitosamente a @{username}: {mensaje}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar mensaje a @{username}: {e}")
        return False
