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


def tabla(data, column_config=None, **kwargs):
    """Igual que st.dataframe, con formato $1,234.56 en las columnas de dinero, coma de miles
    en las demás cantidades (1,234) y los guiones bajos de los encabezados cambiados por espacios."""
    config = {}
    for col in _columnas(data):
        etiqueta = str(col).replace("_", " ")
        if es_dinero(col):
            config[col] = st.column_config.NumberColumn(etiqueta, format="dollar")
        elif _es_numero(data, col) and not es_identificador(col):
            config[col] = st.column_config.NumberColumn(etiqueta, format="localized")
        elif etiqueta != col:
            config[col] = st.column_config.Column(etiqueta)
    config.update(column_config or {})  # lo que indique cada pantalla tiene prioridad
    kwargs.setdefault("width", "stretch")
    kwargs.setdefault("hide_index", True)
    return st.dataframe(data, column_config=config, **kwargs)
