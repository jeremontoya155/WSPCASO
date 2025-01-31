
from config import MONGO_URI, DB_NAME
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo.errors import DuplicateKeyError
from datetime import datetime
from pymongo import MongoClient
import os
import logging



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
    collection_tokens = db["tokens"]
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

def borrar_token(username):
    nombre_archivo = f"sesion_{username}.json"  # Nombre del archivo para este usuario
    ruta_archivo = os.path.join("ruta/a/tus/archivos/sesion", nombre_archivo)  # Ruta completa al archivo

    try:
        os.remove(ruta_archivo)  # Elimina el archivo
        logging.info(f"Sesión borrada para @{username} (archivo: {nombre_archivo})")
    except FileNotFoundError:
        logging.warning(f"No se encontró archivo de sesión para @{username}")
    except Exception as e:
        logging.error(f"Error al borrar sesión para @{username}: {e}")
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

