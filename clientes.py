import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DE PÁGINA
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

# 2. ESTILOS CSS
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
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(0,0,0,0.1);
        border-radius: 15px;
        padding: 1.5rem;
        margin-top: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-top: 5px solid #eb0a1e;
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
        background-color: rgba(0,0,0,0.05);
        padding: 15px;
        border-radius: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Estilos para Desglose */
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
    
    /* Footer Legal */
    .legal-footer {
        text-align: justify; 
        font-size: 0.70rem; 
        color: var(--text-color);
        opacity: 0.7;
        margin-top: 50px; 
        padding: 20px;
        background-color: rgba(0,0,0,0.03);
        border-radius: 10px;
        line-height: 1.4;
        border-top: 1px solid #ddd;
    }
    
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
        return GoogleTranslator(source='en', target='es').translate(str(texto))
    except: return str(texto)

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_catalogo():
    try:
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        
        cols_posibles_sku = [c for c in df.columns if 'PART' in c or 'NUM' in c or 'SKU' in c]
        if not cols_posibles_sku: return None
        c_sku = cols_posibles_sku[0]
        
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
c_left, c_center, c_right = st.columns([1, 2, 1])

with c_center:
    try:
        st.image("logo.png", use_container_width=True) 
    except:
        st.markdown("<h1 style='text-align: center; color: #eb0a1e;'>TOYOTA</h1>", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center;'>Consulta de Precios</h3>", unsafe_allow_html=True)

busqueda = st.text_input("Buscador", placeholder="🔍 Escribe el Número de Parte o Nombre...", label_visibility="collapsed")

if df is not None and busqueda:
    busqueda_raw = busqueda.upper().strip()
    busqueda_clean = busqueda_raw.replace('-', '')
    
    mask_sku = df['SKU_CLEAN'].str.contains(busqueda_clean, na=False)
    mask_desc = df.apply(lambda x: x.astype(str).str.contains(busqueda_raw, case=False)).any(axis=1)
    
    resultados = df[mask_sku | mask_desc].head(3).copy()

    if not resultados.empty:
        c_sku = [c for c in resultados.columns if 'PART' in c or 'NUM' in c][0]
        c_desc = [c for c in resultados.columns if 'DESC' in c][0]
        c_precio = [c for c in resultados.columns if 'PRICE' in c or 'PRECIO' in c][0]
        
        for i, row in resultados.iterrows():
            sku_mostrado = row[c_sku]
            desc_es = traducir_texto(row[c_desc])
            
            try:
                precio_txt = str(row[c_precio]).replace(',', '').replace('$', '').strip()
                precio_base_subtotal = float(precio_txt)
            except: 
                precio_base_subtotal = 0.0
            
            iva_monto = precio_base_subtotal * 0.16
            precio_total_final = precio_base_subtotal + iva_monto
            
            # --- CARD VISUAL AJUSTADA ---
            # Se usa "Precio Lista Unitario" y "1 Unidad" para cubrir Piezas, Kits o Juegos.
            st.markdown(f"""
<div class="result-card">
    <div class="sku-label">NÚMERO DE PARTE: {sku_mostrado}</div>
    <div class="desc-product">{desc_es}</div>
    <div class="price-block">
        <div class="breakdown-container">
            <div class="price-sub">Precio Lista Unitario: ${precio_base_subtotal:,.2f}</div>
            <div class="price-sub">IVA (16%): ${iva_monto:,.2f}</div>
        </div>
        <div>
            <div style="font-size:0.8rem; text-align:right; color:#888;">Total a Pagar (1 Unidad)</div>
            <div class="price-big">${precio_total_final:,.2f} <span style="font-size:1rem; color:var(--text-color); opacity:0.5;">MXN</span></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
            
    else:
        st.info("🔎 No encontramos coincidencias. Intenta con otro número o nombre.")
elif not busqueda:
    st.markdown("<br><p style='text-align:center; opacity:0.6;'>Ingresa el código o nombre de la refacción arriba.</p>", unsafe_allow_html=True)

# 4. FOOTER LEGAL (Aclarando Kits/Juegos/Piezas)
st.markdown("---")
st.markdown(f"""
<div class="legal-footer">
    <strong>AVISO DE PRIVACIDAD Y TÉRMINOS COMERCIALES</strong><br>
    La presente información cumple con la <strong>Ley Federal de Protección al Consumidor (LFPC)</strong>.
    <br><br>
    <ul>
        <li><strong>Precios Unitarios (LFPC Art. 7):</strong> El precio exhibido corresponde a una sola unidad de venta comercial. Dependiendo de la descripción, la "Unidad" puede referirse a una <strong>Pieza individual, un Juego, un Kit o un Paquete</strong>.</li>
        <li><strong>Montos Totales:</strong> Los precios incluyen IVA (16%) y están expresados en Moneda Nacional (MXN).</li>
        <li><strong>Vigencia (LFPC Art. 12):</strong> Precios válidos al momento de la consulta: <strong>{fecha_str} {hora_str}</strong>.</li>
        <li><strong>Garantías:</strong> Aplican garantías de fábrica Toyota según la naturaleza de la parte (eléctrica, desgaste o mecánica).</li>
    </ul>
    <em>Nota: Disponibilidad sujeta a inventario en almacén ("Salvo venta previa").</em>
</div>
""", unsafe_allow_html=True)
