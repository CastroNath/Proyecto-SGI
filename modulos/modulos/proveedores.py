import streamlit as st
from config.conexion import obtener_conexion

def mostrar_proveedores():
    st.header("Gestión de Proveedores")
    
    with st.form("form_proveedor"):
        nombre = st.text_input("Nombre o Razón Social")
        tipo = st.selectbox("Tipo de Proveedor", ["Persona Natural", "Empresa", "Cooperativa", "Otro"])
        dui_nit = st.text_input("DUI o NIT")
        telefono = st.text_input("Teléfono")
        guardar = st.form_submit_button("Guardar Proveedor")
        
    if guardar:
        if not nombre.strip():
            st.warning("El nombre del proveedor es obligatorio.")
        else:
            conexion = obtener_conexion()
            if conexion:
                try:
                    cursor = conexion.cursor()
                    consulta = """
                        INSERT INTO Proveedor (Nombre, Tipo, DUI_NIT, Telefono)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(consulta, (
                        nombre.strip(),
                        tipo,
                        dui_nit.strip(),
                        telefono.strip()
                    ))
                    conexion.commit()
                    st.success("Proveedor registrado correctamente.")
                except Exception as e:
                    st.error(f"Error al registrar proveedor: {e}")
                finally:
                    cursor.close()
                    conexion.close()
