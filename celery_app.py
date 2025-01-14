from celery import Celery
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Crear instancia de Celery
celery = Celery(
    'code_nuevo',  # Nombre de la aplicación
    broker=os.getenv('CELERY_BROKER_URL'),  # URL del broker
    backend=os.getenv('CELERY_RESULT_BACKEND')  # Backend para almacenar resultados
)

# Configuración adicional de Celery
celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json']
)

# Importar tareas para registrarlas
import tasks.celery_tasks
