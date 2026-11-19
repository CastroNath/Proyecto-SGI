"""Reglas de negocio del sistema.

Toda operación que mueve inventario pasa por aquí y se ejecuta en UNA transacción:
si cualquier validación falla, se revierte todo (no quedan compras o ventas a medias).
Los módulos de interfaz (compras.py, ventas.py, inventario.py) solo llaman estas funciones.
"""
import hashlib
import hmac
import os
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from config.conexion import obtener_conexion

ZONA_SV = ZoneInfo("America/El_Salvador")
MARGEN_VENTA = Decimal("1.20")  # precio sugerido = costo + 20 %


class ReglaNegocioError(Exception):
    """Error de validación con un mensaje comprensible para el usuario."""


def ahora_sv():
    return datetime.now(ZONA_SV).replace(tzinfo=None)


def _d(x):
    return Decimal(str(x))


@contextmanager
def transaccion():
    cx = obtener_conexion()
    if cx is None:
        raise ReglaNegocioError("No hay conexión con la base de datos.")
    cur = cx.cursor(dictionary=True)
    try:
        cx.start_transaction()
        yield cur
        cx.commit()
    except Exception:
        cx.rollback()
        raise
    finally:
        cur.close()
        cx.close()


# =====================================================================
# 1.0 Gestión de usuarios y acceso
# =====================================================================
def hash_password(password, iteraciones=120_000):
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iteraciones).hex()
    return f"pbkdf2${iteraciones}${salt}${h}"


def verificar_password(password, almacenado):
    """Acepta hash PBKDF2. Por compatibilidad acepta texto plano (usuarios antiguos)."""
    if not almacenado.startswith("pbkdf2$"):
        return hmac.compare_digest(password, almacenado)
    try:
        _, it, salt, h = almacenado.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(it)).hex()
        return hmac.compare_digest(calc, h)
    except ValueError:
        return False


def autenticar(usuario, password):
    with transaccion() as cur:
        cur.execute("""SELECT u.id_usuario, u.Nombre, u.Contrasena, u.Activo, u.id_rol, r.Nombre AS Rol,
                              u.id_tienda, t.Nombre AS Tienda, t.Tipo AS Tipo_tienda
                       FROM Usuario u JOIN Rol r ON r.id_rol = u.id_rol
                       JOIN Tienda t ON t.id_tienda = u.id_tienda
                       WHERE u.Usuario = %s""", (usuario.strip(),))
        u = cur.fetchone()
        if not u or not verificar_password(password, u["Contrasena"]):
            raise ReglaNegocioError("Usuario o contraseña incorrectos.")
        if not u["Activo"]:
            raise ReglaNegocioError("Este usuario está desactivado. Contacte al administrador.")
        if not u["Contrasena"].startswith("pbkdf2$"):
            # Migración transparente: la contraseña en texto plano se reemplaza por su hash
            cur.execute("UPDATE Usuario SET Contrasena=%s WHERE id_usuario=%s",
                        (hash_password(password), u["id_usuario"]))
        u.pop("Contrasena")
        return u


# =====================================================================
# Consultas de apoyo
# =====================================================================
def _tienda(cur, id_tienda):
    cur.execute("SELECT * FROM Tienda WHERE id_tienda=%s", (id_tienda,))
    t = cur.fetchone()
    if not t:
        raise ReglaNegocioError("La tienda indicada no existe.")
    return t


def es_cd(tienda):
    return (tienda.get("Tipo") or "").upper() == "CD"


def _proveedor_cd(cur):
    cur.execute("SELECT p.* FROM Proveedor p JOIN Tienda t ON t.id_tienda = p.id_tienda_cd WHERE t.Tipo='CD' LIMIT 1")
    p = cur.fetchone()
    if not p:
        raise ReglaNegocioError("El Centro de Distribución no está registrado como proveedor. Ejecute la migración.")
    return p


def evaluacion_cd(cur, id_producto):
    cur.execute("SELECT * FROM v_evaluacion_cd WHERE id_producto=%s", (id_producto,))
    return cur.fetchone()


def _validar_cd_autorizado(cur, id_producto, nombre):
    ev = evaluacion_cd(cur, id_producto)
    if not ev or not ev["CD_autorizado"]:
        costo_cd = f"${ev['Costo_CD']}" if ev and ev["Costo_CD"] is not None else "sin compras registradas"
        costo_ext = f"${ev['Costo_externo']}" if ev and ev["Costo_externo"] is not None else "-"
        raise ReglaNegocioError(
            f"El CD no está autorizado para abastecer «{nombre}»: su costo de adquisición ({costo_cd}) "
            f"no es menor que el costo de los proveedores externos ({costo_ext}).")


def _validar_items(items):
    if not items:
        raise ReglaNegocioError("Debe agregar al menos un producto.")
    ids = [i["id_producto"] for i in items]
    if len(ids) != len(set(ids)):
        raise ReglaNegocioError("Hay un producto repetido; unifique las cantidades en una sola línea.")
    for i in items:
        if _d(i["cantidad"]) <= 0:
            raise ReglaNegocioError("Las cantidades deben ser mayores que cero.")


_LOTES = """
    FROM Lote l JOIN Detalle_compra dc ON dc.id_detalle_compra = l.id_detalle_compra
    JOIN Compra c ON c.id_compra = dc.id_compra
    WHERE c.id_tienda=%s AND dc.id_producto=%s AND l.Cantidad_disponible > 0"""


def existencia_vendible(cur, id_tienda, id_producto, al_dia):
    """Existencia menos lo que está en lotes vencidos (no se puede vender producto vencido)."""
    cur.execute("SELECT Existencia FROM Inventario WHERE id_tienda=%s AND id_producto=%s FOR UPDATE",
                (id_tienda, id_producto))
    inv = cur.fetchone()
    if not inv:
        return 0
    cur.execute("SELECT COALESCE(SUM(l.Cantidad_disponible),0) AS q" + _LOTES + " AND l.Fecha_vencimiento < %s",
                (id_tienda, id_producto, al_dia))
    return max(Decimal(0), _d(inv["Existencia"]) - cur.fetchone()["q"])


def _consumir_lotes(cur, id_tienda, id_producto, cantidad, al_dia):
    """Descarga lotes FEFO (primero el que vence antes), sin tocar los vencidos.
    Devuelve el vencimiento más próximo que salió (para heredarlo en despachos del CD)."""
    cur.execute("SELECT l.id_lote, l.Cantidad_disponible, l.Fecha_vencimiento" + _LOTES +
                " AND (l.Fecha_vencimiento IS NULL OR l.Fecha_vencimiento >= %s)"
                " ORDER BY l.Fecha_vencimiento IS NULL, l.Fecha_vencimiento, l.id_lote FOR UPDATE",
                (id_tienda, id_producto, al_dia))
    restante, primer_venc = _d(cantidad), None
    for lote in cur.fetchall():
        if restante <= 0:
            break
        usar = min(restante, lote["Cantidad_disponible"])
        cur.execute("UPDATE Lote SET Cantidad_disponible = Cantidad_disponible - %s WHERE id_lote=%s",
                    (usar, lote["id_lote"]))
        primer_venc = primer_venc or lote["Fecha_vencimiento"]
        restante -= usar
    return primer_venc


# =====================================================================
# 4.0 Gestión de compras
# =====================================================================
def registrar_compra(id_tienda, id_proveedor, id_usuario, items, recibida=False, fecha=None,
                     dias_entrega=1, cur=None, id_venta_origen=None):
    """Registra una orden de compra a un proveedor externo.
    items: [{id_producto, cantidad, precio_compra, precio_venta?, fecha_venc?, stock_minimo?}]
    recibida=False -> queda 'En tránsito' hasta que la tienda confirme la recepción física."""
    if cur is None:
        with transaccion() as c:
            return registrar_compra(id_tienda, id_proveedor, id_usuario, items, recibida, fecha,
                                    dias_entrega, c, id_venta_origen)
    _validar_items(items)
    fecha = fecha or ahora_sv()
    _tienda(cur, id_tienda)
    cur.execute("SELECT * FROM Proveedor WHERE id_proveedor=%s", (id_proveedor,))
    prov = cur.fetchone()
    if not prov:
        raise ReglaNegocioError("El proveedor indicado no existe.")
    if prov["id_tienda_cd"] and id_venta_origen is None:
        raise ReglaNegocioError("Las compras al Centro de Distribución se solicitan como despacho del CD.")
    for it in items:
        if _d(it["precio_compra"]) <= 0:
            raise ReglaNegocioError("El precio de compra debe ser mayor que cero.")
        fv = it.get("fecha_venc")
        if fv and (fv if isinstance(fv, date) else date.fromisoformat(str(fv))) <= fecha.date():
            raise ReglaNegocioError("La fecha de vencimiento debe ser posterior a la fecha de compra.")

    total = sum(_d(i["cantidad"]) * _d(i["precio_compra"]) for i in items)
    cur.execute("""INSERT INTO Compra (id_tienda, id_proveedor, id_usuario, Fecha, Fecha_entrega_estimada,
                                       Total, Estado, id_venta_origen)
                   VALUES (%s,%s,%s,%s,%s,%s,'En tránsito',%s)""",
                (id_tienda, id_proveedor, id_usuario, fecha, fecha + timedelta(days=int(dias_entrega)),
                 total, id_venta_origen))
    id_compra = cur.lastrowid
    for it in items:
        cur.execute("""INSERT INTO Detalle_compra (id_compra, id_producto, Cantidad, Precio_compra,
                                                   Precio_venta_sugerido, Fecha_vencimiento)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (id_compra, it["id_producto"], it["cantidad"], it["precio_compra"],
                     it.get("precio_venta"), it.get("fecha_venc") or None))
        if it.get("stock_minimo") is not None:
            # Deja preparado el punto de reorden calculado (la existencia sube al recibir)
            cur.execute("""INSERT INTO Inventario (id_tienda, id_producto, Existencia, Stock_minimo, Precio_venta)
                           VALUES (%s,%s,0,%s,%s)
                           ON DUPLICATE KEY UPDATE Stock_minimo = VALUES(Stock_minimo)""",
                        (id_tienda, it["id_producto"], it["stock_minimo"], it.get("precio_venta") or 0))
    if recibida:
        _aplicar_recepcion(cur, id_compra, fecha)
    return id_compra


def _aplicar_recepcion(cur, id_compra, fecha):
    """Entrada a inventario + creación de lotes + actualización de ProductoxProveedor."""
    cur.execute("SELECT * FROM Compra WHERE id_compra=%s", (id_compra,))
    compra = cur.fetchone()
    cur.execute("SELECT * FROM Detalle_compra WHERE id_compra=%s", (id_compra,))
    for dc in cur.fetchall():
        if dc["id_producto"] is None:
            raise ReglaNegocioError(f"La compra #{id_compra} tiene líneas sin producto (registro antiguo).")
        sugerido = dc["Precio_venta_sugerido"]
        cur.execute("""INSERT INTO Inventario (id_tienda, id_producto, Existencia, Stock_minimo, Precio_venta)
                       VALUES (%s,%s,%s,5,%s)
                       ON DUPLICATE KEY UPDATE Existencia = Existencia + VALUES(Existencia),
                           Precio_venta = IF(%s IS NULL, Precio_venta, %s)""",
                    (compra["id_tienda"], dc["id_producto"], int(dc["Cantidad"]), sugerido or 0, sugerido, sugerido))
        cur.execute("INSERT INTO Lote (id_detalle_compra, Fecha_vencimiento, Cantidad_disponible) VALUES (%s,%s,%s)",
                    (dc["id_detalle_compra"], dc["Fecha_vencimiento"], dc["Cantidad"]))
        cur.execute("""INSERT INTO ProductoxProveedor (id_producto, id_proveedor, Ultimo_precio, Fecha_ultima_compra)
                       VALUES (%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE Ultimo_precio = VALUES(Ultimo_precio),
                                               Fecha_ultima_compra = VALUES(Fecha_ultima_compra)""",
                    (dc["id_producto"], compra["id_proveedor"], dc["Precio_compra"], fecha.date()))
    cur.execute("UPDATE Compra SET Estado='Recibida', Fecha_recepcion=%s WHERE id_compra=%s", (fecha, id_compra))


def recibir_compra(id_compra, id_tienda_usuario, fecha=None):
    """La tienda confirma que recibió físicamente la mercadería de un proveedor externo."""
    with transaccion() as cur:
        cur.execute("SELECT * FROM Compra WHERE id_compra=%s FOR UPDATE", (id_compra,))
        c = cur.fetchone()
        if not c:
            raise ReglaNegocioError("La compra no existe.")
        if c["id_tienda"] != id_tienda_usuario:
            raise ReglaNegocioError("Solo la tienda que hizo la compra puede confirmar su recepción.")
        if c["Estado"] != "En tránsito":
            raise ReglaNegocioError(f"La compra ya está en estado «{c['Estado']}».")
        _aplicar_recepcion(cur, id_compra, fecha or ahora_sv())


def anular_compra(id_compra, id_tienda_usuario):
    with transaccion() as cur:
        cur.execute("SELECT * FROM Compra WHERE id_compra=%s FOR UPDATE", (id_compra,))
        c = cur.fetchone()
        if not c or c["id_tienda"] != id_tienda_usuario or c["Estado"] != "En tránsito":
            raise ReglaNegocioError("Solo se pueden anular órdenes propias que sigan en tránsito.")
        cur.execute("UPDATE Compra SET Estado='Anulada' WHERE id_compra=%s", (id_compra,))


# =====================================================================
# 2.0 Gestión de ventas (incluye despachos CD -> tienda)
# =====================================================================
def registrar_venta(id_tienda, id_usuario, id_cliente, items, fecha=None):
    """items: [{id_producto, cantidad, precio?}] (sin precio = precio de venta del inventario).
    Si el cliente es una tienda: solo el CD puede vender, se valida la regla de costo y la
    venta queda 'En tránsito' hasta que la tienda receptora confirme la recepción."""
    _validar_items(items)
    fecha = fecha or ahora_sv()
    with transaccion() as cur:
        tienda = _tienda(cur, id_tienda)
        cur.execute("SELECT * FROM Cliente WHERE id_cliente=%s", (id_cliente,))
        cliente = cur.fetchone()
        if not cliente:
            raise ReglaNegocioError("El cliente indicado no existe.")
        a_tienda = cliente["Tipo"] == "Tienda"
        if a_tienda:
            if not es_cd(tienda):
                raise ReglaNegocioError("Solo el Centro de Distribución puede vender a otras tiendas.")
            if not cliente["id_tienda"]:
                raise ReglaNegocioError("El cliente tipo Tienda no está enlazado a una sucursal.")
            if cliente["id_tienda"] == id_tienda:
                raise ReglaNegocioError("El CD no puede venderse a sí mismo.")

        lineas, total = [], Decimal(0)
        for it in items:
            cur.execute("""SELECT i.*, p.Nombre FROM Inventario i JOIN Producto p ON p.id_producto = i.id_producto
                           WHERE i.id_tienda=%s AND i.id_producto=%s""", (id_tienda, it["id_producto"]))
            inv = cur.fetchone()
            nombre = inv["Nombre"] if inv else f"producto {it['id_producto']}"
            cant = _d(it["cantidad"])
            if cant != int(cant):
                raise ReglaNegocioError("Las cantidades vendidas deben ser enteras.")
            disp = existencia_vendible(cur, id_tienda, it["id_producto"], fecha.date())
            if disp < cant:
                raise ReglaNegocioError(f"Existencia insuficiente de «{nombre}»: disponible (no vencido) "
                                        f"{disp:g}, solicitado {cant:g}.")
            precio = _d(it["precio"]) if it.get("precio") else _d(inv["Precio_venta"])
            if precio <= 0:
                raise ReglaNegocioError(f"«{nombre}» no tiene precio de venta definido.")
            if a_tienda:
                _validar_cd_autorizado(cur, it["id_producto"], nombre)
            lineas.append((it["id_producto"], int(cant), precio))
            total += cant * precio

        cur.execute("""INSERT INTO Venta (id_tienda, id_usuario, id_cliente, Fecha, Total, Estado)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (id_tienda, id_usuario, id_cliente, fecha, total, "En tránsito" if a_tienda else "Entregada"))
        id_venta = cur.lastrowid
        for id_prod, cant, precio in lineas:
            venc = _consumir_lotes(cur, id_tienda, id_prod, cant, fecha.date())
            cur.execute("""INSERT INTO Detalle_venta (id_venta, id_producto, Cantidad, Precio_unitario, Fecha_vencimiento)
                           VALUES (%s,%s,%s,%s,%s)""", (id_venta, id_prod, cant, precio, venc))
            cur.execute("UPDATE Inventario SET Existencia = Existencia - %s WHERE id_tienda=%s AND id_producto=%s",
                        (cant, id_tienda, id_prod))
    return id_venta


def solicitar_al_cd(id_tienda, id_usuario, items, fecha=None):
    """La tienda pide mercadería al CD: se genera la salida (venta) en el CD, en tránsito."""
    with transaccion() as cur:
        cur.execute("SELECT id_tienda FROM Tienda WHERE Tipo='CD' LIMIT 1")
        cd = cur.fetchone()
        cur.execute("SELECT id_cliente FROM Cliente WHERE id_tienda=%s", (id_tienda,))
        cli = cur.fetchone()
    if not cd or not cli:
        raise ReglaNegocioError("Falta registrar el CD o esta tienda como cliente del CD.")
    return registrar_venta(cd["id_tienda"], id_usuario, cli["id_cliente"], items, fecha)


def confirmar_despacho_cd(id_venta, id_tienda_destino, id_usuario, fecha=None):
    """La tienda recibe físicamente el despacho del CD: AHORA se registra su compra
    (proveedor = CD, precio = precio del despacho) y entra a su inventario."""
    fecha = fecha or ahora_sv()
    with transaccion() as cur:
        cur.execute("""SELECT v.*, c.id_tienda AS tienda_destino FROM Venta v
                       JOIN Cliente c ON c.id_cliente = v.id_cliente
                       WHERE v.id_venta=%s FOR UPDATE""", (id_venta,))
        v = cur.fetchone()
        if not v or v["tienda_destino"] != id_tienda_destino:
            raise ReglaNegocioError("Ese despacho no está dirigido a su tienda.")
        if v["Estado"] != "En tránsito":
            raise ReglaNegocioError("Ese despacho ya fue recibido.")
        cur.execute("SELECT * FROM Detalle_venta WHERE id_venta=%s", (id_venta,))
        items = [{"id_producto": d["id_producto"], "cantidad": d["Cantidad"], "precio_compra": d["Precio_unitario"],
                  "precio_venta": (_d(d["Precio_unitario"]) * MARGEN_VENTA).quantize(Decimal("0.01")),
                  "fecha_venc": None} for d in cur.fetchall()]
        prov = _proveedor_cd(cur)
        id_compra = registrar_compra(id_tienda_destino, prov["id_proveedor"], id_usuario, items, recibida=False,
                                     fecha=fecha, cur=cur, id_venta_origen=id_venta)
        # Hereda el vencimiento de los lotes que despachó el CD
        cur.execute("""UPDATE Detalle_compra dc JOIN Detalle_venta dv
                         ON dv.id_venta=%s AND dv.id_producto = dc.id_producto
                       SET dc.Fecha_vencimiento = dv.Fecha_vencimiento WHERE dc.id_compra=%s""", (id_venta, id_compra))
        _aplicar_recepcion(cur, id_compra, fecha)
        cur.execute("UPDATE Venta SET Estado='Entregada' WHERE id_venta=%s", (id_venta,))
    return id_compra


# =====================================================================
# 3.0 Gestión de inventarios: bajas con trazabilidad
# =====================================================================
def dar_baja_vencidos(id_tienda, id_usuario, fecha=None):
    fecha = fecha or ahora_sv()
    total = 0
    with transaccion() as cur:
        cur.execute("""SELECT l.id_lote, l.Cantidad_disponible, dc.id_producto
                       FROM Lote l JOIN Detalle_compra dc ON dc.id_detalle_compra = l.id_detalle_compra
                       JOIN Compra c ON c.id_compra = dc.id_compra
                       WHERE c.id_tienda=%s AND l.Cantidad_disponible > 0 AND l.Fecha_vencimiento < %s
                       FOR UPDATE""", (id_tienda, fecha.date()))
        for l in cur.fetchall():
            q = int(l["Cantidad_disponible"])
            cur.execute("UPDATE Lote SET Cantidad_disponible = 0 WHERE id_lote=%s", (l["id_lote"],))
            cur.execute("""UPDATE Inventario SET Existencia = GREATEST(Existencia - %s, 0)
                           WHERE id_tienda=%s AND id_producto=%s""", (q, id_tienda, l["id_producto"]))
            cur.execute("""INSERT INTO Ajuste_inventario (id_tienda, id_producto, id_usuario, id_lote, Fecha, Cantidad,
                                                          Motivo, Observacion)
                           VALUES (%s,%s,%s,%s,%s,%s,'Vencimiento','Baja de lote vencido')""",
                        (id_tienda, l["id_producto"], id_usuario, l["id_lote"], fecha, -q))
            total += q
    return total


def baja_manual(id_tienda, id_producto, id_usuario, cantidad, motivo, observacion=None):
    cant = int(cantidad)
    if cant <= 0:
        raise ReglaNegocioError("La cantidad a dar de baja debe ser mayor que cero.")
    with transaccion() as cur:
        cur.execute("SELECT Existencia FROM Inventario WHERE id_tienda=%s AND id_producto=%s FOR UPDATE",
                    (id_tienda, id_producto))
        inv = cur.fetchone()
        if not inv or inv["Existencia"] < cant:
            raise ReglaNegocioError("No hay existencia suficiente para la baja.")
        _consumir_lotes(cur, id_tienda, id_producto, cant, date(1900, 1, 1))
        cur.execute("UPDATE Inventario SET Existencia = Existencia - %s WHERE id_tienda=%s AND id_producto=%s",
                    (cant, id_tienda, id_producto))
        cur.execute("""INSERT INTO Ajuste_inventario (id_tienda, id_producto, id_usuario, Fecha, Cantidad, Motivo, Observacion)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (id_tienda, id_producto, id_usuario, ahora_sv(), -cant, motivo, observacion))
