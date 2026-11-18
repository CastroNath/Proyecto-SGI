import streamlit as st
import math
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from config.conexion import obtener_conexion

ZONA_SV = ZoneInfo("America/El_Salvador")

def ahora_sv():
    return datetime.now(ZONA_SV).replace(tzinfo=None)

def sincronizar_compras_en_transito():
    """Verifica órdenes 'En tránsito' cuyo Lead Time ya se cumplió y las ingresa al inventario."""
    cx = obtener_conexion()
    if not cx: return
    cur = None
    try:
        cur = cx.cursor(dictionary=True)
        fecha_actual = ahora_sv()
        
        cur.execute("""
            SELECT id_compra, id_tienda 
            FROM Compra 
            WHERE Estado = 'En tránsito' AND Fecha_entrega_estimada <= %s
        """, (fecha_actual,))
        pendientes = cur.fetchall()
        
        for comp in pendientes:
            procesar_ingreso_inventario(cur, comp["id_compra"], comp["id_tienda"])
            
        if pendientes:
            cx.commit()
    except Exception:
        cx.rollback()
    finally:
        if cur: cur.close()
        if cx: cx.close()

def procesar_ingreso_inventario(cur, id_compra, id_tienda):
    """Suma los detalles de una compra al inventario y la marca como Recibida."""
    cur.execute("""
        SELECT dc.id_detalle_compra, dc.Cantidad, dc.Precio_venta_sugerido,
               (SELECT pxp.id_producto FROM ProductoxProveedor pxp 
                INNER JOIN Compra c ON c.id_proveedor = pxp.id_proveedor 
                WHERE c.id_compra = dc.id_compra AND pxp.Ultimo_precio = dc.Precio_compra LIMIT 1) AS id_prod_rel
        FROM Detalle_compra dc
        WHERE dc.id_compra = %s
    """, (id_compra,))
    detalles = cur.fetchall()

    for d in detalles:
        id_prod = d["id_prod_rel"]
        if not id_prod:
            continue
        cur.execute("SELECT id_inventario FROM Inventario WHERE id_tienda = %s AND id_producto = %s LIMIT 1", (id_tienda, id_prod))
        inv = cur.fetchone()
        if inv:
            cur.execute("""
                UPDATE Inventario 
                SET Existencia = Existencia + %s, Precio_venta = %s, id_detalle_compra = %s 
                WHERE id_inventario = %s
            """, (d["Cantidad"], d["Precio_venta_sugerido"], d["id_detalle_compra"], inv["id_inventario"]))
        else:
            cur.execute("""
                INSERT INTO Inventario (id_tienda, id_producto, id_detalle_compra, Existencia, Stock_minimo, Precio_venta)
                VALUES (%s, %s, %s, %s, 2, %s)
            """, (id_tienda, id_prod, d["id_detalle_compra"], d["Cantidad"], d["Precio_venta_sugerido"]))

    cur.execute("UPDATE Compra SET Estado = 'Recibida' WHERE id_compra = %s", (id_compra,))

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

def registrar_orden_compra(id_tienda, id_usuario, id_proveedor, carrito, total_compra):
    cx = obtener_conexion()
    if not cx: return False, "No hay conexión con la base de datos."
    cur = None
    try:
        cur = cx.cursor(dictionary=True)
        fecha_registro = ahora_sv()
        max_lead_time = max(item["lead_time"] for item in carrito)
        fecha_estimada = fecha_registro + timedelta(days=max_lead_time)
        
        cur.execute("""
            INSERT INTO Compra (id_tienda, id_proveedor, id_usuario, Fecha, Fecha_entrega_estimada, Total, Estado) 
            VALUES (%s, %s, %s, %s, %s, %s, 'En tránsito')
        """, (id_tienda, id_proveedor, id_usuario, fecha_registro, fecha_estimada, total_compra))
        id_compra_gen = cur.lastrowid
        
        for item in carrito:
            cur.execute("""
                INSERT INTO Detalle_compra (id_compra, Cantidad, Precio_compra, Precio_venta_sugerido, Fecha_vencimiento) 
                VALUES (%s, %s, %s, %s, %s)
            """, (id_compra_gen, item["cantidad"], item["precio_compra"], item["precio_venta"], item["fecha_venc"]))
            id_det_gen = cur.lastrowid
            
            cur.execute("""
                INSERT INTO ProductoxProveedor (id_producto, id_proveedor, Ultimo_precio, Fecha_ultima_compra)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE Ultimo_precio = VALUES(Ultimo_precio), Fecha_ultima_compra = VALUES(Fecha_ultima_compra)
            """, (item["id_producto"], id_proveedor, item["precio_compra"], fecha_registro.date()))
            
            # Pre-registrar o actualizar el Punto de Reorden (Stock_minimo) en Inventario sin sumar existencia aún
            cur.execute("SELECT id_inventario FROM Inventario WHERE id_tienda = %s AND id_producto = %s LIMIT 1", (id_tienda, item["id_producto"]))
            inv = cur.fetchone()
            if inv:
                cur.execute("UPDATE Inventario SET Stock_minimo = %s WHERE id_inventario = %s", (item["stock_minimo"], inv["id_inventario"]))
            else:
                cur.execute("""
                    INSERT INTO Inventario (id_tienda, id_producto, id_detalle_compra, Existencia, Stock_minimo, Precio_venta) 
                    VALUES (%s, %s, %s, 0, %s, %s)
                """, (id_tienda, item["id_producto"], id_det_gen, item["stock_minimo"], item["precio_venta"]))
                
        cx.commit()
        fecha_str = fecha_estimada.strftime("%d/%m/%Y %H:%M")
        return True, f"🚚 Orden #{id_compra_gen} registrada **En tránsito**. Ingresará al inventario el **{fecha_str}** (Lead Time: {max_lead_time} día(s))."
    except Exception as e:
        cx.rollback()
        return False, f"❌ Error al registrar la compra: {e}"
    finally:
        if cur: cur.close()
        if cx: cx.close()

def mostrar_compras():
    sincronizar_compras_en_transito()
    st.header("📥 Gestión de Compras")
    id_tienda = st.session_state.get("id_tienda")
    id_usuario = st.session_state.get("id_usuario")
    
    tab_nueva, tab_transito = st.tabs(["➕ Nueva Orden de Compra", "🚚 Pedidos en Tránsito"])

    with tab_nueva:
        if "reset_prov_comp" not in st.session_state: st.session_state["reset_prov_comp"] = 0
        if "reset_prod_comp" not in st.session_state: st.session_state["reset_prod_comp"] = 0

        if st.session_state.get("limpiar_item_compra", False):
            st.session_state["reset_prod_comp"] += 1
            st.session_state["comp_cant_0"] = 0
            st.session_state["comp_costo_0"] = 0.00
            st.session_state["comp_lead_0"] = 1
            st.session_state["comp_dem_0"] = 15
            st.session_state["comp_venc_chk_0"] = False
            st.session_state["limpiar_item_compra"] = False

        if st.session_state.get("limpiar_todo_compra", False):
            st.session_state["reset_prov_comp"] += 1
            st.session_state["reset_prod_comp"] += 1
            st.session_state["comp_cant_0"] = 0
            st.session_state["comp_costo_0"] = 0.00
            st.session_state["comp_lead_0"] = 1
            st.session_state["comp_dem_0"] = 15
            st.session_state["comp_venc_chk_0"] = False
            st.session_state["limpiar_todo_compra"] = False

        if "carrito_compras" not in st.session_state: st.session_state["carrito_compras"] = []
        if "comp_cant_0" not in st.session_state: st.session_state["comp_cant_0"] = 0
        if "comp_costo_0" not in st.session_state: st.session_state["comp_costo_0"] = 0.00
        if "comp_lead_0" not in st.session_state: st.session_state["comp_lead_0"] = 1
        if "comp_dem_0" not in st.session_state: st.session_state["comp_dem_0"] = 15
        if "comp_venc_chk_0" not in st.session_state: st.session_state["comp_venc_chk_0"] = False
            
        if st.session_state.get("msg_exito_compra"):
            st.success(st.session_state.pop("msg_exito_compra"))

        proveedores = obtener_proveedores(id_tienda)
        productos = obtener_productos_catalogo()
        
        if not proveedores or not productos:
            st.warning("⚠️ Verifica que tengas proveedores y productos registrados en el catálogo.")
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
        st.subheader("Detalle de Productos Solicitados")
        
        c1, c2 = st.columns(2)
        with c1:
            prod_sel = st.selectbox(
                "Producto del Catálogo",
                [None] + productos,
                index=0,
                format_func=lambda x: "-- Selecciona un producto --" if x is None else f"{x['Nombre']} ({x['Unidad_medida']}) - {x['Codigo_barras']}",
                key=f"sel_prod_comp_{st.session_state['reset_prod_comp']}"
            )
            cantidad = st.number_input("Cantidad solicitada", min_value=0, step=1, key="comp_cant_0")
            lead_time = st.number_input("Lead Time del Proveedor (días de entrega)", min_value=1, max_value=90, step=1, key="comp_lead_0")
            
        with c2:
            precio_compra = st.number_input("Precio de Compra Unitario ($)", min_value=0.00, step=0.05, format="%.2f", key="comp_costo_0")
            precio_sugerido = round(precio_compra * 1.20, 2)
            st.number_input("Precio de Venta Sugerido (+20%)", value=precio_sugerido, format="%.2f", disabled=True)
            demanda_mensual = st.number_input("Demanda Estimada Mensual (unidades/mes)", min_value=1, step=1, key="comp_dem_0")

        demanda_diaria = demanda_mensual / 30.0
        stock_min_calculado = max(1, math.ceil(demanda_diaria * lead_time))
        st.caption(f"📐 **Punto de Reorden calculado:** `{stock_min_calculado}` unidad(es) — *(Demanda diaria: {demanda_diaria:.2f} × Lead Time: {lead_time} días)*")

        tiene_vencimiento = st.checkbox("📅 Este lote tiene fecha de vencimiento", key="comp_venc_chk_0")
        fecha_venc = st.date_input("Fecha de Vencimiento", min_value=date.today()) if tiene_vencimiento else None

        if st.button("➕ Agregar Producto a la Orden"):
            if prov_sel is None:
                st.warning("⚠️ Primero debes seleccionar un proveedor.")
            elif prod_sel is None:
                st.warning("⚠️ Por favor, selecciona un producto del catálogo.")
            elif cantidad <= 0:
                st.warning("⚠️ La cantidad solicitada debe ser mayor a 0.")
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
                    "lead_time": lead_time,
                    "stock_minimo": stock_min_calculado,
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
                col1, col2, col3, col4, col5 = st.columns([3, 1.2, 1.5, 1.5, 0.8])
                col1.write(f"**{item['nombre']}** ({item['unidad']}) · *ROP: {item['stock_minimo']}*")
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
                if st.button("🚚 Confirmar Orden de Compra"):
                    if prov_sel is None:
                        st.error("❌ Debes seleccionar un proveedor.")
                    else:
                        exito, msg = registrar_orden_compra(id_tienda, id_usuario, prov_sel["id_proveedor"], st.session_state["carrito_compras"], total_compra)
                        if exito:
                            st.session_state["carrito_compras"] = []
                            st.session_state["msg_exito_compra"] = msg
                            st.session_state["limpiar_todo_compra"] = True
                            st.rerun()
                        else:
                            st.error(msg)

    with tab_transito:
        st.subheader("🚚 Órdenes de Compra en Camino")
        st.caption(f"Hora actual del sistema (El Salvador): **{ahora_sv().strftime('%d/%m/%Y %H:%M')}**")
        
        cx = obtener_conexion()
        ordenes = []
        if cx:
            try:
                cur = cx.cursor(dictionary=True)
                cur.execute("""
                    SELECT c.id_compra, p.Nombre AS Proveedor, c.Fecha AS Fecha_Pedido, 
                           c.Fecha_entrega_estimada AS Entrega_Estimada, c.Total, c.Estado
                    FROM Compra c
                    INNER JOIN Proveedor p ON c.id_proveedor = p.id_proveedor
                    WHERE c.id_tienda = %s AND c.Estado = 'En tránsito'
                    ORDER BY c.Fecha_entrega_estimada ASC
                """, (id_tienda,))
                ordenes = cur.fetchall()
            finally:
                cur.close(); cx.close()

        if not ordenes:
            st.info("✅ No hay pedidos pendientes en tránsito. Todas las compras anteriores ya fueron recibidas en inventario.")
        else:
            st.dataframe(ordenes, use_container_width=True, hide_index=True)
            sel_recibir = st.selectbox("Confirmar recepción anticipada si el camión ya llegó:", ordenes, format_func=lambda x: f"Orden #{x['id_compra']} - {x['Proveedor']} (${float(x['Total']):.2f})")
            if st.button("✅ Marcar como Recibida e Ingresar al Stock"):
                cx = obtener_conexion()
                if cx:
                    try:
                        cur = cx.cursor(dictionary=True)
                        procesar_ingreso_inventario(cur, sel_recibir["id_compra"], id_tienda)
                        cx.commit()
                        st.success(f"✅ Orden #{sel_recibir['id_compra']} recibida e ingresada al inventario.")
                        st.rerun()
                    except Exception as e:
                        cx.rollback()
                        st.error(f"Error: {e}")
                    finally:
                        cur.close(); cx.close()
