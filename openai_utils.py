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
    Construye un prompt dinámico en inglés para generar un mensaje personalizado y breve.
    """
    contextos = {
        "friendly": "Be casual, warm, and engaging. Keep the message brief and lighthearted.",
        "technical": "Provide concise technical insights or advice in a professional tone.",
        "motivational": "Create short, inspiring, and supportive messages to uplift the user.",
        "expert": "Respond like an expert, offering precise and actionable advice briefly."
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
    Generate a brief, specific, and engaging response considering the user's bio and interests.
    """
def generar_mensaje_ia(username, bio=None, intereses=None, ultima_publicacion=None, rol="friendly", prompt=None, nombre=None):
    """Genera un mensaje breve y personalizado utilizando OpenAI."""
    try:
        if prompt:
            contenido = f"Keep this message in English, improve it but keep the same meaning: {prompt}"
        else:
            contenido = construir_prompt(username=username, bio=bio, intereses=intereses, ultima_publicacion=ultima_publicacion, rol=rol)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant that always responds in English, improving messages without changing their meaning."},
                {"role": "user", "content": contenido}
            ],
            temperature=0.7,
            max_tokens=200  # Aumentado para comentarios más largos
        )

        mensaje = response.choices[0].message.content.strip()

        # Comentarios más largos, se elimina o aumenta el límite según necesidad
        # if len(mensaje.split()) > 50:  # Ajusta este número si es necesario
        #     mensaje = " ".join(mensaje.split()[:50]) + "..."

        return mensaje
    except Exception as e:
        print(f"❌ Error generating message with OpenAI: {e}")
        return "Error generating the message."