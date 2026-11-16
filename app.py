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

# CSS que transforma los botones de las tarjetas en cuadros grandes interactivos
st.markdown("""
    <style>
    @keyframes rebotar {
        0%, 100% { transform: translateY(0); }
        40% { transform: translateY(-8px); }
        70% { transform: translateY(-3px); }
    }
    /* Estilo por defecto para botones normales (navegación inferior y formularios) */
    div.stButton > button {
        background-color: #13294B;
        color: white;
        width: 100%;
        border-radius: 8px;
        border: none;
        padding: 10px 15px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #1e3f73;
        color: white;
    }
    /* Transformar en TARJETA GRANDE cualquier botón dentro de las columnas del menú */
    div[data-testid="stHorizontalBlock"] div.stButton > button {
        background-color: #f8f9fa;
        color: #1f2937;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 28px 15px;
        min-height: 175px;
        white-space: pre-line;
        line-height: 1.5;
        box-shadow: 0 2px 5px rgba(0,0,0,0.04);
    }
    /* Primera línea del texto del botón (el Emoji) se hace grande */
    div[data-testid="stHorizontalBlock"] div.stButton > button p {
        font-size: 14px;
        color: #6b7280;
    }
    div[data-testid="stHorizontalBlock"] div.stButton > button p::first-line {
        font-size: 38px;
        font-weight: bold;
        color: #13294B;
    }
    /* Efecto rebote y elevación al pasar el cursor sobre la tarjeta */
    div[data-testid="stHorizontalBlock"] div.stButton > button:hover {
        background-color: #ffffff;
        border-color: #13294B;
        box-shadow: 0 8px 16px rgba(19, 41, 75, 0.12);
        animation: rebotar 0.5s ease;
    }
    /* Excepción para los botones de navegación inferiores (que sigan siendo azul marino) */
    .nav-inferior div.stButton > button {
        background-color: #13294B !important;
        color: white !important;
        min-height: 42px !important;
        padding: 10px !important;
        animation: none !important;
    }
    .nav-inferior div.stButton > button p,
    .nav-inferior div.stButton > button p::first-line {
        font-size: 15px !important;
        color: white !important;
        font-weight: 500 !important;
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
    
    # --- VISTA 1: MENÚ PRINCIPAL (Tarjetas completas presionables) ---
    if st.session_state["vista_actual"] == "menu_principal":
        st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>Red Cooperativa de Mujeres de Occidente</h2>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📦\n**Gestión de Inventarios**\nExistencias, lotes y stock mínimo por tienda", key="btn_inv"):
                st.session_state["vista_actual"] = "inventario"
                st.rerun()
        with c2:
            if st.button("✏️\n**Catálogos y Registros**\nProductos, clientes, proveedores y categorías", key="btn_reg_info"):
                st.session_state["vista_actual"] = "registra_info"
                st.rerun()
        with c3:
            if st.button("💸\n**Compras y Ventas**\nRegistra entradas de compra y salidas de venta", key="btn_cv"):
                st.session_state["vista_actual"] = "compra_venta"
                st.rerun()

        st.write("")
        espacio_izq, f1, f2, espacio_der = st.columns([0.5, 1, 1, 0.5])
        with f1:
            if st.button("👑\n**Administración**\nGestionar tiendas y cuentas de usuario", key="btn_admin"):
                if st.session_state["id_rol"] == 1:
                    st.session_state["vista_actual"] = "administracion"
                    st.rerun()
                else:
                    st.error("⛔ Acceso denegado. Solo el Administrador General puede gestionar cuentas.")
        with f2:
            if st.button("📊\n**Reportes y Consultas**\nMovimientos y reportes por tienda o globales", key="btn_rep"):
                st.info("Módulo en construcción (Próxima fase).")

    # --- VISTA 2: SUBMENÚ CATÁLOGOS Y REGISTROS ---
    elif st.session_state["vista_actual"] == "registra_info":
        st.markdown("<h3 style='text-align: center; margin-bottom: 25px;'>✏️ Catálogos y Registros</h3>", unsafe_allow_html=True)
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            if st.button("📦\n**Productos**\nAdministra el catálogo de productos", key="sub_prod"):
                st.session_state["vista_actual"] = "form_producto"
                st.rerun()
        with s2:
            if st.button("🤝\n**Clientes**\nRegistra clientes de la tienda", key="sub_cli"):
                st.session_state["vista_actual"] = "form_cliente"
                st.rerun()
        with s3:
            if st.button("🚚\n**Proveedores**\nRegistra proveedores de la tienda", key="sub_prov"):
                st.session_state["vista_actual"] = "form_proveedor"
                st.rerun()
        with s4:
            if st.button("📁\n**Categorías**\nClasificación común de productos", key="sub_cat"):
                st.session_state["vista_actual"] = "form_categoria"
                st.rerun()

    # --- VISTA 3: SUBMENÚ COMPRAS Y VENTAS ---
    elif st.session_state["vista_actual"] == "compra_venta":
        st.markdown("<h3 style='text-align: center; margin-bottom: 25px;'>💸 Operaciones Comerciales</h3>", unsafe_allow_html=True)
        cv1, cv2 = st.columns(2)
        with cv1:
            if st.button("🛍️\n**Registrar Venta**\nSalida de productos a clientes o sucursales", key="sub_venta"):
                st.session_state["vista_actual"] = "form_venta"
                st.rerun()
        with cv2:
            if st.button("📥\n**Registrar Compra**\nEntrada de mercadería de proveedores al inventario", key="sub_compra"):
                st.session_state["vista_actual"] = "form_compra"
                st.rerun()

    # --- VISTAS DE FORMULARIOS ---
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

    # --- BOTONES INFERIORES DE NAVEGACIÓN ---
    st.markdown('<div class="nav-inferior"><br>', unsafe_allow_html=True)
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
