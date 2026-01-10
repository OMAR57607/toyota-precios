import streamlit as st
import pandas as pd

# 1. Configuración
st.set_page_config(page_title="Toyota Los Fuertes", page_icon="🚗", layout="centered")

# 2. Estilos
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    h1 { color: #000000; }
    </style>
    """, unsafe_allow_html=True)

# 3. Encabezado
st.title("🚗 Consulta de Precios")
st.markdown("**Toyota Los Fuertes** | Lista Oficial con IVA")
st.write("---")

# 4. Carga de datos (DESDE ZIP)
@st.cache_data
def cargar_catalogo():
    try:
        # AQUI ESTA EL CAMBIO: Leemos el ZIP directamente
        # Pandas es listo y descomprime el archivo en memoria
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        return df
    except Exception as e:
        return None

# 5. Lógica
df = cargar_catalogo()

if df is not None:
    st.info("👇 Escribe el SKU o Descripción")
    busqueda = st.text_input("Buscar:", label_visibility="collapsed")

    if busqueda:
        busqueda = busqueda.upper().strip()
        mask = df.apply(lambda x: x.astype(str).str.contains(busqueda, case=False)).any(axis=1)
        resultados = df[mask]
        cantidad = len(resultados)

        if cantidad > 0:
            st.success(f"✅ {cantidad} coincidencias.")
            st.dataframe(resultados.head(50), hide_index=True, use_container_width=True)
            if cantidad > 50:
                st.warning("⚠️ Hay más resultados. Sé más específico.")
        else:
            st.error("❌ No encontrado.")
else:
    st.error("Error: No encuentro 'lista_precios.zip' o está dañado.")

# 6. Pie de página
st.write("---")

st.caption("Precios con IVA incluido. Vigencia Mes en Curso.")
