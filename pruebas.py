import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import urllib.parse
from datetime import datetime
from fpdf import FPDF
from PIL import Image
from pyzbar.pyzbar import decode
import pytz
import easyocr
import numpy as np
import re
import requests
import tempfile
import os

# --- URL DEL LOGO MODERNO (Alta Resolución) ---
LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Toyota_EU_2020_Logo.svg/1024px-Toyota_EU_2020_Logo.svg.png"

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Toyota Asesores", page_icon="🔧", layout="wide")

# Configurar Zona Horaria CDMX
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    tz_cdmx = None 

def obtener_hora_mx():
    if tz_cdmx:
        return datetime.now(tz_cdmx)
    return datetime.now()

# Inicializar variables de sesión
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'errores_carga' not in st.session_state: st.session_state.errores_carga = [] 
if 'auto_cliente' not in st.session_state: st.session_state.auto_cliente = ""
if 'auto_vin' not in st.session_state: st.session_state.auto_vin = ""
if 'auto_orden' not in st.session_state: st.session_state.auto_orden = ""

@st.cache_resource
def cargar_lector_ocr():
    return easyocr.Reader(['en'], gpu=False) 

# 2. ESTILOS CSS (Mejorados con tipografía corporativa)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    h1 { color: #000000 !important; font-weight: 700; text-align: left; }
    .stButton button { width: 100%; border-radius: 4px; font-weight: bold; text-transform: uppercase; }
    
    /* Cajas de estado */
    .error-box { background-color: #fff0f0; padding: 15px; border-radius: 4px; border-left: 5px solid #eb0a1e; color: #333; }
    .success-box { background-color: #f0fff4; padding: 15px; border-radius: 4px; border-left: 5px solid #28a745; color: #155724; }
    
    /* Footer */
    .legal-footer { text-align: center; font-size: 10px; color: #666; margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- CLASE PDF ---
class PDF(FPDF):
    def header(self):
        # Intentar descargar el logo temporalmente para el PDF
        try:
            # Posición del Logo (x, y, ancho)
            self.image(LOGO_URL, 10, 8, 25) 
            offset_y_titulo = 0
        except:
            # Si falla la descarga, solo texto
            offset_y_titulo = 0
            pass

        self.set_font('Arial', 'B', 16)
        self.set_text_color(0) # Negro Corporativo
        # Ajustamos posición del titulo para que no choque con el logo
        self.set_xy(40, 10) 
        self.cell(0, 10, 'TOYOTA LOS FUERTES', 0, 1, 'L')
        
        self.set_xy(40, 18)
        self.set_font('Arial', '', 9)
        self.set_text_color(100)
        self.cell(0, 5, 'COTIZACION OFICIAL DE REFACCIONES', 0, 1, 'L')
        
        # Linea roja decorativa
        self.set_draw_color(235, 10, 30) # Rojo Toyota
        self.set_line_width(0.5)
        self.line(10, 30, 200, 30)
        self.ln(15)

    def footer(self):
        self.set_y(-30)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.multi_cell(0, 4, 'Precios en MXN. Incluyen IVA (16%). VIGENCIA: 24 HORAS. Descripciones bajo NOM-050-SCFI-2004.', 0, 'C')

def generar_pdf_bytes(carrito, subtotal, iva, total, cliente, vin, orden):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=30)
    
    fecha_mx = obtener_hora_mx().strftime("%d/%m/%Y %H:%M")
    
    # Datos Cliente (Diseño limpio)
    pdf.set_fill_color(250, 250, 250)
    pdf.rect(10, 35, 190, 28, 'F')
    
    # Columna Izquierda
    pdf.set_xy(15, 38)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 6, 'CLIENTE:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(80, 6, cliente if cliente else "Mostrador", 0, 1)
    
    pdf.set_x(15)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 6, 'VIN:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(80, 6, vin if vin else "N/A", 0, 0)

    # Columna Derecha (Datos de Control)
    pdf.set_xy(120, 38)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 6, 'FECHA:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, 6, fecha_mx, 0, 1)

    pdf.set_xy(120, 44)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 6, 'ORDEN:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, 6, orden if orden else "S/N", 0, 1)

    pdf.ln(15)

    # --- ENCABEZADOS DE TABLA (Negro/Gris Oscuro en lugar de rojo chillón) ---
    pdf.set_fill_color(50, 50, 50) 
    pdf.set_text_color(255)
    pdf.set_font('Arial', 'B', 8)
    
    w_sku = 30
    w_desc = 60
    w_cant = 10
    w_base = 25
    w_iva = 20
    w_total = 25
    w_estatus = 20

    pdf.cell(w_sku, 8, 'SKU', 0, 0, 'C', True)
    pdf.cell(w_desc, 8, 'DESCRIPCION', 0, 0, 'C', True)
    pdf.cell(w_cant, 8, 'CANT', 0, 0, 'C', True)
    pdf.cell(w_base, 8, 'P. UNIT', 0, 0, 'C', True)
    pdf.cell(w_iva, 8, 'IVA', 0, 0, 'C', True)
    pdf.cell(w_total, 8, 'TOTAL', 0, 0, 'C', True)
    pdf.cell(w_estatus, 8, 'ESTATUS', 0, 1, 'C', True)

    # --- CONTENIDO DE TABLA ---
    pdf.set_text_color(0)
    pdf.set_font('Arial', '', 7)
    
    for i, item in enumerate(carrito):
        fill = (i % 2 == 0) # Alternar color de filas
        pdf.set_fill_color(248, 248, 248) if fill else pdf.set_fill_color(255, 255, 255)
        
        desc = item['Descripción'][:40]
        pdf.cell(w_sku, 7, item['SKU'], 0, 0, 'C', fill)
        pdf.cell(w_desc, 7, desc, 0, 0, 'L', fill)
        pdf.cell(w_cant, 7, str(int(item['Cantidad'])), 0, 0, 'C', fill)
        pdf.cell(w_base, 7, f"${item['Precio Base']:,.2f}", 0, 0, 'R', fill)
        pdf.cell(w_iva, 7, f"${item['IVA']:,.2f}", 0, 0, 'R', fill)
        pdf.cell(w_total, 7, f"${item['Importe Total']:,.2f}", 0, 0, 'R', fill)
        
        st_txt = item['Estatus']
        pdf.set_font('Arial', 'B', 7)
        if "Back Order" in st_txt: pdf.set_text_color(200, 0, 0)
        elif "No" in st_txt: pdf.set_text_color(100, 100, 100)
        else: pdf.set_text_color(0, 100, 0)
        pdf.cell(w_estatus, 7, st_txt, 0, 1, 'C', fill)
        pdf.set_text_color(0)
        pdf.set_font('Arial', '', 7)

    pdf.ln(5)
    
    # --- TOTALES ---
    pdf.set_font('Arial', '', 10)
    offset_x = 135
    pdf.cell(offset_x)
    pdf.cell(25, 6, 'Subtotal:', 0, 0, 'R')
    pdf.cell(30, 6, f"${subtotal:,.2f}", 0, 1, 'R')
    pdf.cell(offset_x)
    pdf.cell(25, 6, 'IVA (16%):', 0, 0, 'R')
    pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(235, 10, 30) # Rojo Toyota
    pdf.cell(offset_x)
    pdf.cell(25, 8, 'TOTAL:', 0, 0, 'R')
    pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')

    pdf.ln(25)
    pdf.set_draw_color(0)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.set_text_color(0)
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(0, 5, 'Firma de Autorizacion / Asesor', 0, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')

# Traductor
@st.cache_data
def traducir_profe(texto):
    try:
        if pd.isna(texto) or texto == "": return "Sin descripción"
        return GoogleTranslator(source='en', target='es').translate(str(texto))
    except: return texto

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_catalogo():
    try:
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        
        c_sku = [c for c in df.columns if 'PART' in c or 'NUM' in c][0]
        c_desc = [c for c in df.columns if 'DESC' in c][0]
        c_precio = [c for c in df.columns if 'PRICE' in c or 'PRECIO' in c][0]
        
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        df['PRECIO_NUM'] = df[c_precio].astype(str).str.replace('$', '').str.replace(',', '').apply(lambda x: float(x) if x.replace('.', '', 1).isdigit() else 0.0)
        
        return df, c_sku, c_desc
    except Exception as e:
        # st.error(f"Error cargando datos: {e}") 
        # Comentado para que no ensucie la pantalla si no hay archivo, puedes descomentar
        return None, None, None

df, col_sku_db, col_desc_db = cargar_catalogo()
fecha_actual_mx = obtener_hora_mx()
fecha_hoy_str = fecha_actual_mx.strftime("%d/%m/%Y")
hora_hoy_str = fecha_actual_mx.strftime("%H:%M")

# --- FUNCIÓN: DETECTAR METADATOS (Scanner Profundo) ---
def escanear_texto_profundo(texto_completo):
    """ Busca VIN, Orden y Cliente en cualquier bloque de texto desordenado """
    datos = {}
    texto_upper = texto_completo.upper()
    
    # 1. VIN
    match_vin = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', texto_upper)
    if match_vin: datos['VIN'] = match_vin.group(0)

    # 2. CLIENTE
    match_cliente = re.search(r'(?:CLIENTE|ATN|ATENCIÓN|ASESOR|NOMBRE)[:\.\-\s]+([A-Z\s\.]{4,40})', texto_upper)
    if match_cliente: datos['CLIENTE'] = match_cliente.group(1).strip()
    
    # 3. ORDEN
    match_orden = re.search(r'(?:ORDEN|FOLIO|PEDIDO|COTIZACION)[:\.\-\s#]*([A-Z0-9\-]{4,12})', texto_upper)
    if match_orden:
        datos['ORDEN'] = match_orden.group(1).strip()
    else:
        posibles_nums = re.findall(r'\b\d{5,10}\b', texto_upper)
        if posibles_nums: datos['ORDEN'] = posibles_nums[0]

    return datos

# --- FUNCIÓN: PROCESAR LISTA ---
def procesar_lista_sku(lista_skus):
    encontrados = 0
    errores = []
    
    for item in lista_skus:
        sku_raw = str(item['sku']).upper().strip()
        sku_clean = sku_raw.replace('-', '')
        cant = int(item['cant'])
        
        match = df[df['SKU_CLEAN'] == sku_clean] if df is not None else pd.DataFrame()
        
        if not match.empty:
            row = match.iloc[0]
            desc = traducir_profe(row[col_desc_db])
            precio = row['PRECIO_NUM']
            monto_iva = (precio * cant) * 0.16
            monto_total = (precio * cant) + monto_iva
            
            st.session_state.carrito.
