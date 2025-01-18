from instagrapi import Client
from instagrapi.exceptions import LoginRequired
<<<<<<< HEAD
from database.models import guardar_token, obtener_token, limpiar_sesion
from instagrapi.exceptions import ChallengeRequired
from instagrapi.exceptions import TwoFactorRequired
from config import PROXIES
import requests
=======
from database.models import guardar_token, obtener_token,collection_users
from instagrapi.exceptions import ChallengeRequired
from instagrapi.exceptions import TwoFactorRequired
from config import PROXIES
from flask import session
>>>>>>> 3f8b5aa (mejoras)
from instagrapi.exceptions import LoginRequired, TwoFactorRequired

cl = Client()

<<<<<<< HEAD
def autenticar_con_2fa(username, password):
    """
    Autentica en Instagram y gestiona el caso en que se requiera 2FA.
    """
    try:
        print(f"🔐 Iniciando sesión para @{username}")
        cl.login(username, password)  # Intentar autenticación normal
=======
from instagrapi.exceptions import TwoFactorRequired

def autenticar_con_2fa(username, password):
    """
    Autentica en Instagram y maneja el caso en que se requiera 2FA.
    """
    try:
        print(f"🔐 Iniciando sesión para @{username}")
        cl.login(username, password)
>>>>>>> 3f8b5aa (mejoras)
        print(f"✅ Sesión iniciada correctamente para @{username}")
        return {"authenticated": True, "2fa_required": False}
    except TwoFactorRequired as e:
        print(f"⚠️ Se requiere 2FA para @{username}")
        return {"authenticated": False, "2fa_required": True, "error": str(e)}
    except Exception as e:
        print(f"❌ Error durante la autenticación: {e}")
<<<<<<< HEAD
        raise Exception(f"Error de autenticación: {e}")

def validar_codigo_2fa(code):
    """
    Verifica el código 2FA y completa la autenticación.
    """
    try:
        print(f"🔑 Verificando código 2FA: {code}")
        cl.two_factor_login(code)  # Validar el código 2FA con la API de Instagram
        print("✅ Código 2FA verificado correctamente")
        return {"authenticated": True, "message": "Sesión iniciada correctamente con 2FA"}
=======
        return {"authenticated": False, "error": str(e)}

def manejar_2fa(codigo_2fa):
    """
    Enviar el código de 2FA cuando sea requerido.
    """
    try:
        cl.two_factor_login(codigo_2fa)
        print("✅ Código 2FA verificado correctamente.")
        return {"authenticated": True}
>>>>>>> 3f8b5aa (mejoras)
    except Exception as e:
        print(f"❌ Error al verificar el código 2FA: {e}")
        return {"authenticated": False, "error": str(e)}


<<<<<<< HEAD
=======
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

>>>>>>> 3f8b5aa (mejoras)

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
<<<<<<< HEAD
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
=======
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
        guardar_token(username, cl.get_settings())  # Guardar nueva sesión
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
>>>>>>> 3f8b5aa (mejoras)




def autenticar_bot(username, password):
<<<<<<< HEAD
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

=======
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
>>>>>>> 3f8b5aa (mejoras)


def verificar_autenticacion():
    try:
<<<<<<< HEAD
        cl.get_timeline_feed()  # Validar sesión
        print("✅ Autenticación verificada correctamente.")
        return True
    except LoginRequired:
        print("⚠️ La sesión no es válida. Se requiere login.")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al verificar autenticación: {e}")
=======
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
>>>>>>> 3f8b5aa (mejoras)
        return False



<<<<<<< HEAD
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



=======
>>>>>>> 3f8b5aa (mejoras)

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
