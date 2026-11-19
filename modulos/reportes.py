"""5.0 Gestión de reportes y consultas para la toma de decisiones."""
import math
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from config.conexion import consultar
from modulos.inventario import selector_tienda
from modulos.formato import tabla

DINERO = st.column_config.NumberColumn(format="$%.2f")


def _df(sql, params=()):
    df = pd.DataFrame(consultar(sql, params))
    for c in df.columns:  # DECIMAL -> float
        if df[c].dtype == object and len(df) and df[c].map(lambda v: type(v).__name__ == "Decimal").any():
            df[c] = df[c].astype(float)
    return df


def mostrar_reportes():
    st.header("📊 Reportes y Consultas")
    if st.session_state.get("id_rol") not in (1, 2):
        st.error("⛔ Los reportes están disponibles para Administrador y Encargados.")
        return
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        id_t = selector_tienda("rep_t")
    desde = c2.date_input("Desde", date.today() - timedelta(days=30), key="rep_desde")
    hasta = c3.date_input("Hasta", date.today(), key="rep_hasta")
    ft = "AND v.id_tienda = %s" if id_t else ""
    pt = (id_t,) if id_t else ()

    ve_costos_cd = st.session_state.get("id_rol") == 1 or st.session_state.get("es_cd")
    nombres = ["🛒 ¿Cuándo y cuánto comprar?", "💵 Ventas", "🔄 Movimientos", "🏪 Comparativo por tienda"]
    tabs = st.tabs(nombres + (["🏢 Evaluación del CD"] if ve_costos_cd else []))
    t1, t2, t3, t4 = tabs[:4]
    t5 = tabs[4] if ve_costos_cd else None

    # -----------------------------------------------------------------
    with t1:
        st.caption("Demanda diaria = unidades vendidas en el período ÷ días del período. "
                   "Punto de reorden = demanda diaria × lead time + stock mínimo. "
                   "Cantidad sugerida = demanda × (lead time + días de cobertura) + stock mínimo − existencia − en tránsito.")
        a, b = st.columns(2)
        lead = a.number_input("Lead time de entrega (días)", 1, 60, 3)
        cobertura = b.number_input("Días de cobertura deseados", 1, 90, 15)
        dias = max(1, (hasta - desde).days + 1)
        fi = "WHERE i.id_tienda = %s" if id_t else ""
        df = _df(f"""
            SELECT t.Nombre AS Tienda, p.Nombre AS Producto, i.Existencia, i.Stock_minimo,
                   COALESCE(vt.vendido, 0) AS Vendido_periodo,
                   COALESCE(tr.en_transito, 0) AS En_transito
            FROM Inventario i
            JOIN Tienda t ON t.id_tienda = i.id_tienda
            JOIN Producto p ON p.id_producto = i.id_producto
            LEFT JOIN (SELECT v.id_tienda, dv.id_producto, SUM(dv.Cantidad) vendido
                       FROM Venta v JOIN Detalle_venta dv ON dv.id_venta = v.id_venta
                       WHERE DATE(v.Fecha) BETWEEN %s AND %s GROUP BY v.id_tienda, dv.id_producto) vt
                   ON vt.id_tienda = i.id_tienda AND vt.id_producto = i.id_producto
            LEFT JOIN (SELECT c.id_tienda, dc.id_producto, SUM(dc.Cantidad) en_transito
                       FROM Compra c JOIN Detalle_compra dc ON dc.id_compra = c.id_compra
                       WHERE c.Estado = 'En tránsito' GROUP BY c.id_tienda, dc.id_producto
                       UNION ALL
                       SELECT cl.id_tienda, dv.id_producto, SUM(dv.Cantidad)
                       FROM Venta v JOIN Detalle_venta dv ON dv.id_venta = v.id_venta
                       JOIN Cliente cl ON cl.id_cliente = v.id_cliente
                       WHERE v.Estado = 'En tránsito' GROUP BY cl.id_tienda, dv.id_producto) tr
                   ON tr.id_tienda = i.id_tienda AND tr.id_producto = i.id_producto
            {fi}""", (desde, hasta) + pt)
        if df.empty:
            st.info("Sin inventario para analizar.")
        else:
            df = df.groupby(["Tienda", "Producto", "Existencia", "Stock_minimo", "Vendido_periodo"],
                            as_index=False)["En_transito"].sum()
            df["Demanda_diaria"] = (df["Vendido_periodo"] / dias).round(2)
            df["Dias_de_stock"] = df.apply(lambda r: round(r["Existencia"] / r["Demanda_diaria"], 1)
                                           if r["Demanda_diaria"] > 0 else None, axis=1)
            df["Punto_reorden"] = (df["Demanda_diaria"] * lead + df["Stock_minimo"]).apply(math.ceil)
            df["Comprar_ahora"] = (df["Existencia"] + df["En_transito"]) <= df["Punto_reorden"]
            df["Cantidad_sugerida"] = (df["Demanda_diaria"] * (lead + cobertura) + df["Stock_minimo"]
                                       - df["Existencia"] - df["En_transito"]).apply(lambda x: max(0, math.ceil(x)))
            urgentes = df[df["Comprar_ahora"]].sort_values("Dias_de_stock", na_position="last")
            st.metric("Productos que hay que comprar ya", len(urgentes))
            tabla(urgentes if st.toggle("Solo los que hay que comprar", value=True) else df,
                         width="stretch", hide_index=True)

    # -----------------------------------------------------------------
    with t2:
        ventas = _df(f"""SELECT DATE(v.Fecha) AS Dia, SUM(v.Total) AS Total, COUNT(*) AS Transacciones
                         FROM Venta v WHERE DATE(v.Fecha) BETWEEN %s AND %s {ft}
                         GROUP BY DATE(v.Fecha) ORDER BY Dia""", (desde, hasta) + pt)
        if ventas.empty:
            st.info("No hay ventas en el período.")
        else:
            a, b, c = st.columns(3)
            a.metric("Total vendido", f"${ventas['Total'].sum():,.2f}")
            b.metric("Transacciones", int(ventas["Transacciones"].sum()))
            c.metric("Ticket promedio", f"${ventas['Total'].sum() / ventas['Transacciones'].sum():,.2f}")
            st.bar_chart(ventas.set_index("Dia")["Total"])
            top = _df(f"""SELECT p.Nombre AS Producto, c.Nombre AS Categoria, SUM(dv.Cantidad) AS Unidades,
                                 SUM(dv.Cantidad * dv.Precio_unitario) AS Ingreso
                          FROM Venta v JOIN Detalle_venta dv ON dv.id_venta = v.id_venta
                          JOIN Producto p ON p.id_producto = dv.id_producto
                          JOIN Categoria c ON c.id_categoria = p.id_categoria
                          WHERE DATE(v.Fecha) BETWEEN %s AND %s {ft}
                          GROUP BY p.id_producto, p.Nombre, c.Nombre ORDER BY Ingreso DESC""", (desde, hasta) + pt)
            st.subheader("Comportamiento de productos")
            tabla(top, width="stretch", hide_index=True, column_config={"Ingreso": DINERO})
            sin_mov = _df(f"""SELECT t.Nombre AS Tienda, p.Nombre AS Producto, i.Existencia
                              FROM Inventario i JOIN Producto p ON p.id_producto = i.id_producto
                              JOIN Tienda t ON t.id_tienda = i.id_tienda
                              WHERE i.Existencia > 0 {'AND i.id_tienda = %s' if id_t else ''}
                                AND NOT EXISTS (SELECT 1 FROM Venta v JOIN Detalle_venta dv ON dv.id_venta = v.id_venta
                                                WHERE v.id_tienda = i.id_tienda AND dv.id_producto = i.id_producto
                                                  AND DATE(v.Fecha) BETWEEN %s AND %s)""", pt + (desde, hasta))
            if not sin_mov.empty:
                st.subheader("Productos sin ventas en el período (inventario inmovilizado)")
                tabla(sin_mov, width="stretch", hide_index=True)

    # -----------------------------------------------------------------
    with t3:
        fm = "AND m.id_tienda = %s" if id_t else ""
        mov = _df(f"""SELECT m.Fecha, t.Nombre AS Tienda, m.Tipo, m.Documento, p.Nombre AS Producto,
                             m.Cantidad, m.Precio, m.Importe
                      FROM v_movimientos m JOIN Tienda t ON t.id_tienda = m.id_tienda
                      JOIN Producto p ON p.id_producto = m.id_producto
                      WHERE DATE(m.Fecha) BETWEEN %s AND %s {fm} ORDER BY m.Fecha DESC""", (desde, hasta) + pt)
        if mov.empty:
            st.info("Sin movimientos en el período.")
        else:
            resumen = mov.groupby("Tipo").agg(Lineas=("Cantidad", "size"), Unidades=("Cantidad", "sum"),
                                              Importe=("Importe", "sum")).reset_index()
            tabla(resumen, width="stretch", hide_index=True, column_config={"Importe": DINERO})
            tipos = st.multiselect("Tipo de movimiento", sorted(mov["Tipo"].unique()), default=sorted(mov["Tipo"].unique()))
            tabla(mov[mov["Tipo"].isin(tipos)], width="stretch", hide_index=True,
                         column_config={"Precio": DINERO, "Importe": DINERO})

    # -----------------------------------------------------------------
    with t4:
        comp = _df("""SELECT t.Nombre AS Tienda, t.Tipo,
                             COALESCE((SELECT SUM(v.Total) FROM Venta v WHERE v.id_tienda = t.id_tienda
                                       AND DATE(v.Fecha) BETWEEN %s AND %s), 0) AS Ventas,
                             COALESCE((SELECT SUM(c.Total) FROM Compra c WHERE c.id_tienda = t.id_tienda
                                       AND c.Estado = 'Recibida' AND DATE(c.Fecha_recepcion) BETWEEN %s AND %s), 0) AS Compras,
                             COALESCE((SELECT SUM(i.Existencia * i.Precio_venta) FROM Inventario i
                                       WHERE i.id_tienda = t.id_tienda), 0) AS Valor_inventario,
                             (SELECT COUNT(*) FROM v_inventario vi WHERE vi.id_tienda = t.id_tienda
                                      AND vi.Estado_stock <> 'OK') AS Productos_a_reponer
                      FROM Tienda t ORDER BY t.Tipo = 'CD' DESC, t.Nombre""", (desde, hasta, desde, hasta))
        tabla(comp, width="stretch", hide_index=True,
                     column_config={"Ventas": DINERO, "Compras": DINERO, "Valor_inventario": DINERO})
        if not comp.empty:
            st.bar_chart(comp.set_index("Tienda")[["Ventas", "Compras"]])

    # -----------------------------------------------------------------
    if t5 is None:
        return
    with t5:
        st.caption("Regla de negocio: el CD solo puede abastecer a una tienda si su costo global de adquisición "
                   "(promedio ponderado) es menor que lo que pagan las tiendas a proveedores externos.")
        ev = _df("SELECT Producto, Costo_CD, Costo_externo, CD_autorizado FROM v_evaluacion_cd ORDER BY Producto")
        if not ev.empty:
            ev["Ahorro_por_unidad"] = (ev["Costo_externo"] - ev["Costo_CD"]).round(2)
            ev["CD_autorizado"] = ev["CD_autorizado"].map({1: "✅ Sí", 0: "❌ No"})
            tabla(ev, width="stretch", hide_index=True,
                         column_config={"Costo_CD": DINERO, "Costo_externo": DINERO, "Ahorro_por_unidad": DINERO})
