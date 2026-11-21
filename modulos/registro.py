import mysql.connector
import streamlit as st

from config.conexion import consultar, obtener_conexion
from modulos.negocio import hash_password
from modulos.formato import tabla


# Cupo de usuarios activos por tienda según el rol (se reconoce el rol por su nombre)
LIMITES_POR_ROL = {"encargado": 1, "cajero": 5}


def limite_del_rol(nombre_rol):
    n = (nombre_rol or "").lower()
    for clave, maximo in LIMITES_POR_ROL.items():
        if clave in n:
            return maximo
    return None  # sin límite (p. ej. Administrador)


def revisar_cupo(cursor, id_rol, id_tienda, excluir_usuario=0):
    """Devuelve un mensaje de error si la tienda ya llegó al máximo de usuarios ACTIVOS de ese rol."""
    cursor.execute("SELECT Nombre FROM Rol WHERE id_rol = %s", (id_rol,))
    fila = cursor.fetchone()
    nombre_rol = fila[0] if fila else ""
    maximo = limite_del_rol(nombre_rol)
    if maximo is None:
        return None
    cursor.execute("""SELECT COUNT(*) FROM Usuario
                      WHERE id_tienda = %s AND id_rol = %s AND Activo = 1 AND id_usuario <> %s""",
                   (id_tienda, id_rol, excluir_usuario))
    activos = cursor.fetchone()[0]
    if activos >= maximo:
        cursor.execute("SELECT Nombre FROM Tienda WHERE id_tienda = %s", (id_tienda,))
        tienda = cursor.fetchone()[0]
        if maximo == 1:
            return (f"❌ «{tienda}» ya tiene un {nombre_rol.lower()} activo. Solo se permite uno por tienda; "
                    "si lo vas a reemplazar, desactiva primero al actual en «Usuarios registrados».")
        return (f"❌ «{tienda}» ya tiene {activos} usuarios con rol {nombre_rol.lower()} activos "
                f"(máximo {maximo} por tienda). Desactiva uno para registrar otro.")
    return None


def registrar_usuario(id_rol, id_tienda, nombre, usuario, contrasena):
    conexion = obtener_conexion()
    if conexion is None:
        return False, "No hay conexión con la base de datos."
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT id_usuario FROM Usuario WHERE LOWER(Usuario) = LOWER(%s)", (usuario,))
        if cursor.fetchone():
            return False, f"❌ El nombre de usuario '{usuario}' ya está en uso. Elige otro."
        error_cupo = revisar_cupo(cursor, id_rol, id_tienda)
        if error_cupo:
            return False, error_cupo
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


def crear_tienda(nombre, direccion):
    """Registra una tienda nueva que se une a la cooperativa."""
    if consultar("SELECT 1 FROM Tienda WHERE LOWER(TRIM(Nombre)) = LOWER(%s)", (nombre,)):
        return False, f"❌ Ya existe una tienda llamada «{nombre}»."
    cx = obtener_conexion()
    if cx is None:
        return False, "No hay conexión con la base de datos."
    cur = cx.cursor()
    try:
        cur.execute("INSERT INTO Tienda (Nombre, Tipo, Direccion) VALUES (%s, 'Tienda', %s)", (nombre, direccion))
        cx.commit()
        return True, (f"✅ Tienda «{nombre}» creada. Siguientes pasos: asígnale usuarios en la pestaña «Crear cuenta», "
                      "y el Centro de Distribución la registra como cliente en Catálogos y Registros → Clientes.")
    except Exception as e:
        cx.rollback()
        return False, f"❌ Error al crear la tienda: {e}"
    finally:
        cur.close()
        cx.close()


def gestionar_tiendas():
    if st.session_state.get("msg_tienda"):
        st.success(st.session_state.pop("msg_tienda"))

    st.subheader("Tiendas de la red")
    tabla(consultar("""SELECT t.id_tienda AS ID, t.Nombre AS Tienda,
                              IF(t.Tipo = 'CD', 'Centro de Distribución', 'Tienda') AS Tipo,
                              IFNULL(t.Direccion, '') AS `Dirección`,
                              (SELECT COUNT(*) FROM Usuario u WHERE u.id_tienda = t.id_tienda) AS Usuarios,
                              CASE WHEN t.Tipo = 'CD' THEN '—'
                                   WHEN EXISTS (SELECT 1 FROM Cliente c WHERE c.id_tienda = t.id_tienda) THEN 'Sí'
                                   ELSE 'Pendiente' END AS `Cliente del CD`
                       FROM Tienda t ORDER BY t.Tipo = 'CD' DESC, t.Nombre"""))

    st.subheader("➕ Nueva tienda")
    st.caption("Cuando una tienda se une a la cooperativa, regístrala aquí. Su inventario empieza vacío y se llena "
               "con sus primeras compras.")
    with st.form("form_tienda", clear_on_submit=True):
        nombre = st.text_input("Nombre de la tienda *", placeholder="Ej. Tienda Chalchuapa")
        direccion = st.text_input("Dirección *", placeholder="Ej. 3a Calle Oriente #8, Chalchuapa")
        guardar = st.form_submit_button("Crear tienda")
    if guardar:
        nombre, direccion = nombre.strip(), direccion.strip()
        if not nombre or not direccion:
            st.error("❌ El nombre y la dirección de la tienda son obligatorios.")
        else:
            ok, msg = crear_tienda(nombre, direccion)
            if ok:
                st.session_state["msg_tienda"] = msg
                st.rerun()
            st.error(msg)

    st.subheader("✏️ Modificar tienda")
    tiendas = consultar("SELECT id_tienda, Nombre, Tipo, Direccion FROM Tienda ORDER BY Nombre")
    sel = st.selectbox("Tienda", [None] + tiendas, key="tienda_editar",
                       format_func=lambda x: "-- Selecciona una tienda --" if x is None else x["Nombre"])
    if sel:
        with st.form(f"form_editar_tienda_{sel['id_tienda']}"):
            nuevo_nombre = st.text_input("Nombre *", value=sel["Nombre"])
            nueva_dir = st.text_input("Dirección *", value=sel["Direccion"] or "")
            if st.form_submit_button("💾 Guardar cambios"):
                nuevo_nombre, nueva_dir = nuevo_nombre.strip(), nueva_dir.strip()
                if not nuevo_nombre or not nueva_dir:
                    st.error("❌ El nombre y la dirección son obligatorios.")
                elif consultar("SELECT 1 FROM Tienda WHERE LOWER(TRIM(Nombre)) = LOWER(%s) AND id_tienda <> %s",
                               (nuevo_nombre, sel["id_tienda"])):
                    st.error(f"❌ Ya existe otra tienda llamada «{nuevo_nombre}».")
                else:
                    cx = obtener_conexion(); cur = cx.cursor()
                    cur.execute("UPDATE Tienda SET Nombre=%s, Direccion=%s WHERE id_tienda=%s",
                                (nuevo_nombre, nueva_dir, sel["id_tienda"]))
                    # El nombre del cliente que la representa ante el CD se mantiene igual al de la tienda
                    cur.execute("UPDATE Cliente SET Nombre=%s WHERE id_tienda=%s", (nuevo_nombre, sel["id_tienda"]))
                    cx.commit(); cur.close(); cx.close()
                    st.session_state["msg_tienda"] = f"✅ Datos de «{nuevo_nombre}» actualizados."
                    st.session_state.pop("tienda_editar", None)
                    st.rerun()


def mostrar_registro():
    st.header("👑 Administración de Tiendas y Cuentas")
    if st.session_state.get("id_rol") != 1:
        st.error("⛔ Acceso denegado. Solo el Administrador General puede gestionar cuentas.")
        return
    tab_tiendas, tab_nuevo, tab_lista = st.tabs(["🏪 Tiendas", "➕ Crear cuenta", "📋 Usuarios registrados"])

    with tab_tiendas:
        gestionar_tiendas()

    with tab_nuevo:
        st.write("Asigna un nuevo empleado operativo a su rol y tienda correspondiente.")
        if st.session_state.get("msg_exito_reg"):
            st.success(st.session_state.pop("msg_exito_reg"))

        roles = consultar("SELECT id_rol, Nombre FROM Rol WHERE id_rol <> 1 ORDER BY id_rol")
        tiendas = consultar("SELECT id_tienda, Nombre FROM Tienda ORDER BY Nombre")
        with st.expander("👥 Cupos por tienda (1 encargado y hasta 5 cajeros activos)", expanded=True):
            cupos = []
            for t in tiendas:
                fila = {"Tienda": t["Nombre"]}
                for r in roles:
                    maximo = limite_del_rol(r["Nombre"])
                    if maximo is None:
                        continue
                    n = consultar("""SELECT COUNT(*) AS n FROM Usuario WHERE id_tienda=%s AND id_rol=%s AND Activo=1""",
                                  (t["id_tienda"], r["id_rol"]))[0]["n"]
                    fila[r["Nombre"]] = f"{n} de {maximo}" + (" (completo)" if n >= maximo else "")
                cupos.append(fila)
            tabla(cupos)
        if not roles or not tiendas:
            st.warning("⚠️ Faltan roles operativos o tiendas en la base de datos.")
        else:
            with st.form("form_registro", clear_on_submit=True):
                nombre = st.text_input("Nombre Completo del Empleado")
                usuario = st.text_input("Nombre de Usuario")
                contrasena = st.text_input("Contraseña (mínimo 4 caracteres)", type="password")
                rol_sel = st.selectbox("Asignar Rol", roles, format_func=lambda x: x["Nombre"])
                tienda_sel = st.selectbox("Asignar Tienda / Sucursal", tiendas, format_func=lambda x: x["Nombre"])
                guardar = st.form_submit_button("Guardar Usuario")
            if guardar:
                if not nombre.strip() or not usuario.strip() or not contrasena.strip():
                    st.error("⚠️ Por favor, llena todos los campos.")
                elif len(contrasena) < 4:
                    st.error("⚠️ La contraseña debe tener al menos 4 caracteres.")
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
        tabla(usuarios, width="stretch", hide_index=True)
        sel = st.selectbox("Usuario", usuarios, format_func=lambda x: f"{x['Usuario']} · {x['Nombre']} ({x['Estado']})")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔁 Activar / desactivar"):
                if sel["id_usuario"] == st.session_state.get("id_usuario"):
                    st.error("No puedes desactivar tu propia cuenta.")
                else:
                    cx = obtener_conexion(); cur = cx.cursor()
                    error_cupo = None
                    if sel["Estado"] == "Inactivo":  # al reactivar se vuelve a revisar el cupo de la tienda
                        cur.execute("SELECT id_rol, id_tienda FROM Usuario WHERE id_usuario=%s", (sel["id_usuario"],))
                        id_rol_u, id_tienda_u = cur.fetchone()
                        error_cupo = revisar_cupo(cur, id_rol_u, id_tienda_u, excluir_usuario=sel["id_usuario"])
                    if error_cupo:
                        st.error(error_cupo)
                    else:
                        cur.execute("UPDATE Usuario SET Activo = 1 - Activo WHERE id_usuario=%s", (sel["id_usuario"],))
                        cx.commit()
                    cur.close(); cx.close()
                    if not error_cupo:
                        st.rerun()
        with c2:
            nueva = st.text_input("Nueva contraseña", type="password", key="reset_pw")
            if st.button("🔑 Restablecer contraseña"):
                if len(nueva) < 4:
                    st.error("La contraseña debe tener al menos 4 caracteres.")
                else:
                    cx = obtener_conexion(); cur = cx.cursor()
                    cur.execute("UPDATE Usuario SET Contrasena=%s WHERE id_usuario=%s",
                                (hash_password(nueva), sel["id_usuario"]))
                    cx.commit(); cur.close(); cx.close()
                    st.success("Contraseña actualizada.")
