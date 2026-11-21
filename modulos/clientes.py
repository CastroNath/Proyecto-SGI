import re

import mysql.connector
import streamlit as st

from config.conexion import consultar, obtener_conexion
from modulos.catalogos import GIROS
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
    """NRC: hasta 7 dígitos (6 del registro + 1 verificador, ej. 123456-7).
    Los NRC antiguos pueden tener menos dígitos, por eso se aceptan de 3 a 7."""
    d = _solo_digitos(texto)
    return f"{d[:-1]}-{d[-1]}" if 3 <= len(d) <= 7 else None


def formatear_telefono(texto):
    d = _solo_digitos(texto)
    return f"{d[:4]}-{d[4:]}" if len(d) == 8 else None


def _formulario_cliente(clave, actual=None):
    """Formulario de cliente (registro o edición). Los campos de crédito fiscal aparecen solo si se piden.
    `actual` trae los datos del cliente cuando se edita. Devuelve los valores escritos o None si no se envió."""
    actual = actual or {}
    # Solo se registran clientes de crédito fiscal; las ventas sin registro son a consumidor final
    ccf = True
    tipo_doc = "NIT"
    if ccf:
        # Fuera del formulario para que el campo cambie en cuanto se elige el tipo
        doc_actual = actual.get("NIT") or ""
        tipo_doc = st.radio("Documento de identificación *", ["DUI", "NIT"], horizontal=True,
                            index=0 if len(_solo_digitos(doc_actual)) == 9 else 1, key=f"{clave}_tipo_doc")
    valores = {"ccf": ccf, "tipo_doc": tipo_doc, "nit": "", "nrc": "", "giro": "", "direccion": "",
               "telefono": "", "correo": ""}
    editar = bool(actual)
    with st.form(f"{clave}_form_{ccf}_{tipo_doc}", clear_on_submit=not editar):
        valores["nombre"] = st.text_input("Nombre o razón social *" if ccf else "Nombre del cliente *",
                                          value=actual.get("Nombre", ""),
                                          placeholder="Ej. Comedor La Bendición, S.A. de C.V." if ccf
                                          else "Ej. María González")
        if ccf:
            # Conserva el documento solo si coincide con el tipo elegido
            doc = actual.get("NIT") or ""
            doc = doc if len(_solo_digitos(doc)) == (9 if tipo_doc == "DUI" else 14) else ""
            c1, c2 = st.columns(2)
            if tipo_doc == "DUI":
                valores["nit"] = c1.text_input("Número de DUI *", value=doc, placeholder="00000000-0", max_chars=10,
                                               help="Escribe solo los 9 números; el guion se agrega solo.")
            else:
                valores["nit"] = c1.text_input("Número de NIT *", value=doc, placeholder="0000-000000-000-0",
                                               max_chars=17,
                                               help="Escribe solo los 14 números; los guiones se agregan solos.")
            valores["nrc"] = c2.text_input("NRC *", value=actual.get("NRC") or "", placeholder="123456-7", max_chars=8,
                                           help="Número de Registro de Contribuyente: escribe solo los números "
                                                "(hasta 7); el guion antes del dígito verificador se agrega solo.")
            giro_actual = actual.get("Giro") or None
            opciones_giro = GIROS if (giro_actual is None or giro_actual in GIROS) else [giro_actual] + GIROS
            valores["giro"] = st.selectbox(
                "Giro o actividad económica *", opciones_giro,
                index=opciones_giro.index(giro_actual) if giro_actual else None,
                placeholder="Escribe para buscar (ej. comida, ferretería, panadería)…",
                accept_new_options=True,
                help="Busca escribiendo una palabra. Si el giro no aparece, escríbelo completo y presiona Enter.") or ""
            valores["direccion"] = st.text_input("Dirección *", value=actual.get("Direccion") or "",
                                                 placeholder="Ej. Calle Libertad #10, Santa Ana")
            c3, c4 = st.columns(2)
            valores["telefono"] = c3.text_input("Teléfono de contacto", value=actual.get("Telefono") or "",
                                                placeholder="0000-0000", max_chars=9,
                                                help="8 números; el guion se agrega solo. Opcional.")
            valores["correo"] = c4.text_input("Correo electrónico", value=actual.get("Correo") or "",
                                              placeholder="cliente@correo.com")
        enviado = st.form_submit_button("💾 Guardar cambios" if editar else "Guardar cliente")
    return valores if enviado else None


def _validar(v, id_tienda, excluir_id=None):
    """Valida los datos del formulario. Devuelve (datos listos para guardar, lista de errores)."""
    errores = []
    excluir = excluir_id or 0
    nombre = v["nombre"].strip()
    datos = {"Nombre": nombre, "NIT": None, "NRC": None, "Giro": None, "Direccion": None,
             "Telefono": None, "Correo": None}
    if not nombre:
        errores.append("El nombre del cliente es obligatorio.")
    elif nombre.lower() in ("externo", "consumidor final"):
        errores.append("Ese nombre está reservado por el sistema para ventas sin registro.")
    elif consultar("""SELECT 1 FROM Cliente WHERE LOWER(Nombre) = LOWER(%s) AND Tipo = 'Publico general'
                      AND id_tienda_registro = %s AND id_cliente <> %s""", (nombre, id_tienda, excluir)):
        errores.append(f"«{nombre}» ya está registrado como cliente de tu tienda.")

    if v["ccf"]:
        tipo_doc = v["tipo_doc"]
        digitos = len(_solo_digitos(v["nit"]))
        esperados = 9 if tipo_doc == "DUI" else 14
        datos["NIT"] = formatear_nit(v["nit"]) if digitos == esperados else None
        if not datos["NIT"]:
            errores.append(f"El {tipo_doc} debe tener {esperados} números (escribiste {digitos}).")
        elif consultar("SELECT 1 FROM Cliente WHERE NIT = %s AND id_tienda_registro = %s AND id_cliente <> %s",
                       (datos["NIT"], id_tienda, excluir)):
            errores.append(f"Ya tienes otro cliente registrado con el {tipo_doc} {datos['NIT']}.")
        datos["NRC"] = formatear_nrc(v["nrc"])
        if not datos["NRC"]:
            errores.append("El NRC debe tener de 3 a 7 números (ej. 123456-7).")
        datos["Giro"] = v["giro"].strip() or None
        if not datos["Giro"]:
            errores.append("El giro es obligatorio para crédito fiscal.")
        datos["Direccion"] = v["direccion"].strip() or None
        if not datos["Direccion"]:
            errores.append("La dirección es obligatoria para crédito fiscal.")
        if v["telefono"].strip():
            datos["Telefono"] = formatear_telefono(v["telefono"])
            if not datos["Telefono"]:
                errores.append("El teléfono debe tener 8 dígitos.")
        if v["correo"].strip():
            if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v["correo"].strip()):
                datos["Correo"] = v["correo"].strip().lower()
            else:
                errores.append("El correo no tiene un formato válido.")
    return datos, errores


def _ejecutar(sql, params):
    cx = obtener_conexion()
    if not cx:
        return False
    cur = cx.cursor()
    try:
        cur.execute(sql, params)
        cx.commit()
        return True
    except mysql.connector.IntegrityError:
        st.error("❌ Ya existe un cliente con esos datos en tu tienda.")
        return False
    finally:
        cur.close()
        cx.close()


def _registrar_cliente(id_tienda):
    v = _formulario_cliente("nuevo")
    if v is None:
        return
    datos, errores = _validar(v, id_tienda)
    if errores:
        st.error("❌ Revisa los datos:\n\n" + "\n".join(f"- {e}" for e in errores))
        return
    if _ejecutar("""INSERT INTO Cliente (Nombre, Tipo, id_tienda_registro, NIT, NRC, Giro, Direccion, Telefono, Correo)
                    VALUES (%s, 'Publico general', %s, %s, %s, %s, %s, %s, %s)""",
                 (datos["Nombre"], id_tienda, datos["NIT"], datos["NRC"], datos["Giro"], datos["Direccion"],
                  datos["Telefono"], datos["Correo"])):
        st.session_state["msg_exito_cli"] = f"✅ Cliente «{datos['Nombre']}» registrado para crédito fiscal."
        st.rerun()


def _editar_cliente(id_tienda):
    clientes = consultar("""SELECT * FROM Cliente WHERE Tipo = 'Publico general' AND id_tienda_registro = %s
                            ORDER BY Nombre""", (id_tienda,))
    if not clientes:
        st.info("Aún no has registrado clientes.")
        return
    sel = st.selectbox("Cliente a modificar", [None] + clientes, key="cli_editar_sel",
                       format_func=lambda x: "-- Selecciona un cliente --" if x is None else
                       x["Nombre"] + (" · Crédito fiscal" if x["NRC"] else ""))
    if sel is None:
        return
    if not sel["NRC"]:
        st.warning("⚠️ A este cliente le faltan sus datos de crédito fiscal. Complétalos para poder facturarle.")
    v = _formulario_cliente(f"editar_{sel['id_cliente']}", actual=sel)
    if v is None:
        return
    datos, errores = _validar(v, id_tienda, excluir_id=sel["id_cliente"])
    if errores:
        st.error("❌ Revisa los datos:\n\n" + "\n".join(f"- {e}" for e in errores))
        return
    nuevos = {k: datos[k] for k in ("Nombre", "NIT", "NRC", "Giro", "Direccion", "Telefono", "Correo")}
    if all((sel.get(k) or None) == nuevos[k] for k in nuevos):
        st.info("No cambiaste ningún dato.")
        return
    # La condición id_tienda_registro asegura que una tienda solo modifique sus propios clientes
    if _ejecutar("""UPDATE Cliente SET Nombre=%s, NIT=%s, NRC=%s, Giro=%s, Direccion=%s, Telefono=%s, Correo=%s
                    WHERE id_cliente = %s AND id_tienda_registro = %s""",
                 (nuevos["Nombre"], nuevos["NIT"], nuevos["NRC"], nuevos["Giro"], nuevos["Direccion"],
                  nuevos["Telefono"], nuevos["Correo"], sel["id_cliente"], id_tienda)):
        st.session_state["msg_exito_cli"] = f"✅ Datos de «{nuevos['Nombre']}» actualizados."
        st.session_state.pop("cli_editar_sel", None)
        st.rerun()


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
                                      CASE WHEN c.NIT IS NULL THEN ''
                                        WHEN CHAR_LENGTH(c.NIT) = 10 THEN CONCAT('DUI ', c.NIT)
                                        ELSE CONCAT('NIT ', c.NIT) END AS `DUI / NIT`, IFNULL(c.NRC, '') AS NRC,
                                      IF(c.NRC IS NULL, 'Consumidor final', 'Crédito fiscal') AS Comprobante
                               FROM Cliente c JOIN Tienda t ON t.id_tienda = c.id_tienda_registro
                               WHERE c.Tipo = 'Publico general' ORDER BY t.Nombre, c.Nombre"""))
        return

    # Usuarios de tienda: solo SUS clientes
    t_nuevo, t_lista, t_editar = st.tabs(["➕ Registrar cliente", "📋 Mis clientes", "✏️ Editar cliente"])
    with t_nuevo:
        st.caption("🧾 Registra aquí a los clientes que piden **Comprobante de Crédito Fiscal**. "
                   "Las ventas sin cliente se registran como consumidor final y no necesitan registro.")
        _registrar_cliente(id_tienda)
    with t_editar:
        _editar_cliente(id_tienda)
    with t_lista:
        _lista_clientes(id_tienda)


def _lista_clientes(id_tienda):
    clientes = consultar("""SELECT id_cliente AS ID, Nombre,
                                   IF(NRC IS NULL, '⚠️ Faltan datos fiscales', '') AS Pendiente,
                                   CASE WHEN NIT IS NULL THEN ''
                                        WHEN CHAR_LENGTH(NIT) = 10 THEN CONCAT('DUI ', NIT)
                                        ELSE CONCAT('NIT ', NIT) END AS `DUI / NIT`,
                                   IFNULL(NRC, '') AS NRC, IFNULL(Giro, '') AS Giro,
                                   IFNULL(Direccion, '') AS `Dirección`, IFNULL(Telefono, '') AS `Teléfono`,
                                   IFNULL(Correo, '') AS Correo
                            FROM Cliente
                            WHERE Tipo = 'Publico general' AND id_tienda_registro = %s
                            ORDER BY Nombre""", (id_tienda,))
    if not clientes:
        st.info("Aún no has registrado clientes de crédito fiscal. Las ventas sin cliente se registran como "
                "consumidor final.")
    else:
        # La columna «Pendiente» solo se muestra si algún cliente tiene datos fiscales incompletos
        if not any(c["Pendiente"] for c in clientes):
            for c in clientes:
                c.pop("Pendiente")
        tabla(clientes)
