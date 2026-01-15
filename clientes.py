import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import os
import zipfile

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Consulta de Precios | Toyota",
    page_icon="🔍",
    layout="centered", # Diseño centrado tipo Google para enfoque en búsqueda
    initial_sidebar_state="collapsed" # Sin barra lateral para modo kiosco/cliente
)

# ==========================================
# 2. ESTILOS CSS (MINIMALISMO + LOGO ADAPTATIVO)
# ==========================================
st.markdown("""
    <style>
    /* Tipografía Limpia */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }

    /* Ocultar elementos de Streamlit (Menu hamburguesa, footer) para modo Kiosco */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* LOGO ADAPTATIVO */
    /* Esta clase invierte los colores de la imagen SOLO si el tema es oscuro */
    @media (prefers-color-scheme: dark) {
        .logo-adaptive img {
            filter: brightness(0) invert(1);
            opacity: 0.9;
        }
    }
    /* Forzar inversión si Streamlit está en modo oscuro */
    [data-theme="dark"] .logo-adaptive img {
        filter: brightness(0) invert(1);
    }

    /* Estilo del Buscador */
    .stTextInput input {
        font-size: 1.2rem;
        padding: 15px;
        border-radius: 25px;
        border: 2px solid #eb0a1e; /* Rojo Toyota */
    }

    /* Tarjetas de Resultados */
    .result-card {
        padding: 15px;
        border-radius: 10px;
        background-color: var(--background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .result-card:hover {
        border-color: #eb0a1e;
        transform: scale(1.01);
    }
    
    .price-tag {
        font-size: 1.4rem;
        font-weight: 800;
        color: #eb0a1e;
        text-align: right;
    }
    .iva-tag {
        font-size: 0.8rem;
        color: gray;
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS (LECTURA ROBUSTA TXT/ZIP)
# ==========================================
@st.cache_data
def cargar_catalogo_consulta():
    ARCHIVO = "lista_precios2.zip"
    c_sku = 'PART_NO'
    c_desc = 'DESCRIPTION'
    c_precio = 'PRICE'
    
    df = None

    # Lógica de carga robusta (Zip o Texto plano disfrazado)
    if os.path.exists(ARCHIVO):
        try:
            # Intento 1: Zip Real
            df = pd.read_csv(ARCHIVO, compression='zip', header=None, names=[c_sku, c_desc, c_precio], dtype=str, encoding='latin-1', sep=None, engine='python')
        except:
            try:
                # Intento 2: Texto plano
                df = pd.read_csv(ARCHIVO, compression=None, header=None, names=[c_sku, c_desc, c_precio], dtype=str, encoding='latin-1', sep=None, engine='python')
            except: df = None

    # Fallback a Demo si falla
    if df is None:
        st.warning("⚠️ Base de datos no disponible. Mostrando datos DEMO.", icon="ℹ️")
        data_demo = {
            c_sku: ["90915-YZZD1", "04465-02240", "90919-01253"],
            c_desc: ["FILTRO DE ACEITE", "BALATAS DELANTERAS", "BUJIA IRIDIUM"],
            c_precio: ["185.00", "1450.50", "320.00"]
        }
        df = pd.DataFrame(data_demo)

    # Limpieza
    try:
        df.dropna(how='all', inplace=True)
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        
        def limpiar_precio(x):
            try:
                s = str(x).replace('$', '').replace(',', '').strip()
                if s.replace('.', '', 1).isdigit(): return float(s)
                return 0.0
            except: return 0.0

        df['PRECIO_NUM'] = df[c_precio].apply(limpiar_precio)
        return df, c_sku, c_desc
    except: return None, None, None

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
    # Contenedor con clase CSS para el filtro adaptativo
    st.markdown('<div class="logo-adaptive">', unsafe_allow_html=True)
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.write("🔴 Toyota")
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
    resultados = df_db[mask].head(10) # Limitamos a 10 resultados para no saturar

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
        st.warning("No se encontraron productos que coincidan con su búsqueda.")
        st.info("Intente escribir solo los primeros 5 dígitos del número de parte.")

elif not query:
    # Estado inicial (Pantalla de bienvenida vacía)
    st.markdown("""
    <div style="text-align: center; opacity: 0.5; margin-top: 50px;">
        <h3>👋 Bienvenido</h3>
        <p>Utilice la barra de búsqueda para consultar precios al instante.</p>
    </div>
    """, unsafe_allow_html=True)

# Footer discreto
st.markdown("<br><br><div style='text-align:center; font-size:10px; color:gray;'>Toyota Los Fuertes | Sistema de Consulta v2.0</div>", unsafe_allow_html=True)

