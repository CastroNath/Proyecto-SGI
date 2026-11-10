import bcrypt
import mysql.connector
import streamlit as st

ROLES = ["Administrador general", "Encargado de tienda", "Cajero"]


def get_conn():
    # Si tu Configuración/conexion.py ya tiene una función de conexión,
    # reemplaza el contenido de esta función por esa llamada.
    return mysql.connector.connect(**st.secrets["mysql"])


def mostrar_registro():
    st.title("Crear usuario")

    with st.form("registro"):
        usuario = st.text_input("Usuario")
        pw1 = st.text_input("Contraseña", type="password")
        pw2 = st.text_input("Confirmar contraseña", type="password")
        rol = st.selectbox("Rol", ROLES)
        enviar = st.form_submit_button("Crear usuario")

    if not enviar:
        return

    if not usuario.strip() or not pw1:
        st.error("Completa todos los campos.")
    elif pw1 != pw2:
        st.error("Las contraseñas no coinciden.")
    else:
        hashed = bcrypt.hashpw(pw1.encode(), bcrypt.gensalt()).decode()
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO usuarios (usuario, contrasena, rol) VALUES (%s, %s, %s)",
                (usuario.strip(), hashed, rol),
            )
            conn.commit()
            st.success(f"Usuario creado con el rol: {rol}")
        except mysql.connector.IntegrityError:
            st.error("Ese nombre de usuario ya existe.")
        finally:
            conn.close()
