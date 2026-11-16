import streamlit as st
from modulos.login import login
from modulos.categorias import mostrar_categorias
from modulos.productos import mostrar_productos
from modulos.proveedores import mostrar_proveedores
from modulos.clientes import mostrar_clientes
from modulos.registro import mostrar_registro
from modulos.ventas import mostrar_ventas
from modulos.compras import mostrar_compras
from modulos.inventario import mostrar_inventario

st.set_page_config(page_title="Red Cooperativa de Mujeres de Occidente", layout="wide")

st.markdown("""
    <style>
    @keyframes rebotar {
        0%, 100% { transform: translateY(0); }
        40% { transform: translateY(-8px); }
        70% { transform: translateY(-3px); }
    }
    div.stButton > button[kind="secondary"] {
        background-color: #13294B;
        color: white;
        width: 100%;
        border-radius: 8px;
        border: none;
        padding: 10px 15px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    div.stButton > button[kind="secondary"]:hover {
        background-color: #1e3f73;
        color: white;
    }
    div.stButton > button[kind="primary"] {
        background-color: #f8f9fa;
        color: #1f2937;
        border: 1px solid #d1d5db;
        border-radius: 12px;
        padding: 24px 15px;
        height: 195px;
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
    }
    div.stButton > button[kind="primary"] p {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        margin: 0;
        line-height: 1.3;
        white-space: normal;
    }
    div.stButton > button[kind="primary"] em {
        font-style: normal;
        font-size: 42px;
        margin-bottom: 8px;
        display: block;
    }
    div.stButton > button[kind="primary"] strong {
        font-size: 17px;
        font-weight: bold;
        color: #111827;
        margin-bottom: 6px;
        display: block;
    }
    div.stButton > button[kind="primary"] code {
        background-color: transparent;
        font-family: inherit;
        font-size: 13px;
        color: #6b7280;
        padding: 0;
        display: block;
        white-space: normal;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #ffffff;
        border-color: #13294B;
        box-shadow: 0 8px 16px rgba(19, 41, 75, 0.12);
        animation: rebotar 0.5s ease;
    }
    </style>
""", unsafe_allow_html=True)

if "sesion_iniciada" not in st.session_state:
    st.session_state["sesion_iniciada"] = False
if "vista_actual" not in st.session_state:
    st.session_state["vista_actual"] = "menu_principal"

if not st.session_state["sesion_iniciada"]:
    login()
else:
    st.caption(f"👤 Usuario: **{st.session_state['nombre_completo']}** | 🏪 ID Tienda: **{st.session_state['id_tienda']}** | 🔑 ID Rol: **{st.session_state['id_rol']}**")
    
    if st.session_state["vista_actual"] == "menu_principal":
        st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>Red Cooperativa de Mujeres de Occidente</h2>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("*📦* **Gestión de Inventarios** `Existencias, lotes y stock mínimo por tienda`", key="btn_inv", type="primary"):
                st.session_state["vista_actual"] = "inventario"
                st.rerun()
        with c2:
            if st.button("*✏️* **Catálogos y Registros** `Productos, clientes, proveedores y categorías`", key="btn_reg_info", type="primary"):
                st.session_state["vista_actual"] = "registra_info"
                st.rerun()
        with c3:
            if st.button("*💸* **Compras y Ventas** `Registra entradas de compra y salidas de venta`", key="btn_cv", type="primary"):
                st.session_state["vista_actual"] = "compra_venta"
                st.rerun()

        st.write("")
        espacio_izq, f1, f2, espacio_der = st.columns([0.5, 1, 1, 0.5])
        with f1:
            if st.button("*👑* **Administración** `Gestionar tiendas y cuentas de usuario`", key="btn_admin", type="primary"):
                if st.session_state["id_rol"] == 1:
                    st.session_state["vista_actual"] = "administracion"
                    st.rerun()
                else:
                    st.error("⛔ Acceso denegado. Solo el Administrador General puede gestionar cuentas.")
        with f2:
            if st.button("*📊* **Reportes y Consultas** `Movimientos y reportes por tienda o globales`", key="btn_rep", type="primary"):
                st.info("Módulo en construcción (Próxima fase).")

    elif st.session_state["vista_actual"] == "registra_info":
        st.markdown("<h3 style='text-align: center; margin-bottom: 25px;'>✏️ Catálogos y Registros</h3>", unsafe_allow_html=True)
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            if st.button("*📦* **Productos** `Administra el catálogo de productos`", key="sub_prod", type="primary"):
                st.session_state["vista_actual"] = "form_producto"
                st.rerun()
        with s2:
            if st.button("*🤝* **Clientes** `Registra clientes de la tienda`", key="sub_cli", type="primary"):
                st.session_state["vista_actual"] = "form_cliente"
                st.rerun()
        with s3:
            if st.button("*🚚* **Proveedores** `Registra proveedores de la tienda`", key="sub_prov", type="primary"):
                st.session_state["vista_actual"] = "form_proveedor"
                st.rerun()
        with s4:
            if st.button("*📁* **Categorías** `Clasificación común de productos`", key="sub_cat", type="primary"):
                st.session_state["vista_actual"] = "form_categoria"
                st.rerun()

    elif st.session_state["vista_actual"] == "compra_venta":
        st.markdown("<h3 style='text-align: center; margin-bottom: 25px;'>💸 Operaciones Comerciales</h3>", unsafe_allow_html=True)
        esp1, cv1, cv2, esp2 = st.columns([0.5, 1, 1, 0.5])
        with cv1:
            if st.button("*🛍️* **Registrar Venta** `Salida de productos a clientes o sucursales`", key="sub_venta", type="primary"):
                st.session_state["vista_actual"] = "form_venta"
                st.rerun()
        with cv2:
            if st.button("*📥* **Registrar Compra** `Entrada de mercadería de proveedores al inventario`", key="sub_compra", type="primary"):
                st.session_state["vista_actual"] = "form_compra"
                st.rerun()

    elif st.session_state["vista_actual"] == "administracion":
        mostrar_registro()
    elif st.session_state["vista_actual"] == "form_producto":
        mostrar_productos()
    elif st.session_state["vista_actual"] == "form_cliente":
        mostrar_clientes()
    elif st.session_state["vista_actual"] == "form_proveedor":
        mostrar_proveedores()
    elif st.session_state["vista_actual"] == "form_categoria":
        mostrar_categorias()
    elif st.session_state["vista_actual"] == "form_venta":
        mostrar_ventas()
    elif st.session_state["vista_actual"] == "form_compra":
        mostrar_compras()
    elif st.session_state["vista_actual"] == "inventario":
        mostrar_inventario()

    st.markdown("<br>", unsafe_allow_html=True)
    formularios_catalogo = ["form_producto", "form_cliente", "form_proveedor", "form_categoria"]
    formularios_comerciales = ["form_venta", "form_compra"]
    
    if st.session_state["vista_actual"] in formularios_catalogo:
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("⬅️ Volver a Catálogos y Registros"):
                st.session_state["vista_actual"] = "registra_info"
                st.rerun()
        with col_nav2:
            if st.button("🏠 Volver al menú principal"):
                st.session_state["vista_actual"] = "menu_principal"
                st.rerun()
    elif st.session_state["vista_actual"] in formularios_comerciales:
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("⬅️ Volver a Compras y Ventas"):
                st.session_state["vista_actual"] = "compra_venta"
                st.rerun()
        with col_nav2:
            if st.button("🏠 Volver al menú principal"):
                st.session_state["vista_actual"] = "menu_principal"
                st.rerun()
    elif st.session_state["vista_actual"] != "menu_principal":
        if st.button("🏠 Volver al menú principal"):
            st.session_state["vista_actual"] = "menu_principal"
            st.rerun()
            
    if st.button("🚪 Cerrar sesión"):
        st.session_state["sesion_iniciada"] = False
        st.session_state["vista_actual"] = "menu_principal"
        st.rerun()
