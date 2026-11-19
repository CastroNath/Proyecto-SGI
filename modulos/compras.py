import math
from datetime import date, timedelta

import streamlit as st

from config.conexion import consultar, consultar_uno
from modulos.negocio import (MARGEN_VENTA, ReglaNegocioError, ahora_sv, anular_compra, confirmar_despacho_cd,
                             recibir_compra, registrar_compra, solicitar_al_cd)


def obtener_proveedores(es_cd):
    """El CD compra solo a externos; las tiendas también pueden pedir al CD."""
    filtro = "WHERE id_tienda_cd IS NULL" if es_cd else ""
    return consultar(f"SELECT id_proveedor, Nombre, Tipo, id_tienda_cd FROM Proveedor {filtro} "
                     "ORDER BY id_tienda_cd IS NULL, Nombre")


def obtener_comparativa_producto(id_producto):
    return consultar("""SELECT p.Nombre AS Proveedor, p.Tipo, pxp.Ultimo_precio AS Precio, pxp.Fecha_ultima_compra
                        FROM ProductoxProveedor pxp JOIN Proveedor p ON p.id_proveedor = pxp.id_proveedor
                        WHERE pxp.id_producto = %s ORDER BY pxp.Ultimo_precio""", (id_producto,))


def datos_cd_producto(id_producto):
    return consultar_uno("""SELECT i.Existencia, i.Precio_venta, e.Costo_CD, e.Costo_externo, e.CD_autorizado
                            FROM v_evaluacion_cd e
                            LEFT JOIN Inventario i ON i.id_producto = e.id_producto
                                 AND i.id_tienda = (SELECT id_tienda FROM Tienda WHERE Tipo='CD' LIMIT 1)
                            WHERE e.id_producto = %s""", (id_producto,))


def _limpiar_carrito():
    st.session_state["carrito_compras"] = []
    st.session_state["reset_comp"] = st.session_state.get("reset_comp", 0) + 1


def mostrar_compras():
    st.header("📥 Gestión de Compras")
    id_tienda = st.session_state.get("id_tienda")
    id_usuario = st.session_state.get("id_usuario")
    es_cd = st.session_state.get("es_cd", False)
    st.caption(f"🏪 Registrando para: **{st.session_state.get('nombre_tienda')}**")

    tab_nueva, tab_transito, tab_hist = st.tabs(["➕ Nueva Orden de Compra", "🚚 Pedidos en Tránsito / Recepción",
                                                 "📋 Historial de Compras"])

    # =====================================================================
    # NUEVA ORDEN
    # =====================================================================
    with tab_nueva:
        st.session_state.setdefault("carrito_compras", [])
        st.session_state.setdefault("reset_comp", 0)
        r = st.session_state["reset_comp"]
        if st.session_state.get("msg_exito_compra"):
            st.success(st.session_state.pop("msg_exito_compra"))

        proveedores = obtener_proveedores(es_cd)
        productos = consultar("SELECT id_producto, Nombre, Unidad_medida, Codigo_barras FROM Producto ORDER BY Nombre")
        if not proveedores or not productos:
            st.warning("⚠️ Verifica que existan proveedores y productos en el catálogo.")
            return

        carrito = st.session_state["carrito_compras"]
        prov_sel = st.selectbox(
            "Proveedor de la orden", [None] + proveedores, index=0, key=f"prov_{r}",
            format_func=lambda x: "-- Selecciona un proveedor --" if x is None else
            (f"🏢 {x['Nombre']} (Centro de Distribución)" if x["id_tienda_cd"] else f"{x['Nombre']} ({x['Tipo']})"),
            disabled=len(carrito) > 0, help="Para cambiar de proveedor, limpia la orden.")
        al_cd = bool(prov_sel and prov_sel["id_tienda_cd"])

        prod_sel = st.selectbox(
            "Producto del Catálogo", [None] + productos, index=0, key=f"prod_{r}_{len(carrito)}",
            format_func=lambda x: "-- Selecciona un producto --" if x is None else
            f"{x['Nombre']} ({x['Unidad_medida']}) - {x['Codigo_barras']}")

        info_cd = datos_cd_producto(prod_sel["id_producto"]) if prod_sel else None
        if prod_sel:
            comp = obtener_comparativa_producto(prod_sel["id_producto"])
            if comp:
                with st.expander("📊 Comparativa de precios por proveedor", expanded=True):
                    st.dataframe(comp, width="stretch", hide_index=True,
                                 column_config={"Precio": st.column_config.NumberColumn(format="$%.2f")})
            if not es_cd and info_cd:
                if info_cd["CD_autorizado"]:
                    st.success(f"✅ El CD está **autorizado** para este producto: su costo (${info_cd['Costo_CD']}) es "
                               f"menor que el de proveedores externos (${info_cd['Costo_externo'] or '—'}). "
                               f"Existencia en CD: **{info_cd['Existencia'] or 0}**.")
                else:
                    st.info(f"💡 El CD **no** está autorizado para este producto (costo CD: "
                            f"{'$' + str(info_cd['Costo_CD']) if info_cd['Costo_CD'] else 'sin compras'}, "
                            f"externo: {'$' + str(info_cd['Costo_externo']) if info_cd['Costo_externo'] else '—'}). "
                            "Compra a un proveedor externo.")

        st.divider()
        with st.form(f"item_compra_{r}_{len(carrito)}"):
            c1, c2 = st.columns(2)
            with c1:
                cantidad = st.number_input("Cantidad solicitada", min_value=0, step=1)
                lead_time = st.number_input("Lead time (días de entrega)", min_value=1, max_value=90, step=1, value=1,
                                            disabled=al_cd)
                demanda_mensual = st.number_input("Demanda estimada mensual (unidades/mes)", min_value=1, step=1,
                                                  value=30)
            with c2:
                if al_cd:
                    precio_cd = float(info_cd["Precio_venta"]) if info_cd and info_cd["Precio_venta"] else 0.0
                    st.number_input("Precio unitario ($ - tarifa del CD)", value=precio_cd, format="%.2f", disabled=True)
                    precio_compra = precio_cd
                else:
                    precio_compra = st.number_input("Precio de compra unitario ($)", min_value=0.0, step=0.05,
                                                    format="%.2f")
                margen = st.number_input("Margen sobre costo (%)", min_value=0, max_value=200,
                                         value=int((MARGEN_VENTA - 1) * 100))
                tiene_venc = st.checkbox("📅 Este lote tiene fecha de vencimiento", disabled=al_cd)
                fecha_venc = st.date_input("Fecha de vencimiento", min_value=date.today() + timedelta(days=1),
                                           disabled=al_cd)
            agregar = st.form_submit_button("➕ Agregar producto a la orden")

        demanda_diaria = demanda_mensual / 30.0
        rop = max(1, math.ceil(demanda_diaria * (1 if al_cd else lead_time)))
        st.caption(f"📐 Punto de reorden (stock mínimo) = demanda diaria {demanda_diaria:.2f} × lead time "
                   f"{1 if al_cd else lead_time} días → **{rop}** unidades. Se guardará en el inventario de la tienda.")

        if agregar:
            if prov_sel is None:
                st.warning("⚠️ Selecciona un proveedor.")
            elif prod_sel is None:
                st.warning("⚠️ Selecciona un producto.")
            elif cantidad <= 0:
                st.warning("⚠️ La cantidad debe ser mayor a 0.")
            elif any(i["id_producto"] == prod_sel["id_producto"] for i in carrito):
                st.warning("⚠️ Ese producto ya está en la orden; elimínalo para cambiar la cantidad.")
            elif al_cd and not (info_cd and info_cd["CD_autorizado"]):
                st.error("❌ No se puede pedir este producto al CD: su costo global no es menor que el externo.")
            elif al_cd and (info_cd["Existencia"] or 0) < cantidad:
                st.error(f"❌ El CD solo tiene {info_cd['Existencia'] or 0} unidades de este producto.")
            elif precio_compra <= 0:
                st.warning("⚠️ El precio de compra debe ser mayor a $0.00." if not al_cd
                           else "⚠️ El CD no tiene precio de venta definido para este producto.")
            else:
                carrito.append({
                    "id_producto": prod_sel["id_producto"], "nombre": prod_sel["Nombre"],
                    "unidad": prod_sel["Unidad_medida"], "cantidad": int(cantidad),
                    "precio_compra": round(precio_compra, 2),
                    "precio_venta": round(precio_compra * (1 + margen / 100), 2),
                    "fecha_venc": fecha_venc if (tiene_venc and not al_cd) else None,
                    "lead_time": int(lead_time), "stock_minimo": rop})
                st.rerun()

        if carrito:
            st.divider()
            st.subheader("Resumen de la Orden de Compra")
            total = 0.0
            for idx, it in enumerate(carrito):
                c1, c2, c3, c4, c5 = st.columns([3, 1.2, 1.5, 1.5, 0.8])
                c1.write(f"**{it['nombre']}** ({it['unidad']}) · *ROP: {it['stock_minimo']}*"
                         + (f" · vence {it['fecha_venc']:%d/%m/%Y}" if it["fecha_venc"] else ""))
                c2.write(f"Cant: {it['cantidad']}")
                c3.write(f"Costo: ${it['precio_compra']:.2f}")
                c4.write(f"Venta: ${it['precio_venta']:.2f}")
                if c5.button("🗑️", key=f"del_comp_{idx}"):
                    carrito.pop(idx)
                    st.rerun()
                total += it["cantidad"] * it["precio_compra"]
            st.markdown(f"### Total de Compra: `${total:.2f}`")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("🧹 Limpiar Orden"):
                    _limpiar_carrito()
                    st.rerun()
            with b2:
                if st.button("🚚 Confirmar Orden de Compra", type="primary"):
                    try:
                        if al_cd:
                            idv = solicitar_al_cd(id_tienda, id_usuario,
                                                  [{"id_producto": i["id_producto"], "cantidad": i["cantidad"],
                                                    "precio": i["precio_compra"]} for i in carrito])
                            msg = (f"🚚 Pedido al CD registrado como despacho #{idv} por ${total:.2f}. "
                                   "Tu compra quedará registrada cuando confirmes la recepción física.")
                        else:
                            idc = registrar_compra(id_tienda, prov_sel["id_proveedor"], id_usuario, carrito,
                                                   dias_entrega=max(i["lead_time"] for i in carrito))
                            msg = (f"🚚 Orden #{idc} registrada **En tránsito** por ${total:.2f}. "
                                   "Confirma la recepción cuando llegue la mercadería.")
                        _limpiar_carrito()
                        st.session_state["msg_exito_compra"] = msg
                        st.rerun()
                    except ReglaNegocioError as e:
                        st.error(f"❌ {e}")

    # =====================================================================
    # TRÁNSITO Y RECEPCIÓN
    # =====================================================================
    with tab_transito:
        st.caption(f"Hora del sistema (El Salvador): **{ahora_sv():%d/%m/%Y %H:%M}**. "
                   "Nada entra al inventario hasta que se confirma la recepción física.")
        if st.session_state.get("msg_recepcion"):
            st.success(st.session_state.pop("msg_recepcion"))

        if not es_cd:
            st.subheader("🏢 Despachos en camino desde el Centro de Distribución")
            despachos = consultar("""SELECT v.id_venta, v.Fecha, v.Total FROM Venta v
                                     JOIN Cliente c ON c.id_cliente = v.id_cliente
                                     WHERE v.Estado = 'En tránsito' AND c.id_tienda = %s ORDER BY v.Fecha""",
                                  (id_tienda,))
            if not despachos:
                st.info("✅ No tienes despachos pendientes del Centro de Distribución.")
            else:
                st.dataframe(despachos, width="stretch", hide_index=True,
                             column_config={"Total": st.column_config.NumberColumn(format="$%.2f")})
                sel = st.selectbox("Despacho recibido", despachos,
                                   format_func=lambda x: f"Despacho CD #{x['id_venta']} - ${float(x['Total']):.2f}")
                st.dataframe(consultar("""SELECT p.Nombre AS Producto, dv.Cantidad, dv.Precio_unitario,
                                                 dv.Fecha_vencimiento FROM Detalle_venta dv
                                          JOIN Producto p ON p.id_producto = dv.id_producto WHERE dv.id_venta=%s""",
                                       (sel["id_venta"],)), width="stretch", hide_index=True)
                if st.button("✅ Confirmar recepción y registrar mi compra", key="btn_rec_cd"):
                    try:
                        idc = confirmar_despacho_cd(sel["id_venta"], id_tienda, id_usuario)
                        st.session_state["msg_recepcion"] = (f"✅ Despacho #{sel['id_venta']} recibido. "
                                                             f"Se registró la compra #{idc} y entró a tu inventario.")
                        st.rerun()
                    except ReglaNegocioError as e:
                        st.error(f"❌ {e}")
            st.divider()

        st.subheader("🚚 Órdenes a proveedores externos en camino")
        ordenes = consultar("""SELECT c.id_compra, p.Nombre AS Proveedor, c.Fecha AS Fecha_pedido,
                                      c.Fecha_entrega_estimada AS Entrega_estimada, c.Total,
                                      IF(c.Fecha_entrega_estimada < NOW(), '⚠️ Atrasada', 'A tiempo') AS Situación
                               FROM Compra c JOIN Proveedor p ON p.id_proveedor = c.id_proveedor
                               WHERE c.id_tienda = %s AND c.Estado = 'En tránsito'
                               ORDER BY c.Fecha_entrega_estimada""", (id_tienda,))
        if not ordenes:
            st.info("✅ No hay órdenes en tránsito de proveedores externos.")
        else:
            st.dataframe(ordenes, width="stretch", hide_index=True,
                         column_config={"Total": st.column_config.NumberColumn(format="$%.2f")})
            sel = st.selectbox("Orden", ordenes,
                               format_func=lambda x: f"Orden #{x['id_compra']} - {x['Proveedor']} (${float(x['Total']):.2f})")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Marcar como recibida e ingresar al stock", key="btn_rec_prov"):
                    try:
                        recibir_compra(sel["id_compra"], id_tienda)
                        st.session_state["msg_recepcion"] = f"✅ Orden #{sel['id_compra']} recibida e ingresada."
                        st.rerun()
                    except ReglaNegocioError as e:
                        st.error(f"❌ {e}")
            with c2:
                if st.button("🚫 Anular orden", key="btn_anular"):
                    try:
                        anular_compra(sel["id_compra"], id_tienda)
                        st.session_state["msg_recepcion"] = f"Orden #{sel['id_compra']} anulada."
                        st.rerun()
                    except ReglaNegocioError as e:
                        st.error(f"❌ {e}")

    # =====================================================================
    # HISTORIAL
    # =====================================================================
    with tab_hist:
        hist = consultar("""SELECT c.id_compra, c.Fecha, c.Fecha_recepcion, p.Nombre AS Proveedor, c.Total, c.Estado,
                                   c.id_venta_origen AS Despacho_CD
                            FROM Compra c JOIN Proveedor p ON p.id_proveedor = c.id_proveedor
                            WHERE c.id_tienda = %s ORDER BY c.Fecha DESC LIMIT 200""", (id_tienda,))
        st.dataframe(hist, width="stretch", hide_index=True,
                     column_config={"Total": st.column_config.NumberColumn(format="$%.2f")})
        if hist:
            sel = st.selectbox("Ver detalle de la compra", hist, format_func=lambda x: f"Compra #{x['id_compra']}")
            st.dataframe(consultar("""SELECT p.Nombre AS Producto, dc.Cantidad, dc.Precio_compra,
                                             dc.Precio_venta_sugerido, dc.Fecha_vencimiento
                                      FROM Detalle_compra dc LEFT JOIN Producto p ON p.id_producto = dc.id_producto
                                      WHERE dc.id_compra = %s""", (sel["id_compra"],)),
                         width="stretch", hide_index=True)
