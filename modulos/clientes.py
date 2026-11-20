import re

import mysql.connector
import streamlit as st

from config.conexion import consultar, obtener_conexion
from modulos.formato import tabla


def _solo_digitos(texto):
    return "".join(ch for ch in (texto or "") if ch.isdigit())


def formatear_nit(texto):
    """Acepta DUI (9 dígitos, homologado como NIT) o NIT (14 dígitos). Devuelve el texto con guiones o None."""
    d = _solo_digitos(texto)
    if len(d) == 9:
        return f"{d[:8]}-{d[8]}"
    if len(d) == 14:
        return f"{d[:4]}-{d[4:10]}-{d[10:13]}-{d[13]}"
    return None


def formatear_nrc(texto):
    """NRC: de 2 a 8 dígitos; el último es el dígito verificador (ej. 123456-7)."""
    d = _solo_digitos(texto)
    return f"{d[:-1]}-{d[-1]}" if 2 <= len(d) <= 8 else None


def formatear_telefono(texto):
    d = _solo_digitos(texto)
    return f"{d[:4]}-{d[4:]}" if len(d) == 8 else None


def _formulario_cliente_tienda(id_tienda):
    """Registro de clientes de la tienda; los datos de crédito fiscal solo si se requieren."""
    ccf = st.checkbox("🧾 Este cliente requiere **Comprobante de Crédito Fiscal** (CCF)", key="cli_ccf")
    tipo_doc = "NIT"
    if ccf:
        # Fuera del formulario para que el campo cambie en cuanto se elige el tipo
        tipo_doc = st.radio("Documento de identificación *", ["DUI", "NIT"], horizontal=True, key="cli_tipo_doc",
                            help="DUI: 9 dígitos (persona natural, homologado como NIT). NIT: 14 dígitos.")
    with st.form(f"form_cliente_{ccf}_{tipo_doc}", clear_on_submit=True):
        nombre = st.text_input("Nombre o razón social *" if ccf else "Nombre del cliente *",
                               placeholder="Ej. Comedor La Bendición, S.A. de C.V." if ccf else "Ej. María González")
        if ccf:
            c1, c2 = st.columns(2)
            if tipo_doc == "DUI":
                nit = c1.text_input("Número de DUI *", placeholder="00000000-0", max_chars=10,
                                    help="Escribe solo los 9 números; el guion se agrega solo.")
            else:
                nit = c1.text_input("Número de NIT *", placeholder="0000-000000-000-0", max_chars=17,
                                    help="Escribe solo los 14 números; los guiones se agregan solos.")
            nrc = c2.text_input("NRC *", placeholder="123456-7", max_chars=9,
                                help="Número de Registro de Contribuyente: escribe solo los números "
                                     "(hasta 8); el guion antes del dígito verificador se agrega solo.")
            giro = st.text_input("Giro o actividad económica *", placeholder="Ej. Venta de comida preparada")
            direccion = st.text_input("Dirección *", placeholder="Ej. Calle Libertad #10, Santa Ana")
            c3, c4 = st.columns(2)
            telefono = c3.text_input("Teléfono de contacto", placeholder="0000-0000", max_chars=9,
                                     help="8 números; el guion se agrega solo. Opcional.")
            correo = c4.text_input("Correo electrónico", placeholder="cliente@correo.com")
        guardar = st.form_submit_button("Guardar cliente")

    if not guardar:
        return
    nombre = nombre.strip()
    if not nombre:
        st.error("❌ El nombre del cliente es obligatorio.")
        return
    if nombre.lower() in ("externo", "consumidor final"):
        st.error("❌ Ese nombre está reservado por el sistema para ventas rápidas sin registro.")
        return
    if consultar("""SELECT 1 FROM Cliente WHERE LOWER(Nombre) = LOWER(%s) AND Tipo = 'Publico general'
                    AND id_tienda_registro = %s""", (nombre, id_tienda)):
        st.error(f"❌ «{nombre}» ya está registrado como cliente de tu tienda.")
        return

    datos = {"NIT": None, "NRC": None, "Giro": None, "Direccion": None, "Telefono": None, "Correo": None}
    if ccf:
        errores = []
        digitos = len(_solo_digitos(nit))
        esperados = 9 if tipo_doc == "DUI" else 14
        datos["NIT"] = formatear_nit(nit) if digitos == esperados else None
        if not datos["NIT"]:
            errores.append(f"El {tipo_doc} debe tener {esperados} números (escribiste {digitos}).")
        datos["NRC"] = formatear_nrc(nrc)
        if not datos["NRC"]:
            errores.append("El NRC debe tener entre 2 y 8 dígitos (ej. 123456-7).")
        datos["Giro"] = giro.strip() or None
        if not datos["Giro"]:
            errores.append("El giro es obligatorio para crédito fiscal.")
        datos["Direccion"] = direccion.strip() or None
        if not datos["Direccion"]:
            errores.append("La dirección es obligatoria para crédito fiscal.")
        if telefono.strip():
            datos["Telefono"] = formatear_telefono(telefono)
            if not datos["Telefono"]:
                errores.append("El teléfono debe tener 8 dígitos.")
        if correo.strip():
            if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo.strip()):
                datos["Correo"] = correo.strip().lower()
            else:
                errores.append("El correo no tiene un formato válido.")
        if datos["NIT"] and consultar("SELECT 1 FROM Cliente WHERE NIT = %s AND id_tienda_registro = %s",
                                      (datos["NIT"], id_tienda)):
            errores.append(f"Ya tienes un cliente registrado con el {tipo_doc} {datos['NIT']}.")
        if errores:
            st.error("❌ Revisa los datos:\n\n" + "\n".join(f"- {e}" for e in errores))
            return

    cx = obtener_conexion()
    if not cx:
        return
    cur = cx.cursor()
    try:
        cur.execute("""INSERT INTO Cliente (Nombre, Tipo, id_tienda_registro, NIT, NRC, Giro, Direccion, Telefono, Correo)
                       VALUES (%s, 'Publico general', %s, %s, %s, %s, %s, %s, %s)""",
                    (nombre, id_tienda, datos["NIT"], datos["NRC"], datos["Giro"], datos["Direccion"],
                     datos["Telefono"], datos["Correo"]))
        cx.commit()
        st.session_state["msg_exito_cli"] = (f"✅ Cliente «{nombre}» registrado"
                                             + (" con datos de crédito fiscal." if ccf else "."))
        st.rerun()
    except mysql.connector.IntegrityError:
        st.error("❌ Ya existe un cliente con esos datos en tu tienda.")
    finally:
        cur.close()
        cx.close()


def mostrar_clientes():
    st.header("🤝 Gestión de Clientes")
    es_admin = st.session_state.get("id_rol") == 1
    es_cd = st.session_state.get("es_cd", False)
    id_tienda = st.session_state.get("id_tienda")

    if st.session_state.get("msg_exito_cli"):
        st.success(st.session_state.pop("msg_exito_cli"))

    if es_admin or es_cd:
        # El CD solo vende a las tiendas de la red: aquí se registran como clientes del CD
        st.caption("Registra las sucursales de la red como clientes del Centro de Distribución.")
        pendientes = consultar("""SELECT t.id_tienda, t.Nombre FROM Tienda t
                                  WHERE t.Tipo <> 'CD'
                                    AND NOT EXISTS (SELECT 1 FROM Cliente c WHERE c.id_tienda = t.id_tienda)
                                  ORDER BY t.Nombre""")
        if not pendientes:
            st.info("✅ Todas las tiendas ya están registradas como clientes del CD.")
        else:
            sel = st.selectbox("Tienda cliente", pendientes, format_func=lambda x: x["Nombre"])
            if st.button("Guardar cliente"):
                cx = obtener_conexion()
                if cx:
                    cur = cx.cursor()
                    try:
                        cur.execute("INSERT INTO Cliente (Nombre, Tipo, id_tienda) VALUES (%s,'Tienda',%s)",
                                    (sel["Nombre"], sel["id_tienda"]))
                        cx.commit()
                        st.session_state["msg_exito_cli"] = f"✅ «{sel['Nombre']}» registrada como cliente del CD."
                        st.rerun()
                    finally:
                        cur.close(); cx.close()

        st.subheader("Tiendas clientes del CD")
        tabla(consultar("""SELECT c.id_cliente AS ID, c.Nombre AS Tienda, IFNULL(t.Direccion, '') AS `Dirección`
                           FROM Cliente c JOIN Tienda t ON t.id_tienda = c.id_tienda
                           WHERE c.Tipo = 'Tienda' ORDER BY c.Nombre"""))
        if es_admin:
            st.subheader("Clientes registrados por las tiendas")
            tabla(consultar("""SELECT c.id_cliente AS ID, t.Nombre AS Tienda, c.Nombre,
                                      IFNULL(c.NIT, '') AS NIT, IFNULL(c.NRC, '') AS NRC,
                                      IF(c.NRC IS NULL, 'Consumidor final', 'Crédito fiscal') AS Comprobante
                               FROM Cliente c JOIN Tienda t ON t.id_tienda = c.id_tienda_registro
                               WHERE c.Tipo = 'Publico general' ORDER BY t.Nombre, c.Nombre"""))
        return

    # Usuarios de tienda: solo SUS clientes
    _formulario_cliente_tienda(id_tienda)
    st.subheader("Mis clientes")
    clientes = consultar("""SELECT id_cliente AS ID, Nombre,
                                   IF(NRC IS NULL, 'Consumidor final', 'Crédito fiscal') AS Comprobante,
                                   IFNULL(NIT, '') AS NIT, IFNULL(NRC, '') AS NRC, IFNULL(Giro, '') AS Giro,
                                   IFNULL(Direccion, '') AS `Dirección`, IFNULL(Telefono, '') AS `Teléfono`,
                                   IFNULL(Correo, '') AS Correo
                            FROM Cliente
                            WHERE Tipo = 'Publico general' AND id_tienda_registro = %s
                            ORDER BY Nombre""", (id_tienda,))
    if not clientes:
        st.info("Aún no has registrado clientes. Las ventas sin cliente se registran como consumidor final.")
    else:
        tabla(clientes)
