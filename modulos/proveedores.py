import streamlit as st
import mysql.connector
from config.conexion import obtener_conexion

def limpiar_y_formatear_dui():
    texto = st.session_state.get("input_dui", "")
    solo_num = "".join(filter(str.isdigit, texto))[:9]
    if len(solo_num) > 8:
        st.session_state["input_dui"] = f"{solo_num[:8]}-{solo_num[8:]}"
    else:
        st.session_state["input_dui"] = solo_num

def limpiar_y_formatear_nit():
    texto = st.session_state.get("input_nit", "")
    solo_num = "".join(filter(str.isdigit, texto))[:14]
    if len(solo_num) > 13:
        st.session_state["input_nit"] = f"{solo_num[:4]}-{solo_num[4:10]}-{solo_num[10:13]}-{solo_num[13:]}"
    elif len(solo_num) > 10:
        st.session_state["input_nit"] = f"{solo_num[:4]}-{solo_num[4:10]}-{solo_num[10:]}"
    elif len(solo_num) > 4:
        st.session_state["input_nit"] = f"{solo_num[:4]}-{solo_num[4:]}"
    else:
        st.session_state["input_nit"] = solo_num

def limpiar_y_formatear_tel():
    texto = st.session_state.get("input_tel", "")
    solo_num = "".join(filter(str.isdigit, texto))[:8]
    if len(solo_num) > 4:
        st.session_state["input_tel"] = f"{solo_num[:4]}-{solo_num[4:]}"
    else:
        st.session_state["input_tel"] = solo_num

def mostrar_proveedores():
    st.header("🚚 Gestión de Proveedores")
    
    # 1. Vaciar los campos ANTES de dibujarlos si se activó la bandera de limpieza
    if st.session_state.get("limpiar_campos_prov", False):
        st.session_state["input_nombre_prov"] = ""
        st.session_state["input_tipo_prov"] = "Persona Natural"
        st.session_state["input_doc_radio"] = "Ninguno"
        st.session_state["input_dui"] = ""
        st.session_state["input_nit"] = ""
        st.session_state["input_tel"] = ""
        st.session_state["limpiar_campos_prov"] = False

    # 2. Mostrar mensaje de éxito si se acaba de guardar un proveedor
    if st.session_state.get("msg_exito_prov"):
        st.success(st.session_state["msg_exito_prov"])
        st.session_state["msg_exito_prov"] = ""

    # 3. Inicializar claves de los campos si es la primera vez que se abre
    if "input_nombre_prov" not in st.session_state:
        st.session_state["input_nombre_prov"] = ""
    if "input_tipo_prov" not in st.session_state:
        st.session_state["input_tipo_prov"] = "Persona Natural"
    if "input_doc_radio" not in st.session_state:
        st.session_state["input_doc_radio"] = "Ninguno"
    if "input_dui" not in st.session_state:
        st.session_state["input_dui"] = ""
    if "input_nit" not in st.session_state:
        st.session_state["input_nit"] = ""
    if "input_tel" not in st.session_state:
        st.session_state["input_tel"] = ""

    # 4. Dibujar los campos del formulario
    nombre = st.text_input("Nombre o Razón Social", key="input_nombre_prov")
    tipo = st.selectbox(
        "Tipo de Proveedor", 
        ["Persona Natural", "Empresa", "Cooperativa", "Otro"],
        key="input_tipo_prov"
    )
    
    opciones_doc = ["Ninguno", "DUI", "NIT"] if tipo == "Persona Natural" else ["Ninguno", "NIT"]
    if st.session_state["input_doc_radio"] not in opciones_doc:
        st.session_state["input_doc_radio"] = "Ninguno"
        
    tipo_doc = st.radio(
        "Documento de Identificación",
        opciones_doc,
        horizontal=True,
        key="input_doc_radio"
    )
    
    dui_nit_raw = ""
    if tipo_doc == "DUI":
        valor_dui = st.session_state.get("input_dui", "")
        tope_dui = 10 if "-" in valor_dui else 9
        dui_nit_raw = st.text_input(
            "Número de DUI",
            max_chars=tope_dui,
            placeholder="00000000-0",
            key="input_dui",
            on_change=limpiar_y_formatear_dui
        )
            
    elif tipo_doc == "NIT":
        valor_nit = st.session_state.get("input_nit", "")
        tope_nit = 17 if "-" in valor_nit else 14
        dui_nit_raw = st.text_input(
            "Número de NIT",
            max_chars=tope_nit,
            placeholder="0000-000000-000-0",
            key="input_nit",
            on_change=limpiar_y_formatear_nit
        )
        
    valor_tel = st.session_state.get("input_tel", "")
    tope_tel = 9 if "-" in valor_tel else 8
    telefono_raw = st.text_input(
        "Teléfono",
        max_chars=tope_tel,
        placeholder="0000-0000",
        key="input_tel",
        on_change=limpiar_y_formatear_tel
    )

    # 5. Guardar en la base de datos con validación de duplicados
    if st.button("Guardar Proveedor"):
        if not nombre.strip():
            st.warning("⚠️ El nombre del proveedor es obligatorio.")
            return
            
        num_doc = "".join(filter(str.isdigit, dui_nit_raw))
        num_tel = "".join(filter(str.isdigit, telefono_raw))
        
        if tipo_doc == "DUI" and len(num_doc) != 9:
            st.error("❌ El DUI debe tener 9 dígitos.")
            return
        if tipo_doc == "NIT" and len(num_doc) != 14:
            st.error("❌ El NIT debe tener 14 dígitos.")
            return
        if len(num_tel) > 0 and len(num_tel) != 8:
            st.error("❌ El número de teléfono debe tener 8 dígitos.")
            return

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
                
                st.session_state["msg_exito_prov"] = f"✅ Proveedor '{nombre.strip()}' registrado correctamente."
                st.session_state["limpiar_campos_prov"] = True
                st.rerun()
            except mysql.connector.IntegrityError as err:
                if "DUI_NIT" in str(err):
                    st.error(f"❌ El {tipo_doc} ingresado ya pertenece a otro proveedor registrado.")
                elif "Telefono" in str(err):
                    st.error("❌ Ese número de teléfono ya pertenece a otro proveedor registrado.")
                else:
                    st.error("❌ Ya existe un proveedor registrado con esos datos.")
            except Exception as e:
                st.error(f"Error al registrar proveedor: {e}")
            finally:
                cursor.close()
                conexion.close()
