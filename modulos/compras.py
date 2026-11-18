import streamlit as st
from datetime import date
from config.conexion import obtener_conexion

def obtener_proveedores(id_tienda_actual):
    cx = obtener_conexion()
    if not cx: return []
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT Nombre, Tipo FROM Tienda WHERE id_tienda = %s", (id_tienda_actual,))
        t = cur.fetchone()
        es_cd = t and ("distribuci" in (t["Nombre"] or "").lower() or "distribuci" in (t["Tipo"] or "").lower())
        if es_cd:
            cur.execute("SELECT id_proveedor, Nombre, Tipo FROM Proveedor WHERE LOWER(Nombre) NOT LIKE '%distribuci%' ORDER BY Nombre")
        else:
            cur.execute("SELECT id_proveedor, Nombre, Tipo FROM Proveedor ORDER BY Nombre")
        return cur.fetchall()
    finally:
        cur.close(); cx.close()

def obtener_productos_catalogo():
    cx = obtener_conexion()
    if not cx: return []
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT id_producto, Nombre, Unidad_medida, Codigo_barras FROM Producto ORDER BY Nombre")
        return cur.fetchall()
    finally:
        cur.close(); cx.close()

def registrar_compra_completa(id_tienda, id_usuario, id_proveedor, carrito, total_compra):
    cx = obtener_conexion()
    if not cx: return False, "No hay conexión con la base de datos."
    cur = None
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("INSERT INTO Compra (id_tienda, id_proveedor, id_usuario, Total, Estado) VALUES (%s, %s, %s, %s, 'Recibida')", (id_tienda, id_proveedor, id_usuario, total_compra))
        id_compra_gen = cur.lastrowid
        
        for item in carrito:
            cur.execute("INSERT INTO Detalle_compra (id_compra, Cantidad, Precio_compra, Precio_venta_sugerido, Fecha_vencimiento) VALUES (%s, %s, %s, %s, %s)", (id_compra_gen, item["cantidad"], item["precio_compra"], item["precio_venta"], item["fecha_venc"]))
            id_det_gen = cur.lastrowid
            
            cur.execute("""
                INSERT INTO ProductoxProveedor (id_producto, id_proveedor, Ultimo_precio, Fecha_ultima_compra)
                VALUES (%s, %s, %s, CURDATE())
                ON DUPLICATE KEY UPDATE Ultimo_precio = VALUES(Ultimo_precio), Fecha_ultima_compra = CURDATE()
            """, (item["id_producto"], id_proveedor, item["precio_compra"]))
            
            cur.execute("SELECT id_inventario FROM Inventario WHERE id_tienda = %s AND id_producto = %s LIMIT 1", (id_tienda, item["id_producto"]))
            inv = cur.fetchone()
            
            if inv:
                cur.execute("UPDATE Inventario SET Existencia = Existencia + %s, Precio_venta = %s, id_detalle_compra = %s WHERE id_inventario = %s", (item["cantidad"], item["precio_venta"], id_det_gen, inv["id_inventario"]))
            else:
                cur.execute("INSERT INTO Inventario (id_tienda, id_producto, id_detalle_compra, Existencia, Stock_minimo, Precio_venta) VALUES (%s, %s, %s, %s, 5, %s)", (id_tienda, item["id_producto"], id_det_gen, item["cantidad"], item["precio_venta"]))
                
        cx.commit()
        return True, f"✅ Compra #{id_compra_gen} registrada e inventario actualizado (${total_compra:.2f})."
    except Exception as e:
        cx.rollback()
        return False, f"❌ Error al registrar la compra: {e}"
    finally:
        if cur: cur.close()
        if cx: cx.close()

def mostrar_compras():
    st.header("📥 Registrar Compra de Mercadería")
    id_tienda = st.session_state.get("id_tienda")
    id_usuario = st.session_state.get("id_usuario")
    
    if "reset_prov_comp" not in st.session_state: st.session_state["reset_prov_comp"] = 0
    if "reset_prod_comp" not in st.session_state: st.session_state["reset_prod_comp"] = 0

    if st.session_state.get("limpiar_item_compra", False):
        st.session_state["reset_prod_comp"] += 1
        st.session_state["comp_cant_0"] = 0
        st.session_state["comp_costo_0"] = 0.00
        st.session_state["comp_venc_chk_0"] = False
        st.session_state["limpiar_item_compra"] = False

    if st.session_state.get("limpiar_todo_compra", False):
        st.session_state["reset_prov_comp"] += 1
        st.session_state["reset_prod_comp"] += 1
        st.session_state["comp_cant_0"] = 0
        st.session_state["comp_costo_0"] = 0.00
        st.session_state["comp_venc_chk_0"] = False
        st.session_state["limpiar_todo_compra"] = False

    if "carrito_compras" not in st.session_state: st.session_state["carrito_compras"] = []
    if "comp_cant_0" not in st.session_state: st.session_state["comp_cant_0"] = 0
    if "comp_costo_0" not in st.session_state: st.session_state["comp_costo_0"] = 0.00
    if "comp_venc_chk_0" not in st.session_state: st.session_state["comp_venc_chk_0"] = False
        
    if st.session_state.get("msg_exito_compra"):
        st.success(st.session_state.pop("msg_exito_compra"))

    proveedores = obtener_proveedores(id_tienda)
    productos = obtener_productos_catalogo()
    
    if not proveedores:
        st.warning("⚠️ No hay proveedores disponibles para esta sucursal.")
        return
    if not productos:
        st.warning("⚠️ Primero debes registrar productos en el catálogo.")
        return

    prov_sel = st.selectbox(
        "Proveedor",
        [None] + proveedores,
        index=0,
        format_func=lambda x: "-- Selecciona un proveedor --" if x is None else f"{x['Nombre']} ({x['Tipo']})",
        key=f"sel_prov_comp_{st.session_state['reset_prov_comp']}",
        disabled=(len(st.session_state["carrito_compras"]) > 0)
    )

    st.divider()
    st.subheader("Detalle de Productos Recibidos")
    
    c1, c2 = st.columns(2)
    with c1:
        prod_sel = st.selectbox(
            "Producto del Catálogo",
            [None] + productos,
            index=0,
            format_func=lambda x: "-- Selecciona un producto --" if x is None else f"{x['Nombre']} ({x['Unidad_medida']}) - {x['Codigo_barras']}",
            key=f"sel_prod_comp_{st.session_state['reset_prod_comp']}"
        )
        cantidad = st.number_input("Cantidad recibida", min_value=0, step=1, key="comp_cant_0")
    with c2:
        precio_compra = st.number_input("Precio de Compra Unitario ($)", min_value=0.00, step=0.05, format="%.2f", key="comp_costo_0")
        precio_sugerido = round(precio_compra * 1.20, 2)
        st.number_input("Precio de Venta Sugerido (+20%)", value=precio_sugerido, format="%.2f", disabled=True)

    tiene_vencimiento = st.checkbox("📅 Este lote tiene fecha de vencimiento", key="comp_venc_chk_0")
    fecha_venc = st.date_input("Fecha de Vencimiento", min_value=date.today()) if tiene_vencimiento else None

    if st.button("➕ Agregar Producto a la Compra"):
        if prod_sel is None:
            st.warning("⚠️ Por favor, selecciona un producto del catálogo.")
        elif cantidad <= 0:
            st.warning("⚠️ La cantidad recibida debe ser mayor a 0.")
        elif precio_compra <= 0:
            st.warning("⚠️ El precio de compra unitario debe ser mayor a $0.00.")
        else:
            st.session_state["carrito_compras"].append({
                "id_producto": prod_sel["id_producto"],
                "nombre": prod_sel["Nombre"],
                "unidad": prod_sel["Unidad_medida"],
                "cantidad": cantidad,
                "precio_compra": precio_compra,
                "precio_venta": precio_sugerido,
                "fecha_venc": fecha_venc,
                "subtotal": cantidad * precio_compra
            })
            st.session_state["limpiar_item_compra"] = True
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
            col4.write(f"Sugerido: ${item['precio_venta']:.2f}")
            if col5.button("🗑️", key=f"del_comp_{idx}"):
                st.session_state["carrito_compras"].pop(idx)
                st.rerun()
            total_compra += item["subtotal"]

        st.markdown(f"### Total de Compra: `${total_compra:.2f}`")
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🧹 Limpiar Orden"):
                st.session_state["carrito_compras"] = []
                st.session_state["limpiar_todo_compra"] = True
                st.rerun()
        with b2:
            if st.button("💾 Confirmar Compra e Ingresar al Inventario"):
                if prov_sel is None:
                    st.error("❌ Debes seleccionar un proveedor para confirmar la compra.")
                else:
                    exito, msg = registrar_compra_completa(id_tienda, id_usuario, prov_sel["id_proveedor"], st.session_state["carrito_compras"], total_compra)
                    if exito:
                        st.session_state["carrito_compras"] = []
                        st.session_state["msg_exito_compra"] = msg
                        st.session_state["limpiar_todo_compra"] = True
                        st.rerun()
                    else:
                        st.error(msg)
