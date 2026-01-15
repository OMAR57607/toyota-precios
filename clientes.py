import streamlit as st
import pandas as pd
import os
import zipfile
from datetime import datetime
from PIL import Image
import pytz

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Verificador Toyota",
    page_icon="🔴",
    layout="centered",
    initial_sidebar_state="collapsed" # Oculta la barra lateral en móviles para ganar espacio
)

# --- 2. CONFIGURACIÓN REGIONAL ---
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    tz_cdmx = None

def obtener_hora_mx():
    if tz_cdmx:
        return datetime.now(tz_cdmx)
    return datetime.now()

# --- 3. ESTILOS CSS ADAPTABLES (RESPONSIVE & THEME AWARE) ---
st.markdown("""
    <style>
    /* Ocultar elementos de Streamlit no deseados */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* --- TIPOGRAFÍA RESPONSIVA --- */
    /* Usamos clamp(minimo, ideal, maximo) para adaptar el tamaño */
    
    .big-price {
        /* Se adapta: Mínimo 40px, Ideal 15% del ancho, Máximo 90px */
        font-size: clamp(40px, 15vw, 90px); 
        font-weight: 800;
        color: #eb0a1e; /* Rojo Toyota (visible en dark y light mode) */
        text-align: center;
        margin: 10px 0;
        line-height: 1.1;
    }
   
    .price-label {
        font-size: clamp(14px, 4vw, 20px);
        font-weight: 600;
        /* No definimos color fijo, hereda del tema (blanco/negro) */
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 2px;
        opacity: 0.9;
    }

    .sku-title {
        font-size: clamp(18px, 5vw, 26px);
        font-weight: bold;
        text-align: center;
        margin-top: 10px;
    }
   
    .desc-text {
        font-size: clamp(16px, 4vw, 20px);
        text-align: center;
        margin-bottom: 20px;
        opacity: 0.8; /* Efecto gris sin usar color fijo */
    }

    /* Input del Buscador Adaptable */
    .stTextInput input {
        font-size: 20px;
        text-align: center;
        border: 2px solid #eb0a1e;
        border-radius: 10px;
        padding: 10px;
    }

    /* Footer Legal Adaptable */
    .legal-footer {
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid rgba(150, 150, 150, 0.3); /* Borde semitransparente */
        font-size: clamp(9px, 2.5vw, 11px);
        text-align: justify;
        font-family: sans-serif;
        line-height: 1.4;
        opacity: 0.7;
    }
    
    /* Centrado de imágenes */
    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }
    
    /* Ajustes para móviles */
    @media (max-width: 600px) {
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. CARGA DE DATOS ---
@st.cache_data
def cargar_catalogo():
    archivo_objetivo = "lista_precios.zip"
    if not os.path.exists(archivo_objetivo):
        st.error(f"⚠️ Falta archivo: {archivo_objetivo}")
        return None

    try:
        with zipfile.ZipFile(archivo_objetivo, "r") as z:
            archivos = [f for f in z.namelist() if f.endswith('.xlsx')]
            if not archivos: return None
            with z.open(archivos[0]) as f:
                df = pd.read_excel(f, dtype=str)
        
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        
        cols_sku = [c for c in df.columns if 'ITEM' in c or 'PART' in c or 'SKU' in c]
        if cols_sku:
            c_sku = cols_sku[0]
            df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.replace(' ', '').str.strip().str.upper()
            return df
        return None
    except:
        return None

df = cargar_catalogo()
fecha_actual = obtener_hora_mx()

# --- 5. HEADER ADAPTABLE ---
# Layout responsive: En móviles se apila, en escritorio usa columnas
col_vacia, col_logo, col_fecha = st.columns([1, 2, 1])

with col_logo:
    if os.path.exists("logo.png"):
        # use_container_width=True hace que el logo se adapte al ancho del celular o PC
        st.image("logo.png", use_container_width=True) 
    else:
        st.markdown("<h1 style='text-align: center; color: #eb0a1e;'>TOYOTA</h1>", unsafe_allow_html=True)

with col_fecha:
    # Fecha pequeña y alineada, se adapta al color de fondo
    st.markdown(f"""
    <div style="text-align: right; font-size: 10px; opacity: 0.8; margin-top: 5px;">
        <strong>LOS FUERTES</strong><br>
        {fecha_actual.strftime("%d/%m/%Y")}<br>
        {fecha_actual.strftime("%H:%M")}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- 6. BUSCADOR ---
st.markdown("<h3 style='text-align: center;'>🔍 Verificador de Precios</h3>", unsafe_allow_html=True)

busqueda = st.text_input("Ingresa Número de Parte:",
                         placeholder="Ej. 90915-YZZD1",
                         help="Escanea o escribe el código").strip()

# --- 7. RESULTADOS ---
if busqueda and df is not None:
    busqueda_clean = busqueda.upper().replace('-', '').replace(' ', '')
    mask = df['SKU_CLEAN'] == busqueda_clean
    resultados = df[mask]

    if not resultados.empty:
        row = resultados.iloc[0]
        
        # Detección de columnas
        c_sku = [c for c in df.columns if 'ITEM' in c or 'PART' in c or 'SKU' in c][0]
        c_desc = [c for c in df.columns if 'DESC' in c][0]
        c_precio_list = [c for c in df.columns if 'TOTAL' in c or 'UNITARIO' in c or 'PRICE' in c or 'PRECIO' in c]
        
        sku_val = row[c_sku]
        desc_val = row[c_desc]
        precio_final = 0.0
        
        if c_precio_list:
            try:
                precio_txt = str(row[c_precio_list[0]]).replace(',', '').replace('$', '').strip()
                # Ajuste de IVA (1.16)
                precio_final = float(precio_txt) * 1.16 
            except:
                precio_final = 0.0

        # Mostramos resultados con las clases CSS responsivas
        st.markdown(f"<div class='sku-title'>SKU: {sku_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='desc-text'>{desc_val}</div>", unsafe_allow_html=True)
        
        if precio_final > 0:
            st.markdown("<div class='price-label'>Precio Público (Neto)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
            st.caption("MXN - Incluye Impuestos")
        else:
            st.warning("Precio no disponible.")
    else:
        st.error("❌ Producto no encontrado.")

elif not busqueda:
    st.info("👋 Escanee el código.")

# --- 8. FOOTER LEGAL COMPACTO ---
st.markdown("---")
st.markdown(f"""
<div class="legal-footer">
    <strong>AVISO LEGAL - TOYOTA LOS FUERTES</strong><br>
    <strong>1. PRECIOS:</strong> Incluyen IVA (16%) conforme al Art. 7 Bis de la <strong>LFPC</strong>. Montos en Moneda Nacional (MXN).
    <br>
    <strong>2. VIGENCIA:</strong> Precios válidos al momento de la consulta: <strong>{fecha_actual.strftime("%d/%m/%Y %H:%M")}</strong>. Respetamos el precio exhibido salvo error de sistema.
    <br>
    <strong>3. NORMATIVIDAD:</strong> Cumple con <strong>NOM-050-SCFI-2004</strong> (Info. Comercial) y <strong>NOM-174-SCFI-2007</strong> (Transacciones electrónicas/Kioscos).
    <br>
    <strong>4. GARANTÍA:</strong> Refacciones genuinas: 12 meses o 20,000 km. Partes eléctricas sin devolución.
</div>
""", unsafe_allow_html=True)
