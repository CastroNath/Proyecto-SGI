import streamlit as st
from modulos.login import login
from modulos.categorias import mostrar_categorias
from modulos.productos import mostrar_productos
from modulos.proveedores import mostrar_proveedores
from modulos.clientes import mostrar_clientes
from modulos.registro import mostrar_registro

# Configuración de página ancha
st.set_page_config(page_title="Red Cooperativa de Mujeres de Occidente", layout="wide")

# Estilos CSS personalizados con animación de rebote en los emojis
st.markdown("""
    <style>
    @keyframes flotar {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-5px); }
    }
    @keyframes rebotar {
        0%, 100% { transform: scale(1) translateY(0); }
        40% { transform: scale(1.2) translateY(-10px); }
        60% { transform: scale(1.1) translateY(-4px); }
    }
    .tarjeta {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 25px 15px;
        text-align: center;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .tarjeta:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.08);
        border-color: #13294B;
    }
    .emoji-grande {
        font-size: 42px;
        margin-bottom: 10px;
        display: inline-block;
        animation: flotar 3s ease-in-out infinite;
    }
    .tarjeta:hover .emoji-grande {
        animation: rebotar 0.6s ease;
    }
    .titulo-tarjeta {
        font-size: 18px;
        font-weight: bold;
        color: #1f2937;
        margin-bottom: 5px;
    }
    .desc-tarjeta {
        font-size: 13px;
        color: #6b7280;
        margin-bottom: 15px;
    }
    div.stButton > button {
        background-color: #13294B;
        color: white;
        width: 100%;
        border-radius: 6px;
        border: none;
        padding: 10px;
        font-weight: 500;
    }
    div.stButton > button:hover {
        background-color: #1e3f73;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# Inicializar variables de sesión y navegación
if "sesion_iniciada" not in st.session_state:
    st.session_state["sesion_iniciada"] = False
if "vista_actual" not in st.session_state:
    st.session_state["vista_actual"] = "menu_principal"

# Si no ha iniciado sesión, mostrar únicamente el Login
if not st.session_state["sesion_iniciada"]:
    login()
else:
    # Encabezado discreto con datos del usuario autenticado
    col_info1, col_info2 = st.columns([4, 1])
    with col_info1:
        st.caption(f"👤 Usuario: **{st.session_state['nombre_completo']}** | 🏪 ID Tienda asignada: **{st.session_state['id_tienda']}** | 🔑 ID Rol: **{st.session_state['id_rol']}**")
    
    # --- VISTA 1: MENÚ PRINCIPAL (5 módulos alineados al DFD) ---
    if st.session_state["vista_actual"] == "menu_principal":
        st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>Red Cooperativa de Mujeres de Occidente</h2>", unsafe_allow_html=True)
        
        # Primera fila de 3 tarjetas
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">📦</div><div class="titulo-tarjeta">Gestión de Inventarios</div><div class="desc-tarjeta">Existencias, lotes y stock mínimo por tienda</div></div>', unsafe_allow_html=True)
            if st.button("📋 Ver inventario", key="btn_inv"):
                st.session_state["vista_actual"] = "inventario"
                st.rerun()
        with c2:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">✏️</div><div class="titulo-tarjeta">Catálogos y Registros</div><div class="desc-tarjeta">Productos, clientes, proveedores y categorías</div></div>', unsafe_allow_html=True)
            if st.button("📝 Gestionar catálogos", key="btn_reg_info"):
                st.session_state["vista_actual"] = "registra_info"
                st.rerun()
        with c3:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">💸</div><div class="titulo-tarjeta">Compras y Ventas</div><div class="desc-tarjeta">Registra entradas de compra y salidas de venta</div></div>', unsafe_allow_html=True)
            if st.button("🛒 Comprar / Vender", key="btn_cv"):
                st.session_state["vista_actual"] = "compra_venta"
                st.rerun()

        st.write("") # Espacio entre filas

        # Segunda fila centrada de 2 tarjetas
        espacio_izq, f1, f2, espacio_der = st.columns([0.5, 1, 1, 0.5])
        with f1:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">👑</div><div class="titulo-tarjeta">Administración</div><div class="desc-tarjeta">Gestionar tiendas y cuentas de usuario</div></div>', unsafe_allow_html=True)
            if st.button("⚙️ Gestionar", key="btn_admin"):
                if st.session_state["id_rol"] == 1:
                    st.session_state["vista_actual"] = "administracion"
                    st.rerun()
                else:
                    st.error("⛔ Acceso denegado. Solo el Administrador General puede gestionar cuentas.")
        with f2:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">📊</div><div class="titulo-tarjeta">Reportes y Consultas</div><div class="desc-tarjeta">Movimientos y reportes por tienda o globales</div></div>', unsafe_allow_html=True)
            if st.button("📑 Ver reportes", key="btn_rep"):
                st.info("Módulo en construcción (Próxima fase).")

    # --- VISTA 2: SUBMENÚ CATÁLOGOS Y REGISTROS (4 tarjetas: Producto, Cliente, Proveedor, Categoría) ---
    elif st.session_state["vista_actual"] == "registra_info":
        st.markdown("<h3 style='text-align: center; margin-bottom: 25px;'>✏️ Catálogos y Registros</h3>", unsafe_allow_html=True)
        
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">📦</div><div class="titulo-tarjeta">Productos</div><div class="desc-tarjeta">Administra el catálogo de productos</div></div>', unsafe_allow_html=True)
            if st.button("Agregar Producto", key="sub_prod"):
                st.session_state["vista_actual"] = "form_producto"
                st.rerun()
        with s2:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">🤝</div><div class="titulo-tarjeta">Clientes</div><div class="desc-tarjeta">Registra clientes de la tienda</div></div>', unsafe_allow_html=True)
            if st.button("Agregar Cliente", key="sub_cli"):
                st.session_state["vista_actual"] = "form_cliente"
                st.rerun()
        with s3:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">🚚</div><div class="titulo-tarjeta">Proveedores</div><div class="desc-tarjeta">Registra proveedores de la tienda</div></div>', unsafe_allow_html=True)
            if st.button("Agregar Proveedor", key="sub_prov"):
                st.session_state["vista_actual"] = "form_proveedor"
                st.rerun()
        with s4:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">📁</div><div class="titulo-tarjeta">Categorías</div><div class="desc-tarjeta">Clasificación común de productos</div></div>', unsafe_allow_html=True)
            if st.button("Gestionar Categorías", key="sub_cat"):
                st.session_state["vista_actual"] = "form_categoria"
                st.rerun()

    # --- VISTAS DE FORMULARIOS ESPECÍFICOS ---
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
    elif st.session_state["vista_actual"] in ["inventario", "compra_venta"]:
        st.warning("🚧 Aún nos falta crear las tablas de Compras, Ventas e Inventario en phpMyAdmin para habilitar esta pantalla.")

    # --- BOTONES INFERIORES DE NAVEGACIÓN ---
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state["vista_actual"] != "menu_principal":
        if st.button("⬅️ Volver al menú principal"):
            st.session_state["vista_actual"] = "menu_principal"
            st.rerun()
            
    if st.button("🚪 Cerrar sesión"):
        st.session_state["sesion_iniciada"] = False
        st.session_state["vista_actual"] = "menu_principal"
        st.rerun()
