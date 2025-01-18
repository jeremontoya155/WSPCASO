# filters.py (Funciones de filtrado de usuarios)
from database.models import collection_seguidos  # Si necesitas acceder a usuarios seguidos
from instagram.follow import dar_me_gusta_a_publicaciones


<<<<<<< HEAD
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
=======
def aplicar_filtros_individual(usuario, filtros):
    """
    Aplica filtros a un usuario individual basado en los criterios proporcionados.
    Retorna True si el usuario cumple con los filtros, False en caso contrario.
    """
    try:
        print(f"[DEBUG] Procesando usuario: {usuario.get('username', 'desconocido')}")
        
        # Filtros específicos aquí...
        if filtros.get("min_seguidores") and usuario.get("follower_count", 0) < filtros["min_seguidores"]:
            print(f"[DEBUG] Usuario @{usuario['username']} descartado por no cumplir con el mínimo de seguidores.")
            return False

        return True
    except Exception as e:
        print(f"❌ Error al aplicar filtros a @{usuario.get('username', 'desconocido')}: {e}")
        return False


>>>>>>> 3f8b5aa (mejoras)

def filtrar_usuarios(usuarios, filtros):
    print(f"Aplicando filtros a {len(usuarios)} usuarios...")
    usuarios_filtrados = []
    usuarios_omitidos = []

    for usuario in usuarios:
        motivo_exclusion = None  # Variable para almacenar el motivo de exclusión
        try:
            # Convertir a estructura de usuario si es necesario
            if isinstance(usuario, str):  # Si es un string, crear un diccionario básico
<<<<<<< HEAD
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
=======
                usuario = {"username": usuario, "biography": ""}

            # Validar que el usuario tenga los campos necesarios
            username = usuario.get("username", "desconocido")
            biography = usuario.get("biography", "").lower()

            # Filtro por ubicación
            if "ubicaciones" in filtros and filtros["ubicaciones"]:
                ubicaciones = [ubicacion.lower() for ubicacion in filtros["ubicaciones"]]
                if not any(ubicacion in biography for ubicacion in ubicaciones):
                    motivo_exclusion = "ubicación no coincide"

            # Filtro por palabras clave
            if motivo_exclusion is None and "palabras_clave" in filtros and filtros["palabras_clave"]:
                palabras_clave = [palabra.lower() for palabra in filtros["palabras_clave"]]
                if not any(palabra in biography for palabra in palabras_clave):
                    motivo_exclusion = "sin palabras clave en biografía"

            # Filtro por número mínimo de publicaciones
            if motivo_exclusion is None and "min_publicaciones" in filtros:
                publicaciones = usuario.get("media_count", 0)
                if publicaciones < filtros["min_publicaciones"]:
                    motivo_exclusion = f"menos de {filtros['min_publicaciones']} publicaciones"

            # Filtro por número mínimo de seguidores
            if motivo_exclusion is None and "min_seguidores" in filtros:
                seguidores = usuario.get("followers", 0)
                if seguidores < filtros["min_seguidores"]:
                    motivo_exclusion = f"menos de {filtros['min_seguidores']} seguidores"

            # Filtro por tipo de cuenta (pública/privada)
            if motivo_exclusion is None and "tipo_cuenta" in filtros:
                tipo_cuenta = filtros["tipo_cuenta"]
                es_privada = usuario.get("is_private", False)
                if tipo_cuenta == "publica" and es_privada:
                    motivo_exclusion = "cuenta privada"
                elif tipo_cuenta == "privada" and not es_privada:
                    motivo_exclusion = "cuenta pública"

            # Decidir si incluir o excluir al usuario
            if motivo_exclusion is None:
                usuarios_filtrados.append(usuario)
            else:
                usuarios_omitidos.append((username, motivo_exclusion))
>>>>>>> 3f8b5aa (mejoras)

        except Exception as e:
            print(f"Error al filtrar usuario @{usuario.get('username', 'desconocido')}: {e}")
            usuarios_omitidos.append((usuario.get("username", "desconocido"), "error en filtro"))

<<<<<<< HEAD
=======
    # Resumen final de usuarios filtrados y omitidos
    print(f"Usuarios filtrados: {len(usuarios_filtrados)}")
    print(f"Usuarios omitidos: {len(usuarios_omitidos)}")
    for omitido in usuarios_omitidos:
        print(f"Usuario omitido: {omitido[0]}, Motivo: {omitido[1]}")

>>>>>>> 3f8b5aa (mejoras)
    return usuarios_filtrados, usuarios_omitidos



<<<<<<< HEAD

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
=======
>>>>>>> 3f8b5aa (mejoras)
