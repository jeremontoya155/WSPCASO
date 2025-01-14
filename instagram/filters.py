# filters.py (Funciones de filtrado de usuarios)
from database.models import collection_seguidos  # Si necesitas acceder a usuarios seguidos
from instagram.follow import dar_me_gusta_a_publicaciones


def aplicar_filtros(user, filtros):
    # Filtrar por ubicación
    if not any(ubicacion in user.biography.lower() for ubicacion in filtros["ubicaciones"]):
        return False

    # Filtrar por palabras clave en la biografía
    if not any(palabra in user.biography.lower() for palabra in filtros["palabras_clave"]):
        return False

    # Filtrar por cantidad mínima de publicaciones y seguidores
    if user.media_count < filtros["min_publicaciones"] or user.follower_count < filtros["min_seguidores"]:
        return False

    # Filtrar por tipo de cuenta
    if (filtros["tipo_cuenta"] == "publica" and user.is_private) or (filtros["tipo_cuenta"] == "privada" and not user.is_private):
        return False

    return True

def filtrar_usuarios(usuarios, filtros):
    print(f"Aplicando filtros a {len(usuarios)} usuarios...")
    usuarios_filtrados = []
    usuarios_omitidos = []

    for usuario in usuarios:
        motivo_exclusion = None  # Variable para almacenar el motivo de exclusión
        try:
            # Convertir a estructura de usuario si es necesario
            if isinstance(usuario, str):  # Si es un string, crear un diccionario básico
                usuario = {
                    "username": usuario
                }

            # Filtro por ubicación
            if "ubicaciones" in filtros and filtros["ubicaciones"] and not any(
                ubicacion.lower() in (usuario.get("biography", "").lower()) for ubicacion in filtros["ubicaciones"]
            ):
                motivo_exclusion = "ubicación no coincide"

            # Filtro por palabras clave
            elif "palabras_clave" in filtros and filtros["palabras_clave"] and not any(
                palabra.lower() in (usuario.get("biography", "").lower()) for palabra in filtros["palabras_clave"]
            ):
                motivo_exclusion = "sin palabras clave en biografía"

            # Si no hay motivo de exclusión, añadir a filtrados
            if motivo_exclusion is None:
                usuarios_filtrados.append(usuario)
            else:
                usuarios_omitidos.append((usuario.get("username", "desconocido"), motivo_exclusion))

        except Exception as e:
            print(f"Error al filtrar usuario @{usuario.get('username', 'desconocido')}: {e}")
            usuarios_omitidos.append((usuario.get("username", "desconocido"), "error en filtro"))

    return usuarios_filtrados, usuarios_omitidos




# Ejemplo de flujo para filtrar usuarios y dar "me gusta"
def ejecutar_me_gusta_con_filtros(usuarios, filtros_formulario):
    print(f"Aplicando filtros a {len(usuarios)} usuarios...")
    usuarios_filtrados, usuarios_omitidos = filtrar_usuarios(usuarios, filtros_formulario)

    print(f"Usuarios filtrados: {len(usuarios_filtrados)}")
    print(f"Usuarios omitidos: {len(usuarios_omitidos)}")

    for usuario in usuarios_filtrados:
        try:
            print(f"Dando 'me gusta' al usuario @{usuario.username}...")
            dar_me_gusta_a_publicaciones(usuario.id)
        except Exception as e:
            print(f"❌ Error al dar 'me gusta' a @{usuario.username}: {e}")

    # Mostrar estadísticas de los filtros
    print(f"Proceso completado: {len(usuarios_filtrados)} usuarios con 'me gusta', {len(usuarios_omitidos)} omitidos.")
