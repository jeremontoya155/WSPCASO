import requests
from config import PROXIES  # Asegúrate de que PROXIES está correctamente definido en config.py

# Definición de la función antes de usarla
def make_request(url):
    try:
        response = requests.get(url, proxies=PROXIES, verify=False)  # Deshabilitar verificación SSL
        print(f"Estado de la respuesta: {response.status_code}")
        return response
    except Exception as e:
        print(f"Error al realizar la solicitud: {e}")
        return None


# Uso de la función
url = "https://httpbin.org/ip"  # URL de prueba para ver la IP pública
response = make_request(url)

if response:
    print("Solicitud realizada con éxito.")
    print(f"Contenido de la respuesta: {response.text}")
else:
    print("Error en la solicitud.")
