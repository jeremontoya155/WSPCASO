import requests
from config import PROXIES

def make_request(url, method="GET", data=None, headers=None):
    """
    Realiza solicitudes HTTP utilizando los proxies configurados.
    """
    try:
        if method == "GET":
            response = requests.get(url, proxies=PROXIES, verify=False, headers=headers)
        elif method == "POST":
            response = requests.post(url, proxies=PROXIES, data=data, verify=False, headers=headers)
        else:
            raise ValueError("Método HTTP no soportado.")
        
        print(f"Estado de la respuesta: {response.status_code}")
        return response
    except Exception as e:
        print(f"Error al realizar la solicitud: {e}")
        return None
