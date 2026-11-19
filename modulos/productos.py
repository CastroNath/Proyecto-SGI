import streamlit as st
import mysql.connector
from config.conexion import obtener_conexion

def es_centro_distribucion(id_tienda):
    cx = obtener_conexion()
    if not cx: return False
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT Nombre, Tipo FROM Tienda WHERE id_tienda = %s", (id_tienda,))
        t = cur.fetchone()
        if t:
            nom = (t["Nombre"] or "").lower()
            tip = (t["Tipo"] or "").lower()
            return "distribuci" in nom or "distribuci" in tip
        return False
    finally:
        cur.close(); cx.close()

def obtener_categorias():
    cx = obtener_conexion()
    if not cx: return []
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT id_categoria, Nombre FROM Categoria ORDER BY Nombre")
        return cur.fetchall()
    finally:
        cur.close(); cx.close()

def generar_siguiente_codigo():
    cx = obtener_conexion()
    if not cx: return "7411000000001"
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT MAX(id_producto) AS ultimo FROM Producto")
        res = cur.fetchone()
        sig = (res["ultimo"] or 0) + 1
        return f"7411{sig:09d}"
    finally:
        cur.close(); cx.close()

def obtener_catalogo_completo():
    cx = obtener_conexion()
    if not cx: return []
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("""
            SELECT p.id_producto AS ID, p.Codigo_barras AS Código, p.Nombre AS Producto, 
                   c.Nombre AS Categoría, p.Unidad_medida AS Unidad
            FROM Producto p
            INNER JOIN Categoria c ON p.id_categoria = c.id_categoria
            ORDER BY p.id_producto ASC
        """)
        return cur.fetchall()
    finally:
        cur.close(); cx.close()

def mostrar_productos():
    st.header("📦 Catálogo de Productos")
    id_tienda = st.session_state.get("id_tienda")
    es_cd = es_centro_distribucion(id_tienda)

    # Si pertenece al Centro de Distribución, bloquear creación y mostrar solo el catálogo existente
    if es_cd:
        st.info("🏢 **Modo Centro de Distribución:** Según las reglas operativas, el Centro de Distribución opera únicamente con el catálogo existente y no registra productos nuevos.")
        catalogo = obtener_catalogo_completo()
        if catalogo:
            st.subheader("Productos Disponibles en el Catálogo Global")
            st.dataframe(catalogo, use_container_width=True, hide_index=True)
        else:
            st.warning("📭 Aún no hay productos registrados en el catálogo.")
        return

    # Si pertenece a una Tienda Minorista, permitir registrar y consultar
    tab1, tab2 = st.tabs(["➕ Registrar Nuevo Producto", "📋 Consultar Catálogo Global"])

    with tab1:
        if st.session_state.get("limpiar_prod", False):
            st.session_state["prod_nom"] = ""
            st.session_state["prod_uni"] = "Unidad"
            st.session_state["limpiar_prod"] = False

        if st.session_state.get("ok_prod"):
            st.success(st.session_state.pop("ok_prod"))

        if "prod_nom" not in st.session_state: st.session_state["prod_nom"] = ""
        if "prod_uni" not in st.session_state: st.session_state["prod_uni"] = "Unidad"

        categorias = obtener_categorias()
        if not categorias:
            st.warning("⚠️ Primero debes crear al menos una categoría en el catálogo.")
            return

        codigo_auto = generar_siguiente_codigo()
        st.text_input("Código de Barras (EAN-13 Automático)", value=codigo_auto, disabled=True)
        
        nombre = st.text_input("Nombre del Producto", key="prod_nom")
        cat_sel = st.selectbox("Categoría", categorias, format_func=lambda x: x["Nombre"])
        unidad = st.selectbox(
            "Unidad de Medida",
            ["Unidad", "Libra", "Kilogramo", "Litro", "Mililitro", "Paquete", "Caja", "Saco"],
            key="prod_uni"
        )

        if st.button("Guardar Producto", key="btn_save_prod"):
            if not nombre.strip():
                st.warning("⚠️ El nombre del producto es obligatorio.")
            else:
                cx = obtener_conexion()
                if cx:
                    try:
                        cur = cx.cursor()
                        cur.execute(
                            "INSERT INTO Producto (id_categoria, Nombre, Unidad_medida, Codigo_barras) VALUES (%s, %s, %s, %s)",
                            (cat_sel["id_categoria"], nombre.strip(), unidad, codigo_auto)
                        )
                        cx.commit()
                        st.session_state["ok_prod"] = f"✅ Producto '{nombre.strip()}' registrado con código {codigo_auto}."
                        st.session_state["limpiar_prod"] = True
                        st.rerun()
                    except mysql.connector.IntegrityError:
                        st.error("❌ Ya existe un producto con ese nombre o código de barras.")
                    except Exception as e:
                        st.error(f"Error al guardar producto: {e}")
                    finally:
                        cur.close(); cx.close()

    with tab2:
        catalogo = obtener_catalogo_completo()
        if catalogo:
            st.subheader("Productos Registrados en la Red")
            st.dataframe(catalogo, use_container_width=True, hide_index=True)
        else:
            st.info("📭 No hay productos registrados aún.")
