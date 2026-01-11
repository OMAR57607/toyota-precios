import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator

# 1. Configuración
st.set_page_config(page_title="Toyota Los Fuertes", page_icon="🚗", layout="wide")

# Inicializar el carrito en la memoria del navegador
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 2. Estilos
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    h1 { color: #eb0a1e; }
    </style>
    """, unsafe_allow_html=True)

# Función de traducción para PROFECO
@st.cache_data
def traducir_profe(texto):
    try:
        if pd.isna(texto) or texto == "": return "Sin descripción"
        return GoogleTranslator(source='en', target='es').translate(str(texto))
    except:
        return texto

# 3. Encabezado
st.title("🚗 Consulta de Precios")
st.markdown("**Toyota Los Fuertes** | Lista Oficial con IVA")
st.write("---")

# 4. Carga de datos (DESDE ZIP)
@st.cache_data
def cargar_catalogo():
    try:
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        # LIMPIEZA DE COLUMNAS: Quita espacios y pone todo en mayúsculas
        df.columns = [c.strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

df = cargar_catalogo()

if df is not None:
    # Creamos dos columnas: una para buscar y otra para el carrito
    col_izq, col_der = st.columns([2, 1])

    with col_izq:
        st.info("👇 Escribe el SKU o Descripción")
        busqueda = st.text_input("Buscar:", label_visibility="collapsed")

        if busqueda:
            busqueda = busqueda.upper().strip()
            # Buscamos en todas las columnas
            mask = df.apply(lambda x: x.astype(str).str.contains(busqueda, case=False)).any(axis=1)
            resultados = df[mask].head(25).copy() # Copia para evitar alertas de Pandas

            if not resultados.empty:
                # Identificar nombres de columnas dinámicamente
                c_sku = [c for c in resultados.columns if 'PART' in c or 'NUM' in c][0]
                c_desc = [c for c in resultados.columns if 'DESC' in c][0]
                c_precio = [c for c in resultados.columns if 'PRICE' in c or 'PRECIO' in c][0]

                # Traducir solo lo que se va a mostrar
                with st.spinner('Traduciendo descripciones...'):
                    resultados['DESCRIPCIÓN_ES'] = resultados[c_desc].apply(traducir_profe)
                
                # Mostrar resultados con opción de añadir
                for i, row in resultados.iterrows():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.write(f"**{row['DESCRIPCIÓN_ES']}** ({row[c_sku]})")
                    c2.write(f"${row[c_precio]}")
                    if c3.button("Añadir 🛒", key=f"btn_{i}"):
                        item = {"SKU": row[c_sku], "Desc": row['DESCRIPCIÓN_ES'], "Precio": row[c_precio]}
                        st.session_state.carrito.append(item)
                        st.toast(f"Agregado: {row[c_sku]}")
            else:
                st.error("❌ No encontrado.")

    with col_der:
        st.subheader("🛒 Carrito")
        if st.session_state.carrito:
            df_carro = pd.DataFrame(st.session_state.carrito)
            st.table(df_carro[['SKU', 'Precio']])
            
            # Convertir precios a número para sumar
            total = pd.to_numeric(df_carro['Precio'], errors='coerce').sum()
            st.write(f"### Total: ${total:,.2f}")
            
            if st.button("Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.write("Tu carrito está vacío.")

else:
    st.error("Error: No encuentro 'lista_precios.zip' o las columnas no coinciden.")

st.write("---")
st.caption("Precios con IVA incluido. Descripciones traducidas para cumplimiento de normativas PROFECO.")
