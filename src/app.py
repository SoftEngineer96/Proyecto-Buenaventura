import streamlit as st
import streamlit as st
import eda_compute

# Título principal
st.title("Proyecto Buenaventura")

# Mensaje inicial
st.write("¡Hola! Esta es la primera versión de tu aplicación en Streamlit.")

st.title("Proyecto Buenaventura")

st.header("Exploración de Datos")

# Aquí llamamos la función principal de eda_compute
eda_compute.run_eda()
