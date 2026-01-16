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

# --- 1. ESTILOS, MODO KIOSCO Y EFECTO NIEVE GOOGLE ---
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    tz_cdmx = None

def obtener_hora_mx():
    if tz_cdmx:
        return datetime.now(tz_cdmx)
    return datetime.now()

# CÓDIGO PARA EL EFECTO DE NIEVE FINA (TIPO GOOGLE)
# Este bloque define cómo se ven y se mueven las partículas
def activar_efecto_nieve_fina():
    snow_code = """
    <div id="snow-overlay"></div>
    <style>
    /* Contenedor transparente que cubre toda la pantalla */
    #snow-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none; /* Permite dar clic a través de la nieve */
        z-index: 99999;
    }
    /* Estilo de la partícula de nieve (pequeño punto blanco) */
    .snow-flake {
        position: absolute;
        top: -10px;
        background: white; /* Color blanco */
        border-radius: 50%; /* Forma redonda */
        opacity: 0.7; /* Ligeramente transparente */
        animation: snowfall linear infinite; /* Animación continua */
    }
    /* Animación de caída */
    @keyframes snowfall {
        to { transform: translateY(100vh); }
    }
    </style>
    <script>
    // Script para generar múltiples partículas aleatorias
    (function() {
        // Evitar duplicar si ya existe
        if (document.getElementById('snow-generated')) return;
        const container = document.getElementById('snow-overlay');
        container.id = 'snow-generated'; // Marcar como generado

        const particleCount = 150; // Cantidad de partículas (ajustar densidad)

        for (let i = 0; i < particleCount; i++) {
            const flake = document.createElement('div');
            flake.className = 'snow-flake';
            
            // Tamaño aleatorio muy pequeño (entre 1px y 3px) como en la imagen de Google
            const size = (Math.random() * 2 + 1) + 'px';
            flake.style.width = size;
            flake.style.height = size;
            
            // Posición horizontal aleatoria
            flake.style.left = Math.random() * 100 + 'vw';
            
            // Velocidad de caída aleatoria (entre 5s y 12s)
            const duration = (Math.random() * 7 + 5) + 's';
            flake.style.animationDuration = duration;
            
            // Retraso aleatorio para que no empiecen todas juntas
            flake.style.animationDelay = (Math.random() * -10) + 's';
            
            container.appendChild(flake);
        }
    })();
    </script>
    """
    # Inyectamos este código en la aplicación
    st.markdown(snow_code, unsafe_allow_html=True)


st.markdown("""
    <style>
    /* Ocultar elementos de Streamlit (Modo Kiosco) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Estilos Adaptativos */
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
        color: inherit; 
    }
    
    .desc-text {
        font-size: clamp(16px, 4vw, 22px);
        text-align: center;
        margin-bottom: 20px;
        color: inherit; 
        opacity: 0.9;
        font-style: italic;
    }

    /* Input estilo Google */
    .stTextInput input {
        font-size: 22px;
        text-align: center;
        border: 2px solid #eb0a1e;
        border-radius: 25px;
        padding: 10px;
    }

    /* Botón personalizado */
    .stButton button {
        width: 100%;
        border-radius: 20px;
        font-size: 18px;
        font-weight: bold;
        background-color: #f0f2f6;
        color: #31333F;
        border: 1px solid #d0d0d0;
    }
    .stButton button:hover {
        border-color: #eb0a1e;
        color: #eb0a1e;
    }

    .legal-footer {
        margin-top: 60px;
        padding-top: 20px;
        border-top: 1px solid rgba(128, 128, 128, 0.4); 
        font-size: 10px;
        color: inherit; 
        opacity: 0.6;   
        text-align: justify;
    }
    
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
        st.markdown("<h1 style='text-align: center; color: #eb0a1e;'>TOYOTA</h1>", unsafe_allow_html=True)

with col_fecha:
    st.markdown(f"""
    <div style="text-align: right; opacity: 0.7; font-size: 11px;">
        <strong>LOS FUERTES</strong><br>
        {fecha_actual.strftime("%d/%m/%Y")}<br>
        {fecha_actual.strftime("%H:%M")}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- 4. BUSCADOR Y BOTÓN ---
st.markdown("<h4 style='text-align: center; opacity: 0.8;'>Verificador de Precios</h4>", unsafe_allow_html=True)

busqueda_input = st.text_input("Código de Parte:", placeholder="Escanea o escribe aquí...", label_visibility="collapsed").strip()
boton_consultar = st.button("🔍 Consultar Precio")

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

        # Mostrar Resultados
        st.markdown(f"<div class='sku-title'>{sku_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='desc-text'>{desc_es}</div>", unsafe_allow_html=True)
        
        if precio_final > 0:
            # --- ACTIVAR EL EFECTO DE NIEVE FINA ---
            activar_efecto_nieve_fina()
            # ---------------------------------------
            st.markdown(f"<div class='big-price'>${precio_final:,.2f}</div>", unsafe_allow_html=True)
            st.caption("Precio Neto (Incluye IVA). Moneda Nacional.")
        else:
            st.warning("Precio no disponible al público.")
            
    elif busqueda_input:
        st.error("❌ Código no encontrado.")

# --- 5. FOOTER LEGAL ---
st.markdown(f"""
<div class="legal-footer">
    <strong>MARCO LEGAL Y NORMATIVO (PROFECO)</strong><br>
    1. <strong>Precio Total (LFPC Art. 7 Bis):</strong> El monto exhibido incluye IVA y cargos aplicables.<br>
    2. <strong>Información en Español (NOM-050):</strong> Descripción traducida para cumplimiento de información comercial.<br>
    3. <strong>Vigencia (NOM-174):</strong> Válido al {fecha_actual.strftime("%d/%m/%Y %H:%M")}.
</div>
""", unsafe_allow_html=True)
