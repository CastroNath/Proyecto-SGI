import streamlit as st
import mysql.connector
from config.conexion import obtener_conexion

def fmt_dui(k):
    n = "".join(filter(str.isdigit, st.session_state.get(k, "")))[:9]
    st.session_state[k] = f"{n[:8]}-{n[8:]}" if len(n) > 8 else n

def fmt_nit(k):
    n = "".join(filter(str.isdigit, st.session_state.get(k, "")))[:14]
    if len(n) > 13: st.session_state[k] = f"{n[:4]}-{n[4:10]}-{n[10:13]}-{n[13:]}"
    elif len(n) > 10: st.session_state[k] = f"{n[:4]}-{n[4:10]}-{n[10:]}"
    elif len(n) > 4: st.session_state[k] = f"{n[:4]}-{n[4:]}"
    else: st.session_state[k] = n

def fmt_tel(k):
    n = "".join(filter(str.isdigit, st.session_state.get(k, "")))[:8]
    st.session_state[k] = f"{n[:4]}-{n[4:]}" if len(n) > 4 else n

def validar_datos(nombre, tipo_doc, raw_doc, raw_tel):
    if not nombre.strip():
        return False, "⚠️ El nombre completo o razón social es obligatorio.", None, None
    nd = "".join(filter(str.isdigit, raw_doc))
    nt = "".join(filter(str.isdigit, raw_tel))
    if tipo_doc == "DUI" and len(nd) != 9:
        return False, "❌ El DUI debe tener 9 dígitos.", None, None
    if tipo_doc == "NIT" and len(nd) != 14:
        return False, "❌ El NIT debe tener 14 dígitos.", None, None
    if len(nt) > 0 and len(nt) != 8:
        return False, "❌ El teléfono debe tener 8 dígitos.", None, None
    doc_ok = f"{nd[:8]}-{nd[8:]}" if tipo_doc == "DUI" else (f"{nd[:4]}-{nd[4:10]}-{nd[10:13]}-{nd[13:]}" if tipo_doc == "NIT" else None)
    tel_ok = f"{nt[:4]}-{nt[4:]}" if len(nt) == 8 else None
    return True, "", doc_ok, tel_ok

def mostrar_proveedores():
    st.header("🚚 Gestión de Proveedores")
    tab1, tab2 = st.tabs(["➕ Registrar Nuevo Proveedor", "📋 Directorio y Edición"])

    with tab1:
        if st.session_state.get("limpiar_prov", False):
            for k, v in [("p_nom", ""), ("p_tipo", "Persona Natural"), ("p_rad", "Ninguno"), ("p_dui", ""), ("p_nit", ""), ("p_tel", "")]:
                st.session_state[k] = v
            st.session_state["limpiar_prov"] = False

        if st.session_state.get("ok_prov"):
            st.success(st.session_state.pop("ok_prov"))

        for k, v in [("p_nom", ""), ("p_tipo", "Persona Natural"), ("p_rad", "Ninguno"), ("p_dui", ""), ("p_nit", ""), ("p_tel", "")]:
            if k not in st.session_state: st.session_state[k] = v

        nom = st.text_input("Nombre Completo o Razón Social", key="p_nom")
        tipo = st.selectbox("Tipo de Proveedor", ["Persona Natural", "Empresa", "Cooperativa"], key="p_tipo")
        opc = ["Ninguno", "DUI"] if tipo == "Persona Natural" else ["Ninguno", "NIT"]
        if st.session_state["p_rad"] not in opc: st.session_state["p_rad"] = "Ninguno"
        tdoc = st.radio("Documento de Identificación", opc, horizontal=True, key="p_rad")

        raw_doc = ""
        if tdoc == "DUI":
            raw_doc = st.text_input("Número de DUI", max_chars=10 if "-" in st.session_state["p_dui"] else 9, placeholder="00000000-0", key="p_dui", on_change=fmt_dui, args=("p_dui",))
        elif tdoc == "NIT":
            raw_doc = st.text_input("Número de NIT", max_chars=17 if "-" in st.session_state["p_nit"] else 14, placeholder="0000-000000-000-0", key="p_nit", on_change=fmt_nit, args=("p_nit",))

        raw_tel = st.text_input("Teléfono", max_chars=9 if "-" in st.session_state["p_tel"] else 8, placeholder="0000-0000", key="p_tel", on_change=fmt_tel, args=("p_tel",))

        if st.button("Guardar Proveedor", key="btn_save_p"):
            valido, err, doc_f, tel_f = validar_datos(nom, tdoc, raw_doc, raw_tel)
            if not valido:
                st.error(err)
            else:
                cx = obtener_conexion()
                if cx:
                    try:
                        cur = cx.cursor()
                        cur.execute("INSERT INTO Proveedor (Nombre, Tipo, DUI_NIT, Telefono) VALUES (%s, %s, %s, %s)", (nom.strip(), tipo, doc_f, tel_f))
                        cx.commit()
                        st.session_state["ok_prov"] = f"✅ Proveedor '{nom.strip()}' registrado."
                        st.session_state["limpiar_prov"] = True
                        st.rerun()
                    except mysql.connector.IntegrityError as e:
                        st.error("❌ El documento o teléfono ingresado ya pertenece a otro proveedor." if ("DUI_NIT" in str(e) or "Telefono" in str(e)) else "❌ Datos duplicados.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        cur.close(); cx.close()

    with tab2:
        if st.session_state.get("limpiar_ed_prov", False):
            st.session_state["sel_ed_p"] = None
            st.session_state["last_ed_id"] = None
            for k, v in [("ed_nom", ""), ("ed_tipo", "Persona Natural"), ("ed_rad", "Ninguno"), ("ed_dui", ""), ("ed_nit", ""), ("ed_tel", "")]:
                st.session_state[k] = v
            st.session_state["limpiar_ed_prov"] = False

        if st.session_state.get("ok_edit_p"):
            st.success(st.session_state.pop("ok_edit_p"))

        cx = obtener_conexion()
        provs = []
        if cx:
            try:
                cur = cx.cursor(dictionary=True)
                cur.execute("SELECT id_proveedor, Nombre, Tipo, DUI_NIT, Telefono FROM Proveedor ORDER BY id_proveedor ASC")
                provs = cur.fetchall()
            finally:
                cur.close(); cx.close()

        if not provs:
            st.info("📭 No hay proveedores registrados.")
            return

        st.subheader("Directorio de Proveedores")
        st.dataframe(provs, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("✏️ Editar Información")

        opciones_ed = [None] + provs
        sel = st.selectbox(
            "Selecciona el proveedor a modificar",
            opciones_ed,
            format_func=lambda x: "-- Selecciona un proveedor --" if x is None else f"{x['id_proveedor']} - {x['Nombre']} ({x['Tipo']})",
            key="sel_ed_p"
        )

        if sel is None:
            st.session_state["last_ed_id"] = None
            for k, v in [("ed_nom", ""), ("ed_tipo", "Persona Natural"), ("ed_rad", "Ninguno"), ("ed_dui", ""), ("ed_nit", ""), ("ed_tel", "")]:
                st.session_state[k] = v
        else:
            pid = sel["id_proveedor"]
            if st.session_state.get("last_ed_id") != pid:
                st.session_state["last_ed_id"] = pid
                st.session_state["ed_nom"] = sel["Nombre"]
                st.session_state["ed_tipo"] = sel["Tipo"] if sel["Tipo"] in ["Persona Natural", "Empresa", "Cooperativa"] else "Empresa"
                doc_bd = sel["DUI_NIT"] or ""
                st.session_state["ed_rad"] = "DUI" if len(doc_bd) == 10 else ("NIT" if len(doc_bd) == 17 else "Ninguno")
                st.session_state["ed_dui"] = doc_bd if len(doc_bd) == 10 else ""
                st.session_state["ed_nit"] = doc_bd if len(doc_bd) == 17 else ""
                st.session_state["ed_tel"] = sel["Telefono"] or ""

        enom = st.text_input("Nombre Completo o Razón Social", key="ed_nom", disabled=(sel is None))
        etipo = st.selectbox("Tipo de Proveedor", ["Persona Natural", "Empresa", "Cooperativa"], key="ed_tipo", disabled=(sel is None))
        eopc = ["Ninguno", "DUI"] if etipo == "Persona Natural" else ["Ninguno", "NIT"]
        if st.session_state.get("ed_rad") not in eopc: st.session_state["ed_rad"] = "Ninguno"
        etdoc = st.radio("Documento de Identificación", eopc, horizontal=True, key="ed_rad", disabled=(sel is None))

        eraw_doc = ""
        if etdoc == "DUI":
            eraw_doc = st.text_input("Número de DUI", max_chars=10 if "-" in st.session_state["ed_dui"] else 9, placeholder="00000000-0", key="ed_dui", on_change=fmt_dui, args=("ed_dui",), disabled=(sel is None))
        elif etdoc == "NIT":
            eraw_doc = st.text_input("Número de NIT", max_chars=17 if "-" in st.session_state["ed_nit"] else 14, placeholder="0000-000000-000-0", key="ed_nit", on_change=fmt_nit, args=("ed_nit",), disabled=(sel is None))

        eraw_tel = st.text_input("Teléfono", max_chars=9 if "-" in st.session_state["ed_tel"] else 8, placeholder="0000-0000", key="ed_tel", on_change=fmt_tel, args=("ed_tel",), disabled=(sel is None))

        if st.button("💾 Actualizar Proveedor", key="btn_upd_p", disabled=(sel is None)):
            valido, err, doc_f, tel_f = validar_datos(enom, etdoc, eraw_doc, eraw_tel)
            if not valido:
                st.error(err)
            else:
                cx = obtener_conexion()
                if cx:
                    try:
                        cur = cx.cursor()
                        cur.execute("UPDATE Proveedor SET Nombre=%s, Tipo=%s, DUI_NIT=%s, Telefono=%s WHERE id_proveedor=%s", (enom.strip(), etipo, doc_f, tel_f, sel["id_proveedor"]))
                        cx.commit()
                        st.session_state["ok_edit_p"] = f"✅ Datos de '{enom.strip()}' actualizados."
                        st.session_state["limpiar_ed_prov"] = True
                        st.rerun()
                    except mysql.connector.IntegrityError as e:
                        st.error("❌ El documento o teléfono ya pertenece a otro proveedor." if ("DUI_NIT" in str(e) or "Telefono" in str(e)) else "❌ Error de duplicidad.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        cur.close(); cx.close()
