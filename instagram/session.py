from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from database.models import guardar_token, obtener_token, limpiar_sesion
from instagrapi.exceptions import ChallengeRequired
from instagrapi.exceptions import TwoFactorRequired
from config import PROXIES
import requests
from instagrapi.exceptions import LoginRequired, TwoFactorRequired

cl = Client()

def autenticar_con_2fa(username, password):
    """
    Autentica en Instagram con manejo de 2FA si es requerido.
    """
    try:
        cl.login(username, password)
        print("✅ Sesión iniciada correctamente.")
    except TwoFactorRequired:
        code = input("Introduce el código 2FA de tu aplicación autenticadora: ")
        cl.two_factor_login(code)
        print("✅ Sesión iniciada con 2FA correctamente.")
    except Exception as e:
        print(f"❌ Error durante la autenticación: {e}")
        raise



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

def iniciar_sesion_persistente(username, password):
    """
    Intenta iniciar sesión utilizando una sesión guardada, o inicia una nueva sesión.
    """
    try:
        # Intenta cargar la sesión desde la base de datos o archivo
        settings = obtener_token(username)
        if settings:
            cl.set_settings(settings)
            cl.get_timeline_feed()  # Valida la sesión
            print(f"✅ Sesión restaurada para @{username}.")
            return
        else:
            print(f"No se encontró sesión guardada para @{username}, iniciando una nueva.")
    except Exception as e:
        print(f"⚠️ Error al restaurar sesión: {e}")

    # Si no hay sesión o es inválida, inicia una nueva
    try:
        cl.login(username, password)
        guardar_token(username, cl.get_settings())  # Guarda la nueva sesión
        print("✅ Sesión iniciada y guardada correctamente.")
    except Exception as e:
        print(f"❌ Error al iniciar sesión: {e}")
        raise




def autenticar_bot(username, password):
    """
    Autentica al bot en Instagram usando las credenciales proporcionadas.
    """
    try:
        print(f"Iniciando sesión en Instagram para @{username}...")
        cl.login(username, password)
        print("✅ Sesión iniciada correctamente.")
    except TwoFactorRequired:
        code = input("Introduce el código 2FA de tu aplicación autenticadora: ")
        cl.two_factor_login(code)
        print("✅ Sesión iniciada correctamente con 2FA.")
    except LoginRequired:
        print("❌ Se requiere iniciar sesión nuevamente. Intenta resolver manualmente.")
        raise
    except Exception as e:
        print(f"❌ Error durante la autenticación en Instagram: {e}")
        raise



def verificar_autenticacion():
    try:
        cl.get_timeline_feed()  # Validar sesión
        print("✅ Autenticación verificada correctamente.")
        return True
    except LoginRequired:
        print("⚠️ La sesión no es válida. Se requiere login.")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al verificar autenticación: {e}")
        return False



def reconectar_si_es_necesario(func):
    """
    Decorador para reintentar una función en caso de error de conexión o sesión expirada.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except LoginRequired:
            print("⚠️ Sesión expirada. Reintentando autenticación...")
            if not verificar_autenticacion():
                raise Exception("⚠️ No se pudo autenticar automáticamente.")
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            raise
    return wrapper




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
