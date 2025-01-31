from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from database.models import guardar_token, obtener_token,collection_users, borrar_token
from instagrapi.exceptions import TwoFactorRequired
from config import PROXIES
from flask import session
from instagrapi.exceptions import LoginRequired, TwoFactorRequired
import logging
from instagrapi.exceptions import ChallengeRequired
cl = Client()

from instagrapi.exceptions import TwoFactorRequired

def autenticar_con_2fa(username, password):
    """
    Autentica en Instagram y maneja el caso en que se requiera 2FA.
    """
    try:
        print(f"🔐 Iniciando sesión para @{username}")
        cl.login(username, password)
        print(f"✅ Sesión iniciada correctamente para @{username}")
        return {"authenticated": True, "2fa_required": False}
    except TwoFactorRequired as e:
        print(f"⚠️ Se requiere 2FA para @{username}")
        return {"authenticated": False, "2fa_required": True, "error": str(e)}
    except Exception as e:
        print(f"❌ Error durante la autenticación: {e}")
        return {"authenticated": False, "error": str(e)}

def manejar_2fa(codigo_2fa):
    """
    Enviar el código de 2FA cuando sea requerido.
    """
    try:
        # Usamos el método correcto para completar el login con 2FA
        result = cl.complete_two_factor_login(codigo_2fa)

        if result:
            print("✅ Código 2FA verificado correctamente.")
            return {"authenticated": True}
        else:
            return {"authenticated": False, "error": "Código incorrecto o sesión inválida."}
    except Exception as e:
        print(f"❌ Error al verificar el código 2FA: {e}")
        return {"authenticated": False, "error": str(e)}



def reautenticar_sesion():
    """
    Reautentica la sesión de Instagram utilizando las credenciales almacenadas.
    """
    username = session.get('instagram_user')
    password = session.get('instagram_password')

    if not username or not password:
        print("[ERROR] No se encontraron las credenciales en la sesión.")
        return False

    try:
        print(f"🔑 Reautenticando sesión de Instagram para @{username}...")
        cl.login(username, password)
        session['instagram_client'] = cl.get_settings()  # Actualiza los datos de sesión en Flask
        print("✅ Sesión reautenticada correctamente.")
        return True
    except Exception as e:
        print(f"❌ Error al reautenticar la sesión: {e}")
        return False
    

def verificar_autenticacion():
    """
    Verifica si la sesión de Instagram es válida. Si no lo es, intenta renovarla.
    """
    try:
        cl.get_timeline_feed()  # Prueba la sesión activa
        print("✅ Sesión de Instagram válida.")
        return True
    except LoginRequired:
        print("⚠️ Sesión no válida. Intentando renovar...")
        return reautenticar_sesion()
    except Exception as e:
        print(f"❌ Error al verificar la autenticación: {e}")
        return False


def iniciar_sesion(username, password):
    try:
        cl.login(username, password)
        print("Sesión iniciada correctamente.")
    except ChallengeRequired:
        print("Se requiere resolver un desafío de seguridad.")
        challenge_url = cl.last_json.get("challenge", {}).get("url")
        if challenge_url:
            try:
                cl.challenge_resolve(challenge_url)
                print("Desafío resuelto automáticamente.")
            except Exception as e:
                print(f"No se pudo resolver el desafío automáticamente: {e}")
                print("Es necesario que inicies sesión manualmente.")
                raise
    except Exception as e:
        print(f"Error al iniciar sesión: {e}")
        raise


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def iniciar_sesion_persistente(username, password):
    try:
        # Intentar cargar sesión
        settings = obtener_token(username)
        if settings:
            try:
                cl.set_settings(settings)
                cl.get_timeline_feed()
                logging.info(f"Sesión restaurada para @{username}")
                return True
            except EOFError:
                logging.error(f"Error EOF al cargar sesión para @{username}. Se borrará la sesión.")
                borrar_token(username)  # Función para borrar el token guardado
            except Exception as e:
                logging.error(f"Error al cargar sesión para @{username}: {e}")
        else:
            logging.info(f"No se encontró sesión guardada para @{username}")
    except Exception as e:
        logging.error(f"Error al intentar cargar sesión para @{username}: {e}")

    # Iniciar sesión desde cero si falla la carga o no hay sesión
    try:
        cl.login(username, password)
        guardar_token(username, cl.get_settings())
        logging.info(f"Sesión iniciada y guardada para @{username}")
        return True
    except Exception as e:
        logging.error(f"Error al iniciar sesión para @{username}: {e}")
        return False



def guardar_sesion(username):
    settings = cl.get_settings()
    # Guarda las configuraciones de sesión en tu base de datos
    collection_users.update_one({"username": username}, {"$set": {"settings": settings}}, upsert=True)
    print(f"✅ Sesión guardada para @{username}")

def cargar_sesion(username):
    user = collection_users.find_one({"username": username})
    if user and "settings" in user:
        cl.set_settings(user["settings"])
        print(f"✅ Sesión cargada para @{username}")




def autenticar_bot(username, password):
    print(f"[DEBUG] 🔐 Intentando iniciar sesión persistente para @{username}...")
    try:
        # Intentar restaurar una sesión persistente
        iniciar_sesion_persistente(username, password)
        print("[DEBUG] ✅ Sesión persistente restaurada o iniciada correctamente.")
        return {"authenticated": True, "message": "✅ Sesión iniciada correctamente."}
    except TwoFactorRequired as e:
        print("[DEBUG] ⚠️ Se requiere 2FA para este usuario.")
        return {"2fa_required": True, "message": "⚠️ Se requiere autenticación 2FA. Ingresa el código."}
    except Exception as e:
        print(f"[DEBUG] ❌ Error al intentar restaurar sesión persistente: {e}")
    
    # Si no se pudo restaurar la sesión persistente, intentar una nueva autenticación
    print(f"[DEBUG] 🔐 Iniciando nueva sesión en Instagram para @{username}...")
    try:
        cl.login(username, password)
        print("[DEBUG] ✅ Nueva sesión iniciada correctamente en Instagram.")
        return {"authenticated": True, "message": "✅ Nueva sesión iniciada correctamente."}
    except TwoFactorRequired as e:
        print("[DEBUG] ⚠️ Se requiere 2FA para este usuario.")
        return {"2fa_required": True, "message": "⚠️ Se requiere autenticación 2FA. Ingresa el código."}
    except Exception as e:
        print(f"[DEBUG] ❌ Error al autenticar en Instagram: {e}")
        return {"authenticated": False, "error": str(e)}

def reautenticar_si_es_necesario():
    try:
        cl.get_timeline_feed()
        print("✅ Sesión activa verificada.")
    except LoginRequired:
        print("⚠️ Sesión expirada. Reintentando autenticación...")
        username = session.get('instagram_user')
        password = session.get('instagram_password')
        if username and password:
            cl.login(username, password)
            print("✅ Sesión renovada exitosamente.")
        else:
            raise Exception("⚠️ Credenciales no disponibles para renovar la sesión.")


def verificar_autenticacion():
    try:
        cl.get_timeline_feed()  # Valida la sesión activa
        print("✅ Sesión de Instagram válida.")
        return True
    except LoginRequired:
        print("⚠️ Sesión no válida. Reintentando autenticación...")
        username = session.get('instagram_user')
        password = session.get('instagram_password')
        if username and password:
            try:
                cl.login(username, password)
                print("✅ Sesión renovada con éxito.")
                return True
            except Exception as e:
                print(f"❌ Error al reautenticar: {e}")
        return False
    except Exception as e:
        print(f"❌ Error al verificar la autenticación: {e}")
        return False




def manejar_login(username, password, intentos=3):
    while intentos > 0:
        if verificar_autenticacion():
            print(f"✅ Sesión ya válida para @{username}.")
            return True
        try:
            print(f"Intentando iniciar sesión para @{username}...")
            iniciar_sesion(username, password)
            print(f"✅ Sesión iniciada correctamente para @{username}.")
            return True
        except Exception as e:
            print(f"❌ Error al iniciar sesión: {e}")
            intentos -= 1
            if intentos > 0:
                print(f"Reintentando... Intentos restantes: {intentos}")
            else:
                print("⚠️ No se pudo iniciar sesión tras varios intentos.")
                raise


def verificar_sesion():
    """
    Verifica si la sesión de Instagram es válida.
    """
    try:
        cl.get_timeline_feed()
        print("✅ Sesión verificada correctamente.")
        return True
    except LoginRequired:
        print("❌ Sesión no válida. Es necesario iniciar sesión nuevamente.")
        return False
    except Exception as e:
        print(f"❌ Error al verificar la sesión: {e}")
        return False




def configurar_cliente():
    cl.set_device({
        "app_version": "269.0.0.18.75",
        "android_version": 26,
        "android_release": "8.0.0",
        "dpi": "480dpi",
        "resolution": "1080x1920",
        "manufacturer": "Samsung",
        "device": "Galaxy S10",
        "model": "SM-G973F",
        "cpu": "exynos9820",
        "version_code": "269185202"
    })
    cl.set_user_agent(
        "Instagram 269.0.0.18.75 Android (26/8.0.0; 480dpi; 1080x1920; Samsung; Galaxy S10; exynos9820; en_US; 269185202)"
    )
    cl.set_proxy(PROXIES["http"])
