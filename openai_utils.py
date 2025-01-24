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

def generar_mensaje_ia(username, bio=None, intereses=None, ultima_publicacion=None):
    """
    Genera un mensaje personalizado utilizando la API de OpenAI.
    """
    try:
        # Construir el prompt
        prompt = f"Genera un mensaje amigable para el usuario @{username}. Biografía: {bio or 'No disponible'}. Intereses: {intereses or 'No especificados'}. Última publicación: {ultima_publicacion or 'No especificada'}."

        # Solicitar a OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        mensaje = response["choices"][0]["message"]["content"].strip()
        print(f"Mensaje generado por OpenAI: {mensaje}")
        return mensaje

    except Exception as e:
        print(f"❌ Error al generar mensaje con OpenAI: {e}")
        return "Error al generar el mensaje con OpenAI."



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
