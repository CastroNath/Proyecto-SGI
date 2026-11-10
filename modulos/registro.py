import streamlit as st
from config.conexion import obtener_conexion

def obtener_roles_y_tiendas():
    conexion = obtener_conexion()
    if conexion is None:
        return [], []
    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        
        # Consultar roles disponibles
        cursor.execute("SELECT id_rol, Nombre FROM Rol")
        roles = cursor.fetchall()
        
        # Consultar tiendas disponibles
        cursor.execute("SELECT id_tienda, Nombre FROM Tienda")
        tiendas = cursor.fetchall()
        
        return roles, tiendas
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return [], []
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()

def registrar_usuario(id_rol, id_tienda, nombre, usuario, contrasena):
    conexion = obtener_conexion()
    if conexion is None:
        return False
    cursor = None
    try:
        cursor = conexion.cursor()
        consulta = """
            INSERT INTO Usuario (id_rol, id_tienda, Nombre, Usuario, Contrasena)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(consulta, (id_rol, id_tienda, nombre, usuario, contrasena))
        conexion.commit()
        return True
    except Exception as e:
        st.error(f"Error al registrar: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()

def registro():
    st.title("Crear una cuenta nueva")
    
    # Cargar los roles y tiendas reales de la BD
    lista_roles, lista_tiendas = obtener_roles_y_tiendas()
    
    if not lista_roles or not lista_tiendas:
        st.warning("⚠️ Para registrar usuarios, primero debes tener Roles y Tiendas creados en la base de datos.")
        return

    with st.form("form_registro"):
        nombre = st.text_input("Nombre Completo")
        usuario = st.text_input("Nombre de Usuario")
        contrasena = st.text_input("Contraseña", type="password")
        
        # selectbox que muestran el Nombre pero guardan el ID interno
        rol_seleccionado = st.selectbox("Selecciona tu Rol", lista_roles, format_func=lambda x: x["Nombre"])
        tienda_seleccionada = st.selectbox("Selecciona tu Tienda", lista_tiendas, format_func=lambda x: x["Nombre"])
        
        btn_registrar = st.form_submit_button("Registrarse")
        
    if btn_registrar:
        if not nombre.strip() or not usuario.strip() or not contrasena.strip():
            st.error("Por favor, llena todos los campos.")
        else:
            exito = registrar_usuario(
                rol_seleccionado["id_rol"], 
                tienda_seleccionada["id_tienda"], 
                nombre.strip(), 
                usuario.strip(), 
                contrasena
            )
            if exito:
                st.success("¡Cuenta creada con éxito! Ya puedes iniciar sesión.")
