
from config import MONGO_URI, DB_NAME
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo.errors import DuplicateKeyError
from datetime import datetime
from pymongo import MongoClient
import os

# Cargar variables de entorno
MONGO_URI = os.getenv("MONGO_URI")  # Asegúrate de que esta variable esté configurada
DB_NAME = os.getenv("DB_NAME")      # Asegúrate de que esta variable esté configurada

# Verificar que las variables no estén vacías
if not MONGO_URI or not DB_NAME:
    raise ValueError("Las variables de entorno MONGO_URI y DB_NAME deben estar configuradas.")

# Conexión al cliente de MongoDB
try:
    client = MongoClient(MONGO_URI)
    print("Conexión exitosa a MongoDB.")
except Exception as e:
    print("Error al conectar con MongoDB:", str(e))
    raise e

# Conexión a la base de datos
try:
    db = client[DB_NAME]
    print(f"Conectado a la base de datos: {DB_NAME}")
except Exception as e:
    print("Error al conectar a la base de datos:", str(e))
    raise e

# Colecciones de la base de datos
try:
    collection_users = db["users"]
    collection_seguidos = db["seguidos"]
    collection_tokens = db["tokens"]
    collection_acciones = db["acciones_realizadas"]
    collection_filtros = db["filters"]
    collection_logs = db["logs"]
    collection_sugerencias = db["sugerencias_diarias"]
    print("Colecciones configuradas correctamente.")
except Exception as e:
    print("Error al configurar las colecciones:", str(e))
    raise e

# Listar colecciones disponibles en la base de datos
try:
    print("Colecciones existentes en la base de datos:", db.list_collection_names())
except Exception as e:
    print("Error al interactuar con las colecciones:", str(e))
    raise e


# Funciones para manejo de tokens
def guardar_token(username, settings):
    """
    Guarda la configuración de sesión (settings) en MongoDB.
    """
    collection_tokens.update_one(
        {"username": username},
        {"$set": {"settings": settings}},  # Almacena las configuraciones de sesión
        upsert=True
    )
    print(f"Configuración de sesión guardada para @{username}.")

def obtener_token(username):
    """
    Obtiene la configuración de sesión desde MongoDB.
    """
    token_doc = collection_tokens.find_one({"username": username})
    return token_doc["settings"] if token_doc else None

def guardar_usuario_seguido(username):
    try:
        if not collection_seguidos.find_one({"username": username}):
            collection_seguidos.insert_one({"username": username})
            print(f"Usuario @{username} guardado como seguido.")
        else:
            print(f"Usuario @{username} ya está registrado.")
    except Exception as e:
        print(f"Error al guardar el usuario @{username}: {e}")
        return False
    return True

def limpiar_sesion(username):
    collection_tokens.delete_one({"username": username})
    print(f"Sesión eliminada para @{username}.")


def registrar_usuario(username, password):
    """
    Registra un nuevo usuario en la base de datos.
    Retorna (True, mensaje) si el registro es exitoso, de lo contrario (False, mensaje).
    """
    try:
        # Verifica si el usuario ya existe
        if collection_users.find_one({"username": username}):
            return False, "El usuario ya existe."

        # Inserta el nuevo usuario en la base de datos
        hashed_password = generate_password_hash(password)
        collection_users.insert_one({"username": username, "password": hashed_password})
        return True, "Usuario registrado exitosamente."
    except DuplicateKeyError:
        return False, "El usuario ya está registrado."
    except Exception as e:
        print(f"Error al registrar usuario: {e}")
        return False, "Error al registrar el usuario. Inténtalo de nuevo más tarde."


def autenticar_usuario(username, password):
    """
    Verifica si las credenciales del usuario son correctas.
    """
    user = collection_users.find_one({"username": username})
    if not user or not check_password_hash(user["password"], password):
        return False
    return True

# database/models.py

def verificar_accion(user_id, accion, detalle=None):
    """
    Verifica si una acción ya fue realizada para un usuario.
    Args:
        user_id (str): ID del usuario objetivo.
        accion (str): Tipo de acción ('me_gusta', 'ver_historia').
        detalle (dict): Detalles adicionales de la acción.
    Returns:
        bool: True si la acción ya fue registrada, False de lo contrario.
    """
    query = {"user_id": user_id, "accion": accion}
    if detalle:
        query["detalle"] = detalle

    return collection_acciones.find_one(query) is not None


def registrar_accion(user_id, accion, detalle=None):
    """
    Registra una acción realizada para evitar duplicados.
    """
    try:
        registro = {
            "user_id": user_id,
            "accion": accion,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "detalle": detalle or {}
        }
        collection_acciones.insert_one(registro)
        print(f"✅ Acción '{accion}' registrada para el usuario {user_id}.")
    except Exception as e:
        print(f"❌ Error al registrar la acción: {e}")
