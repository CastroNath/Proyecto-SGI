import bcrypt
import mysql.connector
import streamlit as st

ROLES = ["Administrador general", "Encargado de tienda", "Cajero"]


def get_conn():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
    )


def mostrar_registro():
    st.subheader("Crear cuenta nueva")

    with st.form("form_registro"):
        usuario = st.text_input("Usuario")
        pw1 = st.text_input("Contraseña", type="password")
        pw2 = st.text_input("Confirmar contraseña", type="password")
        rol = st.selectbox("Rol", ROLES)
        enviar = st.form_submit_button("Crear cuenta")

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
                "INSERT INTO usuarios_nuevos (usuario, contrasena, rol) "
                "VALUES (%s, %s, %s)",
                (usuario.strip(), hashed, rol),
            )
            conn.commit()
            st.success(f"Cuenta creada con el rol: {rol}")
        except mysql.connector.IntegrityError:
            st.error("Ese nombre de usuario ya existe.")
        finally:
            conn.close()
