import streamlit as st
import pandas as pd
import os
import zipfile
from datetime import datetime
from PIL import Image
import pytz
# Nueva librería para traducir al español automáticamente (Cumplimiento NOM)
from deep_translator import GoogleTranslator

# Configuración de página
st.set_page_config(
    page_title="Verificador de Precios - Toyota Los Fuertes",
    page_icon="🔴",
    layout="centered"
)

# --- 1. CONFIGURACIÓN Y ESTILOS (MODO KIOSCO ACTIVADO) ---
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    tz_cdmx = None

def obtener_hora_mx():
    if tz_cdmx:
        return datetime.now(tz_cdmx)
    return datetime.now()

st.markdown("""
    <style>
    /* --- MODO KIOSCO: OCULTAR ELEMENTOS DE STREAMLIT --- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* --- ESTILOS 100% ADAPTATIVOS (CLARO / OSCURO) --- */
    
    .big-price {
        font-size: clamp(40px, 15vw, 90px); 
        font-weight: 800;
        color: #eb0a1e; /* Rojo Toyota */
        text-align: center;
        margin: 0;
        line-height: 1.1;
    }
    
    .price-label {
        font-size: clamp(14px, 4vw, 20px);
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: inherit; 
        opacity: 0.8; 
    }

    .sku-title {
        font-size: clamp(18px, 5vw, 26px);
        font-weight: bold;
        text-align: center;
        color: inherit; 
    }
    
    .desc-text {
        font-size: clamp(16px, 4vw, 20px);
        text-align: center;
        margin-bottom: 20px;
        color: inherit; 
        opacity: 0.9;
        font-style: italic; /* Estilo itálico para la descripción */
    }

    /* Input adaptable */
    .stTextInput input {
        font-size: 20px;
        text-align: center;
        border: 2px solid #eb0a1e;
        border-radius: 10px;
    }

    .legal-footer {
        margin-top: 50px;
        padding-top: 20px;
        border-top: 1px solid rgba(128, 128, 128, 0.4); 
        font-size: clamp(9px, 2.5vw, 11px);
        color: inherit; 
        opacity: 0.6;   
        text-align: justify;
        font-family: Arial, sans-serif;
    }
    
    /* Centrar imágenes */
    div[data-testid="stImage"] {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CARGA DE DATOS ---
@st.cache_data
def cargar_catalogo():
    archivo_objetivo = "base_datos_2026.zip"
    
    if not os.path.exists(archivo_objetivo):
        st.error(f"⚠️ No se encuentra el archivo: {archivo_objetivo}")
        return None

    try:
        with zipfile.ZipFile(archivo_objetivo, "r") as z:
            archivos_excel = [f for f in z.namelist() if f.endswith('.xlsx')]
            
            if not archivos_excel:
                st.error("El archivo ZIP no contiene Excel (.xlsx)")
                return None
                
            nombre_archivo = archivos_excel[0]
            
            with z.open(nombre_archivo) as f:
                df = pd.read_excel(f, dtype=str)
        
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        
        cols_sku = [c for c in df.columns if 'ITEM' in c or 'PART' in c or 'SKU' in c or 'NUMERO' in c]
        
        if cols_sku:
            c_sku = cols_sku[0]
            df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.replace(' ', '').str.strip().str.upper()
            return df
        else:
            st.error("Error: No se encontró columna de SKU/Parte.")
            return None

    except Exception as e:
        st.error(f"Error procesando datos: {e}")
        return None

df = cargar_catalogo()
fecha_actual = obtener_hora_mx()

# --- 3. HEADER (Visible, pero sin menú de Streamlit arriba) ---
col_vacia, col_logo, col_fecha = st.columns([1, 2, 1])

with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True) 
    else:
        st.markdown("<h1 style='text-align: center; color: #eb0a1e;'>TOYOTA</h1>", unsafe_allow_html=True)

with col_fecha:
    st.markdown(f"""
    <div style="text-align: right; opacity: 0.7; font-size: 11px;">
        <strong>TOYOTA LOS FUERTES</strong><br>
        {fecha_actual.strftime("%d/%m/%Y")}<br>
        {fecha_actual.strftime("%H:%M")}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- 4. BUSCADOR ---
st.markdown("<h3 style='text-align: center;'>🔍 Verificador de Precios</h3>", unsafe_allow_html=True)

busqueda = st.text_input("Escanea o escribe el número de parte:",
                          placeholder="Ej. 90915-YZZD1",
                          help="Escribe el código y presiona Enter").strip()

# --- 5. RESULTADOS ---
if busqueda and df is not None:
    busqueda_clean = busqueda.upper().replace('-', '').replace(' ', '')
    mask = df['SKU_CLEAN'] == busqueda_clean
    resultados = df[mask]

    if not resultados.empty:
        row = resultados.iloc[0]
        
        # Detectar columnas
        c_sku = [c for c in df.columns if 'ITEM' in c or 'PART' in c or 'SKU' in c or 'NUMERO' in c][0]
        c_desc_list = [c for c in df.columns if 'DESC' in c]
        c_desc = c_desc_list[0] if c_desc_list else c_sku
        c_precio_list = [c for c in df.columns if 'TOTAL' in c or 'UNITARIO' in c or 'PRICE' in c or 'PRECIO' in c or 'IMPORTE' in c]
        
        sku_val = row[c_sku]
        desc_val_original = row[c_desc] # Descripción original (posiblemente en inglés)
        
        # --- TRADUCCIÓN AUTOMÁTICA (CUMPLIMIENTO NOM-050) ---
        # Intentamos traducir al español. Si falla por internet, usamos la original.
        try:
            desc_val = GoogleTranslator(source='auto', target='es').translate(desc_val_original)
        except:
            desc_val = desc_val_original # Fallback si no hay internet

        precio_final = 0.0
        
        if c_precio_list:
            c_precio = c_precio_list[0]
            try:
                precio_texto = str(row[c_precio]).replace(',', '').replace('$', '').strip()
                precio_base = float(precio_texto)
                precio_final = precio_base * 1.16 
            except:
                precio_final = 0.0

        st.markdown(f"<div class='sku-title'>SKU: {sku_val}</div>", unsafe_allow_html=True)
        # Mostramos la descripción traducida
        st.markdown(f"<div class='desc-text'>{desc_val}</div>", unsafe_allow_html=True)
        
        if precio_final > 0:
            st.snow() # Efecto de Nieve
            st.markdown("<div class='price-label'>Precio Público (Neto)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
            st.caption("Moneda Nacional (MXN). Incluye Impuestos.")
        else:
            st.warning("Precio no disponible para consulta pública.")
    else:
        st.error("❌ Producto no encontrado en el catálogo vigente.")

elif not busqueda:
    st.info("👋 Escanee el código de barras.")

# --- 6. FOOTER LEGAL ---
st.markdown("---")
st.markdown(f"""
<div class="legal-footer">
    <strong>INFORMACIÓN COMERCIAL Y MARCO LEGAL</strong><br>
    La información de precios mostrada en este verificador digital cumple estrictamente con las disposiciones legales vigentes en los Estados Unidos Mexicanos:
    <br><br>
    <strong>1. PRECIO TOTAL A PAGAR (LFPC Art. 7 Bis):</strong> En cumplimiento con la Ley Federal de Protección al Consumidor, el precio exhibido representa el monto final e inequívoco a pagar por el consumidor. Este importe incluye el costo del producto, el Impuesto al Valor Agregado (IVA del 16%) y cualquier cargo administrativo aplicable.
    <br><br>
    <strong>2. IDIOMA Y DESCRIPCIÓN (NOM-050-SCFI-2004):</strong> La descripción de los productos se presenta en idioma español, cumpliendo con la normativa de información comercial para productos extranjeros comercializados en territorio nacional.
    <br><br>
    <strong>3. VIGENCIA (NOM-174-SCFI-2007):</strong> Precio válido al momento de la consulta: <strong>{fecha_actual.strftime("%d/%m/%Y %H:%M:%S")}</strong>.
</div>
""", unsafe_allow_html=True)
