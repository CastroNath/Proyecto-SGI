import math

import pandas as pd
import streamlit as st

from config.conexion import consultar, obtener_conexion
from modulos.negocio import ReglaNegocioError, baja_manual, dar_baja_vencidos


DIAS_DEMANDA = 30
LEAD_TIME_DEFECTO = 3


def sugerencias_stock_minimo(id_tienda):
    """Stock mínimo sugerido por producto = demanda diaria × lead time.
    Demanda diaria: unidades vendidas en la tienda en los últimos DIAS_DEMANDA días ÷ DIAS_DEMANDA.
    Lead time: días promedio entre el pedido y la recepción de ese producto en la tienda."""
    filas = consultar(f"""
        SELECT i.id_inventario, p.Nombre, p.Unidad_medida, i.Existencia, i.Stock_minimo, i.Precio_venta,
               COALESCE((SELECT SUM(dv.Cantidad) FROM Venta v JOIN Detalle_venta dv ON dv.id_venta = v.id_venta
                         WHERE v.id_tienda = i.id_tienda AND dv.id_producto = i.id_producto
                           AND v.Fecha >= NOW() - INTERVAL {DIAS_DEMANDA} DAY), 0) AS Vendido,
               (SELECT AVG(GREATEST(DATEDIFF(c.Fecha_recepcion, c.Fecha), 1))
                FROM Compra c JOIN Detalle_compra dc ON dc.id_compra = c.id_compra
                WHERE c.id_tienda = i.id_tienda AND dc.id_producto = i.id_producto
                  AND c.Estado = 'Recibida' AND c.Fecha_recepcion IS NOT NULL) AS Lead_time
        FROM Inventario i JOIN Producto p ON p.id_producto = i.id_producto
        WHERE i.id_tienda = %s ORDER BY p.Nombre""", (id_tienda,))
    for f in filas:
        f["Lead_time"] = round(float(f["Lead_time"])) if f["Lead_time"] is not None else LEAD_TIME_DEFECTO
        f["Demanda"] = float(f["Vendido"]) / DIAS_DEMANDA
        f["Sugerido"] = max(1, math.ceil(f["Demanda"] * f["Lead_time"])) if f["Vendido"] else None
    return filas


def selector_tienda(clave, permitir_todas=True):
    """Administrador y CD tienen visión global; las tiendas ven solo la suya."""
    vision_global = st.session_state.get("id_rol") == 1 or st.session_state.get("es_cd")
    if not vision_global:
        st.caption(f"Mostrando tu sucursal: **{st.session_state.get('nombre_tienda')}**")
        return st.session_state.get("id_tienda")
    tiendas = consultar("SELECT id_tienda, Nombre FROM Tienda ORDER BY Tipo = 'CD' DESC, Nombre")
    opciones = ([{"id_tienda": None, "Nombre": "🌐 Todas las sucursales (visión global)"}] if permitir_todas else []) + tiendas
    return st.selectbox("Sucursal", opciones, format_func=lambda x: x["Nombre"], key=clave)["id_tienda"]


def mostrar_inventario():
    st.header("📦 Gestión de Inventarios")
    id_usuario = st.session_state.get("id_usuario")
    puede_editar = st.session_state.get("id_rol") in (1, 2)
    t_exist, t_venc, t_ajuste = st.tabs(["📋 Existencias", "⏰ Lotes y vencimientos", "🛠️ Ajustes"])

    with t_exist:
        id_t = selector_tienda("inv_t")
        f, p = ("WHERE id_tienda = %s", (id_t,)) if id_t else ("", ())
        datos = consultar(f"""SELECT Tienda, Codigo_barras, Producto, Categoria, Unidad_medida, Existencia,
                                     Stock_minimo, Precio_venta, Estado_stock
                              FROM v_inventario {f} ORDER BY Tienda, Producto""", p)
        if not datos:
            st.info("📭 Aún no hay productos en el inventario de esta selección.")
        else:
            df = pd.DataFrame(datos)
            bajos = (df["Estado_stock"] != "OK").sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Productos", len(df))
            c2.metric("Bajo el punto de reorden", int(bajos))
            c3.metric("Valor a precio de venta", f"${(df['Existencia'] * df['Precio_venta'].astype(float)).sum():,.2f}")
            if bajos:
                st.warning(f"⚠️ Hay **{bajos}** producto(s) con existencia igual o menor a su stock mínimo. "
                           "Revisa Reportes → ¿Cuándo y cuánto comprar?")
            solo = st.toggle("Mostrar solo productos a reponer")
            if solo:
                df = df[df["Estado_stock"] != "OK"]
            st.dataframe(df, width="stretch", hide_index=True,
                         column_config={"Precio_venta": st.column_config.NumberColumn("Precio Venta ($)", format="$%.2f")})

    with t_venc:
        id_t = selector_tienda("venc_t")
        dias = st.slider("Mostrar lotes que vencen en los próximos (días)", 7, 120, 30)
        f, p = ("AND id_tienda = %s", (dias, id_t)) if id_t else ("", (dias,))
        lotes = consultar(f"""SELECT Tienda, Producto, Fecha_vencimiento, Dias_para_vencer, Cantidad_disponible,
                                     Estado_lote FROM v_lotes
                              WHERE Fecha_vencimiento IS NOT NULL AND Dias_para_vencer <= %s {f}
                              ORDER BY Fecha_vencimiento""", p)
        if not lotes:
            st.success("✅ No hay lotes vencidos ni próximos a vencer en ese plazo.")
        else:
            vencidos = sum(1 for l in lotes if l["Estado_lote"] == "Vencido")
            if vencidos:
                st.error(f"⛔ {vencidos} lote(s) vencido(s): no se pueden vender y deben darse de baja.")
            st.dataframe(lotes, width="stretch", hide_index=True)

    with t_ajuste:
        if not puede_editar:
            st.info("Solo Administrador o Encargado pueden ajustar el inventario.")
        else:
            id_t = st.session_state.get("id_tienda")
            st.caption(f"Ajustes sobre: **{st.session_state.get('nombre_tienda')}**")
            if st.session_state.get("ok_ajuste"):
                st.success(st.session_state.pop("ok_ajuste"))

            st.subheader("Stock mínimo y precio de venta")
            st.caption("El stock mínimo es el punto de reorden: al llegar a ese número el producto se marca "
                       "«Reponer». Se calcula solo con lo que sale del inventario: **demanda diaria** (unidades "
                       f"vendidas en los últimos {DIAS_DEMANDA} días ÷ {DIAS_DEMANDA}) **× lead time** (días promedio "
                       f"entre pedir y recibir el producto; {LEAD_TIME_DEFECTO} si aún no hay compras recibidas).")
            inv = sugerencias_stock_minimo(id_t)
            if not inv:
                st.info("Tu tienda aún no tiene productos en inventario.")
            else:
                cambios = [i for i in inv if i["Sugerido"] is not None and i["Sugerido"] != int(i["Stock_minimo"])]
                with st.expander(f"🔄 Recalcular todos los productos ({len(cambios)} con un valor distinto al actual)"):
                    if cambios:
                        st.dataframe([{"Producto": i["Nombre"], "Vendido 30 días": int(i["Vendido"]),
                                       "Demanda diaria": round(i["Demanda"], 2), "Lead time (días)": i["Lead_time"],
                                       "Actual": int(i["Stock_minimo"]), "Sugerido": i["Sugerido"]} for i in cambios],
                                     width="stretch", hide_index=True)
                        if st.button("Aplicar el stock mínimo sugerido a todos"):
                            cx = obtener_conexion(); cur = cx.cursor()
                            cur.executemany("UPDATE Inventario SET Stock_minimo=%s WHERE id_inventario=%s",
                                            [(i["Sugerido"], i["id_inventario"]) for i in cambios])
                            cx.commit(); cur.close(); cx.close()
                            st.session_state["ok_ajuste"] = f"✅ Stock mínimo recalculado en {len(cambios)} productos."
                            st.rerun()
                    else:
                        st.write("Todos los productos con ventas ya tienen su stock mínimo al día.")

                # Fuera del formulario para que, al cambiar de producto, se carguen sus valores
                sel = st.selectbox("Producto", inv, key="param_prod",
                                   format_func=lambda x: f"{x['Nombre']} ({x['Unidad_medida']})")
                actual_min, actual_precio = int(sel["Stock_minimo"]), float(sel["Precio_venta"])
                st.caption(f"Actual: existencia **{sel['Existencia']}** · stock mínimo **{actual_min}** · "
                           f"precio **\\${actual_precio:.2f}**")
                if sel["Sugerido"] is None:
                    st.caption(f"Sin ventas en los últimos {DIAS_DEMANDA} días: no hay datos para calcularlo; "
                               "se mantiene el valor actual.")
                    valor_min = actual_min
                else:
                    st.caption(f"Calculado: {int(sel['Vendido'])} unidades vendidas en {DIAS_DEMANDA} días → "
                               f"{sel['Demanda']:.2f}/día × {sel['Lead_time']} días de lead time = "
                               f"**{sel['Sugerido']}**")
                    valor_min = sel["Sugerido"]
                with st.form(f"form_parametros_{sel['id_inventario']}"):
                    c1, c2 = st.columns(2)
                    minimo = c1.number_input("Stock mínimo (calculado, puedes ajustarlo)", min_value=0, step=1,
                                             value=valor_min)
                    precio = c2.number_input("Precio de venta ($)", min_value=0.01, step=0.05, format="%.2f",
                                             value=max(actual_precio, 0.01))
                    guardar = st.form_submit_button("💾 Guardar")
                if guardar:
                    if int(minimo) == actual_min and round(precio, 2) == round(actual_precio, 2):
                        st.info("No cambiaste ningún valor.")
                    else:
                        cx = obtener_conexion(); cur = cx.cursor()
                        cur.execute("UPDATE Inventario SET Stock_minimo=%s, Precio_venta=%s WHERE id_inventario=%s",
                                    (int(minimo), round(precio, 2), sel["id_inventario"]))
                        cx.commit(); cur.close(); cx.close()
                        st.session_state["ok_ajuste"] = (f"✅ {sel['Nombre']}: stock mínimo {actual_min} → {int(minimo)}, "
                                                         f"precio \\${actual_precio:.2f} → \\${precio:.2f}.")
                        st.rerun()

            st.subheader("Bajas de inventario")
            c1, c2 = st.columns(2)
            with c1:
                st.write("Retirar todos los lotes **vencidos** de mi sucursal.")
                if st.button("🗑️ Dar de baja vencidos"):
                    n = dar_baja_vencidos(id_t, id_usuario)
                    st.session_state["ok_ajuste"] = f"✅ Se dieron de baja {n} unidades vencidas." if n else \
                        "No había producto vencido."
                    st.rerun()
            with c2:
                con_stock = [i for i in consultar("""SELECT i.id_producto, p.Nombre, i.Existencia FROM Inventario i
                                                     JOIN Producto p ON p.id_producto = i.id_producto
                                                     WHERE i.id_tienda=%s AND i.Existencia > 0 ORDER BY p.Nombre""",
                                                  (id_t,))]
                if con_stock:
                    with st.form("form_baja"):
                        sel = st.selectbox("Producto", con_stock, format_func=lambda x: f"{x['Nombre']} (stock {x['Existencia']})")
                        cant = st.number_input("Cantidad", min_value=1, step=1)
                        motivo = st.selectbox("Motivo", ["Daño", "Conteo"])
                        obs = st.text_input("Observación")
                        if st.form_submit_button("Registrar baja"):
                            try:
                                baja_manual(id_t, sel["id_producto"], id_usuario, cant, motivo, obs or None)
                                st.session_state["ok_ajuste"] = f"✅ Baja registrada: {cant} de {sel['Nombre']}."
                                st.rerun()
                            except ReglaNegocioError as e:
                                st.error(f"❌ {e}")
