from datetime import date, timedelta

import streamlit as st

from config.conexion import consultar
from modulos.negocio import ReglaNegocioError, ahora_sv, registrar_venta
from modulos.formato import tabla


def obtener_clientes(solo_tiendas, id_tienda=None):
    if solo_tiendas:
        return consultar("SELECT id_cliente, Nombre FROM Cliente WHERE Tipo='Tienda' AND id_tienda IS NOT NULL "
                         "ORDER BY Nombre")
    # Cada tienda factura solo a los clientes que ella registró
    return consultar("""SELECT id_cliente, Nombre, NIT, NRC FROM Cliente
                        WHERE Tipo = 'Publico general' AND id_tienda_registro = %s AND NRC IS NOT NULL
                        ORDER BY Nombre""", (id_tienda,))


def obtener_productos_disponibles(id_tienda, solo_autorizados_cd=False):
    filtro = "AND e.CD_autorizado = 1" if solo_autorizados_cd else ""
    return consultar(f"""SELECT p.id_producto, p.Nombre, p.Unidad_medida, i.Existencia, i.Precio_venta,
                                e.CD_autorizado
                         FROM Inventario i JOIN Producto p ON p.id_producto = i.id_producto
                         JOIN v_evaluacion_cd e ON e.id_producto = i.id_producto
                         WHERE i.id_tienda = %s AND i.Existencia > 0 {filtro}
                         ORDER BY p.Nombre""", (id_tienda,))


def mostrar_ventas():
    st.header("💸 Gestión de Ventas")
    id_tienda = st.session_state.get("id_tienda")
    id_usuario = st.session_state.get("id_usuario")
    es_cd = st.session_state.get("es_cd", False)
    st.caption(f"🏪 Registrando en: **{st.session_state.get('nombre_tienda')}**")

    # El CD solo vende a las tiendas (despachos); las tiendas venden al público
    tabs = st.tabs(["🚚 Despacho a Tienda", "📋 Historial"] if es_cd
                   else ["🛍️ Nueva Venta", "📋 Historial"])

    def formulario(tab, a_tienda):
        clave = "carrito_despacho" if a_tienda else "carrito_ventas"
        st.session_state.setdefault(clave, [])
        st.session_state.setdefault(f"reset_{clave}", 0)
        carrito = st.session_state[clave]
        r = st.session_state[f"reset_{clave}"]
        if st.session_state.get(f"ok_{clave}"):
            st.success(st.session_state.pop(f"ok_{clave}"))

        if a_tienda:
            st.caption("Solo aparecen los productos en los que el CD es más barato que los proveedores externos.")
            tiendas = obtener_clientes(solo_tiendas=True)
            sel = st.selectbox("Tienda destino", [None] + tiendas, key=f"cli_{clave}_{r}",
                               format_func=lambda x: "-- Selecciona una tienda --" if x is None else x["Nombre"],
                               disabled=len(carrito) > 0)
            id_cliente = sel["id_cliente"] if sel else None
        else:
            factura = st.checkbox("🧾 El cliente requiere Crédito Fiscal", key=f"fact_{r}",
                                  disabled=len(carrito) > 0)
            if factura:
                clientes = obtener_clientes(solo_tiendas=False, id_tienda=id_tienda)
                sel = st.selectbox("Cliente", [None] + clientes, key=f"cli_{clave}_{r}",
                                   format_func=lambda x: "-- Selecciona un cliente --" if x is None else
                                   f"{x['Nombre']} · NRC {x['NRC']}",
                                   disabled=len(carrito) > 0)
                id_cliente = sel["id_cliente"] if sel else None
                if sel and sel["NRC"]:
                    tipo_doc = "DUI" if len(sel["NIT"] or "") == 10 else "NIT"
                    st.caption(f"🧾 Comprobante de Crédito Fiscal · {tipo_doc} {sel['NIT']} · NRC {sel['NRC']}")
                if not clientes:
                    st.caption("No tienes clientes de crédito fiscal registrados; regístralos en Catálogos y Registros → Clientes.")
            else:
                st.caption("⚡ Venta rápida: se registra como **Consumidor final**.")
                id_cliente = 1

        productos = obtener_productos_disponibles(id_tienda, solo_autorizados_cd=a_tienda)
        if not productos:
            st.warning("📦 No hay productos disponibles para esta operación.")
            return

        with st.form(f"form_{clave}_{r}_{len(carrito)}"):
            c1, c2, c3 = st.columns([3, 1.2, 1.2])
            # Empieza vacío y no repite lo que ya está en el carrito, para no confundir el producto elegido
            en_carrito = {i["id_producto"] for i in carrito}
            prod = c1.selectbox("Producto disponible",
                                [None] + [p for p in productos if p["id_producto"] not in en_carrito],
                                format_func=lambda x: "-- Selecciona un producto --" if x is None else
                                f"{x['Nombre']} ({x['Unidad_medida']}) · Stock: {x['Existencia']} · "
                                f"Precio: ${float(x['Precio_venta']):.2f}")
            cantidad = c2.number_input("Cantidad", min_value=0, step=1)
            precio = c3.number_input("Precio unitario ($)", min_value=0.0, step=0.05, format="%.2f", value=None,
                                     help="Déjalo vacío para usar el precio de venta del producto.")
            agregar = st.form_submit_button("➕ Agregar")
        if agregar:
            if prod is None:
                st.warning("⚠️ Selecciona un producto.")
            elif cantidad <= 0:
                st.warning("⚠️ La cantidad debe ser mayor a 0.")
            elif any(i["id_producto"] == prod["id_producto"] for i in carrito):
                st.warning("⚠️ El producto ya está en el carrito; elimínalo para cambiar la cantidad.")
            elif cantidad > prod["Existencia"]:
                st.error(f"⚠️ No puedes superar el stock disponible ({prod['Existencia']}).")
            else:
                p = precio if precio else float(prod["Precio_venta"])
                carrito.append({"id_producto": prod["id_producto"], "nombre": prod["Nombre"],
                                "unidad": prod["Unidad_medida"], "cantidad": int(cantidad), "precio": p})
                st.rerun()

        if carrito:
            st.divider()
            total = 0.0
            for idx, it in enumerate(carrito):
                c1, c2, c3, c4, c5 = st.columns([3, 1, 1.5, 1.5, 0.8])
                c1.write(f"**{it['nombre']}** ({it['unidad']})")
                c2.write(f"Cant: {it['cantidad']}")
                c3.write(f"\\${it['precio']:.2f} c/u")
                c4.write(f"**\\${it['cantidad'] * it['precio']:.2f}**")
                if c5.button("🗑️", key=f"del_{clave}_{idx}"):
                    carrito.pop(idx)
                    st.rerun()
                total += it["cantidad"] * it["precio"]
            st.markdown(f"### Total: `${total:.2f}`")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("🧹 Vaciar carrito", key=f"vaciar_{clave}"):
                    st.session_state[clave] = []
                    st.session_state[f"reset_{clave}"] += 1
                    st.rerun()
            with b2:
                texto = "🚚 Confirmar despacho (En tránsito)" if a_tienda else "💳 Confirmar y cobrar venta"
                if st.button(texto, key=f"conf_{clave}"):
                    if id_cliente is None:
                        st.error("❌ Selecciona el cliente o la tienda destino.")
                        return
                    try:
                        idv = registrar_venta(id_tienda, id_usuario, id_cliente, carrito)
                        st.session_state[clave] = []
                        st.session_state[f"reset_{clave}"] += 1
                        st.session_state[f"ok_{clave}"] = (
                            f"🚚 Despacho #{idv} enviado por \\${total:.2f}. La tienda destino debe confirmar la recepción."
                            if a_tienda else f"✅ Venta #{idv} registrada por \\${total:.2f}.")
                        st.rerun()
                    except ReglaNegocioError as e:
                        st.error(f"❌ {e}")

    with tabs[0]:
        formulario(tabs[0], a_tienda=es_cd)

    with tabs[-1]:
        c1, c2 = st.columns(2)
        desde = c1.date_input("Desde", date.today() - timedelta(days=7))
        hasta = c2.date_input("Hasta", ahora_sv().date())
        ventas = consultar("""SELECT v.id_venta AS ID, v.Fecha, c.Nombre AS Cliente, u.Nombre AS Atendido_por,
                                     v.Total, v.Estado
                              FROM Venta v JOIN Cliente c ON c.id_cliente = v.id_cliente
                              JOIN Usuario u ON u.id_usuario = v.id_usuario
                              WHERE v.id_tienda = %s AND DATE(v.Fecha) BETWEEN %s AND %s
                              ORDER BY v.id_venta DESC""", (id_tienda, desde, hasta))
        if not ventas:
            st.info("📭 No hay ventas en el rango seleccionado.")
        else:
            st.caption(f"{len(ventas)} ventas · \\${sum(float(v['Total']) for v in ventas):,.2f}")
            tabla(ventas, width="stretch", hide_index=True)
            sel = st.selectbox("Ver detalle", ventas, index=None, placeholder="Selecciona una venta",
                               format_func=lambda x: f"Venta #{x['ID']}")
            if sel is not None:
                tabla(consultar("""SELECT p.Nombre AS Producto, dv.Cantidad, dv.Precio_unitario,
                                          dv.Cantidad * dv.Precio_unitario AS Subtotal
                                   FROM Detalle_venta dv JOIN Producto p ON p.id_producto = dv.id_producto
                                   WHERE dv.id_venta = %s""", (sel["ID"],)))
