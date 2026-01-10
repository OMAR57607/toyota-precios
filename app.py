import streamlit as st
import pandas as pd

# 1. Configuración de página
st.set_page_config(page_title="Toyota Los Fuertes", page_icon="🚗", layout="centered")

# 2. Estilos (Rojo Toyota)
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    h1 { color: #CC0000; }
    </style>
    """, unsafe_allow_html=True)

# 3. Encabezado
st.title("🚗 Consulta de Precios")
st.markdown("**Toyota Los Fuertes** | Lista Oficial con IVA")
st.write("---")

# 4. Carga de datos (Memoria Caché)
@st.cache_data
def cargar_catalogo():
    # Lee el CSV. 'dtype=str' es vital para no perder ceros a la izquierda
    # 'encoding' ayuda si hay acentos o símbolos raros
    try:
        df = pd.read_csv("lista_precios.csv", dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True) # Limpiar filas vacías
        return df
    except Exception as e:
        return None

# 5. Lógica Principal
df = cargar_catalogo()

if df is not None:
    # Buscador
    st.info("👇 Escribe el SKU o Descripción (Ej. BALATA)")
    busqueda = st.text_input("Buscar:", label_visibility="collapsed")

    if busqueda:
        busqueda = busqueda.upper().strip()
        
        # Filtro: Busca en todas las columnas
        mask = df.apply(lambda x: x.astype(str).str.contains(busqueda, case=False)).any(axis=1)
        resultados = df[mask]
        cantidad = len(resultados)

        if cantidad > 0:
            st.success(f"✅ Encontramos {cantidad} coincidencias.")
            st.dataframe(resultados.head(50), hide_index=True, use_container_width=True)
            if cantidad > 50:
                st.warning("⚠️ Hay muchos resultados. Sé más específico.")
        else:
            st.error("❌ No encontrado. Intenta con otra palabra.")
else:
    st.error("Error: No se pudo cargar el archivo 'lista_precios.csv'.")

# 6. Pie de página
st.write("---")
st.caption("Precios con IVA incluido. Vigencia Mes en Curso.")