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


def manejar_2fa(username, codigo_2fa):
    """Maneja la verificación del código 2FA para Instagram."""
    try:
        cl = Client()
        settings = session.get('instagram_client')

        if not settings:
            logging.error(f"❌ No se encontró sesión para {username} antes de verificar 2FA.")
            return {"authenticated": False, "error": "La sesión de Instagram no está disponible. Inténtalo de nuevo."}

        cl.set_settings(settings)  # Restaurar la sesión antes de enviar el código

        # Intentar iniciar sesión con el código 2FA
        result = cl.two_factor_login(codigo_2fa)

        if result:
            logging.info(f"✅ Código 2FA correcto para {username}. Sesión actualizada.")
            session['instagram_client'] = cl.get_settings()
            session['two_fa_pending'] = False
            return {"authenticated": True}
        else:
            return {"authenticated": False, "error": "Código incorrecto o sesión inválida."}

    except Exception as e:
        logging.exception(f"❌ Error al verificar el código 2FA para {username}: {e}")
        return {"authenticated": False, "error": f"Error inesperado: {e}"}


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
    except ChallengeRequired as e:
        print(f"Se requiere resolver un desafío de seguridad: {e}")
        # Intenta resolver el desafío automáticamente o proporciona instrucciones al usuario
        raise  # Vuelve a lanzar la excepción para que se maneje en otro lugar
    except TwoFactorRequired as e:
        print(f"Se requiere autenticación de dos factores: {e}")
        raise
    except LoginRequired as e:
        print(f"Error de inicio de sesión: {e}")
        raise
    except Exception as e:
        print(f"Error inesperado al iniciar sesión: {e}")
        raise

def iniciar_sesion_persistente(username, password):
    """
    Intenta iniciar sesión utilizando una sesión guardada, o inicia una nueva sesión.
    """
    try:
        # Cargar configuración guardada de la sesión
        settings = obtener_token(username)
        if settings:
            cl.set_settings(settings)
            cl.get_timeline_feed()  # Valida la sesión cargada
            print(f"✅ Sesión restaurada para @{username}.")
            return True
        else:
            print(f"No se encontró sesión guardada para @{username}. Iniciando nueva sesión.")
    except Exception as e:
        print(f"⚠️ Error al restaurar sesión: {e}")

    # Si no hay sesión válida, iniciar una nueva
    try:
        cl.login(username, password)
        session['instagram_client'] = cl.get_settings()  # Guardar en la sesión Flask
        guardar_token(username, cl.get_settings())  # Guardar en la base de datos
        print("✅ Sesión iniciada y guardada correctamente.")

        return True
    except Exception as e:
        print(f"❌ Error al iniciar sesión: {e}")
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
    # Cargar la configuración de sesión guardada
    settings = session.get('instagram_client')  # Cargar sesión guardada
    if settings:
        cl.set_settings(settings)  # Restaurar sesión antes de verificar autenticación

    try:
        # Probar la sesión activa
        cl.get_timeline_feed()  # Valida la sesión activa
        print("✅ Sesión de Instagram válida.")
        return True
    except LoginRequired:
        print("⚠️ Sesión no válida. Intentando renovar...")
        # Intentar renovar la sesión si no es válida
        username = session.get('instagram_user')
        password = session.get('instagram_password')
        if username and password:
            try:
                cl.login(username, password)  # Reautenticar
                # Guardar la nueva configuración de sesión
                session['instagram_client'] = cl.get_settings()  
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
    cl.set_proxy(PROXIES.get("https", PROXIES.get("http")))

