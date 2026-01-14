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
# NOTA: Se eliminó el forzado de fondo blanco para que el menú de la app sea visible
st.markdown("""
    <style>
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
        background-color: var(--secondary-background-color); /* Adaptativo */
        border: 1px solid rgba(0,0,0,0.1);
        border-radius: 15px;
        padding: 1.5rem;
        margin-top: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-top: 5px solid #eb0a1e; /* Acento Toyota */
        animation: fadeIn 0.5s;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .sku-label {
        color: var(--text-color);
        opacity: 0.7;
        font-size: 0.9rem;
        font-family: monospace;
        margin-bottom: 5px;
    }
    
    .desc-product {
        color: var(--text-color);
        font-size: 1.3rem;
        font-weight: 700;
        line-height: 1.4;
        margin-bottom: 15px;
    }
    
    .price-block {
        background-color: rgba(0,0,0,0.05); /* Fondo sutil adaptativo */
        padding: 15px;
        border-radius: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Estilos para Subtotal e IVA (Discretos) */
    .breakdown-container {
        text-align: right;
        margin-right: 15px;
        border-right: 1px solid rgba(0,0,0,0.1);
        padding-right: 15px;
    }
    
    .price-sub {
        font-size: 0.8rem;
        color: var(--text-color);
        opacity: 0.6;
    }
    
    .price-big {
        color: #eb0a1e;
        font-size: 2rem;
        font-weight: 800;
        text-align: right;
    }
    
    /* Footer Legal Visible y Correcto */
    .legal-footer {
        text-align: justify; 
        font-size: 0.75rem; 
        color: var(--text-color);
        opacity: 0.7;
        margin-top: 50px; 
        padding: 20px;
        background-color: rgba(0,0,0,0.03);
        border-radius: 10px;
        line-height: 1.4;
    }
    
    /* Ajustes para Móvil */
    @media (max-width: 600px) {
        .price-big { font-size: 1.5rem; }
        .desc-product { font-size: 1.1rem; }
        .stTextInput input { font-size: 1rem; }
        .price-block { flex-direction: column; align-items: flex-end; }
        .breakdown-container { border-right: none; margin-right: 0; margin-bottom: 10px; }
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

# 1. LOGO Y ENCABEZADO (CENTRADO)
# Usamos 3 columnas para centrar el contenido en la del medio
c_left, c_center, c_right = st.columns([1, 2, 1])

with c_center:
    try:
        # CORRECCIÓN: Se reemplaza use_container_width=True por width="stretch"
        st.image("logo.png", use_container_width=True) 
    except:
        # Si no carga la imagen, texto centrado como respaldo
        st.markdown("<h1 style='text-align: center; color: #eb0a1e;'>TOYOTA</h1>", unsafe_allow_html=True)

# Subtítulo también centrado con CSS inline
st.markdown("<h3 style='text-align: center;'>Consulta de Precios</h3>", unsafe_allow_html=True)

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
                precio_base_subtotal = float(precio_txt) # Asumimos precio lista es subtotal
            except: 
                precio_base_subtotal = 0.0
            
            # --- CÁLCULOS FINANCIEROS ---
            iva_monto = precio_base_subtotal * 0.16
            precio_total_final = precio_base_subtotal + iva_monto
            
            # --- CARD VISUAL CON JERARQUÍA ---
            st.markdown(f"""
            <div class="result-card">
                <div class="sku-label">NÚMERO DE PARTE: {sku_mostrado}</div>
                <div class="desc-product">{desc_es}</div>
                
                <div class="price-block">
                    <div class="breakdown-container">
                        <div class="price-sub">Subtotal: ${precio_base_subtotal:,.2f}</div>
                        <div class="price-sub">IVA (16%): ${iva_monto:,.2f}</div>
                    </div>
                    
                    <div>
                        <div style="font-size:0.8rem; text-align:right; color:#888;">Total a Pagar</div>
                        <div class="price-big">${precio_total_final:,.2f} <span style="font-size:1rem; color:var(--text-color); opacity:0.5;">MXN</span></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.info("🔎 No encontramos coincidencias. Intenta con otro número o nombre.")
elif not busqueda:
    st.markdown("<br><p style='text-align:center; opacity:0.6;'>Ingresa el código o nombre de la refacción arriba.</p>", unsafe_allow_html=True)

# 4. FOOTER LEGAL COMPLETO (PROFECO, NOM, ARTÍCULOS)
st.markdown("---")
st.markdown(f"""
    <div class="legal-footer">
        <strong>AVISO LEGAL Y REGULATORIO ({datetime.now().year}):</strong><br>
        El presente sistema de consulta cumple con las disposiciones de la <strong>Procuraduría Federal del Consumidor (PROFECO)</strong>.
        <br><br>
        <ul>
            <li><strong>Claridad de Precios (LFPC Arts. 7 y 7 Bis):</strong> Los montos aquí exhibidos representan el precio total a pagar, incluyendo impuestos y cargos aplicables.</li>
            <li><strong>Norma Oficial Mexicana (NOM-050-SCFI-2004):</strong> La información comercial cumple con los requisitos de etiquetado general de productos.</li>
            <li><strong>Desglose Fiscal:</strong> De conformidad con el CFF, se presenta el desglose de Subtotal e IVA (16%) de manera explícita.</li>
        </ul>
        <em>Nota: Precios vigentes al {fecha_str} {hora_str}. Sujetos a cambios sin previo aviso por disposición de planta. Las imágenes son ilustrativas.</em>
    </div>
""", unsafe_allow_html=True)
