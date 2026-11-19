import mysql.connector
import streamlit as st

from config.conexion import consultar, obtener_conexion


def mostrar_categorias():
    st.header("📁 Gestión de Categorías")
    st.caption("Las categorías son un catálogo común para todas las tiendas.")
    es_admin = st.session_state.get("id_rol") == 1

    if st.session_state.get("ok_cat"):
        st.success(st.session_state.pop("ok_cat"))

    if es_admin:
        with st.form("form_categoria", clear_on_submit=True):
            nombre = st.text_input("Nombre de la Categoría")
            guardar = st.form_submit_button("Guardar Categoría")
        if guardar:
            if not nombre.strip():
                st.warning("Por favor, ingrese el nombre de la categoría.")
            else:
                cx = obtener_conexion()
                if cx:
                    cur = cx.cursor()
                    try:
                        cur.execute("INSERT INTO Categoria (Nombre) VALUES (%s)", (nombre.strip(),))
                        cx.commit()
                        st.session_state["ok_cat"] = f"✅ Categoría '{nombre.strip()}' registrada."
                        st.rerun()
                    except mysql.connector.IntegrityError:
                        st.error("❌ Esa categoría ya existe; el catálogo no admite duplicados.")
                    finally:
                        cur.close(); cx.close()
    else:
        st.info("Solo el Administrador General puede crear categorías, para mantener un catálogo homogéneo.")

    datos = consultar("""SELECT c.id_categoria AS ID, c.Nombre AS Categoría, COUNT(p.id_producto) AS Productos
                         FROM Categoria c LEFT JOIN Producto p ON p.id_categoria = c.id_categoria
                         GROUP BY c.id_categoria, c.Nombre ORDER BY c.Nombre""")
    st.dataframe(datos, width="stretch", hide_index=True)
