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
    @keyframes rebotar { 0%, 100% { transform: translateY(0); } 40% { transform: translateY(-8px); } 70% { transform: translateY(-3px); } }
    div.stButton > button { background-color: #13294B; color: white; width: 100%; border-radius: 8px; border: none; padding: 10px 15px; font-weight: 500; transition: all 0.2s ease; }
    div.stButton > button:hover { background-color: #1e3f73; color: white; }
    div[data-testid="stHorizontalBlock"] div.stButton > button { background-color: #f8f9fa; color: #1f2937; border: 1px solid #d1d5db; border-radius: 12px; padding: 22px 15px; height: 190px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.04); }
    div[data-testid="stHorizontalBlock"] div.stButton > button > div { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; }
    div[data-testid="stHorizontalBlock"] div.stButton > button p:nth-of-type(1) { font-size: 44px; line-height: 1.2; margin-bottom: 8px; }
    div[data-testid="stHorizontalBlock"] div.stButton > button p:nth-of-type(2) { font-size: 17px; font-weight: bold; color: #111827; margin-bottom: 4px; white-space: normal; }
    div[data-testid="stHorizontalBlock"] div.stButton > button p:nth-of-type(3) { font-size: 13px; color: #6b7280; line-height: 1.3; white-space: normal; }
    div[data-testid="stHorizontalBlock"] div.stButton > button:hover { background-color: #ffffff; border-color: #13294B; box-shadow: 0 8px 16px rgba(19, 41, 75, 0.12); animation: rebotar 0.5s ease; }
    .boton-normal div.stButton > button { background-color: #13294B !important; color: white !important; height: auto !important; min-height: 42px !important; padding: 10px 15px !important; animation: none !important; }
    .boton-normal div.stButton > button p { font-size: 15px !important; color: white !important; margin: 0 !important; }
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
            if st.button("📦\n\nGestión de Inventarios\n\nExistencias, lotes y stock mínimo por tienda", key="btn_inv"):
                st.session_state["vista_actual"] = "inventario"
                st.rerun()
        with c2:
            if st.button("✏️\n\nCatálogos y Registros\n\nProductos, clientes, proveedores y categorías", key="btn_reg_info"):
                st.session_state["vista_actual"] = "registra_info"
                st.rerun()
        with c3:
            if st.button("💸\n\nCompras y Ventas\n\nRegistra entradas de compra y salidas de venta", key="btn_cv"):
                st.session_state["vista_actual"] = "compra_venta"
                st.rerun()

        st.write("")
        espacio_izq, f1, f2, espacio_der = st.columns([0.5, 1, 1, 0.5])
        with f1:
            if st.button("👑\n\nAdministración\n\nGestionar tiendas y cuentas de usuario", key="btn_admin"):
                if st.session_state["id_rol"] == 1:
                    st.session_state["vista_actual"] = "administracion"
                    st.rerun()
                else:
                    st.error("⛔ Acceso denegado. Solo el Administrador General puede gestionar cuentas.")
        with f2:
            if st.button("📊\n\nReportes y Consultas\n\nMovimientos y reportes por tienda o globales", key="btn_rep"):
                st.info("Módulo en construcción (Próxima fase).")

    elif st.session_state["vista_actual"] == "registra_info":
        st.markdown("<h3 style='text-align: center; margin-bottom: 25px;'>✏️ Catálogos y Registros</h3>", unsafe_allow_html=True)
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            if st.button("📦\n\nProductos\n\nAdministra el catálogo de productos", key="sub_prod"):
                st.session_state["vista_actual"] = "form_producto"
                st.rerun()
        with s2:
            if st.button("🤝\n\nClientes\n\nRegistra clientes de la tienda", key="sub_cli"):
                st.session_state["vista_actual"] = "form_cliente"
                st.rerun()
        with s3:
            if st.button("🚚\n\nProveedores\n\nRegistra proveedores de la tienda", key="sub_prov"):
                st.session_state["vista_actual"] = "form_proveedor"
                st.rerun()
        with s4:
            if st.button("📁\n\nCategorías\n\nClasificación común de productos", key="sub_cat"):
                st.session_state["vista_actual"] = "form_categoria"
                st.rerun()

    elif st.session_state["vista_actual"] == "compra_venta":
        st.markdown("<h3 style='text-align: center; margin-bottom: 25px;'>💸 Operaciones Comerciales</h3>", unsafe_allow_html=True)
        cv1, cv2 = st.columns(2)
        with cv1:
            if st.button("🛍️\n\nRegistrar Venta\n\nSalida de productos a clientes o sucursales", key="sub_venta"):
                st.session_state["vista_actual"] = "form_venta"
                st.rerun()
        with cv2:
            if st.button("📥\n\nRegistrar Compra\n\nEntrada de mercadería de proveedores al inventario", key="sub_compra"):
                st.session_state["vista_actual"] = "form_compra"
                st.rerun()

    elif st.session_state["vista_actual"] == "administracion":
        st.markdown('<div class="boton-normal">', unsafe_allow_html=True)
        mostrar_registro()
        st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state["vista_actual"] == "form_producto":
        st.markdown('<div class="boton-normal">', unsafe_allow_html=True)
        mostrar_productos()
        st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state["vista_actual"] == "form_cliente":
        st.markdown('<div class="boton-normal">', unsafe_allow_html=True)
        mostrar_clientes()
        st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state["vista_actual"] == "form_proveedor":
        st.markdown('<div class="boton-normal">', unsafe_allow_html=True)
        mostrar_proveedores()
        st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state["vista_actual"] == "form_categoria":
        st.markdown('<div class="boton-normal">', unsafe_allow_html=True)
        mostrar_categorias()
        st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state["vista_actual"] == "form_venta":
        st.markdown('<div class="boton-normal">', unsafe_allow_html=True)
        mostrar_ventas()
        st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state["vista_actual"] == "form_compra":
        st.markdown('<div class="boton-normal">', unsafe_allow_html=True)
        mostrar_compras()
        st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state["vista_actual"] == "inventario":
        st.markdown('<div class="boton-normal">', unsafe_allow_html=True)
        mostrar_inventario()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="boton-normal"><br>', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)
