"""Formato común de las tablas: signo de dólar en columnas de dinero y encabezados legibles."""
import pandas as pd
import streamlit as st

# Una columna es de dinero si su nombre contiene alguna de estas palabras
PALABRAS_DINERO = ("precio", "total", "subtotal", "importe", "costo", "ingreso", "valor", "ahorro",
                   "ventas", "compras", "margen")
# ...salvo estas, que son conteos
NO_DINERO = ("transacciones", "vendido", "productos")


def es_dinero(columna):
    n = str(columna).lower()
    return any(p in n for p in PALABRAS_DINERO) and not any(p in n for p in NO_DINERO)


def _columnas(data):
    if isinstance(data, pd.DataFrame):
        return list(data.columns)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return list(data[0].keys())
    return []


def _es_numero(data, col):
    """True si la columna trae números (para ponerles separador de miles)."""
    from decimal import Decimal
    if isinstance(data, pd.DataFrame):
        return pd.api.types.is_numeric_dtype(data[col]) or any(isinstance(v, Decimal) for v in data[col].dropna())
    valores = [f.get(col) for f in data if f.get(col) is not None]
    return bool(valores) and all(isinstance(v, (int, float, Decimal)) and not isinstance(v, bool) for v in valores)


def es_identificador(col):
    """Los ID y documentos no llevan coma de miles (ej. ID 1234, no 1,234)."""
    n = str(col).lower()
    return n == "id" or n.startswith("id_") or n.startswith("id ") or n in ("documento", "despacho_cd")


def _texto(valor, dinero):
    """1234.5 -> '$1,234.50' (dinero) o '1,234' (cantidad), siempre con coma de miles y punto decimal,
    sin importar el idioma del navegador."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    v = float(valor)
    if dinero:
        return f"-${abs(v):,.2f}" if v < 0 else f"${v:,.2f}"
    return f"{v:,.0f}" if v == int(v) else f"{v:,.2f}"


def _alinear(textos):
    """Rellena con espacios a la izquierda para que al ordenar la columna quede en orden numérico."""
    ancho = max((len(t) for t in textos), default=0)
    return [t.rjust(ancho) if t else t for t in textos]


def tabla(data, column_config=None, **kwargs):
    """Igual que st.dataframe, con formato $1,234.56 en las columnas de dinero, coma de miles
    en las demás cantidades (1,234) y los guiones bajos de los encabezados cambiados por espacios."""
    columnas = _columnas(data)
    config = {}
    convertir = {}
    for col in columnas:
        etiqueta = str(col).replace("_", " ")
        if es_dinero(col) and _es_numero(data, col):
            convertir[col] = True
            config[col] = st.column_config.TextColumn(etiqueta, alignment="right")
        elif _es_numero(data, col) and not es_identificador(col):
            convertir[col] = False
            config[col] = st.column_config.TextColumn(etiqueta, alignment="right")
        elif etiqueta != col:
            config[col] = st.column_config.Column(etiqueta)
    if convertir:
        df = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data, columns=columnas)
        for col, dinero in convertir.items():
            df[col] = _alinear([_texto(v, dinero) for v in df[col]])
        data = df
    config.update(column_config or {})  # lo que indique cada pantalla tiene prioridad
    kwargs.setdefault("width", "stretch")
    kwargs.setdefault("hide_index", True)
    return st.dataframe(data, column_config=config, **kwargs)
