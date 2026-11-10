import streamlit as st
from modulos.login import login

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
    
    opciones = [
        "Inicio",
        "Información"
    ]
    seleccion = st.sidebar.selectbox(
        "Seleccione una opción",
        opciones
    )
    
    # Mostrar el contenido según la opción seleccionada
    if seleccion == "Inicio":
        st.title(f"¡Bienvenido, {st.session_state['nombre_completo']}!")
        st.write("Has iniciado sesión de forma exitosa usando tu base de datos modular.")
        
    elif seleccion == "Información":
        st.header("Información del sistema")
        st.write("Aplicación desarrollada durante el Laboratorio de SGI.")
        
    # Cerrar sesión
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["sesion_iniciada"] = False
        st.session_state["usuario"] = ""
        st.session_state["nombre_completo"] = ""
        st.rerun()
else:
    # Si no hay sesión iniciada, mostrar la pantalla de login que creamos
    login()
