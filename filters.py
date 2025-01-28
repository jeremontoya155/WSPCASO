from instagram.config_bot import cargar_usuarios_procesados, guardar_usuarios_procesados

# Cargar usuarios procesados al inicio
usuarios_procesados = cargar_usuarios_procesados()

def filtrar_usuarios(usuarios, min_publicaciones=1):
    usuarios_filtrados = []
    for usuario in usuarios:
        if usuario["id"] in usuarios_procesados:
            print(f"⚠️ Usuario ya procesado detectado: {usuario['username']}. Saltando...")
            continue
        if usuario.get("is_private"):
            print(f"⚠️ Usuario privado detectado: {usuario['username']}. Saltando...")
            continue
        if usuario.get("media_count", 0) < min_publicaciones:
            print(f"⚠️ Usuario sin suficientes publicaciones detectado: {usuario['username']}. Saltando...")
            continue
        usuarios_filtrados.append(usuario)
        usuarios_procesados.add(usuario["id"])  # Registrar usuario como procesado
    guardar_usuarios_procesados()  # Guardar el estado actualizado
    return usuarios_filtrados


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

def filtrar_usuarios(usuarios, min_publicaciones=1):
    """
    Filtra usuarios para que solo se procesen cuentas públicas, con suficientes publicaciones,
    y excluye usuarios que ya han sido procesados, manejando datos opcionales de forma segura.
    """
    usuarios_filtrados = []
    for usuario in usuarios:
        user_id = usuario.get("id", None)
        username = usuario.get("username", f"Usuario_{user_id if user_id else 'desconocido'}")
        
        # Verificar si el usuario ya ha sido procesado
        if user_id in usuarios_procesados:
            print(f"⚠️ Usuario ya procesado detectado: {username}. Saltando...")
            continue

        # Verificar si la cuenta es privada
        if usuario.get("is_private", False):
            print(f"⚠️ Usuario privado detectado: {username}. Saltando...")
            continue

        # Verificar si cumple con el mínimo de publicaciones
        if usuario.get("media_count", 0) < min_publicaciones:
            print(f"⚠️ Usuario sin suficientes publicaciones detectado: {username}. Saltando...")
            continue

        # Añadir a la lista de usuarios filtrados
        usuarios_filtrados.append(usuario)
        usuarios_procesados.add(user_id)  # Registrar usuario como procesado

    return usuarios_filtrados
