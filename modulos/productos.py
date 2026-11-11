import streamlit as st
from config.conexion import obtener_conexion

def obtener_categorias():
    conexion = obtener_conexion()
    if not conexion:
        return []
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT id_categoria, Nombre FROM Categoria")
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()

def mostrar_productos():
    st.header("Gestión de Productos")
    
    # Regla de negocio: El Centro de Distribución (ej. id_tienda == 1 o según tu BD) no crea productos nuevos
    categorias = obtener_categorias()
    if not categorias:
        st.warning("⚠️ Primero debes registrar al menos una categoría en el módulo de Categorías.")
        return

    with st.form("form_producto"):
        nombre = st.text_input("Nombre del Producto")
        categoria_sel = st.selectbox("Categoría", categorias, format_func=lambda x: x["Nombre"])
        unidad = st.text_input("Unidad de medida (ej. Libra, Unidad, Litro)")
        codigo_barras = st.text_input("Código de barras")
        guardar = st.form_submit_button("Guardar Producto")
        
    if guardar:
        if not nombre.strip():
            st.warning("El nombre del producto es obligatorio.")
        else:
            conexion = obtener_conexion()
            if conexion:
                try:
                    cursor = conexion.cursor()
                    consulta = """
                        INSERT INTO Producto (id_categoria, Nombre, Unidad_medida, Codigo_barras)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(consulta, (
                        categoria_sel["id_categoria"],
                        nombre.strip(),
                        unidad.strip(),
                        codigo_barras.strip()
                    ))
                    conexion.commit()
                    st.success("Producto registrado correctamente.")
                except Exception as e:
                    st.error(f"Error al registrar producto: {e}")
                finally:
                    cursor.close()
                    conexion.close()
