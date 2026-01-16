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

# --- 1. LÓGICA DE TEMA VISUAL (ALTO CONTRASTE + FONDOS REALISTAS) ---
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
    
    # 🌅 MAÑANA (6 AM - 12 PM): Amanecer Claro
    if 6 <= h < 12:
        return {
            # Degradado suave de amanecer
            "css_bg": "linear-gradient(180deg, #87CEEB 0%, #E0F6FF 50%, #FFD194 100%)", 
            "card_bg": "rgba(255, 255, 255, 0.95)", # Tarjeta casi sólida para contraste
            "text_color": "#000000", # NEGRO PURO
            "text_shadow": "none",
            "icon_color": "#eb0a1e",
            "input_bg": "#ffffff",
            "input_text": "#000000"
        }
    
    # ☀️ TARDE (12 PM - 7 PM): Sol Radiante
    elif 12 <= h < 19:
        return {
            # Azul intenso con un "brillo" de sol arriba
            "css_bg": "radial-gradient(circle at 50% 10%, #FFD700 0%, #87CEEB 20%, #1E90FF 100%)",
            "card_bg": "rgba(255, 255, 255, 0.98)", # Blanco total para máximo contraste
            "text_color": "#000000", # NEGRO PURO
            "text_shadow": "none",
            "icon_color": "#eb0a1e",
            "input_bg": "#ffffff",
            "input_text": "#000000"
        }
    
    # 🌌 NOCHE (7 PM - 6 AM): Noche Estrellada
    else:
        return {
            # Truco CSS para generar estrellas sin imágenes
            "css_bg": """
                radial-gradient(white, rgba(255,255,255,.2) 2px, transparent 3px),
                radial-gradient(white, rgba(255,255,255,.15) 1px, transparent 2px),
                radial-gradient(white, rgba(255,255,255,.1) 2px, transparent 3px),
                linear-gradient(to bottom, #020111 0%, #191621 100%)
            """,
            "bg_size": "550px 550px, 350px 350px, 250px 250px, 100% 100%", # Repetir estrellas
            "card_bg": "rgba(0, 0, 0, 0.85)", # Tarjeta oscura
            "text_color": "#FFFFFF", # BLANCO PURO
            "text_shadow": "0px 2px 4px black", # Sombra negra para que la letra flote
            "icon_color": "#ff4d4d", # Rojo neón
            "input_bg": "#ffffff", # Input blanco para que no se pierda nada
            "input_text": "#000000"
        }

def apply_dynamic_styles():
    now = obtener_hora_mx()
    theme = get_theme_by_time(now)
    
    # Ajuste especial para el background-size si es de noche
    bg_size_css = f"background-size: {theme.get('bg_size', 'cover')};"
    
    st.markdown(f"""
        <style>
        /* --- VARIABLES GLOBALES --- */
        :root {{
            --text-color: {theme['text_color']};
            --text-shadow: {theme['text_shadow']};
            --card-bg: {theme['card_bg']};
        }}

        /* 1. FONDO "VIVO" */
        .stApp {{
            background-image: {theme['css_bg']} !important;
            {bg_size_css}
            background-attachment: fixed;
        }}
        
        /* 2. TARJETA DE CONTENIDO (ALTO CONTRASTE) */
        [data-testid="stBlockContainer"] {{
            background-color: var(--card-bg) !important;
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            max-width: 700px;
            margin-top: 20px;
            border: 1px solid rgba(128,128,128, 0.2);
        }}

        /* 3. TEXTOS (FORZAR COLOR) */
        h1, h2, h3, h4, h5, h6, p, div, span, label {{
            color: var(--text-color) !important;
            text-shadow: var(--text-shadow) !important;
            font-family: sans-serif;
        }}
        
        /* 4. INPUT (SIEMPRE BLANCO CON LETRA NEGRA PARA LEER BIEN) */
        .stTextInput input {{
            background-color: #ffffff !important;
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            font-weight: 900 !important; /* Letra muy gruesa */
            font-size: 24px !important;
            border: 3px solid {theme['icon_color']} !important;
            text-align: center !important;
            border-radius: 12px;
        }}
        
        /* 5. PRECIO GIGANTE */
        .big-price {{
            color: {theme['icon_color']} !important;
            text-shadow: 2px 2px 0px #000000; /* Borde negro al precio */
            font-size: clamp(50px, 15vw, 100px); 
            font-weight: 900;
            text-align: center;
            line-height: 1.1;
            margin: 10px 0;
        }}

        /* 6. BOTÓN */
        .stButton button {{
            background-color: {theme['icon_color']} !important;
            color: white !important;
            border: 2px solid white;
            font-weight: bold;
            font-size: 18px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        
        /* 7. KIOSCO */
        #MainMenu, footer, header {{visibility: hidden;}}
        
        /* 8. DISPLAY GRANDE DE SKU */
        .sku-display {{
            font-size: 30px !important;
            font-weight: 900 !important;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        
        /* 9. FOOTER */
        .legal-footer {{
            border-top: 1px solid var(--text-color) !important;
            opacity: 0.8;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 15px;
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
        st.markdown("<h1 style='text-align: center;'>TOYOTA</h1>", unsafe_allow_html=True)

with col_fecha:
    st.markdown(f"""
    <div style="text-align: right; font-size: 12px; font-weight: bold;">
        LOS FUERTES<br>
        {fecha_actual.strftime("%d/%m/%Y")}<br>
        {fecha_actual.strftime("%H:%M")}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- 4. BUSCADOR ---
st.markdown("<h3 style='text-align: center; font-weight: 800;'>VERIFICADOR DE PRECIOS</h3>", unsafe_allow_html=True)

busqueda_input = st.text_input("Ingresa SKU:", placeholder="Ej. 90915-YZZD1", label_visibility="collapsed").strip()
boton_consultar = st.button("🔍 CONSULTAR PRECIO")

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
        
        # Traducción
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

        # SKU y Descripción con clases de alto contraste
        st.markdown(f"<div class='sku-display' style='text-align: center; margin-top: 20px;'>{sku_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 25px;'>{desc_es}</div>", unsafe_allow_html=True)
        
        if precio_final > 0:
            st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center; font-size: 14px; font-weight: bold; margin-top: 5px; opacity: 0.9;'>Precio por Unidad. Neto (Incluye IVA). Moneda Nacional.</div>", unsafe_allow_html=True)
        else:
            st.warning("Precio no disponible al público.")
            
    elif busqueda_input:
        st.error("❌ CÓDIGO NO ENCONTRADO")

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
