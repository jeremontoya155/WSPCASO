import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from celery_tasks import seguir_cuenta
from datetime import datetime, timedelta

# Programar una tarea para dentro de 2 minutos
tiempo_ejecucion = datetime.utcnow() + timedelta(minutes=2)
tarea = seguir_cuenta.apply_async(args=["123456789", "usuario_ejemplo"], eta=tiempo_ejecucion)

print(f"Tarea programada con ID: {tarea.id}")
