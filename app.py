import streamlit as st
from modulos.login import login
from modulos.categorias import mostrar_categorias
from modulos.productos import mostrar_productos
from modulos.proveedores import mostrar_proveedores
from modulos.registro import mostrar_registro  # Ahora vive dentro de Administración

# Configuración de página ancha para que luzcan las tarjetas en columnas
st.set_page_config(page_title="Red Cooperativa de Mujeres de Occidente", layout="wide")

# Estilos CSS personalizados para imitar el diseño de tarjetas y botones azul oscuro
st.markdown("""
    <style>
    .tarjeta {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 25px 15px;
        text-align: center;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    .emoji-grande {
        font-size: 42px;
        margin-bottom: 10px;
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

# Si no ha iniciado sesión, mostrar únicamente el Login (Sin opción de registro público)
if not st.session_state["sesion_iniciada"]:
    login()
else:
    # Encabezado discreto con datos del usuario autenticado
    col_info1, col_info2 = st.columns([4, 1])
    with col_info1:
        st.caption(f"👤 Usuario: **{st.session_state['nombre_completo']}** | 🏪 ID Tienda asignada: **{st.session_state['id_tienda']}** | 🔑 ID Rol: **{st.session_state['id_rol']}**")
    
    # --- VISTA 1: MENÚ PRINCIPAL (Como tu primera foto) ---
    if st.session_state["vista_actual"] == "menu_principal":
        st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>Red Cooperativa de Mujeres de Occidente</h2>", unsafe_allow_html=True)
        
        # Primera fila de 3 tarjetas
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">📦</div><div class="titulo-tarjeta">Inventario Global</div><div class="desc-tarjeta">Ver inventario de las tiendas</div></div>', unsafe_allow_html=True)
            if st.button("📋 Ver inventario", key="btn_inv"):
                st.session_state["vista_actual"] = "inventario"
                st.rerun()
        with c2:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">⚖️</div><div class="titulo-tarjeta">Comparativa de Costos</div><div class="desc-tarjeta">Comparar precios unitarios entre tiendas</div></div>', unsafe_allow_html=True)
            if st.button("💲 Ver comparativa", key="btn_comp"):
                st.info("Módulo en construcción (Próxima fase).")
        with c3:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">📈</div><div class="titulo-tarjeta">Pronósticos y Reorden</div><div class="desc-tarjeta">Rotación, cobertura y compras sugeridas</div></div>', unsafe_allow_html=True)
            if st.button("📊 Ver pronósticos", key="btn_pron"):
                st.info("Módulo en construcción (Próxima fase).")

        st.write("") # Espacio entre filas

        # Segunda fila de 4 tarjetas
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">👑</div><div class="titulo-tarjeta">Administración</div><div class="desc-tarjeta">Gestionar tiendas y usuarios</div></div>', unsafe_allow_html=True)
            if st.button("⚙️ Gestionar", key="btn_admin"):
                # Validación de rol: Supongamos que id_rol == 1 es Administrador General
                if st.session_state["id_rol"] == 1:
                    st.session_state["vista_actual"] = "administracion"
                    st.rerun()
                else:
                    st.error("⛔ Acceso denegado. Solo el Administrador General puede crear cuentas o tiendas.")
        with f2:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">✏️</div><div class="titulo-tarjeta">Registra información</div><div class="desc-tarjeta">Registra productos, proveedores y categorías</div></div>', unsafe_allow_html=True)
            if st.button("📝 Ingresar información", key="btn_reg_info"):
                st.session_state["vista_actual"] = "registra_info"
                st.rerun()
        with f3:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">💸</div><div class="titulo-tarjeta">Compra y vende productos</div><div class="desc-tarjeta">Registra tus compras y ventas diarias</div></div>', unsafe_allow_html=True)
            if st.button("🛒 Comprar/Vender", key="btn_cv"):
                st.session_state["vista_actual"] = "compra_venta"
                st.rerun()
        with f4:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">📊</div><div class="titulo-tarjeta">Reportes Globales</div><div class="desc-tarjeta">Reportes de ventas de las tiendas</div></div>', unsafe_allow_html=True)
            if st.button("📑 Ver reportes", key="btn_rep"):
                st.info("Módulo en construcción (Próxima fase).")

    # --- VISTA 2: SUBMENÚ REGISTRA INFORMACIÓN (Como tu segunda foto) ---
    elif st.session_state["vista_actual"] == "registra_info":
        st.markdown("<h3 style='text-align: center; margin-bottom: 25px;'>✏️ Registra información</h3>", unsafe_allow_html=True)
        
        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">📦</div><div class="titulo-tarjeta">Nuevo Producto</div><div class="desc-tarjeta">Registra productos en el catálogo</div></div>', unsafe_allow_html=True)
            if st.button("Agregar", key="sub_prod"):
                st.session_state["vista_actual"] = "form_producto"
                st.rerun()
        with s2:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">🚚</div><div class="titulo-tarjeta">Nuevo Proveedor</div><div class="desc-tarjeta">Registra proveedores de la tienda</div></div>', unsafe_allow_html=True)
            if st.button("Registrar", key="sub_prov"):
                st.session_state["vista_actual"] = "form_proveedor"
                st.rerun()
        with s3:
            st.markdown('<div class="tarjeta"><div class="emoji-grande">📁</div><div class="titulo-tarjeta">Gestionar Categorías</div><div class="desc-tarjeta">Administra categorías de productos</div></div>', unsafe_allow_html=True)
            if st.button("Gestionar", key="sub_cat"):
                st.session_state["vista_actual"] = "form_categoria"
                st.rerun()

    # --- VISTAS DE FORMULARIOS ESPECÍFICOS ---
    elif st.session_state["vista_actual"] == "administracion":
        mostrar_registro() # Aquí el Admin crea cuentas y asigna tiendas
    elif st.session_state["vista_actual"] == "form_producto":
        mostrar_productos()
    elif st.session_state["vista_actual"] == "form_proveedor":
        mostrar_proveedores()
    elif st.session_state["vista_actual"] == "form_categoria":
        mostrar_categorias()
    elif st.session_state["vista_actual"] in ["inventario", "compra_venta"]:
        st.warning("🚧 Aún nos falta crear las tablas de Compras, Ventas e Inventario en phpMyAdmin para habilitar esta pantalla.")

    # --- BOTONES INFERIORES DE NAVEGACIÓN (Igual a las fotos) ---
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state["vista_actual"] != "menu_principal":
        if st.button("⬅️ Volver al menú principal"):
            st.session_state["vista_actual"] = "menu_principal"
            st.rerun()
            
    if st.button("🚪 Cerrar sesión"):
        st.session_state["sesion_iniciada"] = False
        st.session_state["vista_actual"] = "menu_principal"
        st.rerun()
