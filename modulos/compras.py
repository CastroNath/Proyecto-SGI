import streamlit as st
from datetime import date
from config.conexion import obtener_conexion

def obtener_proveedores(id_tienda_actual):
    conexion = obtener_conexion()
    if not conexion:
        return []
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT Nombre, Tipo FROM Tienda WHERE id_tienda = %s", (id_tienda_actual,))
        tienda_actual = cursor.fetchone()
        
        es_cd = False
        if tienda_actual:
            nombre_t = (tienda_actual["Nombre"] or "").lower()
            tipo_t = (tienda_actual["Tipo"] or "").lower()
            if "distribuci" in nombre_t or "distribuci" in tipo_t:
                es_cd = True

        if es_cd:
            cursor.execute("SELECT id_proveedor, Nombre, Tipo FROM Proveedor WHERE LOWER(Nombre) NOT LIKE '%distribuci%' ORDER BY Nombre")
        else:
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
        
        sql_compra = """
            INSERT INTO Compra (id_tienda, id_proveedor, id_usuario, Total, Estado)
            VALUES (%s, %s, %s, %s, 'Recibida')
        """
        cursor.execute(sql_compra, (id_tienda, id_proveedor, id_usuario, total_compra))
        id_compra_gen = cursor.lastrowid
        
        for item in carrito:
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
            
            sql_pxp = """
                INSERT INTO ProductoxProveedor (id_producto, id_proveedor, Ultimo_precio, Fecha_ultima_compra)
                VALUES (%s, %s, %s, CURDATE())
                ON DUPLICATE KEY UPDATE 
                    Ultimo_precio = VALUES(Ultimo_precio),
                    Fecha_ultima_compra = CURDATE()
            """
            cursor.execute(sql_pxp, (item["id_producto"], id_proveedor, item["precio_compra"]))
            
            cursor.execute(
                "SELECT id_inventario FROM Inventario WHERE id_tienda = %s AND id_producto = %s LIMIT 1",
                (id_tienda, item["id_producto"])
            )
            inv_existente = cursor.fetchone()
            
            if inv_existente:
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
    
    if st.session_state.get("limpiar_campos_compra", False):
        st.session_state["comp_cant"] = 1
        st.session_state["comp_costo"] = 1.00
        st.session_state["comp_venta"] = 1.25
        st.session_state["comp_venc_chk"] = False
        st.session_state["limpiar_campos_compra"] = False

    if "carrito_compras" not in st.session_state:
        st.session_state["carrito_compras"] = []
    if "comp_cant" not in st.session_state:
        st.session_state["comp_cant"] = 1
    if "comp_costo" not in st.session_state:
        st.session_state["comp_costo"] = 1.00
    if "comp_venta" not in st.session_state:
        st.session_state["comp_venta"] = 1.25
    if "comp_venc_chk" not in st.session_state:
        st.session_state["comp_venc_chk"] = False
        
    if st.session_state.get("msg_exito_compra"):
        st.success(st.session_state["msg_exito_compra"])
        st.session_state["msg_exito_compra"] = ""

    proveedores = obtener_proveedores(id_tienda)
    productos = obtener_productos_catalogo()
    
    if not proveedores:
        st.warning("⚠️ No hay proveedores disponibles para esta sucursal en el catálogo.")
        return
    if not productos:
        st.warning("⚠️ Primero debes registrar productos en el catálogo.")
        return

    prov_sel = st.selectbox(
        "Proveedor",
        proveedores,
        format_func=lambda x: f"{x['Nombre']} ({x['Tipo']})"
    )

    st.divider()
    st.subheader("Detalle de Productos Recibidos")
    
    c1, c2 = st.columns(2)
    with c1:
        prod_sel = st.selectbox(
            "Producto del Catálogo",
            productos,
            format_func=lambda x: f"{x['Nombre']} ({x['Unidad_medida']}) - {x['Codigo_barras']}"
        )
        cantidad = st.number_input("Cantidad recibida", min_value=1, step=1, key="comp_cant")
    with c2:
        precio_compra = st.number_input("Precio de Compra Unitario ($)", min_value=0.01, step=0.05, format="%.2f", key="comp_costo")
        precio_venta = st.number_input("Precio de Venta Definido ($)", min_value=0.01, step=0.05, format="%.2f", key="comp_venta")

    tiene_vencimiento = st.checkbox("📅 Este lote tiene fecha de vencimiento", key="comp_venc_chk")
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
        st.session_state["limpiar_campos_compra"] = True
        st.rerun()

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
                st.session_state["limpiar_campos_compra"] = True
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
                    st.session_state["limpiar_campos_compra"] = True
                    st.rerun()
                else:
                    st.error(msg)
