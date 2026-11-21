import math
from datetime import date, timedelta

import streamlit as st

from config.conexion import consultar, consultar_uno
from modulos.inventario import DIAS_DEMANDA
from modulos.negocio import (MARGEN_VENTA, ReglaNegocioError, ahora_sv, anular_compra, confirmar_despacho_cd,
                             recibir_compra, registrar_compra, solicitar_al_cd)
from modulos.formato import tabla


def obtener_proveedores(es_cd):
    """El CD compra solo a externos; las tiendas también pueden pedir al CD."""
    filtro = "WHERE id_tienda_cd IS NULL" if es_cd else ""
    return consultar(f"SELECT id_proveedor, Nombre, Tipo, id_tienda_cd FROM Proveedor {filtro} "
                     "ORDER BY id_tienda_cd IS NULL, Nombre")


def precio_lista(id_producto, id_proveedor):
    """Precio de lista del proveedor para ese producto (ProductoxProveedor), o None."""
    r = consultar_uno("SELECT Ultimo_precio FROM ProductoxProveedor WHERE id_producto=%s AND id_proveedor=%s",
                      (id_producto, id_proveedor))
    return float(r["Ultimo_precio"]) if r and r["Ultimo_precio"] is not None else None


def obtener_comparativa_producto(id_producto, es_cd, info_cd):
    """Precios de lista de los proveedores externos (ProductoxProveedor) y, para las tiendas,
    el precio de venta del CD. Ordenado de más barato a más caro; el primero se marca como mejor opción.
    Nunca muestra el costo de compra del CD."""
    filas = consultar("""SELECT pr.Nombre AS Proveedor, pr.Tipo, pxp.Ultimo_precio AS Precio
                         FROM ProductoxProveedor pxp JOIN Proveedor pr ON pr.id_proveedor = pxp.id_proveedor
                         WHERE pxp.id_producto = %s AND pr.id_tienda_cd IS NULL AND pxp.Ultimo_precio IS NOT NULL""",
                      (id_producto,))
    if not es_cd and info_cd and info_cd["Precio_CD"] and (info_cd["Existencia"] or 0) > 0:
        filas.append({"Proveedor": "🏢 Centro de Distribución", "Tipo": "Centro de Distribución",
                      "Precio": info_cd["Precio_CD"]})
    filas.sort(key=lambda f: float(f["Precio"]))
    for n, f in enumerate(filas):
        f["Mejor opción"] = "✅ Más barato" if n == 0 else ""
    return filas


def demanda_real(id_tienda, id_producto):
    """Unidades diarias vendidas por la tienda en los últimos DIAS_DEMANDA días."""
    r = consultar_uno(f"""SELECT COALESCE(SUM(dv.Cantidad), 0) AS q FROM Venta v
                          JOIN Detalle_venta dv ON dv.id_venta = v.id_venta
                          WHERE v.id_tienda = %s AND dv.id_producto = %s
                            AND v.Fecha >= NOW() - INTERVAL {DIAS_DEMANDA} DAY""", (id_tienda, id_producto))
    return float(r["q"]) / DIAS_DEMANDA if r else 0.0


def aviso_catalogo(prov_sel, prod_sel, comp, info_cd):
    """Avisa si el proveedor elegido no tiene el producto en su catálogo y dice quién sí lo tiene."""
    if not (prov_sel and prod_sel):
        return
    if prov_sel["id_tienda_cd"]:
        tiene = bool(info_cd and info_cd["Precio_CD"] and (info_cd["Existencia"] or 0) > 0)
    else:
        tiene = precio_lista(prod_sel["id_producto"], prov_sel["id_proveedor"]) is not None
    if tiene:
        return
    otros = [f"**{f['Proveedor'].replace('🏢 ', '')}** (\\${float(f['Precio']):.2f})" for f in comp]
    nombre_prov = "El Centro de Distribución" if prov_sel["id_tienda_cd"] else f"**{prov_sel['Nombre']}**"
    msg = f"⚠️ {nombre_prov} no tiene **{prod_sel['Nombre']}** en su catálogo."
    if otros:
        msg += " Lo venden: " + ", ".join(otros) + ". Para comprarlo, cambia de proveedor"
        msg += "." if not prov_sel["id_tienda_cd"] else " (elige un proveedor externo)."
        if not prov_sel["id_tienda_cd"]:
            msg += " Si este proveedor sí te lo vende, escribe el precio acordado y quedará en su catálogo."
    else:
        msg += " Ningún proveedor lo tiene registrado todavía; escribe el precio acordado."
    st.warning(msg)


def datos_cd_producto(id_producto):
    """Precio de venta del CD a las tiendas, su existencia, el mejor precio externo y si está autorizado."""
    return consultar_uno("""SELECT e.Precio_CD, e.Mejor_precio_externo, e.CD_autorizado, i.Existencia
                            FROM v_evaluacion_cd e
                            LEFT JOIN Inventario i ON i.id_producto = e.id_producto
                                 AND i.id_tienda = (SELECT MIN(id_tienda) FROM Tienda WHERE Tipo = 'CD')
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
            comp = obtener_comparativa_producto(prod_sel["id_producto"], es_cd, info_cd)
            aviso_catalogo(prov_sel, prod_sel, comp, info_cd)
            if comp:
                with st.expander("📊 Comparativa de precios por proveedor", expanded=True):
                    tabla(comp)
            else:
                st.info("Ningún proveedor tiene precio registrado para este producto todavía.")
            if not es_cd and info_cd:
                # Regla: comprar al CD solo si vende más barato que el mejor proveedor externo
                mejor_ext = info_cd["Mejor_precio_externo"]
                externo = comp[0]["Proveedor"] if comp and not comp[0]["Proveedor"].startswith("🏢") else None
                hay_stock = (info_cd["Existencia"] or 0) > 0
                if info_cd["CD_autorizado"] and hay_stock:
                    st.success(f"✅ **Compra al Centro de Distribución**: vende a **\\${float(info_cd['Precio_CD']):.2f}**"
                               + (f", más barato que el mejor proveedor externo (\\${float(mejor_ext):.2f})"
                                  if mejor_ext is not None else "")
                               + f". Existencia en el CD: **{info_cd['Existencia']}**.")
                elif info_cd["CD_autorizado"]:
                    st.warning("🏢 El CD sería la opción más barata, pero ahora no tiene existencias. "
                               f"Compra a {externo or 'un proveedor externo'}.")
                elif externo:
                    st.info(f"💡 **Compra a {externo}** (\\${float(mejor_ext):.2f}): "
                            + ("el CD no maneja este producto." if not info_cd["Precio_CD"]
                               else "el Centro de Distribución no es la opción más barata para este producto."))

        st.divider()
        # Fuera del formulario: así la fecha aparece en cuanto se marca la casilla
        if al_cd:
            tiene_venc = False
            st.caption("📅 El vencimiento se hereda automáticamente de los lotes que despacha el CD.")
        else:
            tiene_venc = st.checkbox("📅 Este lote tiene fecha de vencimiento", key=f"venc_{r}_{len(carrito)}")
        lista = (precio_lista(prod_sel["id_producto"], prov_sel["id_proveedor"])
                 if prod_sel and prov_sel and not al_cd else None)
        clave_item = f"{r}_{len(carrito)}_{prod_sel['id_producto'] if prod_sel else 0}_{prov_sel['id_proveedor'] if prov_sel else 0}"
        with st.form(f"item_compra_{clave_item}"):
            c1, c2 = st.columns(2)
            with c1:
                cantidad = st.number_input("Cantidad solicitada", min_value=0, step=1)
                if al_cd:
                    lead_time = 1  # el despacho del CD se recibe al confirmar; no hay plazo que capturar
                else:
                    lead_time = st.number_input("Días que tarda el proveedor en entregar (lead time)", min_value=1,
                                                max_value=90, step=1, value=1,
                                                help="Días desde que haces el pedido hasta que llega a tu tienda. "
                                                     "Sirve para calcular cuándo volver a pedir.")
            with c2:
                if al_cd:
                    precio_cd = float(info_cd["Precio_CD"]) if info_cd and info_cd["Precio_CD"] else 0.0
                    st.number_input("Precio unitario ($ - tarifa del CD)", value=precio_cd, format="%.2f", disabled=True)
                    precio_compra = precio_cd
                else:
                    precio_compra = st.number_input("Precio de compra unitario ($)", min_value=0.0, step=0.05,
                                                    format="%.2f", value=lista or 0.0,
                                                    help="Se llena con el precio de lista del proveedor; "
                                                         "cámbialo si te dio otro precio.")
                margen = st.number_input("Margen sobre costo (%)", min_value=0, max_value=200,
                                         value=int((MARGEN_VENTA - 1) * 100))
                fecha_venc = (st.date_input("Fecha de vencimiento", min_value=date.today() + timedelta(days=1))
                              if tiene_venc else None)
            agregar = st.form_submit_button("➕ Agregar producto a la orden")

        # Stock mínimo automático: misma fórmula que Inventario → Ajustes, con las ventas reales de la tienda
        demanda_diaria = demanda_real(id_tienda, prod_sel["id_producto"]) if prod_sel else 0.0
        rop = max(1, math.ceil(demanda_diaria * lead_time)) if demanda_diaria > 0 else None
        if prod_sel:
            if rop is None:
                st.caption(f"📐 Sin ventas de este producto en los últimos {DIAS_DEMANDA} días: "
                           "el stock mínimo actual no se modifica.")
            else:
                st.caption(f"📐 Stock mínimo automático = demanda diaria real **{demanda_diaria:.2f}** "
                           f"(ventas de los últimos {DIAS_DEMANDA} días)"
                           + ("." if al_cd else " × los días de entrega que indiques. Lo verás en la orden."))

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
                st.error("❌ El Centro de Distribución no ofrece este producto en este momento.")
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
                c1.write(f"**{it['nombre']}** ({it['unidad']})"
                         + (f" · *stock mínimo: {it['stock_minimo']}*" if it["stock_minimo"] else "")
                         + (f" · vence {it['fecha_venc']:%d/%m/%Y}" if it["fecha_venc"] else ""))
                c2.write(f"Cant: {it['cantidad']}")
                c3.write(f"Costo: \\${it['precio_compra']:.2f}")
                c4.write(f"Venta: \\${it['precio_venta']:.2f}")
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
                if st.button("🚚 Confirmar Orden de Compra"):
                    try:
                        if al_cd:
                            idv = solicitar_al_cd(id_tienda, id_usuario,
                                                  [{"id_producto": i["id_producto"], "cantidad": i["cantidad"],
                                                    "precio": i["precio_compra"]} for i in carrito])
                            msg = (f"🚚 Pedido al CD registrado como despacho #{idv} por \\${total:.2f}. "
                                   "Tu compra quedará registrada cuando confirmes la recepción física.")
                        else:
                            idc = registrar_compra(id_tienda, prov_sel["id_proveedor"], id_usuario, carrito,
                                                   dias_entrega=max(i["lead_time"] for i in carrito))
                            msg = (f"🚚 Orden #{idc} registrada **En tránsito** por \\${total:.2f}. "
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
                tabla(despachos, width="stretch", hide_index=True)
                sel = st.selectbox("Despacho recibido", despachos,
                                   format_func=lambda x: f"Despacho CD #{x['id_venta']} - ${float(x['Total']):.2f}")
                tabla(consultar("""SELECT p.Nombre AS Producto, dv.Cantidad, dv.Precio_unitario,
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
            tabla(ordenes, width="stretch", hide_index=True)
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
        tabla(hist, width="stretch", hide_index=True)
        if hist:
            sel = st.selectbox("Ver detalle de la compra", hist, format_func=lambda x: f"Compra #{x['id_compra']}")
            tabla(consultar("""SELECT p.Nombre AS Producto, dc.Cantidad, dc.Precio_compra,
                                             dc.Precio_venta_sugerido, dc.Fecha_vencimiento
                                      FROM Detalle_compra dc LEFT JOIN Producto p ON p.id_producto = dc.id_producto
                                      WHERE dc.id_compra = %s""", (sel["id_compra"],)),
                         width="stretch", hide_index=True)
