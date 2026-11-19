"""Formato común de las tablas: signo de dólar en columnas de dinero y encabezados legibles."""
import pandas as pd
import streamlit as st

# Una columna es de dinero si su nombre contiene alguna de estas palabras
PALABRAS_DINERO = ("precio", "total", "subtotal", "importe", "costo", "ingreso", "valor", "ahorro",
                   "ventas", "compras")
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


def tabla(data, column_config=None, **kwargs):
    """Igual que st.dataframe, pero con formato $0.00 en las columnas de dinero
    y los guiones bajos de los encabezados cambiados por espacios."""
    config = {}
    for col in _columnas(data):
        etiqueta = str(col).replace("_", " ")
        if es_dinero(col):
            config[col] = st.column_config.NumberColumn(etiqueta, format="$%.2f")
        elif etiqueta != col:
            config[col] = st.column_config.Column(etiqueta)
    config.update(column_config or {})  # lo que indique cada pantalla tiene prioridad
    kwargs.setdefault("width", "stretch")
    kwargs.setdefault("hide_index", True)
    return st.dataframe(data, column_config=config, **kwargs)
