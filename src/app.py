import streamlit as st
import eda_compute

# Título principal
st.title("Proyecto Buenaventura")

# Introducción
st.write("¡Hola! Esta es la primera versión de tu aplicación en Streamlit.")

# Sección de EDA
st.header("Exploración de Datos")
eda_compute.run_eda()
