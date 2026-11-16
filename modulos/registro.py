import streamlit as st
import mysql.connector
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
        
        cursor.execute("SELECT id_tienda, Nombre FROM Tienda ORDER BY Nombre")
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
        return False, "No hay conexión con la base de datos."
    cursor = None
    try:
        cursor = conexion.cursor()
        # Verificar si el nombre de usuario ya existe
        cursor.execute("SELECT id_usuario FROM Usuario WHERE LOWER(Usuario) = LOWER(%s)", (usuario,))
        if cursor.fetchone():
            return False, f"❌ El nombre de usuario '{usuario}' ya está en uso. Elige otro."

        consulta = """
            INSERT INTO Usuario (id_rol, id_tienda, Nombre, Usuario, Contrasena)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(consulta, (id_rol, id_tienda, nombre, usuario, contrasena))
        conexion.commit()
        return True, f"✅ Usuario '{usuario}' creado y asignado correctamente."
    except mysql.connector.IntegrityError:
        return False, f"❌ El usuario '{usuario}' ya existe en el sistema."
    except Exception as e:
        return False, f"❌ Error al registrar: {e}"
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()

def mostrar_registro():
    st.header("👑 Administración: Crear Cuenta de Usuario")
    st.write("Asigna un nuevo empleado operativo a su rol y tienda correspondiente.")
    
    # 1. Limpiar los campos ANTES de dibujarlos si se activó la bandera
    if st.session_state.get("limpiar_campos_reg", False):
        st.session_state["reg_nombre"] = ""
        st.session_state["reg_usuario"] = ""
        st.session_state["reg_contrasena"] = ""
        st.session_state["limpiar_campos_reg"] = False

    # 2. Mostrar mensaje de éxito si se acaba de registrar un usuario
    if st.session_state.get("msg_exito_reg"):
        st.success(st.session_state["msg_exito_reg"])
        st.session_state["msg_exito_reg"] = ""

    # 3. Inicializar claves de sesión si no existen
    if "reg_nombre" not in st.session_state:
        st.session_state["reg_nombre"] = ""
    if "reg_usuario" not in st.session_state:
        st.session_state["reg_usuario"] = ""
    if "reg_contrasena" not in st.session_state:
        st.session_state["reg_contrasena"] = ""

    lista_roles, lista_tiendas = obtener_roles_y_tiendas()
    
    if not lista_roles:
        st.warning("⚠️ No hay roles operativos disponibles (ej. Cajero, Encargado). Asegúrate de tener roles distintos a 'Administrador' en la tabla Rol.")
        return
    if not lista_tiendas:
        st.warning("⚠️ No hay tiendas creadas en la base de datos.")
        return

    # 4. Dibujar los campos vinculados a session_state
    nombre = st.text_input("Nombre Completo del Empleado", key="reg_nombre")
    usuario = st.text_input("Nombre de Usuario", key="reg_usuario")
    contrasena = st.text_input("Contraseña", type="password", key="reg_contrasena")
    
    rol_seleccionado = st.selectbox("Asignar Rol", lista_roles, format_func=lambda x: x["Nombre"])
    tienda_seleccionada = st.selectbox("Asignar Tienda / Sucursal", lista_tiendas, format_func=lambda x: x["Nombre"])
    
    # 5. Guardar y limpiar
    if st.button("Guardar Usuario"):
        if not nombre.strip() or not usuario.strip() or not contrasena.strip():
            st.error("⚠️ Por favor, llena todos los campos.")
        else:
            exito, mensaje = registrar_usuario(
                rol_seleccionado["id_rol"], 
                tienda_seleccionada["id_tienda"], 
                nombre.strip(), 
                usuario.strip(), 
                contrasena
            )
            if exito:
                st.session_state["msg_exito_reg"] = f"{mensaje} ({tienda_seleccionada['Nombre']})"
                st.session_state["limpiar_campos_reg"] = True
                st.rerun()
            else:
                st.error(mensaje)
