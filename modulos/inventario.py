import streamlit as st
from config.conexion import obtener_conexion
from modulos.compras import sincronizar_compras_en_transito

def obtener_tiendas():
    conexion = obtener_conexion()
    if not conexion:
        return []
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT id_tienda, Nombre FROM Tienda ORDER BY Nombre")
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()

def consultar_inventario(id_tienda_filtro=None):
    conexion = obtener_conexion()
    if not conexion:
        return []
    try:
        cursor = conexion.cursor(dictionary=True)
        if id_tienda_filtro:
            consulta = """
                SELECT t.Nombre AS Tienda, p.Codigo_barras, p.Nombre AS Producto, 
                       c.Nombre AS Categoria, p.Unidad_medida, i.Existencia, 
                       i.Stock_minimo, i.Precio_venta, dc.Fecha_vencimiento
                FROM Inventario i
                INNER JOIN Tienda t ON i.id_tienda = t.id_tienda
                INNER JOIN Producto p ON i.id_producto = p.id_producto
                INNER JOIN Categoria c ON p.id_categoria = c.id_categoria
                LEFT JOIN Detalle_compra dc ON i.id_detalle_compra = dc.id_detalle_compra
                WHERE i.id_tienda = %s
                ORDER BY p.Nombre
            """
            cursor.execute(consulta, (id_tienda_filtro,))
        else:
            consulta = """
                SELECT t.Nombre AS Tienda, p.Codigo_barras, p.Nombre AS Producto, 
                       c.Nombre AS Categoria, p.Unidad_medida, i.Existencia, 
                       i.Stock_minimo, i.Precio_venta, dc.Fecha_vencimiento
                FROM Inventario i
                INNER JOIN Tienda t ON i.id_tienda = t.id_tienda
                INNER JOIN Producto p ON i.id_producto = p.id_producto
                INNER JOIN Categoria c ON p.id_categoria = c.id_categoria
                LEFT JOIN Detalle_compra dc ON i.id_detalle_compra = dc.id_detalle_compra
                ORDER BY t.Nombre, p.Nombre
            """
            cursor.execute(consulta)
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()

def mostrar_inventario():
    sincronizar_compras_en_transito()
    st.header("📦 Gestión de Inventarios")
    
    es_admin = (st.session_state.get("id_rol") == 1)
    id_tienda_usuario = st.session_state.get("id_tienda")
    
    if es_admin:
        tiendas = obtener_tiendas()
        opciones = [{"id_tienda": None, "Nombre": "🌐 Todas las sucursales (Visión Global)"}] + tiendas
        filtro = st.selectbox("Filtrar por Sucursal", opciones, format_func=lambda x: x["Nombre"])
        datos = consultar_inventario(filtro["id_tienda"])
    else:
        st.caption("Mostrando existencias disponibles en tu sucursal asignada.")
        datos = consultar_inventario(id_tienda_usuario)

    if not datos:
        st.info("📭 Aún no hay productos recibidos en el inventario de esta selección.")
        return

    bajos = [d for d in datos if d["Existencia"] <= d["Stock_minimo"]]
    if bajos:
        st.warning(f"⚠️ Alerta de Punto de Reorden (ROP): Hay **{len(bajos)}** producto(s) con existencias iguales o menores a su stock mínimo calculado.")

    st.dataframe(
        datos,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Precio_venta": st.column_config.NumberColumn("Precio Venta ($)", format="$%.2f")
        }
    )
