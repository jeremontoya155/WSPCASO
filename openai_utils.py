import openai
from config import OPENAI_API_KEY
from genderize import Genderize
from instagrapi import Client
import os
from openai import OpenAI

# Configurar la clave de API de OpenAI

cl = Client()
# Mensajes predefinidos en caso de error o como alternativa
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")  # Se recomienda configurar tu API Key en .env
)

def construir_prompt(username, bio=None, intereses=None, ultima_publicacion=None, rol="friendly", nombre=None):
    """
    Construye un prompt dinámico en inglés para generar un mensaje personalizado.
    """
    contextos = {
        "friendly": "Be casual, warm, and engaging. Use emojis where appropriate to make the message feel lighthearted.",
        "technical": "Provide technical insights or advice, keeping the tone professional yet concise.",
        "motivational": "Create short, inspiring, and supportive messages to uplift the user.",
        "expert": "Respond like an expert, providing actionable and precise advice based on the context."
    }
    contexto = contextos.get(rol, "Be casual and concise.")

    # Usar el nombre si está disponible; de lo contrario, usar "friend"
    saludo = nombre if nombre else "friend"

    # Personalizar el prompt con detalles del usuario
    return f"""
    {contexto}
    User: {saludo}.
    Bio: {bio or 'Not available'}.
    Interests: {intereses or 'Not specified'}.
    Latest post: {ultima_publicacion or 'Not specified'}.
    Your task is to generate a specific and engaging response considering the user's bio and interests.
    """


def generar_mensaje_ia(username, bio=None, intereses=None, ultima_publicacion=None, rol="friendly", prompt=None, nombre=None):
    """
    Genera un mensaje personalizado utilizando OpenAI, priorizando el nombre de la cuenta si está disponible.
    """
    try:
        # Usar username como prioridad, luego nombre, y finalmente "friend"
        saludo = username if username else (nombre if nombre else "friend")

        # Si hay un prompt personalizado, úsalo directamente
        if prompt:
            contenido = prompt
        else:
            # Construir el prompt estándar
            contenido = construir_prompt(username=saludo, bio=bio, intereses=intereses, ultima_publicacion=ultima_publicacion, rol=rol)
        
        # Llamada a la API de OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant generating specific, personalized, and friendly responses."},
                {"role": "user", "content": contenido}
            ],
            temperature=0.7,
            max_tokens=50
        )

        # Obtener y devolver la respuesta generada
        mensaje = response.choices[0].message.content.strip()

        # Enriquecer el mensaje con datos adicionales
        if bio:
            mensaje += f" By the way, I noticed your bio mentions: {bio}."
        if intereses:
            mensaje += f" It's great that you're interested in {intereses}!"
        if ultima_publicacion:
            mensaje += f" I also saw your last post: '{ultima_publicacion}'."

        return mensaje
    except Exception as e:
        print(f"❌ Error generating message with OpenAI: {e}")
        return "There was an error generating the message."



def detectar_genero(nombre):
    """
    Detecta el género del usuario basado en su nombre.
    """
    if any(nombre.lower().endswith(sufijo) for sufijo in ["a", "ella", "ana", "maría", "isa"]):  # Ejemplos
        return "femenino"
    return "masculino"




