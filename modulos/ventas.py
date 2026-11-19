import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from config.conexion import obtener_conexion
from modulos.compras import sincronizar_compras_en_transito

ZONA_SV = ZoneInfo("America/El_Salvador")

def ahora_sv():
    return datetime.now(ZONA_SV).replace(tzinfo=None)

def info_tienda_actual(id_tienda):
    cx = obtener_conexion()
    if not cx: return None
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT id_tienda, Nombre, Tipo FROM Tienda WHERE id_tienda = %s", (id_tienda,))
        return cur.fetchone()
    finally:
        cur.close(); cx.close()

def obtener_clientes_segun_rol(solo_tiendas=False):
    cx = obtener_conexion()
    if not cx: return []
    try:
        cur = cx.cursor(dictionary=True)
        if solo_tiendas:
            cur.execute("SELECT id_cliente, Nombre, Tipo FROM Cliente WHERE Tipo = 'Tienda' ORDER BY Nombre")
        else:
            cur.execute("SELECT id_cliente, Nombre, Tipo FROM Cliente WHERE id_cliente != 1 AND Tipo != 'Tienda' ORDER BY Nombre")
        return cur.fetchall()
    finally:
        cur.close(); cx.close()

def obtener_productos_disponibles(id_tienda):
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
        """, (id_tienda,))
        return cur.fetchall()
    finally:
        cur.close(); cx.close()

def registrar_venta_completa(id_tienda, id_usuario, id_cliente, carrito, total_venta, es_cd):
    cx = obtener_conexion()
    if not cx: return False, "No hay conexión con la base de datos."
    cur = None
    try:
        cur = cx.cursor()
        fecha_actual = ahora_sv()
        estado_inicial = "En tránsito" if es_cd else "Entregada"
        
        cur.execute("""
            INSERT INTO Venta (id_tienda, id_usuario, id_cliente, Fecha, Total, Estado)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id_tienda, id_usuario, id_cliente, fecha_actual, total_venta, estado_inicial))
        id_venta_gen = cur.lastrowid
        
        for item in carrito:
            cur.execute("""
                INSERT INTO Detalle_venta (id_venta, id_producto, Cantidad, Precio_unitario)
                VALUES (%s, %s, %s, %s)
            """, (id_venta_gen, item["id_producto"], item["cantidad"], item["precio"]))
            id_det_gen = cur.lastrowid
            
            cur.execute("""
                UPDATE Inventario 
                SET Existencia = Existencia - %s, id_detalle_venta = %s
                WHERE id_inventario = %s AND Existencia >= %s
            """, (item["cantidad"], id_det_gen, item["id_inventario"], item["cantidad"]))
            
            if cur.rowcount == 0:
                raise Exception(f"Stock insuficiente para '{item['nombre']}'.")
                
        cx.commit()
        if es_cd:
            return True, f"🚚 Despacho #{id_venta_gen} enviado **En tránsito** por **${total_venta:.2f}**. La tienda destino deberá confirmar su recepción."
        return True, f"✅ Venta #{id_venta_gen} cobrada y entregada por **${total_venta:.2f}**."
    except Exception as e:
        cx.rollback()
        return False, f"❌ Error al procesar la operación: {e}"
    finally:
        if cur: cur.close()
        if cx: cx.close()

def confirmar_recepcion_tienda(id_venta, id_tienda_destino):
    """Ingresa al inventario de la tienda destino los productos enviados por el Centro de Distribución."""
    cx = obtener_conexion()
    if not cx: return False, "Sin conexión."
    cur = None
    try:
        cur = cx.cursor(dictionary=True)
        cur.execute("SELECT id_producto, Cantidad, Precio_unitario FROM Detalle_venta WHERE id_venta = %s", (id_venta,))
        detalles = cur.fetchall()
        
        for d in detalles:
            if not d["id_producto"]: continue
            # La tienda aplica margen del 20% sobre el precio al que se lo despachó el CD
            precio_publico = round(float(d["Precio_unitario"]) * 1.20, 2)
            cur.execute("SELECT id_inventario FROM Inventario WHERE id_tienda = %s AND id_producto = %s LIMIT 1", (id_tienda_destino, d["id_producto"]))
            inv = cur.fetchone()
            if inv:
                cur.execute("UPDATE Inventario SET Existencia = Existencia + %s, Precio_venta = %s WHERE id_inventario = %s", (d["Cantidad"], precio_publico, inv["id_inventario"]))
            else:
                cur.execute("INSERT INTO Inventario (id_tienda, id_producto, Existencia, Stock_minimo, Precio_venta) VALUES (%s, %s, %s, 2, %s)", (id_tienda_destino, d["id_producto"], d["Cantidad"], precio_publico))
                
        cur.execute("UPDATE Venta SET Estado = 'Entregada' WHERE id_venta = %s", (id_venta,))
        cx.commit()
        return True, f"✅ Despacho #{id_venta} recibido e ingresado al inventario de tu sucursal."
    except Exception as e:
        cx.rollback()
        return False, f"❌ Error al recibir despacho: {e}"
    finally:
        if cur: cur.close()
        if cx: cx.close()

def mostrar_ventas():
    sincronizar_compras_en_transito()
    st.header("💸 Gestión de Ventas")
    
    id_tienda = st.session_state.get("id_tienda")
    id_usuario = st.session_state.get("id_usuario")
    tienda_info = info_tienda_actual(id_tienda)
    
    es_cd = False
    nombre_tienda_actual = ""
    if tienda_info:
        nombre_tienda_actual = tienda_info["Nombre"] or ""
        es_cd = ("distribuci" in nombre_tienda_actual.lower() or "distribuci" in (tienda_info["Tipo"] or "").lower())

    # Pestañas dinámicas según si es Centro de Distribución o Tienda Minorista
    if es_cd:
        tabs = st.tabs(["🚚 Nuevo Despacho a Tienda", "📋 Despachos del Día"])
    else:
        tabs = st.tabs(["🛍️ Nueva Venta", "📋 Ventas del Día", "📥 Recibir Despachos del CD"])

    # =========================================================================
    # PESTAÑA 1: REGISTRAR VENTA O DESPACHO
    # =========================================================================
    with tabs[0]:
        if "reset_cli_venta" not in st.session_state: st.session_state["reset_cli_venta"] = 0
        if "reset_prod_venta" not in st.session_state: st.session_state["reset_prod_venta"] = 0

        if st.session_state.get("limpiar_item_venta", False):
            st.session_state["reset_prod_venta"] += 1
            st.session_state["venta_cant_0"] = 0
            st.session_state["limpiar_item_venta"] = False

        if st.session_state.get("limpiar_todo_venta", False):
            st.session_state["reset_cli_venta"] += 1
            st.session_state["reset_prod_venta"] += 1
            st.session_state["venta_cant_0"] = 0
            st.session_state["venta_req_factura"] = False
            st.session_state["limpiar_todo_venta"] = False

        if "carrito_ventas" not in st.session_state: st.session_state["carrito_ventas"] = []
        if "venta_cant_0" not in st.session_state: st.session_state["venta_cant_0"] = 0
        if "venta_req_factura" not in st.session_state: st.session_state["venta_req_factura"] = False

        if st.session_state.get("msg_exito_venta"):
            st.success(st.session_state.pop("msg_exito_venta"))

        if es_cd:
            st.subheader("Destino del Despacho")
            tiendas_dest = obtener_clientes_segun_rol(solo_tiendas=True)
            if not tiendas_dest:
                st.warning("⚠️ No hay tiendas registradas como clientes en el catálogo.")
                return
            tienda_sel = st.selectbox(
                "Selecciona la Tienda",
                [None] + tiendas_dest,
                index=0,
                format_func=lambda x: "-- Selecciona una tienda --" if x is None else x["Nombre"],
                key=f"sel_t_venta_{st.session_state['reset_cli_venta']}",
                disabled=(len(st.session_state["carrito_ventas"]) > 0)
            )
            id_cliente_final = tienda_sel["id_cliente"] if tienda_sel else None
        else:
            st.subheader("Datos del Comprador")
            requiere_factura = st.checkbox("🧾 El cliente requiere factura con nombre / datos", key="venta_req_factura", disabled=(len(st.session_state["carrito_ventas"]) > 0))
            if requiere_factura:
                clientes = obtener_clientes_segun_rol(solo_tiendas=False)
                if not clientes:
                    st.warning("⚠️ No hay clientes registrados. Se facturará como Consumidor Final.")
                    id_cliente_final = 1
                else:
                    cli_sel = st.selectbox(
                        "Selecciona el Cliente",
                        [None] + clientes,
                        index=0,
                        format_func=lambda x: "-- Selecciona un cliente --" if x is None else x["Nombre"],
                        key=f"sel_c_venta_{st.session_state['reset_cli_venta']}",
                        disabled=(len(st.session_state["carrito_ventas"]) > 0)
                    )
                    id_cliente_final = cli_sel["id_cliente"] if cli_sel else None
            else:
                st.info("⚡ Venta rápida: Se registrará automáticamente como **Consumidor Final (Externo)**.")
                id_cliente_final = 1

        st.divider()
        st.subheader("Agregar Productos al Carrito")
        productos_disp = obtener_productos_disponibles(id_tienda)
        
        if not productos_disp:
            st.warning("📦 No hay productos con existencias disponibles en el inventario de esta sucursal.")
            return

        col_p1, col_p2, col_p3 = st.columns([3, 1.5, 1.5])
        with col_p1:
            prod_sel = st.selectbox(
                "Producto disponible",
                [None] + productos_disp,
                index=0,
                format_func=lambda x: "-- Selecciona un producto --" if x is None else f"{x['Nombre']} ({x['Unidad_medida']}) - Stock: {x['Existencia']} | ${float(x['Precio_venta']):.2f}",
                key=f"sel_p_venta_{st.session_state['reset_prod_venta']}"
            )
        with col_p2:
            max_cant = int(prod_sel["Existencia"]) if prod_sel else 0
            cantidad = st.number_input("Cantidad", min_value=0, max_value=max(0, max_cant), step=1, key="venta_cant_0")
        with col_p3:
            st.write("")
            st.write("")
            if st.button("➕ Agregar"):
                if id_cliente_final is None:
                    st.warning("⚠️ Primero debes seleccionar el destino o cliente.")
                elif prod_sel is None:
                    st.warning("⚠️ Selecciona un producto disponible.")
                elif cantidad <= 0:
                    st.warning("⚠️ La cantidad debe ser mayor a 0.")
                else:
                    encontrado = False
                    for item in st.session_state["carrito_ventas"]:
                        if item["id_inventario"] == prod_sel["id_inventario"]:
                            if item["cantidad"] + cantidad <= max_cant:
                                item["cantidad"] += cantidad
                                item["subtotal"] = item["cantidad"] * item["precio"]
                            else:
                                st.error(f"⚠️ No puedes superar el stock disponible ({max_cant}).")
                            encontrado = True
                            break
                    if not encontrado:
                        precio_u = float(prod_sel["Precio_venta"])
                        st.session_state["carrito_ventas"].append({
                            "id_inventario": prod_sel["id_inventario"],
                            "id_producto": prod_sel["id_producto"],
                            "nombre": prod_sel["Nombre"],
                            "unidad": prod_sel["Unidad_medida"],
                            "cantidad": cantidad,
                            "precio": precio_u,
                            "subtotal": cantidad * precio_u
                        })
                    st.session_state["limpiar_item_venta"] = True
                    st.rerun()

        if st.session_state["carrito_ventas"]:
            st.divider()
            st.subheader("Detalle de la Operación")
            total_general = 0.0
            for idx, item in enumerate(st.session_state["carrito_ventas"]):
                c1, c2, c3, c4, c5 = st.columns([3, 1, 1.5, 1.5, 0.8])
                c1.write(f"**{item['nombre']}** ({item['unidad']})")
                c2.write(f"Cant: {item['cantidad']}")
                c3.write(f"${item['precio']:.2f} c/u")
                c4.write(f"**${item['subtotal']:.2f}**")
                if c5.button("🗑️", key=f"del_v_{idx}"):
                    st.session_state["carrito_ventas"].pop(idx)
                    st.rerun()
                total_general += item["subtotal"]

            st.markdown(f"### Total a Cobrar: `${total_general:.2f}`")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("🧹 Vaciar Carrito"):
                    st.session_state["carrito_ventas"] = []
                    st.session_state["limpiar_todo_venta"] = True
                    st.rerun()
            with b2:
                texto_btn = "🚚 Confirmar Despacho (En tránsito)" if es_cd else "💳 Confirmar y Cobrar Venta"
                if st.button(texto_btn):
                    if id_cliente_final is None:
                        st.error("❌ Debes seleccionar una tienda o cliente.")
                    else:
                        exito, msg = registrar_venta_completa(id_tienda, id_usuario, id_cliente_final, st.session_state["carrito_ventas"], total_general, es_cd)
                        if exito:
                            st.session_state["carrito_ventas"] = []
                            st.session_state["msg_exito_venta"] = msg
                            st.session_state["limpiar_todo_venta"] = True
                            st.rerun()
                        else:
                            st.error(msg)

    # =========================================================================
    # PESTAÑA 2: HISTORIAL RÁPIDO DEL DÍA (EN ESTA SUCURSAL)
    # =========================================================================
    with tabs[1]:
        hoy_str = ahora_sv().strftime("%Y-%m-%d")
        st.subheader(f"📋 Movimientos de Hoy ({ahora_sv().strftime('%d/%m/%Y')})")
        cx = obtener_conexion()
        ventas_hoy = []
        if cx:
            try:
                cur = cx.cursor(dictionary=True)
                cur.execute("""
                    SELECT v.id_venta, c.Nombre AS Cliente, u.Nombre AS Cajero, v.Fecha, v.Total, v.Estado
                    FROM Venta v
                    INNER JOIN Cliente c ON v.id_cliente = c.id_cliente
                    INNER JOIN Usuario u ON v.id_usuario = u.id_usuario
                    WHERE v.id_tienda = %s AND DATE(v.Fecha) = %s
                    ORDER BY v.id_venta DESC
                """, (id_tienda, hoy_str))
                ventas_hoy = cur.fetchall()
            finally:
                cur.close(); cx.close()

        if not ventas_hoy:
            st.info("📭 Aún no se han registrado ventas hoy en esta sucursal.")
        else:
            tabla_hoy = [
                {
                    "ID": v["id_venta"],
                    "Cliente / Destino": v["Cliente"],
                    "Atendido por": v["Cajero"],
                    "Hora": v["Fecha"].strftime("%H:%M:%S") if v["Fecha"] else "",
                    "Total": f"${float(v['Total']):.2f}",
                    "Estado": v["Estado"]
                }
                for v in ventas_hoy
            ]
            st.dataframe(tabla_hoy, use_container_width=True, hide_index=True)

    # =========================================================================
    # PESTAÑA 3 (SOLO TIENDAS MINORISTAS): RECIBIR DESPACHOS DEL CD
    # =========================================================================
    if not es_cd:
        with tabs[2]:
            st.subheader("📥 Despachos en Camino desde Centro de Distribución")
            cx = obtener_conexion()
            despachos = []
            if cx:
                try:
                    cur = cx.cursor(dictionary=True)
                    cur.execute("""
                        SELECT v.id_venta, v.Fecha, v.Total, v.Estado
                        FROM Venta v
                        INNER JOIN Cliente c ON v.id_cliente = c.id_cliente
                        WHERE v.Estado = 'En tránsito' AND LOWER(c.Nombre) = LOWER(%s)
                        ORDER BY v.Fecha ASC
                    """, (nombre_tienda_actual,))
                    despachos = cur.fetchall()
                finally:
                    cur.close(); cx.close()

            if not despachos:
                st.info("✅ No tienes despachos pendientes en tránsito desde el Centro de Distribución.")
            else:
                tabla_desp = [{"ID Despacho": d["id_venta"], "Fecha Envío": d["Fecha"], "Valor": f"${float(d['Total']):.2f}", "Estado": d["Estado"]} for d in despachos]
                st.dataframe(tabla_desp, use_container_width=True, hide_index=True)
                sel_desp = st.selectbox("Selecciona el despacho recibido:", despachos, format_func=lambda x: f"Despacho #{x['id_venta']} - ${float(x['Total']):.2f}")
                if st.button("✅ Confirmar Recepción e Ingresar a mi Inventario"):
                    ok, msg_rec = confirmar_recepcion_tienda(sel_desp["id_venta"], id_tienda)
                    if ok:
                        st.success(msg_rec)
                        st.rerun()
                    else:
                        st.error(msg_rec)
