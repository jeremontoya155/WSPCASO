# Logs.py (Gestión de Logs)
from database.models import collection_logs
from datetime import datetime


def guardar_log(log):
    """
    Guarda un registro de las interacciones realizadas.
    """
    try:
        for entrada in log:
            collection_logs.insert_one({
                "username": entrada["username"],
                "mensaje": entrada["mensaje"],
                "fecha": datetime.now()
            })
        print(f"{len(log)} interacciones registradas.")
    except Exception as e:
        print(f"Error al guardar log: {e}")
