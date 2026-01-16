import streamlit as st
import pandas as pd
import os
import zipfile
from datetime import datetime
# Librería para la traducción automática (NOM-050)
from deep_translator import GoogleTranslator
import pytz

# Configuración de página
st.set_page_config(
    page_title="Toyota Los Fuertes",
    page_icon="🔴",
    layout="centered"
)

# --- 1. FUNCIONES DE TIEMPO Y FONDO DINÁMICO ---
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    tz_cdmx = None

def obtener_hora_mx():
    if tz_cdmx:
        return datetime.now(tz_cdmx)
    return datetime.now()

def get_season(date):
    m = date.month
    if 3 <= m <= 5: return "primavera"
    elif 6 <= m <= 8: return "verano"
    elif 9 <= m <= 11: return "otoño"
    else: return "invierno"

def get_time_of_day(date):
    h = date.hour
    if 6 <= h < 12: return "mañana"
    elif 12 <= h < 19: return "tarde"
    else: return "noche"

# Diccionario de gradientes para cada combinación
gradients = {
    ("primavera", "mañana"): "linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%)", # Fresco/Claro
    ("primavera", "tarde"): "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)",  # Rosa/Azul pastel
    ("primavera", "noche"): "linear-gradient(135deg, #2c3e50 0%, #3498db 100%)",  # Azul noche
    
    ("verano", "mañana"): "linear-gradient(135deg, #2980b9 0%, #6dd5fa 100%, #ffffff 100%)", # Cielo azul brillante
    ("verano", "tarde"): "linear-gradient(135deg, #fceabb 0%, #f8b500 100%)",     # Sol cálido intenso
    ("verano", "noche"): "linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)", # Noche profunda de verano

    ("otoño", "mañana"): "linear-gradient(135deg, #f12711 0%, #f5af19 100%)",     # Amanecer naranja/rojo
    ("otoño", "tarde"): "linear-gradient(135deg, #dd5e89 0%, #f7bb97 100%)",      # Atardecer cálido
    ("otoño", "noche"): "linear-gradient(135deg, #232526 0%, #414345 100%)",      # Gris oscuro/negro

    ("invierno", "mañana"): "linear-gradient(135deg, #E0EAFC 0%, #CFDEF3 100%)",  # Frío pálido
    ("invierno", "tarde"): "linear-gradient(135deg, #83a4d4 0%, #b6fbff 100%)",   # Azul hielo
    ("invierno", "noche"): "linear-gradient(135deg, #000428 0%, #004e92 100%)",   # Azul oscuro invernal
}

def set_dynamic_background():
    now = obtener_hora_mx()
    season = get_season(now)
    time = get_time_of_day(now)
    # Obtener el gradiente correspondiente o uno por defecto
    gradient = gradients.get((season, time), "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)")
    
    st.markdown(f"""
        <style>
        /* Aplica el fondo al contenedor principal de la app */
        [data-testid="stAppViewContainer"] > .main {{
            background-image: {gradient} !important;
            background-attachment: fixed;
            background-size: cover;
            transition: background-image 1s ease-in-out;
        }}
        /* Crea una "tarjeta" blanca semitransparente para el contenido */
        [data-testid="stBlockContainer"] {{
            background-color: rgba(255, 255, 255, 0.90); /* Blanco al 90% de opacidad */
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1); /* Sombra suave */
            margin-top: 40px;
        }}
        /* Ajuste para que el footer se vea bien dentro de la tarjeta */
        .legal-footer {{
             border-top: 1px solid rgba(0, 0, 0, 0.1) !important;
             color: #555 !important;
        }}
        </style>
    """, unsafe_allow_html=True)

# Llamamos a la función para establecer el fondo inmediatamente
set_dynamic_background()


# --- 2. ESTILOS ADICIONALES Y MODO KIOSCO ---
st.markdown("""
    <style>
    /* Ocultar elementos de Streamlit (Modo Kiosco) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Estilos de Texto */
    .big-price {
        font-size: clamp(45px, 15vw, 95px); 
        font-weight: 800;
        color: #eb0a1e; 
        text-align: center;
        margin: 0;
        line-height: 1.1;
    }
    
    .sku-title {
        font-size: clamp(20px, 5vw, 28px);
        font-weight: bold;
        text-align: center;
        color: #333; /* Color oscuro para contraste con fondo blanco */
    }
    
    .desc-text {
        font-size: clamp(16px, 4vw, 22px);
        text-align: center;
        margin-bottom: 20px;
        color: #555; /* Gris medio */
        opacity: 1;
        font-style: italic;
    }

    /* Input estilo Google */
    .stTextInput input {
        font-size: 22px;
        text-align: center;
        border: 2px solid #eb0a1e;
        border-radius: 25px; 
        padding: 10px;
        background-color: white;
    }

    /* Botón personalizado */
    .stButton button {
        width: 100%;
        border-radius: 20px;
        font-size: 18px;
        font-weight: bold;
        background-color: #eb0a1e; /* Botón rojo para resaltar */
        color: white;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        background-color: #c40012; /* Rojo más oscuro al pasar el mouse */
        box-shadow: 0 4px 8px rgba(235, 10, 30, 0.3);
    }

    .legal-footer {
        margin-top: 50px;
        padding-top: 20px;
        font-size: 10px;
        opacity: 0.7;   
        text-align: justify;
    }
    
    div[data-testid="stImage"] {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. CARGA DE DATOS ---
@st.cache_data
def cargar_catalogo():
    archivo_objetivo = "base_datos_2026.zip"
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
        cols_sku = [c for c in df.columns if 'ITEM' in c or 'PART' in c or 'SKU' in c or 'NUMERO' in c]
        if cols_sku:
            df['SKU_CLEAN'] = df[cols_sku[0]].astype(str).str.replace('-', '').str.replace(' ', '').str.strip().str.upper()
            return df
        return None
    except: return None

df = cargar_catalogo()
fecha_actual = obtener_hora_mx()

# --- 4. INTERFAZ ---
col_vacia, col_logo, col_fecha = st.columns([1, 2, 1])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True) 
    else:
        st.markdown("<h1 style='text-align: center; color: #eb0a1e;'>TOYOTA</h1>", unsafe_allow_html=True)

with col_fecha:
    st.markdown(f"""
    <div style="text-align: right; color: #555; font-size: 11px;">
        <strong>LOS FUERTES</strong><br>
        {fecha_actual.strftime("%d/%m/%Y")}<br>
        {fecha_actual.strftime("%H:%M")}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- 5. BUSCADOR Y BOTÓN ---
st.markdown("<h4 style='text-align: center; color: #333;'>Verificador de Precios</h4>", unsafe_allow_html=True)

busqueda_input = st.text_input("Código de Parte:", placeholder="Escanea o escribe aquí...", label_visibility="collapsed").strip()
boton_consultar = st.button("🔍 Consultar Precio")

# Lógica
if (busqueda_input or boton_consultar) and df is not None:
    busqueda_clean = busqueda_input.upper().replace('-', '').replace(' ', '')
    mask = df['SKU_CLEAN'] == busqueda_clean
    resultados = df[mask]

    if not resultados.empty:
        # SE ELIMINÓ st.snow()

        row = resultados.iloc[0]
        
        # Detectar columnas
        c_sku = [c for c in df.columns if 'ITEM' in c or 'PART' in c or 'SKU' in c or 'NUMERO' in c][0]
        c_desc_list = [c for c in df.columns if 'DESC' in c]
        c_desc = c_desc_list[0] if c_desc_list else c_sku
        c_precio_list = [c for c in df.columns if 'TOTAL' in c or 'UNITARIO' in c or 'PRICE' in c or 'PRECIO' in c or 'IMPORTE' in c]
        
        sku_val = row[c_sku]
        desc_original = row[c_desc]
        
        # Traducción
        try:
            desc_es = GoogleTranslator(source='auto', target='es').translate(desc_original)
        except:
            desc_es = desc_original

        # Cálculo Precio
        precio_final = 0.0
        if c_precio_list:
            try:
                p_text = str(row[c_precio_list[0]]).replace(',', '').replace('$', '').strip()
                precio_final = float(p_text) * 1.16 
            except: pass

        # Mostrar Resultados
        st.markdown(f"<div class='sku-title'>{sku_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='desc-text'>{desc_es}</div>", unsafe_allow_html=True)
        
        if precio_final > 0:
            st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
            st.caption("Precio Neto (Incluye IVA). Moneda Nacional.")
        else:
            st.warning("Precio no disponible al público.")
            
    elif busqueda_input:
        st.error("❌ Código no encontrado.")

# --- 6. FOOTER LEGAL ROBUSTO ---
st.markdown("---")
st.markdown(f"""
<div class="legal-footer">
    <strong>INFORMACIÓN COMERCIAL Y MARCO LEGAL</strong><br>
    La información de precios mostrada en este verificador digital cumple estrictamente con las disposiciones legales vigentes en los Estados Unidos Mexicanos:
    <br><br>
    <strong>1. PRECIO TOTAL A PAGAR (LFPC Art. 7 Bis):</strong> En cumplimiento con la Ley Federal de Protección al Consumidor, el precio exhibido representa el monto final e inequívoco a pagar por el consumidor. Este importe incluye el costo del producto, el Impuesto al Valor Agregado (IVA del 16%) y cualquier cargo administrativo aplicable, evitando prácticas comerciales engañosas.
    <br><br>
    <strong>2. VIGENCIA Y EXACTITUD (NOM-174-SCFI-2007):</strong> El precio mostrado es válido exclusivamente al momento de la consulta (Timbre digital: <strong>{fecha_actual.strftime("%d/%m/%Y %H:%M:%S")}</strong>). Toyota Los Fuertes garantiza el respeto al precio exhibido al momento de la transacción conforme a lo dispuesto en las Normas Oficiales Mexicanas sobre prácticas comerciales en transacciones electrónicas y de información.
    <br><br>
    <strong>3. INFORMACIÓN COMERCIAL (NOM-050-SCFI-2004):</strong> La descripción y especificaciones de las partes cumplen con los requisitos de información comercial general para productos destinados a consumidores en el territorio nacional.
</div>
""", unsafe_allow_html=True)
