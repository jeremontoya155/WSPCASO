import random
import time
from datetime import datetime, timedelta

# Registro de usuarios privados detectados
usuarios_privados = set()  # Este conjunto almacena IDs de usuarios privados

registro_acciones = {
    "follow": [],
    "like": [],
    "comment": [],
    "direct_message": [],
    "view_story": []
}

LIMITES_ACCIONES_POR_HORA = {
    "follow": 50,
    "like": 100,
    "comment": 30,
    "direct_message": 20,
    "view_story": 40
}


PAUSAS_POR_ACCION = {
    "like": (10, 25),  # Pausa entre 15 y 45 segundos para 'Me gusta'
    "comment": (15, 50),  # Pausa entre 30 y 90 segundos para comentarios
    "direct_message": (10, 65),  # Pausa más larga para mensajes directos
}


def acciones_aleatorias(cantidad=2):  # ✅ Cambiado a 2 para asignar dos acciones por usuario
    """
    Genera acciones aleatorias para un usuario.
    """
    ACCIONES_DISPONIBLES = ["like", "comment", "direct_message"]
    random.shuffle(ACCIONES_DISPONIBLES)  # Mezclar acciones disponibles

    # Eliminar combinaciones no permitidas (ej. comment + direct_message)
    if "comment" in ACCIONES_DISPONIBLES and "direct_message" in ACCIONES_DISPONIBLES:
        ACCIONES_DISPONIBLES.remove(random.choice(["comment", "direct_message"]))

    # Seleccionar la cantidad de acciones según lo configurado
    cantidad_acciones = min(cantidad, len(ACCIONES_DISPONIBLES))
    acciones_seleccionadas = random.sample(ACCIONES_DISPONIBLES, cantidad_acciones)

    # Generar pausas correctas
    tiempos_de_pausa = {
        accion: random.uniform(*PAUSAS_POR_ACCION.get(accion, (20, 60)))
        for accion in acciones_seleccionadas
    }

    print(f"[DEBUG] Acciones generadas: {acciones_seleccionadas} con pausas: {tiempos_de_pausa}")
    
    return acciones_seleccionadas, tiempos_de_pausa


