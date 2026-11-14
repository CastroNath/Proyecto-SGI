import streamlit as st
from config.conexion import obtener_conexion

def mostrar_clientes():
    st.header("🤝 Gestión de Clientes")
    
    # 1. Limpiar el campo de texto antes de dibujarlo si se activó la bandera
    if st.session_state.get("limpiar_campos_cli", False):
        st.session_state["input_nombre_cli_ext"] = ""
        st.session_state["limpiar_campos_cli"] = False

    # 2. Mostrar mensaje de éxito si se acaba de guardar un cliente
    if st.session_state.get("msg_exito_cli"):
        st.success(st.session_state["msg_exito_cli"])
        st.session_state["msg_exito_cli"] = ""

    # 3. Inicializar la clave del nombre si no existe
    if "input_nombre_cli_ext" not in st.session_state:
        st.session_state["input_nombre_cli_ext"] = ""

    # 4. Formulario con texto libre para el nombre y tipo fijo bloqueado
    nombre = st.text_input(
        "Nombre del Cliente",
        placeholder="Ej. María González",
        key="input_nombre_cli_ext"
    )
    
    st.text_input(
        "Tipo de Cliente",
        value="Publico general",
        disabled=True
    )

    if st.button("Guardar Cliente"):
        if not nombre.strip():
            st.warning("⚠️ El nombre del cliente es obligatorio.")
            return

        conexion = obtener_conexion()
        if conexion:
            try:
                cursor = conexion.cursor()
                # Verificar si ya existe un cliente registrado con el mismo nombre exacto
                cursor.execute(
                    "SELECT id_cliente FROM Cliente WHERE LOWER(Nombre) = LOWER(%s) AND Tipo = 'Publico general'", 
                    (nombre.strip(),)
                )
                if cursor.fetchone():
                    st.error(f"❌ El cliente '{nombre.strip()}' ya se encuentra registrado.")
                    return

                consulta = "INSERT INTO Cliente (Nombre, Tipo) VALUES (%s, %s)"
                cursor.execute(consulta, (nombre.strip(), "Publico general"))
                conexion.commit()

                st.session_state["msg_exito_cli"] = f"✅ Cliente '{nombre.strip()}' registrado correctamente."
                st.session_state["limpiar_campos_cli"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar cliente: {e}")
            finally:
                cursor.close()
                conexion.close()
