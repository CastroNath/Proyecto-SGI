import mysql.connector
import streamlit as st
from Módulos.login import mostrar_registro

# Verificar la conexión a la base de datos
try:
    conn = mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
    )
    conectado = conn.is_connected()
    conn.close()
except mysql.connector.Error as err:
    conectado = False
    st.error(f"Error al conectar con la base de datos: {err}")

# Si hay conexión, mostrar el formulario de registro
if conectado:
    mostrar_registro()
else:
    st.error("No se pudo conectar a la base de datos.")
