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

# --- 1. LÓGICA DE TEMAS VISUALES (NATURALES Y DE ALTO CONTRASTE) ---
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
    
    # 🌅 MAÑANA (6 AM - 12 PM): Amanecer Limpio
    if 6 <= h < 12:
        return {
            "css_bg": "linear-gradient(180deg, #E0F7FA 0%, #FFFFFF 100%)", # Azul muy pálido a blanco
            "card_bg": "rgba(255, 255, 255, 0.95)",
            "text_color": "#000000",
            "text_shadow": "none",
            "accent_color": "#eb0a1e",
            "footer_border": "#000000"
        }
    
    # ☀️ TARDE (12 PM - 7 PM): Día Soleado (Alto Contraste)
    elif 12 <= h < 19:
        return {
            "css_bg": "linear-gradient(135deg, #87CEEB 0%, #B0E0E6 100%)", # Azul cielo sólido
            "card_bg": "rgba(255, 255, 255, 1)", # Blanco total
            "text_color": "#000000", # Negro puro
            "text_shadow": "none",
            "accent_color": "#eb0a1e",
            "footer_border": "#000000"
        }
    
    # 🌌 NOCHE (7 PM - 6 AM): Cielo Estrellado "Natural" (CSS Puro)
    else:
        return {
            # Técnica de Gradientes Radiales para simular estrellas sin imágenes
            "css_bg": """
                radial-gradient(white, rgba(255,255,255,.2) 2px, transparent 4px),
                radial-gradient(white, rgba(255,255,255,.15) 1px, transparent 3px),
                radial-gradient(white, rgba(255,255,255,.1) 2px, transparent 4px),
                linear-gradient(to bottom, #000000 0%, #0c0c0c 100%)
            """,
            "bg_size": "550px 550px, 350px 350px, 250px 250px, 100% 100%", # Capas de estrellas
            "bg_pos": "0 0, 40px 60px, 130px 270px, 0 0", # Posiciones para que se vea natural
            "card_bg": "rgba(0, 0, 0, 0.9)", # Fondo negro casi sólido
            "text_color": "#FFFFFF", # Blanco puro
            "text_shadow": "0px 2px 4px #000000", # Sombra para resaltar
            "accent_color": "#ff4d4d", # Rojo brillante
            "footer_border": "#FFFFFF"
        }

def apply_dynamic_styles():
    now = obtener_hora_mx()
    theme = get_theme_by_time(now)
    
    # Ajustes CSS condicionales para el fondo complejo de noche
    bg_extra_css = ""
    if "bg_size" in theme:
        bg_extra_css = f"background-size: {theme['bg_size']}; background-position: {theme['bg_pos']};"
    
    st.markdown(f"""
        <style>
        /* --- VARIABLES --- */
        :root {{
            --text-color: {theme['text_color']};
            --card-bg: {theme['card_bg']};
            --accent: {theme['accent_color']};
        }}

        /* 1. FONDO DE PANTALLA (Natural) */
        .stApp {{
            background-image: {theme['css_bg']} !important;
            {bg_extra_css}
            background-attachment: fixed;
        }}
        
        /* 2. TARJETA CENTRAL */
        [data-testid="stBlockContainer"] {{
            background-color: var(--card-bg) !important;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            max-width: 700px;
            margin-top: 20px;
            border: 1px solid rgba(128,128,128, 0.3);
        }}

        /* 3. TEXTOS (Alto Contraste Forzado) */
        h1, h2, h3, h4, h5, h6, p, div, span, label, li {{
            color: var(--text-color) !important;
            text-shadow: {theme['text_shadow']} !important;
            font-family: sans-serif;
        }}
        
        /* 4. INPUT (Blanco con letras Negras SIEMPRE) */
        .stTextInput input {{
            background-color: #ffffff !important;
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            font-weight: 900 !important;
            font-size: 24px !important;
            border: 3px solid var(--accent) !important;
            text-align: center !important;
            border-radius: 10px;
        }}
        
        /* 5. PRECIO */
        .big-price {{
            color: var(--accent) !important;
            font-size: clamp(50px, 15vw, 100px); 
            font-weight: 900;
            text-align: center;
            line-height: 1.1;
            margin: 10px 0;
            text-shadow: 2px 2px 0px black !important;
        }}

        /* 6. BOTÓN */
        .stButton button {{
            background-color: var(--accent) !important;
            color: white !important;
            border: 1px solid white;
            font-weight: bold;
            font-size: 18px;
            border-radius: 8px;
            width: 100%;
        }}
        
        /* 7. TEXTOS GRANDES */
        .sku-display {{
            font-size: 32px !important;
            font-weight: 900 !important;
            text-transform: uppercase;
        }}
        
        /* 8. KIOSCO */
        #MainMenu, footer, header {{visibility: hidden;}}
        
        /* 9. FOOTER LEGAL (Línea divisora adaptable) */
        .legal-footer {{
            border-top: 1px solid {theme['footer_border']} !important;
            opacity: 0.9;
            font-size: 11px;
            margin-top: 40px;
            padding-top: 20px;
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

        # Resultados con clases de alto contraste
        st.markdown(f"<div class='sku-display' style='text-align: center; margin-top: 20px;'>{sku_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 25px;'>{desc_es}</div>", unsafe_allow_html=True)
        
        if precio_final > 0:
            st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align: center; font-size: 14px; font-weight: bold; margin-top: 5px;'>Precio por Unidad. Neto (Incluye IVA). Moneda Nacional.</div>", unsafe_allow_html=True)
        else:
            st.warning("Precio no disponible al público.")
            
    elif busqueda_input:
        st.error("❌ CÓDIGO NO ENCONTRADO")

# --- 6. FOOTER LEGAL ROBUSTO (ORIGINAL RESTAURADO) ---
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
