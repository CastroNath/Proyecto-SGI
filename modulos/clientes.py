import streamlit as st

from config.conexion import consultar, obtener_conexion


def mostrar_clientes():
    st.header("🤝 Gestión de Clientes")
    es_admin = st.session_state.get("id_rol") == 1

    if st.session_state.get("msg_exito_cli"):
        st.success(st.session_state.pop("msg_exito_cli"))

    if es_admin:
        st.caption("Modo Administrador: registra sucursales de la red como clientes del Centro de Distribución.")
        pendientes = consultar("""SELECT t.id_tienda, t.Nombre FROM Tienda t
                                  WHERE t.Tipo <> 'CD'
                                    AND NOT EXISTS (SELECT 1 FROM Cliente c WHERE c.id_tienda = t.id_tienda)
                                  ORDER BY t.Nombre""")
        if not pendientes:
            st.info("✅ Todas las tiendas ya están registradas como clientes del CD.")
        else:
            sel = st.selectbox("Tienda cliente", pendientes, format_func=lambda x: x["Nombre"])
            if st.button("Guardar Cliente"):
                cx = obtener_conexion()
                if cx:
                    cur = cx.cursor()
                    try:
                        cur.execute("INSERT INTO Cliente (Nombre, Tipo, id_tienda) VALUES (%s,'Tienda',%s)",
                                    (sel["Nombre"], sel["id_tienda"]))
                        cx.commit()
                        st.session_state["msg_exito_cli"] = f"✅ '{sel['Nombre']}' registrada como cliente del CD."
                        st.rerun()
                    finally:
                        cur.close(); cx.close()
    else:
        with st.form("form_cliente", clear_on_submit=True):
            nombre_final = st.text_input("Nombre del Cliente", placeholder="Ej. María González")
            st.text_input("Tipo de Cliente", value="Publico general", disabled=True)
            guardar = st.form_submit_button("Guardar Cliente")
        if guardar:
            nombre = nombre_final.strip()
            if not nombre:
                st.warning("⚠️ El nombre del cliente es obligatorio.")
            elif nombre.lower() in ["externo", "consumidor final"]:
                st.error("❌ Ese nombre está reservado por el sistema para ventas rápidas sin registro.")
            elif consultar("SELECT 1 FROM Cliente WHERE LOWER(Nombre)=LOWER(%s) AND Tipo='Publico general'", (nombre,)):
                st.error(f"❌ El cliente '{nombre}' ya se encuentra registrado.")
            else:
                cx = obtener_conexion()
                if cx:
                    cur = cx.cursor()
                    try:
                        cur.execute("INSERT INTO Cliente (Nombre, Tipo) VALUES (%s, 'Publico general')", (nombre,))
                        cx.commit()
                        st.session_state["msg_exito_cli"] = f"✅ Cliente '{nombre}' registrado correctamente."
                        st.rerun()
                    finally:
                        cur.close(); cx.close()

    st.subheader("Clientes registrados")
    st.dataframe(consultar("""SELECT c.id_cliente AS ID, c.Nombre, c.Tipo, t.Nombre AS Sucursal_enlazada
                              FROM Cliente c LEFT JOIN Tienda t ON t.id_tienda = c.id_tienda
                              ORDER BY c.Tipo, c.Nombre"""), width="stretch", hide_index=True)
