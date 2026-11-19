import streamlit as st
import math
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from config.conexion import obtener_conexion

ZONA_SV = ZoneInfo("America/El_Salvador")

def ahora_sv():
    return datetime.now(ZONA_SV).replace(tzinfo=None)

def sincronizar_compras_en_transito():
    cx = obtener_conexion()
    if not cx: return
    cur = None
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT id_compra, id_tienda FROM Compra WHERE Estado = 'En tránsito' AND Fecha_entrega_estimada <= %s", (ahora_sv(),))
        pendientes = cur.fetchall()
        for comp in pendientes:
            procesar_ingreso_inventario(cur, comp["id_compra"], comp["id_tienda"])
        if pendientes: cx.commit()
    except Exception:
        cx.rollback()
    finally:
        if cur: cur.close()
        if cx: cx.close()

def procesar_ingreso_inventario(cur, id_compra, id_tienda):
    cur.execute("""
        SELECT dc.id_detalle_compra, dc.Cantidad, dc.Precio_venta_sugerido, c.Fecha, c.Fecha_entrega_estimada,
               (SELECT pxp.id_producto FROM ProductoxProveedor pxp 
                INNER JOIN Compra c2 ON c2.id_proveedor = pxp.id_proveedor 
                WHERE c2.id_compra = dc.id_compra AND pxp.Ultimo_precio = dc.Precio_compra LIMIT 1) AS id_prod_rel
        FROM Detalle_compra dc
        INNER JOIN Compra c ON dc.id_compra = c.id_compra
        WHERE dc.id_compra = %s
    """, (id_compra,))
    for d in cur.fetchall():
        id_prod = d["id_prod_rel"]
        if not id_prod: continue
        dias_lt = max(1, (d["Fecha_entrega_estimada"] - d["Fecha"]).days) if (d["Fecha_entrega_estimada"] and d["Fecha"]) else 1
        rop_calc = max(1, math.ceil(0.5 * dias_lt))
        cur.execute("SELECT id_inventario FROM Inventario WHERE id_tienda = %s AND id_producto = %s LIMIT 1", (id_tienda, id_prod))
        inv = cur.fetchone()
        if inv:
            cur.execute("UPDATE Inventario SET Existencia = Existencia + %s, Precio_venta = %s, id_detalle_compra = %s WHERE id_inventario = %s", (d["Cantidad"], d["Precio_venta_sugerido"], d["id_detalle_compra"], inv["id_inventario"]))
        else:
            cur.execute("INSERT INTO Inventario (id_tienda, id_producto, id_detalle_compra, Existencia, Stock_minimo, Precio_venta) VALUES (%s, %s, %s, %s, %s, %s)", (id_tienda, id_prod, d["id_detalle_compra"], d["Cantidad"], rop_calc, d["Precio_venta_sugerido"]))
    cur.execute("UPDATE Compra SET Estado = 'Recibida' WHERE id_compra = %s", (id_compra,))

def confirmar_despacho_cd(id_venta, id_tienda_destino):
    cx = obtener_conexion()
    if not cx: return False, "Sin conexión."
    cur = None
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT id_producto, Cantidad, Precio_unitario FROM Detalle_venta WHERE id_venta = %s", (id_venta,))
        detalles = cur.fetchall()
        for d in detalles:
            if not d["id_producto"]: continue
            precio_publico = round(float(d["Precio_unitario"]) * 1.20, 2)
            cur.execute("SELECT id_inventario FROM Inventario WHERE id_tienda = %s AND id_producto = %s LIMIT 1", (id_tienda_destino, d["id_producto"]))
            inv = cur.fetchone()
            if inv:
                cur.execute("UPDATE Inventario SET Existencia = Existencia + %s, Precio_venta = %s WHERE id_inventario = %s", (d["Cantidad"], precio_publico, inv["id_inventario"]))
            else:
                cur.execute("INSERT INTO Inventario (id_tienda, id_producto, Existencia, Stock_minimo, Precio_venta) VALUES (%s, %s, %s, 2, %s)", (id_tienda_destino, d["id_producto"], d["Cantidad"], precio_publico))
        cur.execute("UPDATE Venta SET Estado = 'Entregada' WHERE id_venta = %s", (id_venta,))
        cx.commit()
        return True, f"✅ Despacho #{id_venta} del Centro de Distribución recibido e ingresado al inventario."
    except Exception as e:
        cx.rollback()
        return False, f"❌ Error al recibir despacho: {e}"
    finally:
        if cur: cur.close()
        if cx: cx.close()

def info_tienda(id_tienda):
    cx = obtener_conexion()
    if not cx: return None
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT id_tienda, Nombre, Tipo FROM Tienda WHERE id_tienda = %s", (id_tienda,))
        return cur.fetchone()
    finally:
        cur.close(); cx.close()

def obtener_id_cd():
    cx = obtener_conexion()
    if not cx: return 1
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT id_tienda FROM Tienda WHERE LOWER(Nombre) LIKE '%distribuci%' OR LOWER(Tipo) LIKE '%distribuci%' LIMIT 1")
        r = cur.fetchone()
        return r["id_tienda"] if r else 1
    finally:
        cur.close(); cx.close()

def obtener_proveedores(es_cd):
    cx = obtener_conexion()
    if not cx: return []
    try:
        cur = cx.cursor(dictionary=True)
        if es_cd:
            cur.execute("SELECT id_proveedor, Nombre, Tipo FROM Proveedor WHERE LOWER(Nombre) NOT LIKE '%distribuci%' ORDER BY Nombre")
        else:
            cur.execute("SELECT id_proveedor, Nombre, Tipo FROM Proveedor ORDER BY Nombre")
        return cur.fetchall()
    finally:
        cur.close(); cx.close()

def obtener_productos_disponibles_cd():
    """Trae únicamente productos con stock > 0 en el Centro de Distribución junto con su precio."""
    id_cd = obtener_id_cd()
    cx = obtener_conexion()
    if not cx: return []
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("""
            SELECT i.id_inventario, p.id_producto, p.Nombre, p.Unidad_medida, p.Codigo_barras,
                   i.Existencia, i.Precio_venta
            FROM Inventario i
            INNER JOIN Producto p ON i.id_producto = p.id_producto
            WHERE i.id_tienda = %s AND i.Existencia > 0
            ORDER BY p.Nombre
        """, (id_cd,))
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

def registrar_orden_compra(id_tienda, nombre_tienda, id_usuario, prov_sel, carrito, total_compra):
    cx = obtener_conexion()
    if not cx: return False, "No hay conexión con la base de datos."
    cur = None
    try:
        cur = cx.cursor(dictionary=True)
        fecha_reg = ahora_sv()
        es_compra_al_cd = "distribuci" in (prov_sel["Nombre"] or "").lower()

        # CASO A: La Tienda está comprando directamente al Centro de Distribución (Comunicación bilateral)
        if es_compra_al_cd:
            id_cd = obtener_id_cd()
            # Buscar el id_cliente que corresponde a la tienda que está comprando
            cur.execute("SELECT id_cliente FROM Cliente WHERE TRIM(LOWER(Nombre)) = TRIM(LOWER(%s)) LIMIT 1", (nombre_tienda,))
            cli_t = cur.fetchone()
            id_cliente_tienda = cli_t["id_cliente"] if cli_t else 1

            # 1. Crear el despacho en la tabla Venta del Centro de Distribución ('En tránsito')
            cur.execute("""
                INSERT INTO Venta (id_tienda, id_usuario, id_cliente, Fecha, Total, Estado)
                VALUES (%s, %s, %s, %s, %s, 'En tránsito')
            """, (id_cd, id_usuario, id_cliente_tienda, fecha_reg, total_compra))
            id_despacho = cur.lastrowid

            for item in carrito:
                cur.execute("""
                    INSERT INTO Detalle_venta (id_venta, id_producto, Cantidad, Precio_unitario)
                    VALUES (%s, %s, %s, %s)
                """, (id_despacho, item["id_producto"], item["cantidad"], item["precio_compra"]))
                id_det_v = cur.lastrowid

                # Descontar del inventario del Centro de Distribución
                cur.execute("""
                    UPDATE Inventario
                    SET Existencia = Existencia - %s, id_detalle_venta = %s
                    WHERE id_tienda = %s AND id_producto = %s AND Existencia >= %s
                """, (item["cantidad"], id_det_v, id_cd, item["id_producto"], item["cantidad"]))
                if cur.rowcount == 0:
                    raise Exception(f"El Centro de Distribución no tiene suficiente stock de '{item['nombre']}'.")

                # Actualizar el Punto de Reorden (Stock_minimo) en la tienda destino si ya tiene el producto
                cur.execute("SELECT id_inventario FROM Inventario WHERE id_tienda = %s AND id_producto = %s LIMIT 1", (id_tienda, item["id_producto"]))
                inv_t = cur.fetchone()
                if inv_t:
                    cur.execute("UPDATE Inventario SET Stock_minimo = %s WHERE id_inventario = %s", (item["stock_minimo"], inv_t["id_inventario"]))

            cx.commit()
            return True, f"🚚 Solicitud #{id_despacho} enviada al **Centro de Distribución** por **${total_compra:.2f}**. Aparecerá en tu pestaña **Pedidos en Tránsito** para confirmar cuando llegue."

        # CASO B: Compra a un Proveedor Externo
        max_lt = max(item["lead_time"] for item in carrito)
        fecha_est = fecha_reg + timedelta(days=max_lt)
        cur.execute("INSERT INTO Compra (id_tienda, id_proveedor, id_usuario, Fecha, Fecha_entrega_estimada, Total, Estado) VALUES (%s, %s, %s, %s, %s, %s, 'En tránsito')", (id_tienda, prov_sel["id_proveedor"], id_usuario, fecha_reg, fecha_est, total_compra))
        id_comp = cur.lastrowid
        for item in carrito:
            cur.execute("INSERT INTO Detalle_compra (id_compra, Cantidad, Precio_compra, Precio_venta_sugerido, Fecha_vencimiento) VALUES (%s, %s, %s, %s, %s)", (id_comp, item["cantidad"], item["precio_compra"], item["precio_venta"], item["fecha_venc"]))
            cur.execute("INSERT INTO ProductoxProveedor (id_producto, id_proveedor, Ultimo_precio, Fecha_ultima_compra) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE Ultimo_precio = VALUES(Ultimo_precio), Fecha_ultima_compra = VALUES(Fecha_ultima_compra)", (item["id_producto"], prov_sel["id_proveedor"], item["precio_compra"], fecha_reg.date()))
            cur.execute("SELECT id_inventario FROM Inventario WHERE id_tienda = %s AND id_producto = %s LIMIT 1", (id_tienda, item["id_producto"]))
            inv = cur.fetchone()
            if inv:
                cur.execute("UPDATE Inventario SET Stock_minimo = %s WHERE id_inventario = %s", (item["stock_minimo"], inv["id_inventario"]))
        cx.commit()
        return True, f"🚚 Orden #{id_comp} registrada **En tránsito** por **${total_compra:.2f}**. Ingresará el **{fecha_est.strftime('%d/%m/%Y %H:%M')}**."
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
    t_info = info_tienda(id_tienda)
    nombre_tienda = (t_info["Nombre"] or "").strip() if t_info else ""
    es_cd = t_info and ("distribuci" in nombre_tienda.lower() or "distribuci" in (t_info["Tipo"] or "").lower())

    tab_nueva, tab_transito = st.tabs(["➕ Nueva Orden de Compra", "🚚 Pedidos en Tránsito"])

    with tab_nueva:
        if "reset_prov_comp" not in st.session_state: st.session_state["reset_prov_comp"] = 0
        if "reset_prod_comp" not in st.session_state: st.session_state["reset_prod_comp"] = 0

        if st.session_state.get("limpiar_item_compra", False):
            st.session_state["reset_prod_comp"] += 1
            for k, v in [("comp_cant_0", 0), ("comp_costo_0", 0.00), ("comp_lead_0", 1), ("comp_dem_0", 15), ("comp_venc_chk_0", False)]: st.session_state[k] = v
            st.session_state["limpiar_item_compra"] = False

        if st.session_state.get("limpiar_todo_compra", False):
            st.session_state["reset_prov_comp"] += 1
            st.session_state["reset_prod_comp"] += 1
            for k, v in [("comp_cant_0", 0), ("comp_costo_0", 0.00), ("comp_lead_0", 1), ("comp_dem_0", 15), ("comp_venc_chk_0", False)]: st.session_state[k] = v
            st.session_state["limpiar_todo_compra"] = False

        if "carrito_compras" not in st.session_state: st.session_state["carrito_compras"] = []
        for k, v in [("comp_cant_0", 0), ("comp_costo_0", 0.00), ("comp_lead_0", 1), ("comp_dem_0", 15), ("comp_venc_chk_0", False)]:
            if k not in st.session_state: st.session_state[k] = v
        if st.session_state.get("msg_exito_compra"): st.success(st.session_state.pop("msg_exito_compra"))

        proveedores = obtener_proveedores(es_cd)
        if not proveedores:
            st.warning("⚠️ No hay proveedores registrados en el catálogo.")
            return

        prov_sel = st.selectbox("Proveedor", [None] + proveedores, index=0, format_func=lambda x: "-- Selecciona un proveedor --" if x is None else f"{x['Nombre']} ({x['Tipo']})", key=f"sel_prov_comp_{st.session_state['reset_prov_comp']}", disabled=(len(st.session_state["carrito_compras"]) > 0))
        es_compra_cd = prov_sel is not None and ("distribuci" in (prov_sel["Nombre"] or "").lower())

        st.divider()
        st.subheader("Detalle de Productos Solicitados")

        if es_compra_cd:
            productos_cd = obtener_productos_disponibles_cd()
            if not productos_cd:
                st.warning("📦 El Centro de Distribución no tiene existencias disponibles en este momento.")
                return
            c1, c2 = st.columns(2)
            with c1:
                prod_sel = st.selectbox(
                    "Producto disponible en Centro de Distribución",
                    [None] + productos_cd,
                    index=0,
                    format_func=lambda x: "-- Selecciona un producto --" if x is None else f"{x['Nombre']} ({x['Unidad_medida']}) - Disp: {x['Existencia']} | ${float(x['Precio_venta']):.2f}",
                    key=f"sel_prod_comp_{st.session_state['reset_prod_comp']}"
                )
                max_disp_cd = int(prod_sel["Existencia"]) if prod_sel else 0
                cantidad = st.number_input("Cantidad solicitada", min_value=0, max_value=max(0, max_disp_cd), step=1, key="comp_cant_0")
                lead_time = st.number_input("Lead Time de traslado (días)", min_value=1, max_value=30, step=1, key="comp_lead_0")
            with c2:
                precio_compra = float(prod_sel["Precio_venta"]) if prod_sel else 0.00
                st.number_input("Precio de Compra Unitario ($ - Fijo CD)", value=precio_compra, format="%.2f", disabled=True)
                precio_sugerido = round(precio_compra * 1.20, 2)
                st.number_input("Precio de Venta Sugerido en Tienda (+20%)", value=precio_sugerido, format="%.2f", disabled=True)
                demanda_mensual = st.number_input("Demanda Estimada Mensual (unidades/mes)", min_value=1, step=1, key="comp_dem_0")
        else:
            productos_cat = obtener_productos_catalogo()
            if not productos_cat:
                st.warning("⚠️ Primero debes registrar productos en el catálogo.")
                return
            c1, c2 = st.columns(2)
            with c1:
                prod_sel = st.selectbox(
                    "Producto del Catálogo",
                    [None] + productos_cat,
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
        stock_min_calc = max(1, math.ceil(demanda_diaria * lead_time))
        st.caption(f"📐 **Punto de Reorden calculado:** `{stock_min_calc}` unidad(es) — *(Demanda diaria: {demanda_diaria:.2f} × Lead Time: {lead_time} días)*")

        tiene_venc = st.checkbox("📅 Este lote tiene fecha de vencimiento", key="comp_venc_chk_0")
        fecha_venc = st.date_input("Fecha de Vencimiento", min_value=date.today()) if tiene_venc else None

        if st.button("➕ Agregar Producto a la Orden"):
            if prov_sel is None: st.warning("⚠️ Primero debes seleccionar un proveedor.")
            elif prod_sel is None: st.warning("⚠️ Por favor, selecciona un producto.")
            elif cantidad <= 0: st.warning("⚠️ La cantidad solicitada debe ser mayor a 0.")
            elif precio_compra <= 0: st.warning("⚠️ El precio de compra unitario debe ser mayor a $0.00.")
            else:
                st.session_state["carrito_compras"].append({"id_producto": prod_sel["id_producto"], "nombre": prod_sel["Nombre"], "unidad": prod_sel["Unidad_medida"], "cantidad": cantidad, "precio_compra": precio_compra, "precio_venta": precio_sugerido, "lead_time": lead_time, "stock_minimo": stock_min_calc, "fecha_venc": fecha_venc, "subtotal": cantidad * precio_compra})
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
                    if prov_sel is None: st.error("❌ Debes seleccionar un proveedor.")
                    else:
                        exito, msg = registrar_orden_compra(id_tienda, nombre_tienda, id_usuario, prov_sel, st.session_state["carrito_compras"], total_compra)
                        if exito:
                            st.session_state["carrito_compras"] = []
                            st.session_state["msg_exito_compra"] = msg
                            st.session_state["limpiar_todo_compra"] = True
                            st.rerun()
                        else: st.error(msg)

    with tab_transito:
        st.caption(f"Hora actual del sistema (El Salvador): **{ahora_sv().strftime('%d/%m/%Y %H:%M')}**")
        
        if not es_cd:
            st.subheader("🏢 Envíos en Camino desde Centro de Distribución")
            cx = obtener_conexion()
            envios_cd = []
            if cx:
                try:
                    cur = cx.cursor(dictionary=True)
                    cur.execute("""
                        SELECT v.id_venta, v.Fecha, v.Total, v.Estado
                        FROM Venta v
                        INNER JOIN Cliente c ON v.id_cliente = c.id_cliente
                        WHERE v.Estado = 'En tránsito' AND TRIM(LOWER(c.Nombre)) = TRIM(LOWER(%s))
                        ORDER BY v.Fecha ASC
                    """, (nombre_tienda,))
                    envios_cd = cur.fetchall()
                finally:
                    cur.close(); cx.close()

            if not envios_cd:
                st.info("✅ No tienes envíos pendientes desde el Centro de Distribución.")
            else:
                tabla_cd = [{"ID Despacho": e["id_venta"], "Fecha Envío": e["Fecha"], "Valor": f"${float(e['Total']):.2f}", "Estado": e["Estado"]} for e in envios_cd]
                st.dataframe(tabla_cd, use_container_width=True, hide_index=True)
                sel_cd = st.selectbox("Selecciona el despacho del CD para confirmar ingreso:", envios_cd, format_func=lambda x: f"Despacho CD #{x['id_venta']} - ${float(x['Total']):.2f}", key="sel_rec_cd")
                if st.button("✅ Confirmar Recepción de Centro de Distribución", key="btn_rec_cd"):
                    ok, msg_cd = confirmar_despacho_cd(sel_cd["id_venta"], id_tienda)
                    if ok:
                        st.success(msg_cd)
                        st.rerun()
                    else:
                        st.error(msg_cd)
            st.divider()

        st.subheader("🚚 Órdenes de Compra a Proveedores en Camino")
        cx = obtener_conexion()
        ordenes = []
        if cx:
            try:
                cur = cx.cursor(dictionary=True)
                cur.execute("SELECT c.id_compra, p.Nombre AS Proveedor, c.Fecha AS Fecha_Pedido, c.Fecha_entrega_estimada AS Entrega_Estimada, c.Total, c.Estado FROM Compra c INNER JOIN Proveedor p ON c.id_proveedor = p.id_proveedor WHERE c.id_tienda = %s AND c.Estado = 'En tránsito' ORDER BY c.Fecha_entrega_estimada ASC", (id_tienda,))
                ordenes = cur.fetchall()
            finally:
                cur.close(); cx.close()

        if not ordenes:
            st.info("✅ No hay pedidos pendientes en tránsito de proveedores externos.")
        else:
            ordenes_tabla = [{"ID Compra": o["id_compra"], "Proveedor": o["Proveedor"], "Fecha Pedido": o["Fecha_Pedido"], "Entrega Estimada": o["Entrega_Estimada"], "Total": f"${float(o['Total']):.2f}", "Estado": o["Estado"]} for o in ordenes]
            st.dataframe(ordenes_tabla, use_container_width=True, hide_index=True)
            sel_recibir = st.selectbox("Confirmar recepción anticipada de proveedor:", ordenes, format_func=lambda x: f"Orden #{x['id_compra']} - {x['Proveedor']} (${float(x['Total']):.2f})", key="sel_rec_prov")
            if st.button("✅ Marcar Orden como Recibida e Ingresar al Stock", key="btn_rec_prov"):
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
