import streamlit as st
from config.conexion import obtener_conexion

def formatear_dui_nit(valor):
    # Extrae solo los números ingresados por el usuario
    solo_numeros = "".join(filter(str.isdigit, valor))
    
    if len(solo_numeros) == 0:
        return "", True  # Es válido porque el documento es opcional
    elif len(solo_numeros) == 9:
        # Formato DUI: 00000000-0 (10 caracteres)
        return f"{solo_numeros[:8]}-{solo_numeros[8]}", True
    elif len(solo_numeros) == 14:
        # Formato NIT: 0000-000000-000-0 (17 caracteres)
        return f"{solo_numeros[:4]}-{solo_numeros[4:10]}-{solo_numeros[10:13]}-{solo_numeros[13]}", True
    else:
        return valor, False

def formatear_telefono(valor):
    solo_numeros = "".join(filter(str.isdigit, valor))
    
    if len(solo_numeros) == 0:
        return "", True  # Opcional
    elif len(solo_numeros) == 8:
        # Formato Teléfono: 0000-0000 (9 caracteres)
        return f"{solo_numeros[:4]}-{solo_numeros[4:]}", True
    else:
        return valor, False

def mostrar_proveedores():
    st.header("🚚 Gestión de Proveedores")
    st.caption("Puedes escribir los números sin guiones; el sistema los agregará automáticamente al guardar.")
    
    with st.form("form_proveedor"):
        nombre = st.text_input("Nombre o Razón Social *")
        tipo = st.selectbox("Tipo de Proveedor", ["Persona Natural", "Empresa", "Cooperativa", "Otro"])
        dui_nit_raw = st.text_input("DUI (9 dígitos) o NIT (14 dígitos) - Opcional", max_chars=17)
        telefono_raw = st.text_input("Teléfono (8 dígitos) - Opcional", max_chars=9)
        guardar = st.form_submit_button("Guardar Proveedor")
        
    if guardar:
        if not nombre.strip():
            st.warning("⚠️ El nombre del proveedor es obligatorio.")
            return
            
        dui_nit_formateado, doc_valido = formatear_dui_nit(dui_nit_raw)
        tel_formateado, tel_valido = formatear_telefono(telefono_raw)
        
        if not doc_valido:
            st.error("❌ El DUI debe tener 9 dígitos o el NIT 14 dígitos.")
            return
        if not tel_valido:
            st.error("❌ El número de teléfono debe tener exactamente 8 dígitos.")
            return

        conexion = obtener_conexion()
        if conexion:
            try:
                cursor = conexion.cursor()
                consulta = """
                    INSERT INTO Proveedor (Nombre, Tipo, DUI_NIT, Telefono)
                    VALUES (%s, %s, %s, %s)
                """
                # Si quedan vacíos se guardan como None (NULL en MySQL)
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
