


def filtrar_usuarios(usuarios):
    """
    Filtra usuarios para excluir cuentas privadas y cuentas sin publicaciones.
    """
    print(f"Aplicando filtros a {len(usuarios)} usuarios...")
    usuarios_filtrados = []
    usuarios_omitidos = []

    for usuario in usuarios:
        motivo_exclusion = None  # Variable para almacenar el motivo de exclusión
        try:
            # Convertir a estructura de usuario si es necesario
            if isinstance(usuario, str):  # Si es un string, crear un diccionario básico
                usuario = {"username": usuario, "biography": ""}

            # Validar que el usuario tenga los campos necesarios
            username = usuario.get("username", "desconocido")

            # Filtro: Omitir si la cuenta es privada
            if usuario.get("is_private", False):  
                motivo_exclusion = "cuenta privada"

            # Filtro: Omitir si el usuario no tiene publicaciones
            publicaciones = usuario.get("media_count", 0)
            if motivo_exclusion is None and publicaciones == 0:
                motivo_exclusion = "sin publicaciones"

            # Decidir si incluir o excluir al usuario
            if motivo_exclusion is None:
                usuarios_filtrados.append(usuario)
            else:
                usuarios_omitidos.append((username, motivo_exclusion))

        except Exception as e:
            print(f"Error al filtrar usuario @{usuario.get('username', 'desconocido')}: {e}")
            usuarios_omitidos.append((usuario.get("username", "desconocido"), "error en filtro"))

    # Resumen final de usuarios filtrados y omitidos
    print(f"Usuarios filtrados: {len(usuarios_filtrados)}")
    print(f"Usuarios omitidos: {len(usuarios_omitidos)}")
    for omitido in usuarios_omitidos:
        print(f"Usuario omitido: {omitido[0]}, Motivo: {omitido[1]}")

    return usuarios_filtrados, usuarios_omitidos

