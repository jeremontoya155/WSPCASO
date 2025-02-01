import requests
import socks
import socket

# Configurar el proxy SOCKS5
socks.set_default_proxy(socks.SOCKS5, "p.webshare.io", 80, username="acgcyous-rotate", password="nbz3ct3ouck0")
socket.socket = socks.socksocket

# Definir cabeceras
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Prueba de conexión con Instagram
try:
    print("Probando conexión a Instagram con SOCKS5...")
    response = requests.get("https://www.instagram.com", headers=headers)
    print("Estado de la respuesta:", response.status_code)
except Exception as e:
    print("Error al conectar con Instagram:", e)
