import streamlit as st
import pandas as pd
import os # <--- ESTA LIBRERÍA FALTABA Y ES CRITICA
from datetime import datetime
from PIL import Image
import pytz

# Configuración de página
st.set_page_config(
    page_title="Verificador de Precios - Toyota Los Fuertes",
    page_icon="🔴",
    layout="centered"
)

# --- 1. CONFIGURACIÓN Y ESTILOS ---
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
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
   
    .big-price {
        font-size: 80px;
        font-weight: 800;
        color: #eb0a1e;
        text-align: center;
        margin: 0;
        line-height: 1.1;
    }
   
    .price-label {
        font-size: 20px;
        color: #333;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    .sku-title {
        font-size: 24px;
        font-weight: bold;
        color: #000;
        text-align: center;
    }
   
    .desc-text {
        font-size: 18px;
        color: #555;
        text-align: center;
        margin-bottom: 20px;
    }

    .stTextInput input {
        font-size: 20px;
        text-align: center;
        border: 2px solid #eb0a1e;
        border-radius: 10px;
    }

    .legal-footer {
        margin-top: 50px;
        padding-top: 20px;
        border-top: 1px solid #ddd;
        font-size: 10px;
        color: #777;
        text-align: justify;
        font-family: Arial, sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CARGA DE DATOS (ENFOCADO EN ZIP) ---
@st.cache_data
def cargar_catalogo():
    archivo_objetivo = "lista_precios.zip"
    
    if not os.path.exists(archivo_objetivo):
        st.error(f"⚠️ No se encuentra el archivo: {archivo_objetivo}. Por favor cárgalo en la carpeta del proyecto.")
        return None

    try:
        # Intenta leer el ZIP. Se asume codificación latin-1 común en Excel/Sistemas viejos
        df = pd.read_csv(archivo_objetivo, compression='zip', dtype=str, encoding='latin-1')
        
        # Limpieza básica
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        
        # Intentar identificar columna de número de parte
        cols_posibles = [c for c in df.columns if 'PART' in c or 'NUM' in c or 'COD' in c]
        if cols_posibles:
            c_sku = cols_posibles[0]
            # Limpiar SKU para búsquedas (quitar guiones y espacios)
            df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.replace(' ', '').str.strip().str.upper()
            return df
        else:
            st.error("No se encontró una columna de 'Número de Parte' en el archivo.")
            return None

    except Exception as e:
        st.error(f"Error leyendo {archivo_objetivo}: {e}")
        return None

df = cargar_catalogo()
fecha_actual = obtener_hora_mx()

# --- 3. HEADER ---
col_logo, col_fecha = st.columns([1, 2])

with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
    else:
        st.markdown("## TOYOTA")

with col_fecha:
    st.markdown(f"""
    <div style="text-align: right; color: #555;">
        <strong>TOYOTA LOS FUERTES</strong><br>
        {fecha_actual.strftime("%d/%m/%Y")}<br>
        {fecha_actual.strftime("%H:%M:%S")}
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
    
    # Buscar coincidencia exacta en SKU limpio
    mask = df['SKU_CLEAN'] == busqueda_clean
    resultados = df[mask]

    if not resultados.empty:
        row = resultados.iloc[0]
        
        # Identificar columnas
        c_sku = [c for c in df.columns if 'PART' in c or 'NUM' in c][0]
        c_desc = [c for c in df.columns if 'DESC' in c][0]
        c_precio = [c for c in df.columns if 'PRICE' in c or 'PRECIO' in c or 'PUBLICO' in c][0]

        sku_val = row[c_sku]
        desc_val = row[c_desc]
        
        try:
            precio_texto = str(row[c_precio]).replace(',', '').replace('$', '').strip()
            precio_base = float(precio_texto)
            precio_final = precio_base * 1.16 # IVA
        except:
            precio_final = 0.0

        st.markdown(f"<div class='sku-title'>SKU: {sku_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='desc-text'>{desc_val}</div>", unsafe_allow_html=True)
        
        if precio_final > 0:
            st.markdown("<div class='price-label'>Precio de Lista (Neto)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
            st.caption("Moneda Nacional (MXN). Incluye IVA (16%).")
        else:
            st.warning("Precio no disponible.")
    else:
        st.error("❌ Producto no encontrado.")

elif not busqueda:
    st.info("👋 Escanee el código de barras.")

# --- 6. FOOTER ---
st.markdown("---")
st.markdown(f"""
<div class="legal-footer">
    <strong>INFORMACIÓN AL CONSUMIDOR Y AVISO LEGAL</strong><br><br>
    <strong>1. PRECIOS:</strong> Todos los precios exhibidos están expresados en Moneda Nacional (MXN) e incluyen el Impuesto al Valor Agregado (IVA) del 16%, conforme a lo estipulado en el artículo 7 Bis de la <strong>Ley Federal de Protección al Consumidor (LFPC)</strong>.
    <br><br>
    <strong>2. VIGENCIA:</strong> Los precios mostrados son vigentes al momento de la consulta: <strong>{fecha_actual.strftime("%d/%m/%Y %H:%M")}</strong>. Toyota Los Fuertes se reserva el derecho de modificar los precios sin previo aviso.
    <br><br>
    <strong>3. LIMITACIONES:</strong> Las partes eléctricas no cuentan con garantía ni devoluciones. La garantía de refacciones es de 12 meses o 20,000 km si son instaladas en taller autorizado.
</div>
""", unsafe_allow_html=True)

