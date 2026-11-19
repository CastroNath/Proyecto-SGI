import os

import mysql.connector
import streamlit as st


def _config():
    """Lee [mysql] de .streamlit/secrets.toml (o de los Secrets de Streamlit Cloud).
    Si no existe, usa variables de entorno DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME."""
    try:
        if "mysql" in st.secrets:
            return dict(st.secrets["mysql"])
    except Exception:
        pass
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "sgi_cooperativa"),
    }


def obtener_conexion():
    c = _config()
    try:
        return mysql.connector.connect(
            host=c["host"],
            port=int(c.get("port", 3306)),
            user=c["user"],
            password=c["password"],
            database=c["database"],
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
        )
    except mysql.connector.Error as error:
        st.error(f"Error al conectar con la base de datos: {error}")
        return None


def consultar(sql, params=None):
    """SELECT -> lista de diccionarios. Devuelve [] si no hay conexión."""
    cx = obtener_conexion()
    if not cx:
        return []
    cur = cx.cursor(dictionary=True)
    try:
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        cur.close()
        cx.close()


def consultar_uno(sql, params=None):
    filas = consultar(sql, params)
    return filas[0] if filas else None
