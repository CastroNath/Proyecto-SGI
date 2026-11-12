 import streamlit as st
from config.conexion import obtener_conexion

# Funciones automáticas que acomodan los guiones en pantalla al escribir
def auto_formato_dui():
    raw = "".join(filter(str.isdigit, st.session_state.get("input_dui", "")))[:9]
    if len(raw) > 8:
        st.session_state["input_dui"] = f"{raw[:8]}-{raw[8:]}"
    else:
        st.session_state["input_dui"] = raw

def auto_formato_nit():
    raw = "".join(filter(str.isdigit, st.session_state.get("input_nit", "")))[:14]
    if len(raw) > 13:
        st.session_state["input_nit"] = f"{raw[:4]}-{raw[4:10]}-{raw[10:13]}-{raw[13:]}"
    elif len(raw) > 10:
        st.session_state["input_nit"] = f"{raw[:4]}-{raw[4:10]}-{raw[10:]}"
    elif len(raw) > 4:
        st.session_state["input_nit"] = f"{raw[:4]}-{raw[4:]}"
    else:
        st.session_state["input_nit"] = raw

def auto_formato_tel():
    raw = "".join(filter(str.isdigit, st.session_state.get("input_tel", "")))[:8]
    if len(raw) > 4:
        st.session_state["input_tel"] = f"{raw[:4]}-{raw[4:]}"
    else:
        st.session_state["input_tel"] = raw

# Funciones de validación final antes de guardar en MySQL
def validar_dui_nit(valor, tipo_doc):
    solo_numeros = "".join(filter(str.isdigit, valor))
    if tipo_doc == "Ninguno" or len(solo_numeros) == 0:
        return "", True
    elif tipo_doc == "DUI" and len(solo_numeros) == 9:
        return f"{solo_numeros[:8]}-{solo_numeros[8:]}", True
    elif tipo_doc == "NIT" and len(solo_numeros) == 14:
        return f"{solo_numeros[:4]}-{solo_numeros[4:10]}-{solo_numeros[10:13]}-{solo_numeros[13:]}", True
    return valor, False

def validar_telefono(valor):
    solo_numeros = "".join(filter(str.isdigit, valor))
    if len(solo_numeros) == 0:
        return "", True
    elif len(solo_numeros) == 8:
        return f"{solo_numeros[:4]}-{solo_numeros[4:]}", True
    return valor, False

def mostrar_proveedores():
    st.header("🚚 Gestión de Proveedores")
    
    nombre = st.text_input("Nombre o Razón Social")
    tipo = st.selectbox("Tipo de Proveedor", ["Persona Natural", "Empresa", "Cooperativa", "Otro"])
    
    tipo_doc = st.radio(
        "Documento de Identificación",
        ["Ninguno", "DUI", "NIT"],
        horizontal=True
    )
    
    dui_nit_raw = ""
    if tipo_doc == "DUI":
        dui_nit_raw = st.text_input(
            "Número de DUI",
            max_chars=10,
            placeholder="00000000-0",
            key="input_dui",
            on_change=auto_formato_dui
        )
    elif tipo_doc == "NIT":
        dui_nit_raw = st.text_input(
            "Número de NIT",
            max_chars=17,
            placeholder="0000-000000-000-0",
            key="input_nit",
            on_change=auto_formato_nit
        )
        
    telefono_raw = st.text_input(
        "Teléfono",
        max_chars=9,
        placeholder="0000-0000",
        key="input_tel",
        on_change=auto_formato_tel
    )

    if st.button("Guardar Proveedor"):
        if not nombre.strip():
            st.warning("⚠️ El nombre del proveedor es obligatorio.")
            return
            
        dui_nit_formateado, doc_valido = validar_dui_nit(dui_nit_raw, tipo_doc)
        tel_formateado, tel_valido = validar_telefono(telefono_raw)
        
        if not doc_valido:
            st.error(f"❌ El {tipo_doc} ingresado está incompleto.")
            return
        if not tel_valido:
            st.error("❌ El número de teléfono debe tener 8 dígitos.")
            return

        conexion = obtener_conexion()
        if conexion:
            try:
                cursor = conexion.cursor()
                consulta = """
                    INSERT INTO Proveedor (Nombre, Tipo, DUI_NIT, Telefono)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(consulta, (
                    nombre.strip(),
                    tipo,
                    dui_nit_formateado if dui_nit_formateado else None,
                    tel_formateado if tel_formateado else None
                ))
                conexion.commit()
                st.success(f"✅ Proveedor '{nombre.strip()}' registrado correctamente.")
            except Exception as e:
                st.error(f"Error al registrar proveedor: {e}")
            finally:
                cursor.close()
                conexion.close()
