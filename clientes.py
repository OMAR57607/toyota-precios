import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DE PÁGINA (Adaptativo)
st.set_page_config(
    page_title="Consulta de Precios", 
    page_icon="🚗", 
    layout="centered",
    initial_sidebar_state="collapsed"
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

# 2. ESTILOS CSS (RESPONSIVE & BRANDING)
st.markdown("""
    <style>
    /* Forzar tema claro para consistencia de marca Toyota */
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }
    
    /* Input de búsqueda estilo "Google" / Kiosco */
    .stTextInput input {
        border-radius: 50px;
        border: 2px solid #ddd;
        padding: 15px 20px;
        font-size: 1.2rem;
        text-align: center;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
        transition: all 0.3s;
    }
    .stTextInput input:focus {
        border-color: #eb0a1e;
        box-shadow: 0px 4px 10px rgba(235, 10, 30, 0.2);
    }
    
    /* Tarjeta de Resultado Responsiva */
    .result-card {
        background-color: #fff;
        border: 1px solid #eee;
        border-radius: 15px;
        padding: 1.5rem;
        margin-top: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        border-top: 5px solid #eb0a1e; /* Acento Toyota */
        animation: fadeIn 0.5s;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .sku-label {
        color: #999;
        font-size: 0.9rem;
        font-family: monospace;
        margin-bottom: 5px;
    }
    
    .desc-product {
        color: #333;
        font-size: 1.3rem;
        font-weight: 700;
        line-height: 1.4;
        margin-bottom: 15px;
    }
    
    .price-block {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .price-small {
        font-size: 0.8rem;
        color: #666;
        text-transform: uppercase;
    }
    
    .price-big {
        color: #eb0a1e;
        font-size: 2rem;
        font-weight: 800;
    }
    
    /* Footer Legal Visible y Correcto */
    .legal-footer {
        text-align: center; 
        font-size: 0.85rem; 
        color: #555;
        margin-top: 50px; 
        padding: 20px;
        background-color: #f4f4f4;
        border-radius: 10px;
        line-height: 1.5;
    }
    
    /* Ajustes para Móvil */
    @media (max-width: 600px) {
        .price-big { font-size: 1.8rem; }
        .desc-product { font-size: 1.1rem; }
        .stTextInput input { font-size: 1rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# Función de Traducción Simple
@st.cache_data
def traducir_texto(texto):
    try:
        if pd.isna(texto) or texto == "": return "Descripción no disponible"
        # Usamos Google Translator para rapidez
        return GoogleTranslator(source='en', target='es').translate(str(texto))
    except: return str(texto)

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_catalogo():
    try:
        # Optimización: Cargar solo columnas necesarias si el archivo es muy grande
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        # Normalizar columnas
        df.columns = [c.strip().upper() for c in df.columns]
        
        # Identificar columnas clave dinámicamente
        cols_posibles_sku = [c for c in df.columns if 'PART' in c or 'NUM' in c or 'SKU' in c]
        if not cols_posibles_sku: return None
        c_sku = cols_posibles_sku[0]
        
        # Limpieza previa para búsqueda rápida
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        
        return df
    except Exception as e:
        st.error(f"Error técnico cargando base de datos. Contacte al administrador.")
        return None

df = cargar_catalogo()
fecha_actual_mx = obtener_hora_mx()
fecha_str = fecha_actual_mx.strftime("%d/%m/%Y")
hora_str = fecha_actual_mx.strftime("%H:%M")

# --- INTERFAZ KIOSCO ---

# 1. LOGO Y ENCABEZADO
col_logo, col_vacio = st.columns([1, 0.1])
with col_logo:
    try:
        # Se usa use_container_width para que se adapte al ancho del dispositivo
        st.image("logo.png", width=250) 
    except:
        st.markdown("<h1 style='color: #eb0a1e;'>TOYOTA</h1>", unsafe_allow_html=True)

st.markdown("### Consulta de Precios")

# 2. BUSCADOR INTELIGENTE
busqueda = st.text_input("Buscador", placeholder="🔍 Escribe el Número de Parte o Nombre...", label_visibility="collapsed")

# 3. LÓGICA DE BÚSQUEDA Y VISUALIZACIÓN
if df is not None and busqueda:
    busqueda_raw = busqueda.upper().strip()
    busqueda_clean = busqueda_raw.replace('-', '')
    
    # Filtrado (Prioridad SKU exacto -> SKU parcial -> Descripción)
    mask_sku = df['SKU_CLEAN'].str.contains(busqueda_clean, na=False)
    mask_desc = df.apply(lambda x: x.astype(str).str.contains(busqueda_raw, case=False)).any(axis=1)
    
    # Mostramos máximo 3 resultados para mantener la pantalla limpia
    resultados = df[mask_sku | mask_desc].head(3).copy()

    if not resultados.empty:
        # Detectar columnas
        c_sku = [c for c in resultados.columns if 'PART' in c or 'NUM' in c][0]
        c_desc = [c for c in resultados.columns if 'DESC' in c][0]
        c_precio = [c for c in resultados.columns if 'PRICE' in c or 'PRECIO' in c][0]
        
        for i, row in resultados.iterrows():
            # Procesamiento de datos
            sku_mostrado = row[c_sku]
            desc_es = traducir_texto(row[c_desc])
            
            try:
                precio_txt = str(row[c_precio]).replace(',', '').replace('$', '').strip()
                precio_base = float(precio_txt)
            except: 
                precio_base = 0.0
            
            # Cálculo del Total a Pagar (Requisito PROFECO: Precio Total)
            # Precio Base + 16% IVA
            precio_final = precio_base * 1.16
            
            # --- CARD VISUAL ---
            st.markdown(f"""
            <div class="result-card">
                <div class="sku-label">NÚMERO DE PARTE: {sku_mostrado}</div>
                <div class="desc-product">{desc_es}</div>
                <div class="price-block">
                    <div>
                        <div class="price-small">Precio Público</div>
                        <div class="price-small" style="font-weight:bold;">Total a Pagar</div>
                    </div>
                    <div class="price-big">${precio_final:,.2f} <span style="font-size:1rem; color:#666;">MXN</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.info("🔎 No encontramos coincidencias. Intenta con otro número o nombre.")
elif not busqueda:
    st.markdown("<br><p style='text-align:center; color:#999;'>Ingresa el código o nombre de la refacción arriba.</p>", unsafe_allow_html=True)

# 4. FOOTER LEGAL (Ajustado a Normativa de Precios Totales)
st.markdown("---")
st.markdown(f"""
    <div class="legal-footer">
        <strong>INFORMACIÓN COMERCIAL</strong><br><br>
        Precios expresados en <strong>Moneda Nacional (MXN)</strong>.<br>
        El monto mostrado corresponde al <strong>PRECIO TOTAL</strong> a pagar (Incluye IVA 16%).<br>
        Consulta vigente al: <strong>{fecha_str} {hora_str}</strong>.<br>
        <br>
        <span style="opacity:0.8; font-size: 0.75rem;">
        Sujeto a cambios sin previo aviso y disponibilidad en almacén. 
        Las imágenes y descripciones son ilustrativas. 
        Para garantías y especificaciones técnicas, consulte a su asesor.
        </span>
    </div>
""", unsafe_allow_html=True)
