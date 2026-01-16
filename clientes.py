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

# --- 1. LÓGICA DE TEMA DINÁMICO (Colores y Fondos) ---
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    tz_cdmx = None

def obtener_hora_mx():
    if tz_cdmx:
        return datetime.now(tz_cdmx)
    return datetime.now()

def get_theme_by_time(date):
    h = date.hour
    # Definimos 3 paletas de colores completas según la hora
    if 6 <= h < 12:
        # MAÑANA: Amanecer cálido
        return {
            "bg_gradient": "linear-gradient(to top, #f5af19, #ffdd00, #87ceeb)",
            "card_bg": "rgba(255, 255, 255, 0.90)", # Tarjeta clara
            "text_primary": "#222222", # Texto oscuro
            "text_secondary": "#555555",
            "input_bg": "#ffffff",
            "accent_color": "#eb0a1e"
        }
    elif 12 <= h < 19:
        # TARDE: Sol brillante
        return {
            "bg_gradient": "linear-gradient(to bottom, #2980b9, #6dd5fa, #ffffff)",
            "card_bg": "rgba(255, 255, 255, 0.95)", # Tarjeta muy clara
            "text_primary": "#111111", # Texto muy oscuro (contraste alto)
            "text_secondary": "#444444",
            "input_bg": "#ffffff",
            "accent_color": "#eb0a1e"
        }
    else:
        # NOCHE: Cielo profundo estrellado (simulado con gradiente rico)
        return {
            "bg_gradient": "linear-gradient(to bottom, #0f2027, #203a43, #2c5364)",
            "card_bg": "rgba(20, 30, 40, 0.90)", # ¡Tarjeta oscura!
            "text_primary": "#ffffff", # ¡Texto blanco!
            "text_secondary": "#cccccc", # Texto gris claro
            "input_bg": "#e6e6e6", # Input ligeramente gris para no deslumbrar
            "accent_color": "#ff4d4d" # Rojo un poco más brillante para la noche
        }

def apply_dynamic_styles():
    now = obtener_hora_mx()
    theme = get_theme_by_time(now)
    
    st.markdown(f"""
        <style>
        /* --- VARIABLES CSS DINÁMICAS --- */
        :root {{
            --bg-gradient: {theme['bg_gradient']};
            --card-bg: {theme['card_bg']};
            --text-primary: {theme['text_primary']};
            --text-secondary: {theme['text_secondary']};
            --input-bg: {theme['input_bg']};
            --accent-color: {theme['accent_color']};
        }}

        /* 1. FONDO GLOBAL ANIMADO */
        .stApp {{
            background-image: var(--bg-gradient) !important;
            background-attachment: fixed;
            background-size: 200% 200%;
            animation: gradientBG 15s ease infinite;
        }}
        @keyframes gradientBG {{
            0% {{background-position: 0% 50%;}}
            50% {{background-position: 100% 50%;}}
            100% {{background-position: 0% 50%;}}
        }}
        
        /* 2. TARJETA CENTRAL DINÁMICA */
        [data-testid="stBlockContainer"] {{
            background-color: var(--card-bg) !important;
            border-radius: 25px;
            padding: 2.5rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            backdrop-filter: blur(10px); /* Efecto cristal elegante */
            border: 1px solid rgba(255, 255, 255, 0.1);
            max-width: 700px;
            margin-top: 20px;
        }}

        /* 3. TEXTOS DINÁMICOS */
        h1, h2, h3, h4, h5, h6, div, label, .sku-display {{
            color: var(--text-primary) !important;
            transition: color 0.5s ease;
        }}
        .date-display, .desc-display, .legal-footer {{
            color: var(--text-secondary) !important;
            transition: color 0.5s ease;
        }}
        
        /* 4. INPUT DINÁMICO */
        .stTextInput input {{
            background-color: var(--input-bg) !important;
            color: #222 !important; /* El texto dentro del input siempre oscuro */
            border: 2px solid var(--accent-color) !important;
            font-size: 22px !important;
            font-weight: bold !important;
            text-align: center !important;
            border-radius: 15px;
        }}
        
        /* 5. PRECIO Y BOTÓN (Acento) */
        .big-price {{
            color: var(--accent-color) !important;
            font-size: clamp(45px, 15vw, 95px); 
            font-weight: 900;
            text-align: center;
            line-height: 1.1;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stButton button {{
            background: var(--accent-color) !important;
            color: white !important;
            border: none;
            width: 100%;
            border-radius: 15px;
            font-weight: bold;
            font-size: 18px;
            padding: 10px;
            transition: transform 0.2s;
        }}
        .stButton button:hover {{
            transform: scale(1.02);
        }}
        
        /* 6. KIOSCO Y EXTRAS */
        #MainMenu, footer, header {{visibility: hidden;}}
        .legal-footer {{
            border-top: 1px solid var(--text-secondary) !important;
            opacity: 0.7;
            font-size: 11px;
            margin-top: 30px;
            padding-top: 15px;
            text-align: justify;
        }}
        div[data-testid="stImage"] {{ display: block; margin: auto; }}
        </style>
    """, unsafe_allow_html=True)

apply_dynamic_styles()

# --- 2. CARGA DE DATOS ---
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

# --- 3. INTERFAZ ---
col_vacia, col_logo, col_fecha = st.columns([1, 2, 1])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True) 
    else:
        # Usamos una clase para que el color se adapte
        st.markdown("<h1 style='text-align: center;'>TOYOTA</h1>", unsafe_allow_html=True)

with col_fecha:
    # Usamos la clase date-display para que el color se adapte (claro/oscuro)
    st.markdown(f"""
    <div class="date-display" style="text-align: right; font-size: 11px;">
        <strong>LOS FUERTES</strong><br>
        {fecha_actual.strftime("%d/%m/%Y")}<br>
        {fecha_actual.strftime("%H:%M")}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- 4. BUSCADOR ---
st.markdown("<h4 style='text-align: center; opacity: 0.9;'>Verificador de Precios</h4>", unsafe_allow_html=True)

busqueda_input = st.text_input("Ingresa SKU:", placeholder="Ej. 90915-YZZD1", label_visibility="collapsed").strip()
boton_consultar = st.button("🔍 Consultar Precio")

# --- 5. RESULTADOS ---
if (busqueda_input or boton_consultar) and df is not None:
    busqueda_clean = busqueda_input.upper().replace('-', '').replace(' ', '')
    mask = df['SKU_CLEAN'] == busqueda_clean
    resultados = df[mask]

    if not resultados.empty:
        row = resultados.iloc[0]
        
        c_sku = [c for c in df.columns if 'ITEM' in c or 'PART' in c or 'SKU' in c or 'NUMERO' in c][0]
        c_desc_list = [c for c in df.columns if 'DESC' in c]
        c_desc = c_desc_list[0] if c_desc_list else c_sku
        c_precio_list = [c for c in df.columns if 'TOTAL' in c or 'UNITARIO' in c or 'PRICE' in c or 'PRECIO' in c or 'IMPORTE' in c]
        
        sku_val = row[c_sku]
        desc_original = row[c_desc]
        
        # Traducción automática
        try:
            desc_es = GoogleTranslator(source='auto', target='es').translate(desc_original)
        except:
            desc_es = desc_original

        precio_final = 0.0
        if c_precio_list:
            try:
                p_text = str(row[c_precio_list[0]]).replace(',', '').replace('$', '').strip()
                precio_final = float(p_text) * 1.16 
            except: pass

        # Usamos clases dinámicas para los textos
        st.markdown(f"<div class='sku-display' style='font-size: 26px; font-weight: bold; text-align: center; margin-top: 20px;'>{sku_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='desc-display' style='font-size: 18px; text-align: center; margin-bottom: 25px; font-style: italic;'>{desc_es}</div>", unsafe_allow_html=True)
        
        if precio_final > 0:
            st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
            # Caption también se adapta
            st.markdown(f"<div class='desc-display' style='text-align: center; font-size: 14px; margin-top: 5px;'>Precio por Unidad. Neto (Incluye IVA). Moneda Nacional.</div>", unsafe_allow_html=True)
        else:
            st.warning("Precio no disponible al público.")
            
    elif busqueda_input:
        st.error("❌ Código no encontrado.")

# --- 6. FOOTER LEGAL ---
st.markdown("---")
st.markdown(f"""
<div class="legal-footer">
    <strong>INFORMACIÓN COMERCIAL Y MARCO LEGAL</strong><br>
    1. <strong>PRECIO TOTAL (LFPC Art. 7 Bis):</strong> Incluye IVA y cargos. Monto final a pagar.<br>
    2. <strong>VIGENCIA (NOM-174):</strong> Válido al {fecha_actual.strftime("%d/%m/%Y %H:%M:%S")}.<br>
    3. <strong>IDIOMA (NOM-050):</strong> Descripción en español para información clara al consumidor.
</div>
""", unsafe_allow_html=True)
