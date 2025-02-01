import os
from dotenv import load_dotenv
from celery import Celery
import requests
from requests.auth import HTTPProxyAuth
from instagrapi import Client

# Cargar las variables de entorno desde .env
load_dotenv()

# Configuración de Flask
DEBUG = True
UPLOAD_FOLDER = './mensajes'
LOG_FOLDER = './mensajes/logs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

# Configuración de MongoDB
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

# Configuración de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configuración de Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')  # Lee desde el archivo .env
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')  # Lee desde el archivo .env
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'

def make_celery(app):
    """
    Configura una instancia de Celery con la configuración de Flask.
    """
    celery = Celery(
        app.import_name,
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_BACKEND
    )
    celery.conf.update(app.config)
    return celery

# Cargar proxy desde .env
PROXY = os.getenv("PROXY")
PROXIES = {
    "http": PROXY,
    "https": PROXY
}

# DEBUG: Verificar configuración del proxy
print("[DEBUG] PROXY configurado:", PROXIES)

# Probar conexión con proxy
try:
    response = requests.get("https://www.instagram.com", proxies=PROXIES)
    print("[DEBUG] Estado de la respuesta al probar el proxy:", response.status_code)
except Exception as e:
    print("[ERROR] Falló la prueba de conexión con el proxy:", e)

# Inicialización del cliente de Instagram
cl = Client()

