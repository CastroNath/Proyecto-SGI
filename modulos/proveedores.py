import streamlit as st
import streamlit.components.v1 as components
from config.conexion import obtener_conexion

def formatear_dui_nit(valor, tipo_doc):
    solo_numeros = "".join(filter(str.isdigit, valor))
    
    if tipo_doc == "Ninguno" or len(solo_numeros) == 0:
        return "", True
    elif tipo_doc == "DUI":
        if len(solo_numeros) == 9:
            return f"{solo_numeros[:8]}-{solo_numeros[8:]}", True
        return valor, False
    elif tipo_doc == "NIT":
        if len(solo_numeros) == 14:
            return f"{solo_numeros[:4]}-{solo_numeros[4:10]}-{solo_numeros[10:13]}-{solo_numeros[13:]}", True
        return valor, False
    return valor, False

def formatear_telefono(valor):
    solo_numeros = "".join(filter(str.isdigit, valor))
    
    if len(solo_numeros) == 0:
        return "", True
    elif len(solo_numeros) == 8:
        return f"{solo_numeros[:4]}-{solo_numeros[4:]}", True
    else:
        return valor, False

def mostrar_proveedores():
    st.header("🚚 Gestión de Proveedores")
    
    nombre = st.text_input("Nombre o Razón Social *")
    tipo = st.selectbox("Tipo de Proveedor", ["Persona Natural", "Empresa", "Cooperativa", "Otro"])
    
    # Pestaña selectora para evitar que ingresen ambos documentos y ajustar el límite exacto
    tipo_doc = st.radio(
        "Documento de Identificación (Opcional):",
        ["Ninguno", "DUI", "NIT"],
        horizontal=True
    )
    
    dui_nit_raw = ""
    if tipo_doc == "DUI":
        dui_nit_raw = st.text_input("Número de DUI (9 dígitos)", max_chars=10, placeholder="00000000-0")
    elif tipo_doc == "NIT":
        dui_nit_raw = st.text_input("Número de NIT (14 dígitos)", max_chars=17, placeholder="0000-000000-000-0")
        
    telefono_raw = st.text_input("Teléfono (8 dígitos - Opcional)", max_chars=9, placeholder="0000-0000")
    
    # Script en vivo para poner los guiones automáticamente mientras el usuario teclea
    components.html("""
        <script>
        const doc = window.parent.document;
        setTimeout(() => {
            const inputs = doc.querySelectorAll('input[type="text"]');
            inputs.forEach(input => {
                if (input.dataset.mascaraActiva) return;
                input.dataset.mascaraActiva = "true";
                
                input.addEventListener('input', function(e) {
                    const max = this.getAttribute('maxlength');
                    let val = this.value.replace(/\\D/g, '');
                    
                    if (max === '10') { // Máscara DUI: 00000000-0
                        if (val.length > 8) val = val.slice(0,8) + '-' + val.slice(8,9);
                    } else if (max === '17') { // Máscara NIT: 0000-000000-000-0
                        if (val.length > 13) val = val.slice(0,4) + '-' + val.slice(4,10) + '-' + val.slice(10,13) + '-' + val.slice(13,14);
                        else if (val.length > 10) val = val.slice(0,4) + '-' + val.slice(4,10) + '-' + val.slice(10,13);
                        else if (val.length > 4) val = val.slice(0,4) + '-' + val.slice(4,10);
                    } else if (max === '9') { // Máscara Teléfono: 0000-0000
                        if (val.length > 4) val = val.slice(0,4) + '-' + val.slice(4,8);
                    }
                    
                    if (this.value !== val) {
                        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeSetter.call(this, val);
                        this.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                });
            });
        }, 300);
        </script>
    """, height=0)

    if st.button("Guardar Proveedor"):
        if not nombre.strip():
            st.warning("⚠️ El nombre del proveedor es obligatorio.")
            return
            
        dui_nit_formateado, doc_valido = formatear_dui_nit(dui_nit_raw, tipo_doc)
        tel_formateado, tel_valido = formatear_telefono(telefono_raw)
        
        if not doc_valido:
            if tipo_doc == "DUI":
                st.error("❌ El DUI debe tener exactamente 9 dígitos.")
            else:
                st.error("❌ El NIT debe tener exactamente 14 dígitos.")
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
                cursor.execute(consulta, (
                    nombre.strip(),
                    tipo,
                    dui_nit_formateado if dui_nit_formateado else None,
                    tel_formateado if tel_formateado else None
                ))
                conexion.commit()
                st.success(f"✅ Proveedor '{nombre.strip()}' registrado correctamente (Doc: {dui_nit_formateado or 'N/A'}, Tel: {tel_formateado or 'N/A'}).")
            except Exception as e:
                st.error(f"Error al registrar proveedor: {e}")
            finally:
                cursor.close()
                conexion.close()
