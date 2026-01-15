import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import os
import re

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Consulta de Precios | Toyota",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. ESTILOS CSS (MINIMALISMO + LOGO ADAPTATIVO)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* LOGO ADAPTATIVO */
    @media (prefers-color-scheme: dark) {
        .logo-adaptive img { filter: brightness(0) invert(1); opacity: 0.9; }
    }
    [data-theme="dark"] .logo-adaptive img { filter: brightness(0) invert(1); }

    /* Buscador */
    .stTextInput input {
        font-size: 1.2rem; padding: 15px; border-radius: 25px;
        border: 2px solid #eb0a1e;
    }

    /* Tarjetas */
    .result-card {
        padding: 15px; border-radius: 10px;
        background-color: var(--background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 10px; transition: transform 0.2s;
    }
    .result-card:hover { border-color: #eb0a1e; transform: scale(1.01); }
    
    .price-tag { font-size: 1.4rem; font-weight: 800; color: #eb0a1e; text-align: right; }
    .iva-tag { font-size: 0.8rem; color: gray; text-align: right; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS (SOPORTE EXCEL .XLS / .XLSX)
# ==========================================
@st.cache_data
def cargar_catalogo_consulta():
    # LISTA DE ARCHIVOS QUE BUSCARÁ (EN ORDEN DE PREFERENCIA)
    POSIBLES_ARCHIVOS = [
        "lista_precios.xlsx", 
        "lista_precios.xls", 
        "lista_precios2.zip", 
        "lista_precios.csv"
    ]
    
    c_sku = 'PART_NO'
    c_desc = 'DESCRIPTION'
    c_precio = 'PRICE'
    
    df = None
    archivo_encontrado = None

    # 1. BUSCAR EL ARCHIVO
    for archivo in POSIBLES_ARCHIVOS:
        if os.path.exists(archivo):
            archivo_encontrado = archivo
            break
            
    # 2. CARGAR SEGÚN EL FORMATO
    if archivo_encontrado:
        try:
            if archivo_encontrado.endswith(('.xlsx', '.xls')):
                # LÓGICA PARA EXCEL
                # header=None asume que NO tiene títulos. Si tu archivo TIENE títulos, cambia a header=0
                df = pd.read_excel(archivo_encontrado, header=None, dtype=str)
                # Asignamos nombres a las primeras 3 columnas detectadas
                df = df.iloc[:, :3] # Nos quedamos con las primeras 3 columnas
                df.columns = [c_sku, c_desc, c_precio]
                
            elif archivo_encontrado.endswith('.zip'):
                # LÓGICA PARA ZIP
                df = pd.read_csv(archivo_encontrado, compression='zip', header=None, names=[c_sku, c_desc, c_precio], dtype=str, encoding='latin-1', engine='python')
            
            elif archivo_encontrado.endswith('.csv'):
                # LÓGICA PARA CSV/TXT
                df = pd.read_csv(archivo_encontrado, header=None, names=[c_sku, c_desc, c_precio], dtype=str, encoding='latin-1', engine='python')
                
        except Exception as e:
            st.error(f"Error al leer '{archivo_encontrado}': {e}")
            df = None

    # 3. FALLBACK A DEMO
    if df is None:
        st.warning("⚠️ No se encontró lista de precios (Excel/Zip). Usando MODO DEMO.", icon="ℹ️")
        data_demo = {
            c_sku: ["90915-YZZD1", "04465-02240", "90919-01253"],
            c_desc: ["FILTRO DE ACEITE (DEMO)", "BALATAS DELANTERAS (DEMO)", "BUJIA IRIDIUM (DEMO)"],
            c_precio: ["185.00", "1450.50", "320.00"]
        }
        df = pd.DataFrame(data_demo)

    # 4. LIMPIEZA DE DATOS
    try:
        df.dropna(how='all', inplace=True)
        # Limpieza de SKU
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        
        # Limpieza de Precio
        def limpiar_precio(x):
            try:
                # Si el excel trae fórmulas o texto, intentamos limpiar
                s = str(x).replace('$', '').replace(',', '').strip()
                if s.replace('.', '', 1).isdigit(): return float(s)
                return 0.0
            except: return 0.0

        df['PRECIO_NUM'] = df[c_precio].apply(limpiar_precio)
        
        # Eliminar filas donde el precio sea 0 (posibles encabezados mal leídos)
        df = df[df['PRECIO_NUM'] > 0]
        
        return df, c_sku, c_desc
    except Exception as e:
        st.error(f"Error procesando datos: {e}")
        return None, None, None

df_db, col_sku, col_desc = cargar_catalogo_consulta()

@st.cache_data
def traducir_texto(texto):
    try: return GoogleTranslator(source='en', target='es').translate(str(texto))
    except: return str(texto)

# ==========================================
# 4. INTERFAZ DE USUARIO (KIOSCO)
# ==========================================

# --- ENCABEZADO ---
col_logo, col_titulo = st.columns([1, 4])

with col_logo:
    st.markdown('<div class="logo-adaptive">', unsafe_allow_html=True)
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("## 🔴")
    st.markdown('</div>', unsafe_allow_html=True)

with col_titulo:
    st.markdown("<h1 style='margin-top: 0px; padding-top:0px;'>Consulta de Precios</h1>", unsafe_allow_html=True)
    st.caption("Escriba el número de parte o el nombre de la refacción.")

st.markdown("---")

# --- BARRA DE BÚSQUEDA ---
query = st.text_input("🔍 Buscar:", placeholder="Ej. 90915-YZZD1 o Filtro de Aceite", label_visibility="collapsed")

# --- RESULTADOS ---
if query and df_db is not None:
    # Lógica de búsqueda
    b_clean = query.upper().strip().replace('-', '')
    # Buscar por coincidencia en descripción O sku limpio
    mask = df_db.apply(lambda x: x.astype(str).str.contains(query, case=False)).any(axis=1) | df_db['SKU_CLEAN'].str.contains(b_clean, na=False)
    resultados = df_db[mask].head(10)

    if not resultados.empty:
        st.success(f"Se encontraron {len(resultados)} resultados.")
        
        for idx, row in resultados.iterrows():
            precio_base = row['PRECIO_NUM']
            precio_iva = precio_base * 1.16
            desc_es = traducir_texto(row[col_desc])
            
            # Tarjeta de Producto
            with st.container(border=True):
                c1, c2 = st.columns([3, 1.5])
                
                with c1:
                    st.markdown(f"#### {desc_es}")
                    st.markdown(f"**SKU:** `{row[col_sku]}`")
                    st.caption("Disponibilidad: Consultar en Mostrador")
                
                with c2:
                    st.markdown(f"<div class='price-tag'>${precio_iva:,.2f}</div>", unsafe_allow_html=True)
                    st.markdown("<div class='iva-tag'>IVA Incluido</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='iva-tag'>Subtotal: ${precio_base:,.2f}</div>", unsafe_allow_html=True)
    else:
        st.warning("No se encontraron productos.")
        st.info("Intente escribir solo los primeros 5 dígitos del número de parte.")

elif not query:
    st.markdown("""
    <div style="text-align: center; opacity: 0.5; margin-top: 50px;">
        <h3>👋 Bienvenido</h3>
        <p>Utilice la barra de búsqueda para consultar precios al instante.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><br><div style='text-align:center; font-size:10px; color:gray;'>Toyota Los Fuertes | Sistema de Consulta v2.1</div>", unsafe_allow_html=True)

