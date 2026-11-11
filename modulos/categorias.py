import streamlit as st
from config.conexion import obtener_conexion

def mostrar_categorias():
    st.header("Gestión de Categorías")
    
    with st.form("form_categoria"):
        nombre = st.text_input("Nombre de la Categoría")
        guardar = st.form_submit_button("Guardar Categoría")
        
    if guardar:
        if not nombre.strip():
            st.warning("Por favor, ingrese el nombre de la categoría.")
        else:
            conexion = obtener_conexion()
            if conexion:
                try:
                    cursor = conexion.cursor()
                    cursor.execute("INSERT INTO Categoria (Nombre) VALUES (%s)", (nombre.strip(),))
                    conexion.commit()
                    st.success("Categoría registrada correctamente.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
                finally:
                    cursor.close()
                    conexion.close()
