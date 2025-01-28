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
    "like": (15, 50),  # Pausa entre 15 y 45 segundos para 'Me gusta'
    "comment": (40, 120),  # Pausa entre 30 y 90 segundos para comentarios
    "follow": (20, 60),  # Pausa entre 20 y 60 segundos para seguir usuarios
    "direct_message": (40, 160),  # Pausa más larga para mensajes directos
    "view_story": (10, 30),  # Pausa breve para ver historias
}


def verificar_limite_accion(accion):
    ahora = datetime.now()
    registro_acciones[accion] = [
        t for t in registro_acciones[accion] if t > ahora - timedelta(hours=1)
    ]
    return len(registro_acciones[accion]) < LIMITES_ACCIONES_POR_HORA[accion]

 # Ajusta el rango de pausas entre acciones

PAUSA_ENTRE_ACCIONES = (20, 60)  # Pausa entre acciones en segundos
PAUSA_ENTRE_USUARIOS = (90, 150)  # Pausa entre usuarios en segundos
ACCIONES_DISPONIBLES = ["like", "comment", "follow", "direct_message", "view_story"]  # Acciones posibles

# Variables globales para control de tiempo
hora_inicio = None

def iniciar_sesion_bot():
    """
    Marca el inicio del ciclo del bot.
    """
    global hora_inicio
    hora_inicio = datetime.now()
    print(f"⏳ Bot iniciado a las {hora_inicio}.")

def tiempo_restante(duracion_maxima):
    """
    Calcula el tiempo restante en el ciclo del bot.
    """
    if not hora_inicio:
        return duracion_maxima * 3600  # Retorna el tiempo total en segundos
    tiempo_transcurrido = datetime.now() - hora_inicio
    return max(0, (timedelta(hours=duracion_maxima) - tiempo_transcurrido).total_seconds())

def acciones_aleatorias():
    """
    Genera una lista única y aleatoria de acciones para un usuario,
    asegurando que 'comment' y 'direct_message' no se incluyan juntas.
    """
    ACCIONES_DISPONIBLES = ["like", "comment", "follow", "view_story", "direct_message"]
    random.shuffle(ACCIONES_DISPONIBLES)  # Mezclar acciones disponibles

    # Limitar exclusividad entre 'comment' y 'direct_message'
    if "comment" in ACCIONES_DISPONIBLES and "direct_message" in ACCIONES_DISPONIBLES:
        ACCIONES_DISPONIBLES.remove(random.choice(["comment", "direct_message"]))

    cantidad_acciones = random.randint(1, 3)  # Elegir entre 1 y 3 acciones
    acciones = random.sample(ACCIONES_DISPONIBLES, cantidad_acciones)
    print(f"[DEBUG] Acciones generadas: {acciones}")
    return acciones


def pausa_por_accion(tipo_accion):
    """
    Genera una pausa dinámica según el tipo de acción.
    """
    from instagram.config_bot import PAUSAS_POR_ACCION

    if tipo_accion not in PAUSAS_POR_ACCION:
        print(f"⚠️ Acción desconocida: {tipo_accion}. Usando pausa predeterminada.")
        rango_pausa = (20, 145)  # Pausa predeterminada
    else:
        rango_pausa = PAUSAS_POR_ACCION[tipo_accion]

    pausa = random.uniform(*rango_pausa)
    print(f"⏳ Pausando {pausa:.2f} segundos para la acción '{tipo_accion}'...")
    time.sleep(pausa)


def generar_reporte(acciones_realizadas, total_usuarios):
    """
    Genera un resumen de las acciones realizadas.
    """
    print("\n📊 Resumen del ciclo:")
    print(f"Usuarios procesados: {total_usuarios}")
    for accion, cantidad in acciones_realizadas.items():
        print(f"- {accion.capitalize()}: {cantidad}")

def validar_limites(accion, acciones_realizadas):
    """
    Verifica si una acción específica está dentro de los límites permitidos.
    """
    return acciones_realizadas.get(accion, 0) < LIMITES_ACCIONES_POR_HORA.get(accion, float('inf'))

def registrar_error(usuario, accion, error):
    with open("errores.log", "a") as archivo:
        archivo.write(f"Usuario: {usuario['username']}, Acción: {accion}, Error: {error}\n")

# Guardar usuarios procesados en un archivo
def guardar_usuarios_procesados():
    with open("usuarios_procesados.txt", "w") as archivo:
        archivo.write("\n".join(usuarios_procesados))

# Cargar usuarios procesados al iniciar
def cargar_usuarios_procesados():
    try:
        with open("usuarios_procesados.txt", "r") as archivo:
            return set(archivo.read().splitlines())
    except FileNotFoundError:
        return set()

# Inicializar el conjunto
usuarios_procesados = cargar_usuarios_procesados()

# Antes de finalizar el programa, guarda los usuarios procesados
guardar_usuarios_procesados()

import json

def guardar_usuarios_privados():
    with open("usuarios_privados.json", "w") as archivo:
        json.dump(list(usuarios_privados), archivo)

def cargar_usuarios_privados():
    global usuarios_privados
    try:
        with open("usuarios_privados.json", "r") as archivo:
            usuarios_privados = set(json.load(archivo))
    except FileNotFoundError:
        print("[DEBUG] No se encontró el archivo de usuarios privados. Iniciando vacío.")
        usuarios_privados = set()
