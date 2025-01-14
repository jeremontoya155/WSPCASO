from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from database.models import collection_seguidos
import random
from instagrapi import Client

cl = Client()

def analizar_patrones_perfiles(perfiles):
    """
    Analiza patrones en las biografías de los perfiles y agrupa perfiles similares.
    """
    try:
        # Extraer biografías de los perfiles
        biografias = [perfil.get("biography", "") for perfil in perfiles]

        # Vectorizar las biografías usando TF-IDF
        vectorizer = TfidfVectorizer(stop_words="spanish")
        X = vectorizer.fit_transform(biografias)

        # Aplicar K-Means para agrupar perfiles
        num_clusters = 5  # Número de grupos que deseas crear
        kmeans = KMeans(n_clusters=num_clusters, random_state=42)
        kmeans.fit(X)

        # Asignar cada perfil a un grupo
        grupos = kmeans.labels_
        perfiles_agrupados = {i: [] for i in range(num_clusters)}
        for idx, grupo in enumerate(grupos):
            perfiles_agrupados[grupo].append(perfiles[idx])

        return perfiles_agrupados
    except Exception as e:
        print(f"Error analizando patrones: {e}")
        return {}


def sugerir_perfiles(patrones, cuentas_competencia):
    from instagram.follow import usuario_ya_seguido  # Importación dentro de la función

    sugerencias = []
    # Resto del código...

    for grupo, perfiles in patrones.items():
        print(f"Buscando sugerencias para el grupo {grupo}...")

        # Analizar seguidores de las cuentas competencia
        for cuenta in cuentas_competencia:
            try:
                user_id = cl.user_id_from_username(cuenta)
                seguidores = cl.user_followers(user_id, amount=50)

                for username, datos in seguidores.items():
                    # Filtrar perfiles que no estén ya en la base de datos
                    if not usuario_ya_seguido(username):
                        sugerencias.append({
                            "username": username,
                            "biography": datos.get("biography", ""),
                            "grupo": grupo
                        })
            except Exception as e:
                print(f"Error analizando seguidores de @{cuenta}: {e}")

    return sugerencias


def generar_sugerencia():
    """
    Genera una sugerencia de perfil basado en los patrones o usuarios seguidos.
    """
    try:
        # Obtén usuarios seguidos recientemente
        usuarios = list(collection_seguidos.find().limit(10))  # Ejemplo: últimos 10 seguidos

        # Si no hay suficientes datos, devuelve un mensaje predeterminado
        if not usuarios:
            return "No hay sugerencias disponibles en este momento."

        # Elegir un usuario aleatorio para sugerir (puedes usar otro criterio)
        usuario_sugerido = random.choice(usuarios)
        return f"Te sugerimos seguir a @{usuario_sugerido['username']}."
    except Exception as e:
        print(f"Error al generar sugerencia: {e}")
        return "Error al generar sugerencia."
