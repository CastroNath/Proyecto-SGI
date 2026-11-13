import streamlit as st
from config.conexion import obtener_conexion

def mostrar_clientes():
    st.header("🤝 Gestión de Clientes")
    
    # 1. Limpiar campos antes de dibujarlos si se activó la bandera
    if st.session_state.get("limpiar_campos_cli", False):
        st.session_state["input_nombre_cli"] = ""
        st.session_state["input_tipo_cli"] = "Publico general"
        st.session_state["limpiar_campos_cli"] = False

    # 2. Mostrar mensaje de éxito si se acaba de guardar un cliente
    if st.session_state.get("msg_exito_cli"):
        st.success(st.session_state["msg_exito_cli"])
        st.session_state["msg_exito_cli"] = ""

    # 3. Inicializar claves
    if "input_nombre_cli" not in st.session_state:
        st.session_state["input_nombre_cli"] = ""
    if "input_tipo_cli" not in st.session_state:
        st.session_state["input_tipo_cli"] = "Publico general"

    # 4. Formulario
    nombre = st.text_input("Nombre del Cliente", key="input_nombre_cli")
    tipo = st.selectbox(
        "Tipo de Cliente",
        ["Publico general", "Tienda"],
        key="input_tipo_cli"
    )

    if st.button("Guardar Cliente"):
        if not nombre.strip():
            st.warning("⚠️ El nombre del cliente es obligatorio.")
            return

        conexion = obtener_conexion()
        if conexion:
            try:
                cursor = conexion.cursor()
                # Verificar si ya existe un cliente con el mismo nombre exacto
                cursor.execute("SELECT id_cliente FROM Cliente WHERE LOWER(Nombre) = LOWER(%s)", (nombre.strip(),))
                if cursor.fetchone():
                    st.error("❌ Ya existe un cliente registrado con ese nombre.")
                    return

                consulta = "INSERT INTO Cliente (Nombre, Tipo) VALUES (%s, %s)"
                cursor.execute(consulta, (nombre.strip(), tipo))
                conexion.commit()

                st.session_state["msg_exito_cli"] = f"✅ Cliente '{nombre.strip()}' registrado correctamente."
                st.session_state["limpiar_campos_cli"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar cliente: {e}")
            finally:
                cursor.close()
                conexion.close()
