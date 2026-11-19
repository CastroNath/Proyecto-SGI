import streamlit as st

from modulos.negocio import ReglaNegocioError, autenticar


def login():
    st.title("Red Cooperativa de Mujeres de Occidente")

    with st.form("form_login"):
        usuario_input = st.text_input("Usuario")
        contrasena_input = st.text_input("Contraseña", type="password")
        ingresar = st.form_submit_button("Iniciar sesión")

    if ingresar:
        if usuario_input.strip() == "" or contrasena_input.strip() == "":
            st.warning("Por favor, ingrese su usuario y contraseña.")
            return
        try:
            u = autenticar(usuario_input, contrasena_input)
        except ReglaNegocioError as e:
            st.error(str(e))
            return
        except Exception as e:
            st.error(f"Error al verificar el usuario: {e}")
            return

        # Toda la información del usuario queda en la sesión de Streamlit
        st.session_state["sesion_iniciada"] = True
        st.session_state["usuario"] = usuario_input.strip()
        st.session_state["id_usuario"] = u["id_usuario"]
        st.session_state["nombre_completo"] = u["Nombre"]
        st.session_state["id_rol"] = u["id_rol"]
        st.session_state["rol"] = u["Rol"]
        st.session_state["id_tienda"] = u["id_tienda"]
        st.session_state["nombre_tienda"] = u["Tienda"]
        st.session_state["es_cd"] = (u["Tipo_tienda"] or "").upper() == "CD"
        st.session_state["vista_actual"] = "menu_principal"
        st.rerun()
