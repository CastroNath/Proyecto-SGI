import streamlit as st
from config.conexion import obtener_conexion

def sincronizar_tipo_cliente():
    seleccion = st.session_state.get("input_nombre_cli", "Externo")
    if seleccion == "Externo":
        st.session_state["input_tipo_cli"] = "Publico general"
    else:
        st.session_state["input_tipo_cli"] = "Tienda"

def mostrar_clientes():
    st.header("🤝 Gestión de Clientes")
    
    # 1. Reiniciar los desplegables antes de dibujarlos si se activó la bandera
    if st.session_state.get("limpiar_campos_cli", False):
        st.session_state["input_nombre_cli"] = "Externo"
        st.session_state["input_tipo_cli"] = "Publico general"
        st.session_state["limpiar_campos_cli"] = False

    # 2. Mostrar mensaje de éxito si se acaba de guardar un cliente
    if st.session_state.get("msg_exito_cli"):
        st.success(st.session_state["msg_exito_cli"])
        st.session_state["msg_exito_cli"] = ""

    # 3. Inicializar claves
    if "input_nombre_cli" not in st.session_state:
        st.session_state["input_nombre_cli"] = "Externo"
    if "input_tipo_cli" not in st.session_state:
        st.session_state["input_tipo_cli"] = "Publico general"

    # 4. Formulario con ambos campos como menús desplegables
    nombre = st.selectbox(
        "Nombre del Cliente",
        ["Externo", "Tienda Santa Ana", "Tienda Sonsonate", "Tienda Ahuachapan"],
        key="input_nombre_cli",
        on_change=sincronizar_tipo_cliente
    )
    
    tipo = st.selectbox(
        "Tipo de Cliente",
        ["Publico general", "Tienda"],
        key="input_tipo_cli"
    )

    if st.button("Guardar Cliente"):
        conexion = obtener_conexion()
        if conexion:
            try:
                cursor = conexion.cursor()
                # Verificar si ya existe exactamente esa combinación de Nombre y Tipo para no duplicar
                cursor.execute(
                    "SELECT id_cliente FROM Cliente WHERE Nombre = %s AND Tipo = %s", 
                    (nombre, tipo)
                )
                if cursor.fetchone():
                    st.error(f"❌ El cliente '{nombre}' ({tipo}) ya se encuentra registrado en la base de datos.")
                    return

                consulta = "INSERT INTO Cliente (Nombre, Tipo) VALUES (%s, %s)"
                cursor.execute(consulta, (nombre, tipo))
                conexion.commit()

                st.session_state["msg_exito_cli"] = f"✅ Cliente '{nombre}' registrado correctamente."
                st.session_state["limpiar_campos_cli"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar cliente: {e}")
            finally:
                cursor.close()
                conexion.close()
