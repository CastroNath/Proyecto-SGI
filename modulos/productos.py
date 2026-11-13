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

def es_centro_distribucion(id_tienda):
    conexion = obtener_conexion()
    if not conexion:
        return False
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT Tipo FROM Tienda WHERE id_tienda = %s", (id_tienda,))
        tienda = cursor.fetchone()
        if tienda and tienda["Tipo"] and "distribuci" in tienda["Tipo"].lower():
            return True
        return False
    finally:
        cursor.close()
        conexion.close()

def mostrar_productos():
    st.header("📦 Gestión de Productos")

    # Regla de negocio: El Centro de Distribución no registra productos nuevos
    if es_centro_distribucion(st.session_state.get("id_tienda")):
        st.error("⛔ Acceso restringido: El Centro de Distribución opera únicamente con el catálogo existente y no registra productos nuevos.")
        return

    # 1. Limpiar campos antes de dibujarlos
    if st.session_state.get("limpiar_campos_prod", False):
        st.session_state["input_nombre_prod"] = ""
        st.session_state["input_unidad_prod"] = "Unidad"
        st.session_state["input_cod_prod"] = ""
        st.session_state["limpiar_campos_prod"] = False

    # 2. Mensaje de éxito
    if st.session_state.get("msg_exito_prod"):
        st.success(st.session_state["msg_exito_prod"])
        st.session_state["msg_exito_prod"] = ""

    # 3. Inicializar claves
    if "input_nombre_prod" not in st.session_state:
        st.session_state["input_nombre_prod"] = ""
    if "input_unidad_prod" not in st.session_state:
        st.session_state["input_unidad_prod"] = "Unidad"
    if "input_cod_prod" not in st.session_state:
        st.session_state["input_cod_prod"] = ""

    categorias = obtener_categorias()
    if not categorias:
        st.warning("⚠️ Primero debes registrar al menos una categoría en el módulo de Categorías.")
        return

    nombre = st.text_input("Nombre del Producto", key="input_nombre_prod")
    categoria_sel = st.selectbox("Categoría", categorias, format_func=lambda x: x["Nombre"])
    
    # Menú desplegable cerrado para evitar errores de escritura
    unidad = st.selectbox(
        "Unidad de Medida",
        ["Unidad", "Libra", "Kilogramo", "Gramo", "Onza", "Litro", "Mililitro", "Caja", "Paquete", "Saco", "Docena"],
        key="input_unidad_prod"
    )
    codigo_barras = st.text_input("Código de Barras (Opcional)", key="input_cod_prod")

    if st.button("Guardar Producto"):
        if not nombre.strip():
            st.warning("⚠️ El nombre del producto es obligatorio.")
            return

        conexion = obtener_conexion()
        if conexion:
            try:
                cursor = conexion.cursor()
                # Validar que no se repita el nombre o el código de barras
                if codigo_barras.strip():
                    cursor.execute(
                        "SELECT id_producto FROM Producto WHERE LOWER(Nombre) = LOWER(%s) OR Codigo_barras = %s",
                        (nombre.strip(), codigo_barras.strip())
                    )
                else:
                    cursor.execute(
                        "SELECT id_producto FROM Producto WHERE LOWER(Nombre) = LOWER(%s)",
                        (nombre.strip(),)
                    )

                if cursor.fetchone():
                    st.error("❌ Ya existe un producto registrado con ese mismo nombre o código de barras.")
                    return

                consulta = """
                    INSERT INTO Producto (id_categoria, Nombre, Unidad_medida, Codigo_barras)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(consulta, (
                    categoria_sel["id_categoria"],
                    nombre.strip(),
                    unidad,
                    codigo_barras.strip() if codigo_barras.strip() else None
                ))
                conexion.commit()

                st.session_state["msg_exito_prod"] = f"✅ Producto '{nombre.strip()}' agregado al catálogo."
                st.session_state["limpiar_campos_prod"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar producto: {e}")
            finally:
                cursor.close()
                conexion.close()
