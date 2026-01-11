import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator

# 1. Configuración
st.set_page_config(page_title="Toyota Los Fuertes - Cotizador", page_icon="🚗", layout="wide")

# Inicializar el carrito en la memoria de la sesión si no existe
if 'carrito' not in st.session_state:
    st.session_state.carrito = pd.DataFrame(columns=['PART_NUMBER', 'DESCRIPTION', 'DESCRIPTION_ES', 'PRICE'])

# 2. Estilos
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .stHeader { background-color: #eb0a1e; } /* Rojo Toyota */
    </style>
    """, unsafe_allow_html=True)

# Función de traducción (PROFECO)
@st.cache_data
def traducir_texto(texto):
    try:
        if pd.isna(texto) or texto == "": return texto
        return GoogleTranslator(source='en', target='es').translate(texto)
    except:
        return texto

# 3. Encabezado
st.title("🚗 Sistema de Consulta y Cotización")
st.markdown("**Toyota Los Fuertes** | Control de Precios e Inventario")

# 4. Carga de datos
@st.cache_data
def cargar_catalogo():
    try:
        # Asegúrate de que el nombre coincida con tu archivo en GitHub
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        # Limpieza básica de precios si es necesario
        if 'PRICE' in df.columns:
            df['PRICE'] = pd.to_numeric(df['PRICE'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error al cargar base de datos: {e}")
        return None

df = cargar_catalogo()

# --- INTERFAZ DE COLUMNAS ---
col_busqueda, col_carrito = st.columns([2, 1])

with col_busqueda:
    st.subheader("🔍 Buscador de Refacciones")
    if df is not None:
        busqueda = st.text_input("Ingresa SKU o Nombre de pieza:", placeholder="Ej. Filter...")

        if busqueda:
            busqueda = busqueda.upper().strip()
            mask = df.apply(lambda x: x.astype(str).str.contains(busqueda, case=False)).any(axis=1)
            resultados = df[mask].head(20).copy() # Limitamos a 20 para rapidez
            
            if not resultados.empty:
                # TRADUCCIÓN EN TIEMPO REAL (Solo de los resultados)
                with st.spinner('Traduciendo descripciones para PROFECO...'):
                    resultados['DESCRIPTION_ES'] = resultados['DESCRIPTION'].apply(traducir_texto)
                
                st.write(f"Se encontraron {len(resultados)} coincidencias:")
                
                # Seleccionar columnas a mostrar
                vista_previa = resultados[['PART_NUMBER', 'DESCRIPTION_ES', 'PRICE']].copy()
                
                # MÉTODO DE SELECCIÓN: Usamos st.data_editor para permitir selección
                vista_previa['Seleccionar'] = False
                edited_df = st.data_editor(
                    vista_previa,
                    hide_index=True,
                    column_config={"Seleccionar": st.column_config.CheckboxColumn(required=True)},
                    use_container_width=True
                )

                if st.button("Añadir seleccionados al carrito 🛒"):
                    items_a_agregar = edited_df[edited_df['Seleccionar'] == True]
                    if not items_a_agregar.empty:
                        # Concatenar al carrito existente
                        st.session_state.carrito = pd.concat([st.session_state.carrito, items_a_agregar.drop(columns=['Seleccionar'])], ignore_index=True)
                        st.success("¡Agregado!")
                        st.rerun()
            else:
                st.error("No se encontraron resultados.")

with col_carrito:
    st.subheader("🛒 Mi Cotización")
    if not st.session_state.carrito.empty:
        st.dataframe(st.session_state.carrito, hide_index=True)
        
        total = st.session_state.carrito['PRICE'].sum()
        st.metric("Total (IVA Incluido)", f"${total:,.2f}")
        
        if st.button("Vaciar Carrito 🗑️"):
            st.session_state.carrito = pd.DataFrame(columns=['PART_NUMBER', 'DESCRIPTION', 'DESCRIPTION_ES', 'PRICE'])
            st.rerun()
    else:
        st.write("El carrito está vacío.")

# 6. Pie de página
st.write("---")
st.caption("Cumplimiento con NOM de PROFECO: Descripciones traducidas automáticamente.")

