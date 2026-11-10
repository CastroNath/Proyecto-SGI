import streamlit as st
from modulos.login import login
from modulos.registro import registro  # Importamos el nuevo módulo

# Inicializar variables de sesión si no existen
if "sesion_iniciada" not in st.session_state:
    st.session_state["sesion_iniciada"] = False
if "usuario" not in st.session_state:
    st.session_state["usuario"] = ""
if "nombre_completo" not in st.session_state:
    st.session_state["nombre_completo"] = ""

# Comprobar si el usuario inició sesión
if st.session_state["sesion_iniciada"]:
    st.sidebar.title("Menú")
    st.sidebar.write(f"**Usuario:** {st.session_state['usuario']}")
    
    opciones = ["Inicio", "Información"]
    seleccion = st.sidebar.selectbox("Seleccione una opción", opciones)
    
    if seleccion == "Inicio":
        st.title(f"¡Bienvenido, {st.session_state['nombre_completo']}!")
        st.write("Has iniciado sesión de forma exitosa.")
    elif seleccion == "Información":
        st.header("Información del sistema")
        st.write("Aplicación desarrollada durante el Laboratorio de SGI.")
        
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["sesion_iniciada"] = False
        st.session_state["usuario"] = ""
        st.session_state["nombre_completo"] = ""
        st.rerun()
else:
    # Si no ha iniciado sesión, damos la opción de elegir entre ingresar o registrarse
    menu_acceso = st.radio("¿Ya tienes una cuenta?", ["Iniciar Sesión", "Registrarse"], horizontal=True)
    
    if menu_acceso == "Iniciar Sesión":
        login()
    else:
        registro()
