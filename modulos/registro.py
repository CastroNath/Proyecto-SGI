import streamlit as st
from config.conexion import obtener_conexion

def obtener_roles_y_tiendas():
    conexion = obtener_conexion()
    if conexion is None:
        return [], []
    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        
        # Filtramos para excluir el rol de Administrador (id_rol = 1)
        cursor.execute("SELECT id_rol, Nombre FROM Rol WHERE id_rol != 1 AND Nombre != 'Administrador'")
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

def mostrar_registro():
    st.header("👑 Crear cuenta de usuario")
    st.write("Asigna un nuevo empleado a su rol y tienda correspondiente.")
    
    lista_roles, lista_tiendas = obtener_roles_y_tiendas()
    
    if not lista_roles:
        st.warning("⚠️ No hay roles operativos disponibles (ej. Cajero, Encargado). Asegúrate de tener roles distintos a 'Administrador' en la tabla Rol.")
        return
    if not lista_tiendas:
        st.warning("⚠️ No hay tiendas creadas en la base de datos.")
        return

    with st.form("form_registro"):
        nombre = st.text_input("Nombre completo del empleado")
        usuario = st.text_input("Nombre de usuario")
        contrasena = st.text_input("Contraseña", type="password")
        
        rol_seleccionado = st.selectbox("Asignar Rol", lista_roles, format_func=lambda x: x["Nombre"])
        tienda_seleccionada = st.selectbox("Asignar Tienda", lista_tiendas, format_func=lambda x: x["Nombre"])
        
        btn_registrar = st.form_submit_button("Guardar usuario")
        
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
                st.success(f"✅ Usuario '{usuario.strip()}' creado con el rol de {rol_seleccionado['Nombre']} en {tienda_seleccionada['Nombre']}.")
