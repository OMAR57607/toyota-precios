import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
from fpdf import FPDF
import pytz
import re
import os
import base64
import urllib.parse
import math
import zipfile

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(page_title="Toyota Los Fuertes - Cotizador", page_icon="🚘", layout="wide", initial_sidebar_state="expanded")

# Configurar Zona Horaria
tz_cdmx = pytz.timezone('America/Mexico_City') if 'America/Mexico_City' in pytz.all_timezones else None
def obtener_hora_mx(): return datetime.now(tz_cdmx) if tz_cdmx else datetime.now()

# Inicialización de Sesión
def init_session():
    defaults = {
        'carrito': [],
        'errores_carga': [],
        'cliente': "",
        'vin': "",
        'orden': "",
        'asesor': "",
        'temp_sku': "",
        'temp_desc': "",
        'temp_precio': 0.0,
        'ver_preview': False,
        'nieve_activa': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def limpiar_todo():
    st.session_state.carrito = []
    st.session_state.errores_carga = []
    st.session_state.cliente = ""
    st.session_state.vin = ""
    st.session_state.orden = ""
    st.session_state.asesor = ""
    st.session_state.temp_sku = ""
    st.session_state.temp_desc = ""
    st.session_state.temp_precio = 0.0
    st.session_state.ver_preview = False
    st.session_state.nieve_activa = False

init_session()

# ==========================================
# 2. ESTILOS CSS
# ==========================================
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .wa-btn {
        display: inline-flex; align-items: center; justify-content: center;
        background-color: #25D366; color: white !important;
        padding: 0.6rem 1rem; border-radius: 8px; text-decoration: none;
        font-weight: 700; width: 100%; margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
    }
    .wa-btn:hover { background-color: #128C7E; transform: translateY(-2px); }
    .preview-container { background-color: #525659; padding: 20px; border-radius: 8px; display: flex; justify-content: center; margin-top: 20px; overflow-x: auto; }
    .preview-paper { background-color: white !important; color: black !important; width: 100%; max-width: 950px; min-width: 700px; padding: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); font-family: 'Helvetica', 'Arial', sans-serif; }
    .preview-header { border-bottom: 3px solid #eb0a1e; padding-bottom: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end; }
    .preview-title { font-size: 26px; font-weight: 900; color: #eb0a1e; margin: 0; line-height: 1.2; }
    .preview-subtitle { font-size: 14px; color: #444; text-transform: uppercase; letter-spacing: 1px; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 25px; padding: 15px; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; }
    .info-item { font-size: 12px; margin-bottom: 6px; color: #333; }
    .info-label { font-weight: 700; color: #555; display: inline-block; width: 70px; }
    table.custom-table { width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 20px; table-layout: fixed; }
    table.custom-table th { background-color: #eb0a1e !important; color: white !important; padding: 10px 8px; text-align: left; font-weight: bold; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    table.custom-table td { border-bottom: 1px solid #eee; padding: 8px; color: #333 !important; vertical-align: top; word-wrap: break-word; }
    table.custom-table tr:last-child td { border-bottom: 2px solid #eb0a1e; }
    .total-box { margin-left: auto; width: 300px; }
    .total-final { font-size: 24px; font-weight: 900; color: #eb0a1e; border-top: 2px solid #ccc; padding-top: 10px; margin-top: 10px; text-align: right; }
    .badge-base { padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; display: inline-block; color: white; }
    .badge-urg { background: #d32f2f; }
    .badge-med { background: #1976D2; }
    .badge-baj { background: #757575; }
    .status-base { padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; display: inline-block; }
    .status-disp { color: #1b5e20; background: #c8e6c9; border: 1px solid #1b5e20; }
    .status-ped { color: #e65100; background: #ffe0b2; border: 1px solid #e65100; }
    .status-bo { color: #ffffff; background: #212121; border: 1px solid #000000; }
    .status-rev { color: #880E4F; background: #f8bbd0; border: 1px solid #880E4F; }
    .anticipo-warning { color: #ef6c00; font-weight: bold; font-size: 11px; text-align: right; margin-top: 5px; border: 1px dashed #ef6c00; padding: 5px; border-radius: 4px; background-color: #fff3e0; }
    .revisar-warning { color: #880E4F; font-weight: bold; font-size: 11px; text-align: right; margin-top: 5px; border: 1px dashed #880E4F; padding: 5px; border-radius: 4px; background-color: #f8bbd0; }
    .snowflake { color: #fff; font-size: 1em; font-family: Arial, sans-serif; text-shadow: 0 0 5px #000; position: fixed; top: -10%; z-index: 9999; user-select: none; cursor: default; animation-name: snowflakes-fall, snowflakes-shake; animation-duration: 10s, 3s; animation-timing-function: linear, ease-in-out; animation-iteration-count: infinite, infinite; animation-play-state: running, running; }
    @keyframes snowflakes-fall { 0% { top: -10%; } 100% { top: 100%; } }
    @keyframes snowflakes-shake { 0%, 100% { transform: translateX(0); } 50% { transform: translateX(80px); } }
    .snowflake:nth-of-type(0) { left: 1%; animation-delay: 0s, 0s; } .snowflake:nth-of-type(1) { left: 10%; animation-delay: 1s, 1s; } .snowflake:nth-of-type(2) { left: 20%; animation-delay: 6s, .5s; } .snowflake:nth-of-type(3) { left: 30%; animation-delay: 4s, 2s; } .snowflake:nth-of-type(4) { left: 40%; animation-delay: 2s, 2s; } .snowflake:nth-of-type(5) { left: 50%; animation-delay: 8s, 3s; } .snowflake:nth-of-type(6) { left: 60%; animation-delay: 6s, 2s; } .snowflake:nth-of-type(7) { left: 70%; animation-delay: 2.5s, 1s; } .snowflake:nth-of-type(8) { left: 80%; animation-delay: 1s, 0s; } .snowflake:nth-of-type(9) { left: 90%; animation-delay: 3s, 1.5s; } .snowflake:nth-of-type(10) { left: 25%; animation-delay: 2s, 0s; } .snowflake:nth-of-type(11) { left: 65%; animation-delay: 4s, 2.5s; }
    @media only screen and (max-width: 600px) { .preview-paper { padding: 15px; min-width: 100%; } .info-grid { grid-template-columns: 1fr; gap: 10px; } .total-box { width: 100%; } }
    </style>
    """, unsafe_allow_html=True)

if st.session_state.nieve_activa:
    st.markdown("".join([f'<div class="snowflake">{c}</div>' for c in ['❅','❆']*6]), unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS OPTIMIZADA (PARQUET)
# ==========================================
@st.cache_data(show_spinner="Cargando base de datos maestra (970k items)...")
def cargar_catalogo():
    archivo_zip = "base_datos_2026.zip"
    archivo_parquet = "base_datos_2026.parquet"
    
    # 1. Intentar cargar versión optimizada primero
    if os.path.exists(archivo_parquet):
        try:
            df = pd.read_parquet(archivo_parquet)
            # Reconstruir nombres de columnas base para la lógica de búsqueda
            c_sku = next((c for c in df.columns if c == 'ITEM'), None)
            if not c_sku: c_sku = next((c for c in df.columns if 'PART' in c or 'NUM' in c or 'SKU' in c), None)
            c_desc = next((c for c in df.columns if 'DESC' in c), None)
            return df, c_sku, c_desc
        except: pass # Si falla, intenta desde ZIP

    # 2. Si no hay parquet, cargar desde ZIP y crear parquet
    if not os.path.exists(archivo_zip):
        return None, None, None

    try:
        with zipfile.ZipFile(archivo_zip, "r") as z:
            archivos_validos = [f for f in z.namelist() if (f.endswith('.xlsx') or f.endswith('.xls') or f.endswith('.csv')) and not f.startswith('~') and '__MACOSX' not in f]
            if not archivos_validos: return None, None, None
            
            archivo_elegido = archivos_validos[0]
            with z.open(archivo_elegido) as f:
                if archivo_elegido.endswith('.csv'):
                    try: df = pd.read_csv(f, dtype=str)
                    except: f.seek(0); df = pd.read_csv(f, dtype=str, encoding='latin-1')
                else:
                    df = pd.read_excel(f, dtype=str)

        # Limpieza
        df.dropna(how='all', inplace=True)
        df.columns = [str(c).strip().upper() for c in df.columns]

        # Detección
        c_sku = next((c for c in df.columns if c == 'ITEM'), None)
        if not c_sku: c_sku = next((c for c in df.columns if 'PART' in c or 'NUM' in c or 'SKU' in c), None)
        c_desc = next((c for c in df.columns if 'DESC' in c), None)
        c_precio = next((c for c in df.columns if c == 'TOTAL_UNITARIO'), None)
        if not c_precio: c_precio = next((c for c in df.columns if 'TOTAL' in c or 'PRECIO' in c or 'PRICE' in c), None)

        if not c_sku or not c_precio: return None, None, None

        # Procesamiento
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()

        def limpiar_precio(x):
            try: return float(str(x).replace('$', '').replace(',', '').strip())
            except: return 0.0

        df['PRECIO_NUM'] = df[c_precio].apply(limpiar_precio)
        
        # Guardar versión rápida para la próxima
        df.to_parquet(archivo_parquet)

        return df, c_sku, c_desc

    except Exception as e:
        return None, None, None

# Cargamos usando Session State para persistencia en RAM
if 'df_maestro' not in st.session_state:
    st.session_state.df_maestro, st.session_state.col_sku_db, st.session_state.col_desc_db = cargar_catalogo()

df_db = st.session_state.df_maestro
col_sku_db = st.session_state.col_sku_db
col_desc_db = st.session_state.col_desc_db

def analizador_inteligente_archivos(df_raw):
    hallazgos = []; metadata = {}
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    patron_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    patron_orden_8 = r'\b\d{8}\b'
    patron_sku_fmt = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b'
    patron_sku_pln = r'\b[A-Z0-9]{10,12}\b'
    keywords = {'ORDEN': ['ORDEN', 'FOLIO', 'OT', 'OS'], 'ASESOR': ['ASESOR', 'SA', 'ATENDIO', 'ADVISOR'], 'CLIENTE': ['CLIENTE', 'ATTN', 'NOMBRE']}
 
    for r_idx, row in df.iterrows():
        for c_idx, val in row.items():
            if 'VIN' not in metadata:
                m = re.search(patron_vin, val); if m: metadata['VIN'] = m.group(0)
            if 'ORDEN' not in metadata:
                if any(k in val for k in keywords['ORDEN']):
                    m = re.search(patron_orden_8, val)
                    if m: metadata['ORDEN'] = m.group(0)
            if 'ASESOR' not in metadata and any(k in val for k in keywords['ASESOR']):
                cont = re.sub(r'(?:ASESOR|SA|ATENDIO|ADVISOR)[\:\.\-\s]*', '', val).strip()
                if len(cont)>4 and not re.search(r'\d', cont): metadata['ASESOR'] = cont
            if 'CLIENTE' not in metadata and any(k in val for k in keywords['CLIENTE']):
                cont = re.sub(r'(?:CLIENTE|ATTN|NOMBRE)[\:\.\-\s]*', '', val).strip()
                if len(cont)>4: metadata['CLIENTE'] = cont
            es_sku = False; sku_det = None
            if re.match(patron_sku_fmt, val): sku_det = val; es_sku = True
            elif re.match(patron_sku_pln, val) and not val.isdigit(): sku_det = val; es_sku = True
            if es_sku:
                cant = 1
                try: 
                    vecino = df.iloc[r_idx, df.columns.get_loc(c_idx)+1].replace('.0', '')
                    if vecino.isdigit(): cant = int(vecino)
                except: pass
                hallazgos.append({'sku': sku_det, 'cant': cant})
    if 'ORDEN' not in metadata:
        for _, row in df.iterrows():
            for val in row:
                m = re.search(patron_orden_8, str(val)); if m: metadata['ORDEN'] = m.group(0); break
            if 'ORDEN' in metadata: break
    return hallazgos, metadata

def agregar_item_callback(sku, desc_raw, precio_base, cant, tipo, prioridad="Medio", abasto="⚠️ REVISAR", traducir=True):
    if traducir:
        try: desc = GoogleTranslator(source='en', target='es').translate(str(desc_raw))
        except: desc = str(desc_raw)
    else: desc = str(desc_raw)
    iva_monto = (precio_base * cant) * 0.16
    total_linea = (precio_base * cant) + iva_monto
    precio_unitario_con_iva = precio_base * 1.16
    st.session_state.carrito.append({
        "SKU": sku, "Descripción": desc, "Prioridad": prioridad, "Abasto": abasto, "Tiempo Entrega": "",
        "Cantidad": cant, "Precio Base": precio_base, "Precio Unitario (c/IVA)": precio_unitario_con_iva,
        "IVA": iva_monto, "Importe Total": total_linea, "Estatus": "Disponible", "Tipo": tipo
    })

def cargar_en_manual(sku, desc, precio):
    st.session_state.temp_sku = sku
    try: st.session_state.temp_desc = GoogleTranslator(source='en', target='es').translate(str(desc))
    except: st.session_state.temp_desc = str(desc)
    st.session_state.temp_precio = precio

def toggle_preview(): st.session_state.ver_preview = not st.session_state.ver_preview
def toggle_nieve(): st.session_state.nieve_activa = not st.session_state.nieve_activa

# ==========================================
# 4. GENERADOR PDF
# ==========================================
class PDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try: self.image("logo.png", 10, 8, 33)
            except: pass
        self.set_font('Arial', 'B', 16); self.set_text_color(235, 10, 30)
        self.cell(0, 10, 'TOYOTA LOS FUERTES', 0, 1, 'C')
        self.set_font('Arial', '', 10); self.set_text_color(0)
        self.cell(0, 5, 'PRESUPUESTO DE SERVICIOS Y REFACCIONES', 0, 1, 'C'); self.ln(15)
    def footer(self):
        self.set_y(-75)
        self.set_font('Arial', 'B', 7); self.set_text_color(0)
        self.cell(0, 4, 'CONTRATO DE ADHESIÓN Y TÉRMINOS LEGALES (NOM-174-SCFI-2007)', 0, 1, 'L')
        self.set_font('Arial', '', 5); self.set_text_color(60)
        legales = (
            "1. VIGENCIA Y PRECIOS: Presupuesto válido por 24 horas. Precios en MXN incluyen IVA.\n"
            "2. PEDIDOS ESPECIALES: Requieren anticipo del 100%. Cancelación imputable al consumidor aplica pena del 20% (Art. 92 LFPC).\n"
            "3. GARANTÍA: 12 meses en refacciones genuinas. Partes eléctricas sujetas a diagnóstico (Art. 77 LFPC), sin devolución si funcionan bien.\n"
            "4. CONSENTIMIENTO DIGITAL: Aceptación por medios electrónicos (WhatsApp) tiene efectos jurídicos (Art. 89 bis C.Comercio).\n"
            "5. PRIVACIDAD: Datos tratados conforme a la LFPDPPP."
        )
        self.multi_cell(0, 2.5, legales, 0, 'J')
        self.ln(5); y_firma = self.get_y()
        self.line(10, y_firma, 80, y_firma); self.line(110, y_firma, 190, y_firma)
        self.set_font('Arial', 'B', 6)
        self.cell(90, 3, "TOYOTA LOS FUERTES (ASESOR)", 0, 0, 'C'); self.cell(90, 3, "NOMBRE Y FIRMA DE CONFORMIDAD DEL CLIENTE", 0, 1, 'C')
        self.set_y(-12); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

def generar_pdf():
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=80)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9)
    cli_safe = str(st.session_state.cliente.upper()).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(100, 5, cli_safe, 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'FECHA:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, obtener_hora_mx().strftime("%d/%m/%Y"), 0, 1)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'VIN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(100, 5, str(st.session_state.vin.upper()), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'ORDEN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, str(st.session_state.orden.upper()), 0, 1)
    pdf.set_x(10); pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'ASESOR:', 0, 0); pdf.set_font('Arial', '', 9)
    ase_safe = str(st.session_state.asesor.upper()).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(100, 5, ase_safe, 0, 1); pdf.ln(8)
    pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 6)
    cols = [20, 45, 15, 18, 25, 10, 20, 17, 20]
    headers = ['CÓDIGO', 'DESCRIPCIÓN', 'PRIORIDAD', 'ESTATUS', 'TIEMPO ENTREGA', 'CANT', 'UNITARIO', 'IVA', 'TOTAL']
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
    pdf.ln(); pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    sub = 0; iva_total = 0; hay_pedido = False; hay_backorder = False
    for item in st.session_state.carrito:
        sub += item['Precio Base'] * item['Cantidad']; iva_total += item['IVA']
        abasto = item.get('Abasto', '⚠️ REVISAR')
        if "Pedido" in abasto or "Back" in abasto: hay_pedido = True
        if "Back" in abasto: hay_backorder = True
        sku_txt = item['SKU'][:15]; desc_txt = str(item['Descripción']).encode('latin-1', 'replace').decode('latin-1')
        prio = item.get('Prioridad', 'Medio'); st_txt = abasto.replace("⚠️ ", "").upper(); te_txt = str(item['Tiempo Entrega'])[:12]
        text_width = pdf.get_string_width(desc_txt); col_width = cols[1] - 2
        lines = int(math.ceil(text_width / col_width)); lines = 1 if lines < 1 else lines
        row_height = max(6, lines * 4)
        if pdf.get_y() + row_height > 260:
            pdf.add_page(); pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 6)
            for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
            pdf.ln(); pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
        y_start = pdf.get_y(); x_start = pdf.get_x()
        pdf.cell(cols[0], row_height, sku_txt, 1, 0, 'C')
        x_desc = pdf.get_x(); y_desc = pdf.get_y()
        pdf.rect(x_desc, y_desc, cols[1], row_height); pdf.multi_cell(cols[1], 4, desc_txt, 0, 'L')
        pdf.set_xy(x_desc + cols[1], y_desc)
        if prio == 'Urgente': pdf.set_fill_color(211, 47, 47); pdf.set_text_color(255, 255, 255)
        elif prio == 'Medio': pdf.set_fill_color(25, 118, 210); pdf.set_text_color(255, 255, 255)
        else: pdf.set_fill_color(117, 117, 117); pdf.set_text_color(255, 255, 255)
        pdf.cell(cols[2], row_height, prio.upper(), 1, 0, 'C', True)
        pdf.set_fill_color(255, 255, 255); pdf.set_text_color(0, 0, 0)
        if "Disponible" in abasto: pdf.set_fill_color(56, 142, 60); pdf.set_text_color(255, 255, 255)
        elif "Pedido" in abasto: pdf.set_fill_color(245, 124, 0); pdf.set_text_color(255, 255, 255)
        elif "Back" in abasto: pdf.set_fill_color(33, 33, 33); pdf.set_text_color(255, 255, 255)
        else: pdf.set_fill_color(136, 14, 79); pdf.set_text_color(255, 255, 255)
        pdf.cell(cols[3], row_height, st_txt, 1, 0, 'C', True)
        pdf.set_fill_color(255, 255, 255); pdf.set_text_color(0, 0, 0)
        pdf.cell(cols[4], row_height, te_txt, 1, 0, 'C'); pdf.cell(cols[5], row_height, str(item['Cantidad']), 1, 0, 'C')
        pdf.cell(cols[6], row_height, f"${item['Precio Base']:,.2f}", 1, 0, 'R'); pdf.cell(cols[7], row_height, f"${item['IVA'] / item['Cantidad']:,.2f}", 1, 0, 'R')
        pdf.cell(cols[8], row_height, f"${item['Importe Total']:,.2f}", 1, 1, 'R')
    pdf.ln(5); total = sub + iva_total
    if hay_pedido: pdf.set_x(130); pdf.set_font('Arial', 'B', 8); pdf.set_text_color(230, 100, 0); pdf.cell(60, 4, "** REQUIERE ANTICIPO DEL 100% **", 0, 1, 'R')
    if hay_backorder: pdf.set_x(110); pdf.set_font('Arial', 'B', 7); pdf.set_text_color(50, 50, 50); pdf.cell(80, 4, "** REVISAR TIEMPO DE ENTREGA (BACK ORDER) **", 0, 1, 'R')
    pdf.set_x(130); pdf.set_font('Arial', '', 9); pdf.set_text_color(0); pdf.cell(30, 5, 'SUBTOTAL:', 0, 0, 'R'); pdf.cell(30, 5, f"${sub:,.2f}", 0, 1, 'R')
    pdf.set_x(130); pdf.cell(30, 5, 'IVA 16%:', 0, 0, 'R'); pdf.cell(30, 5, f"${iva_total:,.2f}", 0, 1, 'R')
    pdf.set_x(130); pdf.set_font('Arial', 'B', 11); pdf.set_text_color(235, 10, 30); pdf.cell(30, 7, 'GRAN TOTAL:', 0, 0, 'R'); pdf.cell(30, 7, f"${total:,.2f}", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL
# ==========================================
if df_db is None: st.warning(f"⚠️ Atención: No se encontró 'base_datos_2026.zip'.")

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    if st.button("⬜ Apagar Nieve" if st.session_state.nieve_activa else "❄️ Modo Ventisca", type="secondary", use_container_width=True):
        toggle_nieve(); st.rerun()
    st.divider(); st.markdown("### 🚘 Datos del Servicio")
    st.session_state.orden = st.text_input("Orden", st.session_state.orden)
    st.session_state.vin = st.text_input("VIN", st.session_state.vin)
    st.session_state.cliente = st.text_input("Cliente", st.session_state.cliente)
    st.session_state.asesor = st.text_input("Asesor", st.session_state.asesor)
    st.divider(); st.markdown("### 🤖 Carga Inteligente")
    uploaded_file = st.file_uploader("Excel / Macros / CSV", type=['xlsx', 'xlsm', 'csv'], label_visibility="collapsed")
    if uploaded_file and st.button("Analizar Archivo", type="primary"):
        with st.status("Procesando...", expanded=False) as status:
            try:
                df_up = pd.read_csv(uploaded_file, encoding='latin-1', on_bad_lines='skip') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                items, meta = analizador_inteligente_archivos(df_up)
                if 'CLIENTE' in meta: st.session_state.cliente = meta['CLIENTE']
                if 'VIN' in meta: st.session_state.vin = meta['VIN']
                if 'ORDEN' in meta: st.session_state.orden = meta['ORDEN']
                if 'ASESOR' in meta: st.session_state.asesor = meta['ASESOR']
                exitos = 0
                for it in items:
                    clean = str(it['sku']).upper().replace('-', '').strip()
                    if df_db is not None:
                        match = df_db[df_db['SKU_CLEAN'] == clean]
                        if not match.empty:
                            row = match.iloc[0]
                            agregar_item_callback(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], it['cant'], "Refacción", "Medio", "⚠️ REVISAR", traducir=True)
                            exitos += 1
                status.update(label=f"✅ {exitos} items importados", state="complete"); st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    st.divider()
    if st.button("🗑️ Limpieza Total", type="secondary", use_container_width=True): limpiar_todo(); st.rerun()

st.title("Toyota Los Fuertes"); st.caption("Sistema de Cotización de Servicios y Refacciones")

with st.expander("🔎 Agregar Ítems", expanded=True):
    tipo_add = st.radio("Tipo de Ítem:", ["Refacción 🔧", "Mano de Obra 🛠️"], horizontal=True, label_visibility="collapsed")
    if tipo_add == "Refacción 🔧":
        col_l, col_r = st.columns([1.2, 1])
        with col_l:
            q = st.text_input("Buscar SKU o Nombre", key="search_q", placeholder="Ej. Filtro, Balatas...")
            if q and df_db is not None:
                b_raw = q.upper().strip().replace('-', '')
                mask = df_db.apply(lambda x: x.astype(str).str.contains(q, case=False)).any(axis=1) | df_db['SKU_CLEAN'].str.contains(b_raw, na=False)
                for _, row in df_db[mask].head(3).iterrows():
                    c1, c2 = st.columns([3, 1]); sku_db = row[col_sku_db]; pr_db = row['PRECIO_NUM']
                    c1.markdown(f"**{sku_db}**\n${pr_db:,.2f}")
                    c2.button("➕ Agregar", key=f"ad_{sku_db}", type="primary", on_click=agregar_item_callback, args=(sku_db, row[col_desc_db], pr_db, 1, "Refacción"))
        with col_r:
            with st.form("manual"):
                c_s, c_p = st.columns([1, 1]); m_sku = c_s.text_input("SKU", value=st.session_state.temp_sku); m_pr = c_p.number_input("Precio", 0.0, value=float(st.session_state.temp_precio))
                m_desc = st.text_input("Descripción", value=st.session_state.temp_desc)
                if st.form_submit_button("Agregar Manual"):
                    agregar_item_callback(m_sku.upper(), m_desc, m_pr, 1, "Refacción", "Medio", "⚠️ REVISAR", traducir=False)
                    st.session_state.temp_sku = ""; st.session_state.temp_desc = ""; st.session_state.temp_precio = 0.0; st.rerun()
    else:
        with st.form("form_mo"):
            c1, c2, c3 = st.columns([2, 1, 1]); mo_desc = c1.text_input("Servicio", placeholder="Ej. Afinación..."); mo_hrs = c2.number_input("Horas", min_value=0.1, value=1.0); mo_cost = c3.number_input("Costo/Hr", min_value=0.0, value=600.0)
            if st.form_submit_button("Agregar MO"):
                agregar_item_callback("MO-TALLER", f"{mo_desc} ({mo_hrs} hrs)", mo_hrs * mo_cost, 1, "Mano de Obra", "Medio", "Disponible", traducir=False)
                st.rerun()

st.divider(); st.subheader(f"🛒 Carrito ({len(st.session_state.carrito)})")

if st.session_state.carrito:
    def actualizar_cantidad(idx, delta):
        st.session_state.carrito[idx]['Cantidad'] = max(1, st.session_state.carrito[idx]['Cantidad'] + delta)
        item = st.session_state.carrito[idx]; item['IVA'] = (item['Precio Base'] * item['Cantidad']) * 0.16; item['Importe Total'] = (item['Precio Base'] * item['Cantidad']) + item['IVA']
    def eliminar_item(idx): st.session_state.carrito.pop(idx)
    def actualizar_propiedad(idx, clave, key_widget): st.session_state.carrito[idx][clave] = st.session_state[key_widget].replace("🔴 ", "").replace("🔵 ", "").replace("⚪ ", "").replace("✅ ", "").replace("📦 ", "").replace("⚫ ", "").replace("⚠️ ", "")
    def actualizar_tiempo(idx, key_widget): st.session_state.carrito[idx]['Tiempo Entrega'] = st.session_state[key_widget]

    for i, item in enumerate(st.session_state.carrito):
        with st.container(border=True):
            top_col1, top_col2, top_col3 = st.columns([3, 1, 0.3])
            with top_col1: st.markdown(f"**{item['Descripción']}**"); st.caption(f"SKU: {item['SKU']} • P.Unit: ${item['Precio Unitario (c/IVA)']:,.2f}")
            with top_col2: st.markdown(f"<div style='text-align:right; color:#eb0a1e; font-weight:bold; font-size:1.1em;'>${item['Importe Total']:,.2f}</div>", unsafe_allow_html=True)
            with top_col3: st.button("🗑️", key=f"del_{i}", on_click=eliminar_item, args=(i,), type="tertiary")
            c_prio, c_stat, c_time, c_qty = st.columns([1.3, 1.3, 1.5, 1.8])
            idx_prio = 0 if item['Prioridad'] == "Urgente" else (2 if item['Prioridad'] == "Bajo" else 1)
            c_prio.selectbox("Prioridad", ["🔴 Urgente", "🔵 Medio", "⚪ Bajo"], index=idx_prio, key=f"prio_{i}", label_visibility="collapsed", on_change=actualizar_propiedad, args=(i, 'Prioridad', f"prio_{i}"))
            idx_ab = 0 if "Disponible" in item['Abasto'] else (1 if "Pedido" in item['Abasto'] else (2 if "Back" in item['Abasto'] else 3))
            c_stat.selectbox("Abasto", ["✅ Disponible", "📦 Por Pedido", "⚫ Back Order", "⚠️ REVISAR"], index=idx_ab, key=f"abasto_{i}", label_visibility="collapsed", on_change=actualizar_propiedad, args=(i, 'Abasto', f"abasto_{i}"))
            c_time.text_input("Tiempo", value=item['Tiempo Entrega'], placeholder="Tiempo...", key=f"time_{i}", label_visibility="collapsed", on_change=actualizar_tiempo, args=(i, f"time_{i}"))
            with c_qty:
                sc1, sc2, sc3 = st.columns([1, 1, 1])
                sc1.button("➖", key=f"mn_{i}", on_click=actualizar_cantidad, args=(i, -1), use_container_width=True)
                sc2.markdown(f"<div style='text-align:center; font-weight:bold; padding-top:8px;'>{item['Cantidad']}</div>", unsafe_allow_html=True)
                sc3.button("➕", key=f"pl_{i}", on_click=actualizar_cantidad, args=(i, 1), use_container_width=True)

    subtotal = sum(i['Precio Base'] * i['Cantidad'] for i in st.session_state.carrito); total_gral = subtotal * 1.16
    pendientes = [i for i in st.session_state.carrito if "REVISAR" in str(i['Abasto'])]
    if pendientes:
        st.error(f"🛑 REVISAR: {len(pendientes)} partida(s) pendientes de validar estatus.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("👁️ Vista Previa", type="secondary", use_container_width=True): toggle_preview(); st.rerun()
        with c2: st.download_button("📄 PDF", generar_pdf(), f"Cot_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)
        with c3:
            items_wa = "\n".join([f"▪️ {i['Cantidad']}x {i['Descripción']} (${i['Precio Unitario (c/IVA)']:,.2f})" for i in st.session_state.carrito])
            msg = urllib.parse.quote(f"Estimado *{st.session_state.cliente}*,\nPresupuesto Toyota:\nVIN: {st.session_state.vin}\n\n{items_wa}\n\n*TOTAL: ${total_gral:,.2f}*\n\nAtte: {st.session_state.asesor}")
            st.markdown(f'<a href="https://wa.me/?text={msg}" target="_blank" class="wa-btn">📱 WhatsApp</a>', unsafe_allow_html=True)

if st.session_state.ver_preview and st.session_state.carrito:
    # (El HTML de vista previa se mantiene igual que en tu código original)
    rows_html = ""
    hay_p = any("Pedido" in i['Abasto'] or "Back" in i['Abasto'] for i in st.session_state.carrito)
    hay_r = any("REVISAR" in i['Abasto'] for i in st.session_state.carrito)
    for item in st.session_state.carrito:
        p_c = "badge-urg" if item['Prioridad']=="Urgente" else ("badge-med" if item['Prioridad']=="Medio" else "badge-baj")
        a_c = "status-disp" if "Disponible" in item['Abasto'] else ("status-ped" if "Pedido" in item['Abasto'] else ("status-bo" if "Back" in item['Abasto'] else "status-rev"))
        rows_html += f"<tr><td>{item['SKU']}</td><td>{item['Descripción']}</td><td><span class='badge-base {p_c}'>{item['Prioridad']}</span></td><td><span class='status-base {a_c}'>{item['Abasto']}</span></td><td>{item['Tiempo Entrega']}</td><td style='text-align:center'>{item['Cantidad']}</td><td style='text-align:right'>${item['Precio Unitario (c/IVA)']:,.2f}</td><td style='text-align:right'>${item['Importe Total']:,.2f}</td></tr>"
    st.markdown(f"<div class='preview-container'><div class='preview-paper'><div class='preview-header'><h1 class='preview-title'>TOYOTA LOS FUERTES</h1></div><div class='info-grid'><div>CLIENTE: {st.session_state.cliente}<br>VIN: {st.session_state.vin}</div><div>ORDEN: {st.session_state.orden}<br>ASESOR: {st.session_state.asesor}</div></div><table class='custom-table'><thead><tr><th>CÓDIGO</th><th>DESCRIPCIÓN</th><th>PRIORIDAD</th><th>ESTATUS</th><th>T.ENT</th><th>CANT</th><th>UNITARIO</th><th>TOTAL</th></tr></thead><tbody>{rows_html}</tbody></table><div class='total-box'><div class='total-final'>TOTAL: ${total_gral:,.2f}</div></div></div></div>", unsafe_allow_html=True)
