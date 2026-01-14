import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
import pytz
from PIL import Image

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Toyota Los Fuertes - Consulta de Precios", 
    page_icon="🚗", 
    layout="centered" # Layout centrado para efecto "Minimalista/App"
)

# Configurar Zona Horaria CDMX
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    tz_cdmx = None 

def obtener_hora_mx():
    if tz_cdmx:
        return datetime.now(tz_cdmx)
    return datetime.now()

# 2. ESTILOS CSS MODERNOS Y MINIMALISTAS
st.markdown("""
    <style>
    /* Fondo y fuentes */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Input de búsqueda estilizado */
    .stTextInput input {
        border-radius: 20px;
        border: 2px solid #eb0a1e;
        padding: 10px 15px;
        font-size: 16px;
        text-align: center;
    }
    
    /* Tarjeta de Resultado */
    .result-card {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #eb0a1e;
    }
    
    .sku-text {
        color: #666;
        font-size: 12px;
        font-family: monospace;
        letter-spacing: 1px;
    }
    
    .desc-text {
        color: #000;
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 10px;
    }
    
    .price-container {
        display: flex;
        justify-content: space-between;
        align-items: end;
        margin-top: 10px;
        border-top: 1px solid #eee;
        padding-top: 10px;
    }
    
    .price-label {
        font-size: 10px;
        color: #888;
        text-transform: uppercase;
    }
    
    .price-big {
        color: #eb0a1e;
        font-size: 28px;
        font-weight: 800;
    }
    
    /* Footer Legal */
    .legal-footer {
        text-align: center; 
        font-size: 10px; 
        color: #999;
        margin-top: 60px; 
        padding-top: 20px;
        border-top: 1px solid #eee;
        font-family: sans-serif;
        line-height: 1.4;
    }
    </style>
    """, unsafe_allow_html=True)

# Traductor
@st.cache_data
def traducir_profe(texto):
    try:
        if pd.isna(texto) or texto == "": return "Sin descripción"
        return GoogleTranslator(source='en', target='es').translate(str(texto))
    except: return texto

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_catalogo():
    try:
        # Carga optimizada
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        
        c_sku = [c for c in df.columns if 'PART' in c or 'NUM' in c][0]
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        
        return df
    except Exception as e:
        st.error(f"Error cargando base de datos: {e}")
        return None

df = cargar_catalogo()
fecha_actual_mx = obtener_hora_mx()
fecha_hoy_str = fecha_actual_mx.strftime("%d/%m/%Y")

# --- INTERFAZ PRINCIPAL ---

# 1. HEADER CON LOGO
col_l, col_c, col_r = st.columns([1,2,1])
with col_c:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.markdown("<h2 style='text-align: center; color: #eb0a1e;'>TOYOTA LOS FUERTES</h2>", unsafe_allow_html=True)

st.write("") # Espacio
st.markdown("<h5 style='text-align: center; color: #555;'>Consulta de Precios al Público</h5>", unsafe_allow_html=True)

# 2. BARRA DE BÚSQUEDA (CENTER STAGE)
busqueda = st.text_input("🔍", placeholder="Ingresa SKU o Nombre de la parte...", label_visibility="hidden")

if df is not None and busqueda:
    busqueda_raw = busqueda.upper().strip()
    busqueda_clean = busqueda_raw.replace('-', '')
    
    # Lógica de filtrado
    mask_desc = df.apply(lambda x: x.astype(str).str.contains(busqueda_raw, case=False)).any(axis=1)
    mask_sku = df['SKU_CLEAN'].str.contains(busqueda_clean, na=False)
    resultados = df[mask_desc | mask_sku].head(5).copy() # Limitado a 5 para limpieza visual

    if not resultados.empty:
        c_sku = [c for c in resultados.columns if 'PART' in c or 'NUM' in c][0]
        c_desc = [c for c in resultados.columns if 'DESC' in c][0]
        c_precio = [c for c in resultados.columns if 'PRICE' in c or 'PRECIO' in c][0]

        st.write("")
        # --- CARDS DE RESULTADOS ---
        for i, row in resultados.iterrows():
            desc_es = traducir_profe(row[c_desc])
            sku_val = row[c_sku]
            try:
                precio_texto = str(row[c_precio]).replace(',', '').replace('$', '').strip()
                precio_val = float(precio_texto)
            except: precio_val = 0.0

            # Cálculo de Total (Neto)
            total_neto = precio_val * 1.16
            
            # HTML Card
            st.markdown(f"""
            <div class="result-card">
                <div class="sku-text">SKU: {sku_val}</div>
                <div class="desc-text">{desc_es}</div>
                <div class="price-container">
                    <div>
                        <div class="price-label">Precio Unitario</div>
                        <div style="font-size: 11px; color: #888;">(Inc. IVA 16%)</div>
                    </div>
                    <div class="price-big">${total_neto:,.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.warning("No se encontraron coincidencias en el catálogo.")

# 3. FOOTER LEGAL (PROFECO / NOM)
st.markdown(f"""
    <div class="legal-footer">
        <p><strong>INFORMACIÓN AL CONSUMIDOR</strong></p>
        <p>
            En cumplimiento a lo dispuesto por la <strong>Ley Federal de Protección al Consumidor (LFPC)</strong> y la <strong>Norma Oficial Mexicana NOM-050-SCFI-2004</strong>:
        </p>
        <p>
            1. Los precios aquí mostrados están expresados en Moneda Nacional (MXN) e <strong>incluyen el Impuesto al Valor Agregado (IVA) del 16%</strong>.<br>
            2. La información de precios es vigente al día <strong>{fecha_hoy_str}</strong> y está sujeta a cambios sin previo aviso por parte de Toyota de México.<br>
            3. Las descripciones de los productos son de carácter informativo.<br>
            4. Para verificar disponibilidad física, favor de acudir al mostrador de refacciones.
        </p>
        <p style="margin-top: 15px; font-weight: bold; color: #eb0a1e;">TOYOTA LOS FUERTES</p>
    </div>
""", unsafe_allow_html=True)
