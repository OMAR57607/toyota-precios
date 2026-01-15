import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from PIL import Image
import os

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
st.set_page_config(
    page_title="Verificador de Precios - Toyota Los Fuertes",
    page_icon="🔴", # Símbolo del sistema cambiado
    layout="centered"
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

# Estilos CSS Minimalistas y Profesionales
st.markdown("""
    <style>
    /* Ocultar elementos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Estilo del Precio Gigante */
    .big-price {
        font-size: 80px;
        font-weight: 800;
        color: #eb0a1e; /* Rojo Toyota */
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

    /* Input estilo buscador */
    .stTextInput input {
        font-size: 20px;
        text-align: center;
        border: 2px solid #eb0a1e;
        border-radius: 10px;
    }

    /* Footer Legal */
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

# 2. CARGA DE DATOS (Misma lógica pero sin traductor lento)
@st.cache_data
def cargar_catalogo():
    try:
        # Se asume que el archivo sigue siendo el mismo
        if os.path.exists("lista_precios.zip"):
            df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        elif os.path.exists("lista_precios.csv"):
            df = pd.read_csv("lista_precios.csv", dtype=str, encoding='latin-1')
        else:
            return None

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
fecha_actual = obtener_hora_mx()

# 3. HEADER (Logo y Fecha)
col_logo, col_fecha = st.columns([1, 2])

with col_logo:
    try:
        # Busca el logo.png, si no usa un placeholder
        if os.path.exists("logo.png"):
            image = Image.open("logo.png")
            st.image(image, width=150)
        else:
            st.markdown("## TOYOTA")
    except:
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

# 4. BUSCADOR CENTRAL
st.markdown("<h3 style='text-align: center;'>🔍 Verificador de Precios</h3>", unsafe_allow_html=True)

# El text_input funciona con pistolas de códigos de barras (que envían 'Enter' al final)
busqueda = st.text_input("Escanea o escribe el número de parte:", 
                         placeholder="Ej. 90915-YZZD1", 
                         help="Escribe el código y presiona Enter").strip()

# 5. LÓGICA DE BÚSQUEDA Y VISUALIZACIÓN
if busqueda and df is not None:
    busqueda_clean = busqueda.upper().replace('-', '').replace(' ', '')
    
    # Búsqueda exacta por SKU limpio o coincidencia en descripción
    mask_sku = df['SKU_CLEAN'] == busqueda_clean
    # Si no encuentra exacto, busca contenido (opcional, para buscador manual)
    mask_desc = df.iloc[:, 1].astype(str).str.contains(busqueda.upper(), na=False)
    
    resultados = df[mask_sku | mask_desc].head(1) # Solo el primer resultado (Kiosco style)

    if not resultados.empty:
        row = resultados.iloc[0]
        
        # Identificar columnas dinámicamente
        c_sku = [c for c in resultados.columns if 'PART' in c or 'NUM' in c][0]
        c_desc = [c for c in resultados.columns if 'DESC' in c][0]
        c_precio = [c for c in resultados.columns if 'PRICE' in c or 'PRECIO' in c][0]

        sku_val = row[c_sku]
        desc_val = row[c_desc]
        
        # Cálculo de precio
        try:
            precio_texto = str(row[c_precio]).replace(',', '').replace('$', '').strip()
            precio_base = float(precio_texto)
            precio_final = precio_base * 1.16 # IVA 16%
        except:
            precio_final = 0.0

        # --- DISPLAY DE RESULTADO ---
        st.markdown(f"<div class='sku-title'>SKU: {sku_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='desc-text'>{desc_val}</div>", unsafe_allow_html=True)
        
        if precio_final > 0:
            st.markdown("<div class='price-label'>Precio de Lista (Neto)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
            st.caption("Moneda Nacional (MXN). Incluye IVA (16%).")
        else:
            st.warning("Precio no disponible en sistema. Consulte a un asesor.")
            
    else:
        st.error("❌ Producto no encontrado. Verifique el código.")

elif not busqueda:
    st.info("👋 Escanee el código de barras del producto en el lector inferior.")

# 6. FOOTER LEGAL (Protección al Consumidor y Garantías)
st.markdown("---")
st.markdown(f"""
<div class="legal-footer">
    <strong>INFORMACIÓN AL CONSUMIDOR Y AVISO LEGAL</strong><br><br>
    <strong>1. PRECIOS:</strong> Todos los precios exhibidos están expresados en Moneda Nacional (MXN) e incluyen el Impuesto al Valor Agregado (IVA) del 16%, conforme a lo estipulado en el artículo 7 Bis de la <strong>Ley Federal de Protección al Consumidor (LFPC)</strong>.
    <br><br>
    <strong>2. VIGENCIA:</strong> Los precios mostrados son vigentes al momento de la consulta: <strong>{fecha_actual.strftime("%d/%m/%Y %H:%M")}</strong>. Toyota Los Fuertes se reserva el derecho de modificar los precios sin previo aviso, en función de las actualizaciones del corporativo Toyota de México.
    <br><br>
    <strong>3. DESCRIPCIÓN DE PRODUCTOS:</strong> Las descripciones y números de parte cumplen con la <strong>NOM-050-SCFI-2004</strong> (Información comercial - Etiquetado general de productos). Las imágenes (si las hubiera) son ilustrativas.
    <br><br>
    <strong>4. LIMITACIONES DE GARANTÍA:</strong> 
    <ul>
        <li>Las partes eléctricas no cuentan con garantía ni devoluciones una vez salidas del mostrador, salvo defecto de fábrica validado por el departamento técnico.</li>
        <li>La garantía de refacciones es de 12 meses o 20,000 km (lo que ocurra primero) únicamente si son instaladas en un taller autorizado Toyota.</li>
        <li>La venta de refacciones sueltas (mostrador) cuenta con garantía limitada contra defectos de fabricación.</li>
    </ul>
    <br>
    <strong>TOYOTA LOS FUERTES</strong> | Para cualquier duda o aclaración, favor de acudir al módulo de atención a clientes.
</div>
""", unsafe_allow_html=True)
