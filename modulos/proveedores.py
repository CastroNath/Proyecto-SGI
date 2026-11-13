import streamlit as st
from config.conexion import obtener_conexion

def limpiar_y_formatear_dui():
    texto_actual = st.session_state.get("input_dui", "")
    solo_num = "".join(filter(str.isdigit, texto_actual))
    if len(solo_num) > 9:
        st.session_state["alerta_dui"] = "⚠️ El DUI solo permite 9 dígitos. Se ajustó al límite."
        solo_num = solo_num[:9]
    else:
        st.session_state["alerta_dui"] = ""
        
    if len(solo_num) > 8:
        st.session_state["input_dui"] = f"{solo_num[:8]}-{solo_num[8:]}"
    else:
        st.session_state["input_dui"] = solo_num

def limpiar_y_formatear_nit():
    texto_actual = st.session_state.get("input_nit", "")
    solo_num = "".join(filter(str.isdigit, texto_actual))
    if len(solo_num) > 14:
        st.session_state["alerta_nit"] = "⚠️ El NIT solo permite 14 dígitos. Se ajustó al límite."
        solo_num = solo_num[:14]
    else:
        st.session_state["alerta_nit"] = ""
        
    if len(solo_num) > 13:
        st.session_state["input_nit"] = f"{solo_num[:4]}-{solo_num[4:10]}-{solo_num[10:13]}-{solo_num[13:]}"
    elif len(solo_num) > 10:
        st.session_state["input_nit"] = f"{solo_num[:4]}-{solo_num[4:10]}-{solo_num[10:]}"
    elif len(solo_num) > 4:
        st.session_state["input_nit"] = f"{solo_num[:4]}-{solo_num[4:]}"
    else:
        st.session_state["input_nit"] = solo_num

def limpiar_y_formatear_tel():
    texto_actual = st.session_state.get("input_tel", "")
    solo_num = "".join(filter(str.isdigit, texto_actual))
    if len(solo_num) > 8:
        st.session_state["alerta_tel"] = "⚠️ El teléfono en El Salvador solo tiene 8 dígitos."
        solo_num = solo_num[:8]
    else:
        st.session_state["alerta_tel"] = ""
        
    if len(solo_num) > 4:
        st.session_state["input_tel"] = f"{solo_num[:4]}-{solo_num[4:]}"
    else:
        st.session_state["input_tel"] = solo_num

def mostrar_proveedores():
    st.header("🚚 Gestión de Proveedores")
    
    nombre = st.text_input("Nombre o Razón Social")
    tipo = st.selectbox("Tipo de Proveedor", ["Persona Natural", "Empresa", "Cooperativa", "Otro"])
    
    # Regla de negocio: Solo las personas naturales pueden registrar DUI
    opciones_doc = ["Ninguno", "DUI", "NIT"] if tipo == "Persona Natural" else ["Ninguno", "NIT"]
        
    tipo_doc = st.radio(
        "Documento de Identificación",
        opciones_doc,
        horizontal=True
    )
    
    dui_nit_raw = ""
    if tipo_doc == "DUI":
        # Tope dinámico: 9 caracteres si aún no tiene guion, 10 cuando ya tiene guion
        tope_dui = 10 if "-" in st.session_state.get("input_dui", "") else 9
        dui_nit_raw = st.text_input(
            "Número de DUI",
            max_chars=tope_dui,
            placeholder="00000000-0",
            key="input_dui",
            on_change=limpiar_y_formatear_dui
        )
        if st.session_state.get("alerta_dui"):
            st.caption(st.session_state["alerta_dui"])
            
    elif tipo_doc == "NIT":
        tope_nit = 17 if "-" in st.session_state.get("input_nit", "") else 14
        dui_nit_raw = st.text_input(
            "Número de NIT",
            max_chars=tope_nit,
            placeholder="0000-000000-000-0",
            key="input_nit",
            on_change=limpiar_y_formatear_nit
        )
        if st.session_state.get("alerta_nit"):
            st.caption(st.session_state["alerta_nit"])
        
    # Tope dinámico: 8 caracteres si aún no tiene guion, 9 cuando ya tiene guion
    tope_tel = 9 if "-" in st.session_state.get("input_tel", "") else 8
    telefono_raw = st.text_input(
        "Teléfono",
        max_chars=tope_tel,
        placeholder="0000-0000",
        key="input_tel",
        on_change=limpiar_y_formatear_tel
    )
    if st.session_state.get("alerta_tel"):
        st.caption(st.session_state["alerta_tel"])

    if st.button("Guardar Proveedor"):
        if not nombre.strip():
            st.warning("⚠️ El nombre del proveedor es obligatorio.")
            return
            
        # Validación final de longitudes exactas
        num_doc = "".join(filter(str.isdigit, dui_nit_raw))
        num_tel = "".join(filter(str.isdigit, telefono_raw))
        
        if tipo_doc == "DUI" and len(num_doc) != 9:
            st.error("❌ El DUI debe tener exactamente 9 dígitos.")
            return
        if tipo_doc == "NIT" and len(num_doc) != 14:
            st.error("❌ El NIT debe tener exactamente 14 dígitos.")
            return
        if len(num_tel) > 0 and len(num_tel) != 8:
            st.error("❌ El número de teléfono debe tener exactamente 8 dígitos.")
            return

        # Formateo garantizado antes de insertar
        doc_final = None
        if tipo_doc == "DUI" and len(num_doc) == 9:
            doc_final = f"{num_doc[:8]}-{num_doc[8:]}"
        elif tipo_doc == "NIT" and len(num_doc) == 14:
            doc_final = f"{num_doc[:4]}-{num_doc[4:10]}-{num_doc[10:13]}-{num_doc[13:]}"
            
        tel_final = f"{num_tel[:4]}-{num_tel[4:]}" if len(num_tel) == 8 else None

        conexion = obtener_conexion()
        if conexion:
            try:
                cursor = conexion.cursor()
                consulta = """
                    INSERT INTO Proveedor (Nombre, Tipo, DUI_NIT, Telefono)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(consulta, (nombre.strip(), tipo, doc_final, tel_final))
                conexion.commit()
                st.success(f"✅ Proveedor '{nombre.strip()}' registrado correctamente.")
            except Exception as e:
                st.error(f"Error al registrar proveedor: {e}")
            finally:
                cursor.close()
                conexion.close()
