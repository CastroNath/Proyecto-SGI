import mysql.connector
import streamlit as st

from config.conexion import consultar, obtener_conexion
from modulos.negocio import hash_password


def registrar_usuario(id_rol, id_tienda, nombre, usuario, contrasena):
    conexion = obtener_conexion()
    if conexion is None:
        return False, "No hay conexión con la base de datos."
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT id_usuario FROM Usuario WHERE LOWER(Usuario) = LOWER(%s)", (usuario,))
        if cursor.fetchone():
            return False, f"❌ El nombre de usuario '{usuario}' ya está en uso. Elige otro."
        cursor.execute("""INSERT INTO Usuario (id_rol, id_tienda, Nombre, Usuario, Contrasena)
                          VALUES (%s, %s, %s, %s, %s)""",
                       (id_rol, id_tienda, nombre, usuario, hash_password(contrasena)))
        conexion.commit()
        return True, f"✅ Usuario '{usuario}' creado y asignado correctamente."
    except mysql.connector.IntegrityError:
        return False, f"❌ El usuario '{usuario}' ya existe en el sistema."
    except Exception as e:
        return False, f"❌ Error al registrar: {e}"
    finally:
        cursor.close()
        conexion.close()


def mostrar_registro():
    st.header("👑 Administración de Cuentas")
    if st.session_state.get("id_rol") != 1:
        st.error("⛔ Acceso denegado. Solo el Administrador General puede gestionar cuentas.")
        return
    tab_nuevo, tab_lista = st.tabs(["➕ Crear cuenta", "📋 Usuarios registrados"])

    with tab_nuevo:
        st.write("Asigna un nuevo empleado operativo a su rol y tienda correspondiente.")
        if st.session_state.get("msg_exito_reg"):
            st.success(st.session_state.pop("msg_exito_reg"))

        roles = consultar("SELECT id_rol, Nombre FROM Rol WHERE id_rol <> 1 ORDER BY id_rol")
        tiendas = consultar("SELECT id_tienda, Nombre FROM Tienda ORDER BY Nombre")
        if not roles or not tiendas:
            st.warning("⚠️ Faltan roles operativos o tiendas en la base de datos.")
        else:
            with st.form("form_registro", clear_on_submit=True):
                nombre = st.text_input("Nombre Completo del Empleado")
                usuario = st.text_input("Nombre de Usuario")
                contrasena = st.text_input("Contraseña (mínimo 6 caracteres)", type="password")
                rol_sel = st.selectbox("Asignar Rol", roles, format_func=lambda x: x["Nombre"])
                tienda_sel = st.selectbox("Asignar Tienda / Sucursal", tiendas, format_func=lambda x: x["Nombre"])
                guardar = st.form_submit_button("Guardar Usuario")
            if guardar:
                if not nombre.strip() or not usuario.strip() or not contrasena.strip():
                    st.error("⚠️ Por favor, llena todos los campos.")
                elif len(contrasena) < 6:
                    st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
                else:
                    ok, msg = registrar_usuario(rol_sel["id_rol"], tienda_sel["id_tienda"],
                                                nombre.strip(), usuario.strip(), contrasena)
                    if ok:
                        st.session_state["msg_exito_reg"] = f"{msg} ({tienda_sel['Nombre']})"
                        st.rerun()
                    st.error(msg)

    with tab_lista:
        usuarios = consultar("""SELECT u.id_usuario, u.Nombre, u.Usuario, r.Nombre AS Rol, t.Nombre AS Tienda,
                                       IF(u.Activo = 1, 'Activo', 'Inactivo') AS Estado
                                FROM Usuario u JOIN Rol r ON r.id_rol = u.id_rol
                                JOIN Tienda t ON t.id_tienda = u.id_tienda ORDER BY t.Nombre, u.Nombre""")
        st.dataframe(usuarios, width="stretch", hide_index=True)
        sel = st.selectbox("Usuario", usuarios, format_func=lambda x: f"{x['Usuario']} · {x['Nombre']} ({x['Estado']})")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔁 Activar / desactivar"):
                if sel["id_usuario"] == st.session_state.get("id_usuario"):
                    st.error("No puedes desactivar tu propia cuenta.")
                else:
                    cx = obtener_conexion(); cur = cx.cursor()
                    cur.execute("UPDATE Usuario SET Activo = 1 - Activo WHERE id_usuario=%s", (sel["id_usuario"],))
                    cx.commit(); cur.close(); cx.close()
                    st.rerun()
        with c2:
            nueva = st.text_input("Nueva contraseña", type="password", key="reset_pw")
            if st.button("🔑 Restablecer contraseña"):
                if len(nueva) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres.")
                else:
                    cx = obtener_conexion(); cur = cx.cursor()
                    cur.execute("UPDATE Usuario SET Contrasena=%s WHERE id_usuario=%s",
                                (hash_password(nueva), sel["id_usuario"]))
                    cx.commit(); cur.close(); cx.close()
                    st.success("Contraseña actualizada.")
