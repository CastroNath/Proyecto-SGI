import streamlit as st
from datetime import date
from config.conexion import obtener_conexion

def obtener_proveedores():
    conexion = obtener_conexion()
    if not conexion:
        return []
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT id_proveedor, Nombre, Tipo FROM Proveedor ORDER BY Nombre")
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()

def obtener_productos_catalogo():
    conexion = obtener_conexion()
    if not conexion:
        return []
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT id_producto, Nombre, Unidad_medida, Codigo_barras FROM Producto ORDER BY Nombre")
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()

def registrar_compra_completa(id_tienda, id_usuario, id_proveedor, carrito, total_compra):
    conexion = obtener_conexion()
    if not conexion:
        return False, "No hay conexión con la base de datos."
    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        
        # 1. Insertar encabezado en Compra
        sql_compra = """
            INSERT INTO Compra (id_tienda, id_proveedor, id_usuario, Total, Estado)
            VALUES (%s, %s, %s, %s, 'Recibida')
        """
        cursor.execute(sql_compra, (id_tienda, id_proveedor, id_usuario, total_compra))
        id_compra_gen = cursor.lastrowid
        
        # 2. Procesar cada producto del carrito de compra
        for item in carrito:
            # A. Insertar en Detalle_compra
            sql_det = """
                INSERT INTO Detalle_compra (id_compra, Cantidad, Precio_compra, Precio_venta_sugerido, Fecha_vencimiento)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql_det, (
                id_compra_gen,
                item["cantidad"],
                item["precio_compra"],
                item["precio_venta"],
                item["fecha_venc"]
            ))
            id_det_compra_gen = cursor.lastrowid
            
            # B. Actualizar o insertar en ProductoxProveedor (Muchos a Muchos)
            sql_pxp = """
                INSERT INTO ProductoxProveedor (id_producto, id_proveedor, Ultimo_precio, Fecha_ultima_compra)
                VALUES (%s, %s, %s, CURDATE())
                ON DUPLICATE KEY UPDATE 
                    Ultimo_precio = VALUES(Ultimo_precio),
                    Fecha_ultima_compra = CURDATE()
            """
            cursor.execute(sql_pxp, (item["id_producto"], id_proveedor, item["precio_compra"]))
            
            # C. Verificar si el producto ya existe en el Inventario de esta tienda
            cursor.execute(
                "SELECT id_inventario FROM Inventario WHERE id_tienda = %s AND id_producto = %s LIMIT 1",
                (id_tienda, item["id_producto"])
            )
            inv_existente = cursor.fetchone()
            
            if inv_existente:
                # Sumar existencias y actualizar precio de venta
                sql_upd_inv = """
                    UPDATE Inventario
                    SET Existencia = Existencia + %s,
                        Precio_venta = %s,
                        id_detalle_compra = %s
                    WHERE id_inventario = %s
                """
                cursor.execute(sql_upd_inv, (
                    item["cantidad"],
                    item["precio_venta"],
                    id_det_compra_gen,
                    inv_existente["id_inventario"]
                ))
            else:
                # Crear registro nuevo en el Inventario de esta tienda
                sql_ins_inv = """
                    INSERT INTO Inventario (id_tienda, id_producto, id_detalle_compra, Existencia, Stock_minimo, Precio_venta)
                    VALUES (%s, %s, %s, %s, 5, %s)
                """
                cursor.execute(sql_ins_inv, (
                    id_tienda,
                    item["id_producto"],
                    id_det_compra_gen,
                    item["cantidad"],
                    item["precio_venta"]
                ))
                
        conexion.commit()
        return True, f"✅ Compra #{id_compra_gen} registrada e inventario actualizado (${total_compra:.2f})."
    except Exception as e:
        conexion.rollback()
        return False, f"❌ Error al registrar la compra: {e}"
    finally:
        if cursor: cursor.close()
        if conexion: conexion.close()

def mostrar_compras():
    st.header("📥 Registrar Compra de Mercadería")
    
    id_tienda = st.session_state.get("id_tienda")
    id_usuario = st.session_state.get("id_usuario")
    
    if "carrito_compras" not in st.session_state:
        st.session_state["carrito_compras"] = []
        
    if st.session_state.get("msg_exito_compra"):
        st.success(st.session_state["msg_exito_compra"])
        st.session_state["msg_exito_compra"] = ""

    proveedores = obtener_proveedores()
    productos = obtener_productos_catalogo()
    
    if not proveedores:
        st.warning("⚠️ Primero debes registrar al menos un proveedor en el catálogo.")
        return
    if not productos:
        st.warning("⚠️ Primero debes registrar productos en el catálogo.")
        return

    # 1. Selección de Proveedor
    prov_sel = st.selectbox(
        "Proveedor",
        proveedores,
        format_func=lambda x: f"{x['Nombre']} ({x['Tipo']})"
    )

    st.divider()

    # 2. Agregar productos a la compra
    st.subheader("Detalle de Productos Recibidos")
    c1, c2 = st.columns(2)
    with c1:
        prod_sel = st.selectbox(
            "Producto del Catálogo",
            productos,
            format_func=lambda x: f"{x['Nombre']} ({x['Unidad_medida']}) - {x['Codigo_barras']}"
        )
        cantidad = st.number_input("Cantidad recibida", min_value=1, value=10, step=1)
    with c2:
        precio_compra = st.number_input("Precio de Compra Unitario ($)", min_value=0.01, value=1.00, step=0.05, format="%.2f")
        precio_venta = st.number_input("Precio de Venta Definido ($)", min_value=0.01, value=1.25, step=0.05, format="%.2f")

    tiene_vencimiento = st.checkbox("📅 Este lote tiene fecha de vencimiento")
    fecha_venc = None
    if tiene_vencimiento:
        fecha_venc = st.date_input("Fecha de Vencimiento", min_value=date.today())

    if st.button("➕ Agregar Producto a la Compra"):
        st.session_state["carrito_compras"].append({
            "id_producto": prod_sel["id_producto"],
            "nombre": prod_sel["Nombre"],
            "unidad": prod_sel["Unidad_medida"],
            "cantidad": cantidad,
            "precio_compra": precio_compra,
            "precio_venta": precio_venta,
            "fecha_venc": fecha_venc,
            "subtotal": cantidad * precio_compra
        })
        st.rerun()

    # 3. Resumen y Guardado
    if st.session_state["carrito_compras"]:
        st.divider()
        st.subheader("Resumen de la Orden de Compra")
        total_compra = 0.0
        
        for idx, item in enumerate(st.session_state["carrito_compras"]):
            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1.5, 0.8])
            col1.write(f"**{item['nombre']}** ({item['unidad']})")
            col2.write(f"Cant: {item['cantidad']}")
            col3.write(f"Costo: ${item['precio_compra']:.2f}")
            col4.write(f"Venta: ${item['precio_venta']:.2f}")
            if col5.button("🗑️", key=f"del_comp_{idx}"):
                st.session_state["carrito_compras"].pop(idx)
                st.rerun()
            total_compra += item["subtotal"]

        st.markdown(f"### Total de Compra: `${total_compra:.2f}`")
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🧹 Limpiar Orden"):
                st.session_state["carrito_compras"] = []
                st.rerun()
        with b2:
            if st.button("💾 Confirmar Compra e Ingresar al Inventario"):
                exito, msg = registrar_compra_completa(
                    id_tienda,
                    id_usuario,
                    prov_sel["id_proveedor"],
                    st.session_state["carrito_compras"],
                    total_compra
                )
                if exito:
                    st.session_state["carrito_compras"] = []
                    st.session_state["msg_exito_compra"] = msg
                    st.rerun()
                else:
                    st.error(msg)
