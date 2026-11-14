import streamlit as st
from config.conexion import obtener_conexion

def sincronizar_tipo_cliente():
    seleccion = st.session_state.get("sel_nombre_cli_admin", "Externo")
    if seleccion == "Externo":
        st.session_state["sel_tipo_cli_admin"] = "Publico general"
    else:
        st.session_state["sel_tipo_cli_admin"] = "Tienda"

def mostrar_clientes():
    st.header("🤝 Gestión de Clientes")
    
    # Determinar si el usuario conectado es el Administrador General (id_rol == 1)
    es_admin = (st.session_state.get("id_rol") == 1)

    # 1. Limpiar campos antes de dibujarlos si se activó la bandera
    if st.session_state.get("limpiar_campos_cli", False):
        st.session_state["sel_nombre_cli_admin"] = "Externo"
        st.session_state["sel_tipo_cli_admin"] = "Publico general"
        st.session_state["input_nombre_cli_ext"] = ""
        st.session_state["limpiar_campos_cli"] = False

    # 2. Mostrar mensaje de éxito si se acaba de guardar un cliente
    if st.session_state.get("msg_exito_cli"):
        st.success(st.session_state["msg_exito_cli"])
        st.session_state["msg_exito_cli"] = ""

    # 3. Inicializar claves según el rol
    if "sel_nombre_cli_admin" not in st.session_state:
        st.session_state["sel_nombre_cli_admin"] = "Externo"
    if "sel_tipo_cli_admin" not in st.session_state:
        st.session_state["sel_tipo_cli_admin"] = "Publico general"
    if "input_nombre_cli_ext" not in st.session_state:
        st.session_state["input_nombre_cli_ext"] = ""

    # 4. Dibujar formulario diferenciado por Rol
    if es_admin:
        st.caption("Modo Administrador: Puedes registrar sucursales de la red.")
        nombre_final = st.selectbox(
            "Nombre del Cliente",
            ["Externo", "Tienda Santa Ana", "Tienda Sonsonate", "Tienda Ahuachapan"],
            key="sel_nombre_cli_admin",
            on_change=sincronizar_tipo_cliente
        )
        
        st.selectbox(
            "Tipo de Cliente",
            ["Publico general", "Tienda"],
            key="sel_tipo_cli_admin",
            disabled=True
        )
        tipo_final = "Publico general" if nombre_final == "Externo" else "Tienda"
    else:
        nombre_final = st.text_input(
            "Nombre del Cliente",
            placeholder="Ej. María González",
            key="input_nombre_cli_ext"
        )
        
        st.text_input(
            "Tipo de Cliente",
            value="Publico general",
            disabled=True
        )
        tipo_final = "Publico general"

    # 5. Guardar en la base de datos
    if st.button("Guardar Cliente"):
        if not nombre_final.strip():
            st.warning("⚠️ El nombre del cliente es obligatorio.")
            return

        conexion = obtener_conexion()
        if conexion:
            try:
                cursor = conexion.cursor()
                # Verificar duplicados
                cursor.execute(
                    "SELECT id_cliente FROM Cliente WHERE LOWER(Nombre) = LOWER(%s) AND Tipo = %s", 
                    (nombre_final.strip(), tipo_final)
                )
                if cursor.fetchone():
                    st.error(f"❌ El cliente '{nombre_final.strip()}' ({tipo_final}) ya se encuentra registrado.")
                    return

                consulta = "INSERT INTO Cliente (Nombre, Tipo) VALUES (%s, %s)"
                cursor.execute(consulta, (nombre_final.strip(), tipo_final))
                conexion.commit()

                st.session_state["msg_exito_cli"] = f"✅ Cliente '{nombre_final.strip()}' ({tipo_final}) registrado correctamente."
                st.session_state["limpiar_campos_cli"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar cliente: {e}")
            finally:
                cursor.close()
                conexion.close()
