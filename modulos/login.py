import bcrypt
import streamlit as st
from config.conexion import obtener_conexion


def verificar_usuario(usuario, contrasena):
    conexion = obtener_conexion()
    if conexion is None:
        return None
    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True) # Retorna los datos como diccionario para leerlos fácil

        # Consulta adaptada a tus atributos exactos: id_usuario, Usuario, Contrasena, Nombre, id_rol e id_tienda
        consulta = """
            SELECT id_usuario, Nombre, id_rol, id_tienda 
            FROM Usuario 
            WHERE Usuario = %s AND Contrasena = %s 
            LIMIT 1
        """
        cursor.execute(consulta, (usuario, contrasena))
        resultado = cursor.fetchone()
        return resultado
    except Exception as error:
        st.error(f"Error al verificar el usuario: {error}")
        return None
    finally:
        if cursor is not None:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()


def verificar_usuario_nuevo(usuario, contrasena):
    """Busca en la tabla usuarios_nuevos (contraseña cifrada con bcrypt)."""
    conexion = obtener_conexion()
    if conexion is None:
        return None
    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, usuario, contrasena, rol FROM usuarios_nuevos "
            "WHERE usuario = %s LIMIT 1",
            (usuario,),
        )
        fila = cursor.fetchone()
        if fila and bcrypt.checkpw(contrasena.encode(), fila["contrasena"].encode()):
            # Se devuelve con la misma forma que usa el resto del login
            return {
                "id_usuario": fila["id"],
                "Nombre": fila["usuario"],
                "id_rol": None,
                "id_tienda": None,
                "rol": fila["rol"],
            }
        return None
    except Exception as error:
        st.error(f"Error al verificar el usuario: {error}")
        return None
    finally:
        if cursor is not None:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()


def login():
    st.title("Inicio de sesión - Sistema de Ventas")

    # Formulario de credenciales
    usuario_input = st.text_input("Usuario")
    contrasena_input = st.text_input("Contraseña", type="password")

    if st.button("Iniciar sesión"):
        if usuario_input.strip() == "" or contrasena_input.strip() == "":
            st.warning("Por favor, ingrese su usuario y contraseña.")
        else:
            # 1) Usuarios ya guardados; 2) si no aparece, usuarios nuevos
            datos_usuario = verificar_usuario(usuario_input, contrasena_input)
            if not datos_usuario:
                datos_usuario = verificar_usuario_nuevo(usuario_input, contrasena_input)

            if datos_usuario:
                # Almacena toda la información del usuario en la sesión de Streamlit
                st.session_state["sesion_iniciada"] = True
                st.session_state["usuario"] = usuario_input
                st.session_state["id_usuario"] = datos_usuario["id_usuario"]
                st.session_state["nombre_completo"] = datos_usuario["Nombre"]
                st.session_state["id_rol"] = datos_usuario["id_rol"]
                st.session_state["id_tienda"] = datos_usuario["id_tienda"]
                st.session_state["rol"] = datos_usuario.get("rol")

                st.success(f"¡Bienvenido(a) {datos_usuario['Nombre']}!")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
