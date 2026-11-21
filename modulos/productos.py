import streamlit as st
import mysql.connector
from config.conexion import consultar_uno, obtener_conexion
from modulos.formato import tabla

def es_centro_distribucion(id_tienda):
    cx = obtener_conexion()
    if not cx: return False
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT Tipo FROM Tienda WHERE id_tienda = %s", (id_tienda,))
        t = cur.fetchone()
        return bool(t) and (t["Tipo"] or "").upper() == "CD"
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

PREFIJO_INTERNO = "20"  # GS1 reserva 20-29 para códigos de uso interno (circulación restringida)


def digito_verificador(datos):
    """Dígito verificador GS1 (EAN-13, EAN-8, UPC-A): desde la derecha se multiplica por 3, 1, 3, 1…"""
    suma = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(datos)))
    return str((10 - suma % 10) % 10)


def codigo_valido(codigo):
    """True si es un EAN-8, UPC-A (12) o EAN-13 con su dígito verificador correcto."""
    return codigo.isdigit() and len(codigo) in (8, 12, 13) and digito_verificador(codigo[:-1]) == codigo[-1]


def generar_siguiente_codigo():
    """Siguiente código interno EAN-13: 20 + correlativo de 10 dígitos + dígito verificador."""
    cx = obtener_conexion()
    if not cx:
        datos = f"{PREFIJO_INTERNO}{1:010d}"
        return datos + digito_verificador(datos)
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT Codigo_barras FROM Producto WHERE Codigo_barras LIKE %s AND CHAR_LENGTH(Codigo_barras) = 13",
                    (PREFIJO_INTERNO + "%",))
        correlativos = [int(r["Codigo_barras"][2:12]) for r in cur.fetchall() if r["Codigo_barras"].isdigit()]
        datos = f"{PREFIJO_INTERNO}{(max(correlativos) + 1 if correlativos else 1):010d}"
        return datos + digito_verificador(datos)
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
            tabla(catalogo, width="stretch", hide_index=True)
        else:
            st.warning("📭 Aún no hay productos registrados en el catálogo.")
        return

    # Si pertenece a una Tienda Minorista, permitir registrar y consultar
    tab1, tab2 = st.tabs(["➕ Registrar Nuevo Producto", "📋 Consultar Catálogo Global"])

    with tab1:
        if st.session_state.get("limpiar_prod", False):
            st.session_state["prod_nom"] = ""
            st.session_state["prod_uni"] = None
            st.session_state["prod_cat"] = None
            st.session_state["prod_con_codigo"] = False
            st.session_state["prod_cod_fab"] = ""
            st.session_state["limpiar_prod"] = False

        if st.session_state.get("ok_prod"):
            st.success(st.session_state.pop("ok_prod"))

        if "prod_nom" not in st.session_state: st.session_state["prod_nom"] = ""
        if "prod_uni" not in st.session_state: st.session_state["prod_uni"] = None
        if "prod_cat" not in st.session_state: st.session_state["prod_cat"] = None

        categorias = obtener_categorias()
        if not categorias:
            st.warning("⚠️ Primero debes crear al menos una categoría en el catálogo.")
            return

        con_codigo = st.checkbox("El producto ya tiene código de barras del fabricante", key="prod_con_codigo")
        if con_codigo:
            codigo_fab = st.text_input("Código de barras del fabricante *", max_chars=13, key="prod_cod_fab",
                                       placeholder="7501234567893",
                                       help="Escribe los números que aparecen bajo el código de barras del empaque "
                                            "(8, 12 o 13 dígitos). El sistema revisa que el dígito verificador sea correcto.")
            codigo_auto = None
        else:
            codigo_fab = ""
            codigo_auto = generar_siguiente_codigo()
            st.text_input("Código de barras interno (EAN-13 automático)", value=codigo_auto, disabled=True,
                          help="Se genera con el prefijo 20, reservado para uso interno, y su dígito verificador.")
        
        nombre = st.text_input("Nombre del Producto", key="prod_nom")
        # Sin opción preseleccionada: se obliga a elegir conscientemente
        nombres_cat = {c["id_categoria"]: c["Nombre"] for c in categorias}
        id_cat = st.selectbox("Categoría", list(nombres_cat), format_func=nombres_cat.get, index=None,
                              placeholder="-- Selecciona una categoría --", key="prod_cat")
        unidad = st.selectbox(
            "Unidad de Medida",
            ["Unidad", "Libra", "Kilogramo", "Gramo", "Onza", "Litro", "Mililitro", "Paquete", "Bolsa",
             "Caja", "Docena", "Frasco", "Saco"],
            index=None, placeholder="-- Selecciona una unidad de medida --", key="prod_uni"
        )

        if st.button("Guardar Producto", key="btn_save_prod"):
            if not nombre.strip():
                st.warning("⚠️ El nombre del producto es obligatorio.")
            elif id_cat is None:
                st.warning("⚠️ Selecciona la categoría del producto.")
            elif unidad is None:
                st.warning("⚠️ Selecciona la unidad de medida.")
            elif con_codigo and not codigo_valido(codigo_fab.strip()):
                st.warning("⚠️ El código del fabricante no es válido: debe tener 8, 12 o 13 dígitos y el último "
                           "(dígito verificador) debe coincidir. Revisa que lo hayas copiado bien.")
            elif con_codigo and consultar_uno("SELECT Nombre FROM Producto WHERE Codigo_barras = %s", (codigo_fab.strip(),)):
                st.warning(f"⚠️ El código {codigo_fab.strip()} ya pertenece a «"
                           f"{consultar_uno('SELECT Nombre FROM Producto WHERE Codigo_barras = %s', (codigo_fab.strip(),))['Nombre']}».")
            elif consultar_uno("SELECT 1 AS x FROM Producto WHERE LOWER(TRIM(Nombre)) = LOWER(%s) AND Unidad_medida = %s",
                               (nombre.strip(), unidad)):
                st.warning(f"⚠️ Ya existe «{nombre.strip()}» ({unidad}) en el catálogo.")
            else:
                codigo_final = codigo_fab.strip() if con_codigo else codigo_auto
                cx = obtener_conexion()
                if cx:
                    try:
                        cur = cx.cursor()
                        cur.execute(
                            "INSERT INTO Producto (id_categoria, Nombre, Unidad_medida, Codigo_barras) VALUES (%s, %s, %s, %s)",
                            (id_cat, nombre.strip(), unidad, codigo_final)
                        )
                        cx.commit()
                        st.session_state["ok_prod"] = f"✅ Producto '{nombre.strip()}' registrado con código {codigo_final}."
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
            tabla(catalogo, width="stretch", hide_index=True)
        else:
            st.info("📭 No hay productos registrados aún.")
