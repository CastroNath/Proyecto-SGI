import streamlit as st
from config.conexion import obtener_conexion

def obtener_clientes_registrados():
    conexion = obtener_conexion()
    if not conexion:
        return []
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT id_cliente, Nombre, Tipo FROM Cliente WHERE id_cliente != 1 ORDER BY Nombre")
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()

def obtener_productos_disponibles(id_tienda):
    conexion = obtener_conexion()
    if not conexion:
        return []
    try:
        cursor = conexion.cursor(dictionary=True)
        consulta = """
            SELECT i.id_inventario, p.id_producto, p.Nombre, p.Unidad_medida, p.Codigo_barras,
                   i.Existencia, i.Precio_venta
            FROM Inventario i
            INNER JOIN Producto p ON i.id_producto = p.id_producto
            WHERE i.id_tienda = %s AND i.Existencia > 0
            ORDER BY p.Nombre
        """
        cursor.execute(consulta, (id_tienda,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()

def registrar_venta_completa(id_tienda, id_usuario, id_cliente, carrito, total_venta):
    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos."
    cursor = None
    try:
        cursor = conexion.cursor()
        
        sql_venta = """
            INSERT INTO Venta (id_tienda, id_usuario, id_cliente, Total)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql_venta, (id_tienda, id_usuario, id_cliente, total_venta))
        id_venta_generado = cursor.lastrowid
        
        for item in carrito:
            sql_detalle = """
                INSERT INTO Detalle_venta (id_venta, Cantidad, Precio_unitario)
                VALUES (%s, %s, %s)
            """
            cursor.execute(sql_detalle, (id_venta_generado, item["cantidad"], item["precio"]))
            id_detalle_generado = cursor.lastrowid
            
            sql_inv = """
                UPDATE Inventario 
                SET Existencia = Existencia - %s, id_detalle_venta = %s
                WHERE id_inventario = %s AND Existencia >= %s
            """
            cursor.execute(sql_inv, (
                item["cantidad"], 
                id_detalle_generado, 
                item["id_inventario"], 
                item["cantidad"]
            ))
            
            if cursor.rowcount == 0:
                raise Exception(f"Stock insuficiente para el producto '{item['nombre']}'.")
                
        conexion.commit()
        return True, f"✅ Venta #{id_venta_generado} registrada con éxito por un total de ${total_venta:.2f}."
    except Exception as e:
        conexion.rollback()
        return False, f"❌ Error al procesar la venta: {e}"
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()

def mostrar_ventas():
    st.header("💸 Punto de Venta")
    
    id_tienda = st.session_state.get("id_tienda")
    id_usuario = st.session_state.get("id_usuario")
    
    if st.session_state.get("limpiar_campos_venta", False):
        st.session_state["venta_req_factura"] = False
        st.session_state["limpiar_campos_venta"] = False

    if "carrito_ventas" not in st.session_state:
        st.session_state["carrito_ventas"] = []
    if "venta_req_factura" not in st.session_state:
        st.session_state["venta_req_factura"] = False

    if st.session_state.get("msg_exito_venta"):
        st.success(st.session_state["msg_exito_venta"])
        st.session_state["msg_exito_venta"] = ""

    st.subheader("Datos del Comprador")
    requiere_factura = st.checkbox("🧾 El cliente requiere factura con nombre / datos (o es venta a sucursal)", key="venta_req_factura")
    
    id_cliente_final = 1
    if requiere_factura:
        clientes = obtener_clientes_registrados()
        if not clientes:
            st.warning("⚠️ No hay clientes registrados aún. Puedes registrarlo en el catálogo de Clientes o continuar como Consumidor Final.")
            id_cliente_final = 1
        else:
            cliente_sel = st.selectbox(
                "Selecciona el Cliente o Tienda",
                clientes,
                format_func=lambda x: f"{x['Nombre']} ({x['Tipo']})"
            )
            id_cliente_final = cliente_sel["id_cliente"]
    else:
        st.info("⚡ Venta rápida: Se registrará automáticamente como **Consumidor Final (Externo)**.")

    st.divider()

    st.subheader("Agregar Productos al Carrito")
    productos_disp = obtener_productos_disponibles(id_tienda)
    
    if not productos_disp:
        st.warning("📦 No hay productos con existencias disponibles en el inventario de esta tienda. Debes registrar una compra primero.")
        return

    col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
    with col_p1:
        prod_sel = st.selectbox(
            "Producto disponible",
            productos_disp,
            format_func=lambda x: f"{x['Nombre']} ({x['Unidad_medida']}) - Stock: {x['Existencia']} | ${float(x['Precio_venta']):.2f}"
        )
    with col_p2:
        max_cant = int(prod_sel["Existencia"])
        cantidad = st.number_input("Cantidad", min_value=1, max_value=max_cant, value=1, step=1)
    with col_p3:
        st.write("")
        st.write("")
        if st.button("➕ Agregar"):
            encontrado = False
            for item in st.session_state["carrito_ventas"]:
                if item["id_inventario"] == prod_sel["id_inventario"]:
                    if item["cantidad"] + cantidad <= max_cant:
                        item["cantidad"] += cantidad
                        item["subtotal"] = item["cantidad"] * item["precio"]
                    else:
                        st.error(f"⚠️ No puedes superar el stock disponible ({max_cant} unidades).")
                    encontrado = True
                    break
                    
            if not encontrado:
                precio_unit = float(prod_sel["Precio_venta"])
                st.session_state["carrito_ventas"].append({
                    "id_inventario": prod_sel["id_inventario"],
                    "id_producto": prod_sel["id_producto"],
                    "nombre": prod_sel["Nombre"],
                    "unidad": prod_sel["Unidad_medida"],
                    "cantidad": cantidad,
                    "precio": precio_unit,
                    "subtotal": cantidad * precio_unit
                })
            st.rerun()

    if st.session_state["carrito_ventas"]:
        st.divider()
        st.subheader("Detalle de la Venta")
        
        total_general = 0.0
        for idx, item in enumerate(st.session_state["carrito_ventas"]):
            c_item1, c_item2, c_item3, c_item4, c_item5 = st.columns([3, 1, 1.5, 1.5, 0.8])
            c_item1.write(f"**{item['nombre']}** ({item['unidad']})")
            c_item2.write(f"Cant: {item['cantidad']}")
            c_item3.write(f"${item['precio']:.2f} c/u")
            c_item4.write(f"**${item['subtotal']:.2f}**")
            if c_item5.button("🗑️", key=f"del_item_{idx}"):
                st.session_state["carrito_ventas"].pop(idx)
                st.rerun()
            total_general += item["subtotal"]

        st.markdown(f"### Total a Pagar: `${total_general:.2f}`")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🧹 Vaciar Carrito"):
                st.session_state["carrito_ventas"] = []
                st.session_state["limpiar_campos_venta"] = True
                st.rerun()
        with col_btn2:
            if st.button("💳 Confirmar y Cobrar Venta"):
                exito, mensaje = registrar_venta_completa(
                    id_tienda,
                    id_usuario,
                    id_cliente_final,
                    st.session_state["carrito_ventas"],
                    total_general
                )
                if exito:
                    st.session_state["carrito_ventas"] = []
                    st.session_state["msg_exito_venta"] = mensaje
                    st.session_state["limpiar_campos_venta"] = True
                    st.rerun()
                else:
                    st.error(mensaje)
