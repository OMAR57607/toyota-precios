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
import zipfile  # <--- NUEVO IMPORT NECESARIO

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
        'nieve_activa': False # Nuevo estado para la nieve
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
# 2. ESTILOS CSS (PALETA DE ALTO CONTRASTE Y NIEVE)
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

    /* VISTA PREVIA CONTAINER */
    .preview-container { background-color: #525659; padding: 20px; border-radius: 8px; display: flex; justify-content: center; margin-top: 20px; overflow-x: auto; }
    .preview-paper { background-color: white !important; color: black !important; width: 100%; max-width: 950px; min-width: 700px; padding: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); font-family: 'Helvetica', 'Arial', sans-serif; }
    
    .preview-header { border-bottom: 3px solid #eb0a1e; padding-bottom: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end; }
    .preview-title { font-size: 26px; font-weight: 900; color: #eb0a1e; margin: 0; line-height: 1.2; }
    .preview-subtitle { font-size: 14px; color: #444; text-transform: uppercase; letter-spacing: 1px; }
    
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 25px; padding: 15px; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; }
    .info-item { font-size: 12px; margin-bottom: 6px; color: #333; }
    .info-label { font-weight: 700; color: #555; display: inline-block; width: 70px; }
    
    table.custom-table { width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 20px; table-layout: fixed; }
    table.custom-table th {
        background-color: #eb0a1e !important;
        color: white !important;
        padding: 10px 8px;
        text-align: left;
        font-weight: bold;
        text-transform: uppercase;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    table.custom-table td { border-bottom: 1px solid #eee; padding: 8px; color: #333 !important; vertical-align: top; word-wrap: break-word; }
    table.custom-table tr:last-child td { border-bottom: 2px solid #eb0a1e; }
    
    .total-box { margin-left: auto; width: 300px; }
    .total-final { font-size: 24px; font-weight: 900; color: #eb0a1e; border-top: 2px solid #ccc; padding-top: 10px; margin-top: 10px; text-align: right; }
    
    /* --- PALETA NUEVA: PRIORIDAD --- */
    .badge-base { padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; display: inline-block; color: white; }
    .badge-urg { background: #d32f2f; }  /* ROJO */
    .badge-med { background: #1976D2; }  /* AZUL REY */
    .badge-baj { background: #757575; }  /* GRIS */

    /* --- PALETA NUEVA: ESTATUS --- */
    .status-base { padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; display: inline-block; }
    .status-disp { color: #1b5e20; background: #c8e6c9; border: 1px solid #1b5e20; } /* Verde */
    .status-ped { color: #e65100; background: #ffe0b2; border: 1px solid #e65100; }  /* Naranja */
    .status-bo { color: #ffffff; background: #212121; border: 1px solid #000000; }   /* Negro */
    .status-rev { color: #880E4F; background: #f8bbd0; border: 1px solid #880E4F; }  /* Magenta */

    /* ALERTAS */
    .anticipo-warning { color: #ef6c00; font-weight: bold; font-size: 11px; text-align: right; margin-top: 5px; border: 1px dashed #ef6c00; padding: 5px; border-radius: 4px; background-color: #fff3e0; }
    .revisar-warning { color: #880E4F; font-weight: bold; font-size: 11px; text-align: right; margin-top: 5px; border: 1px dashed #880E4F; padding: 5px; border-radius: 4px; background-color: #f8bbd0; }
    
    /* --- EFECTO NIEVE PERSISTENTE --- */
    .snowflake {
        color: #fff;
        font-size: 1em;
        font-family: Arial, sans-serif;
        text-shadow: 0 0 5px #000;
        position: fixed;
        top: -10%;
        z-index: 9999;
        user-select: none;
        cursor: default;
        animation-name: snowflakes-fall, snowflakes-shake;
        animation-duration: 10s, 3s;
        animation-timing-function: linear, ease-in-out;
        animation-iteration-count: infinite, infinite;
        animation-play-state: running, running;
    }
    @keyframes snowflakes-fall {
        0% { top: -10%; }
        100% { top: 100%; }
    }
    @keyframes snowflakes-shake {
        0%, 100% { transform: translateX(0); }
        50% { transform: translateX(80px); }
    }
    .snowflake:nth-of-type(0) { left: 1%; animation-delay: 0s, 0s; }
    .snowflake:nth-of-type(1) { left: 10%; animation-delay: 1s, 1s; }
    .snowflake:nth-of-type(2) { left: 20%; animation-delay: 6s, .5s; }
    .snowflake:nth-of-type(3) { left: 30%; animation-delay: 4s, 2s; }
    .snowflake:nth-of-type(4) { left: 40%; animation-delay: 2s, 2s; }
    .snowflake:nth-of-type(5) { left: 50%; animation-delay: 8s, 3s; }
    .snowflake:nth-of-type(6) { left: 60%; animation-delay: 6s, 2s; }
    .snowflake:nth-of-type(7) { left: 70%; animation-delay: 2.5s, 1s; }
    .snowflake:nth-of-type(8) { left: 80%; animation-delay: 1s, 0s; }
    .snowflake:nth-of-type(9) { left: 90%; animation-delay: 3s, 1.5s; }
    .snowflake:nth-of-type(10) { left: 25%; animation-delay: 2s, 0s; }
    .snowflake:nth-of-type(11) { left: 65%; animation-delay: 4s, 2.5s; }
    
    @media only screen and (max-width: 600px) {
        .preview-paper { padding: 15px; min-width: 100%; }
        .info-grid { grid-template-columns: 1fr; gap: 10px; }
        .total-box { width: 100%; }
    }
    </style>
    """, unsafe_allow_html=True)

# Lógica del Efecto Nieve
if st.session_state.nieve_activa:
    st.markdown("""
    <div class="snowflake">❅</div>
    <div class="snowflake">❆</div>
    <div class="snowflake">❅</div>
    <div class="snowflake">❆</div>
    <div class="snowflake">❅</div>
    <div class="snowflake">❆</div>
    <div class="snowflake">❅</div>
    <div class="snowflake">❆</div>
    <div class="snowflake">❅</div>
    <div class="snowflake">❆</div>
    <div class="snowflake">❅</div>
    <div class="snowflake">❆</div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS
# ==========================================
@st.cache_data
def cargar_catalogo():
    if not os.path.exists("lista_precios.zip"): return None, None, None
    try:
        # --- MODIFICACIÓN PARA LEER EXCEL DENTRO DE ZIP ---
        with zipfile.ZipFile("lista_precios.zip", 'r') as z:
            # Obtenemos el nombre del primer archivo dentro del ZIP (asumimos que es el Excel)
            nombre_archivo = z.namelist()[0]
            with z.open(nombre_archivo) as f:
                # Leemos como Excel. No se requiere encoding='latin-1' para Excel usualmente
                df = pd.read_excel(f, dtype=str)
        
        # El resto de la lógica de limpieza se mantiene igual
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        c_sku = next((c for c in df.columns if 'PART' in c or 'NUM' in c), None)
        c_desc = next((c for c in df.columns if 'DESC' in c), None)
        c_precio = next((c for c in df.columns if 'PRICE' in c or 'PRECIO' in c), None)
        
        if not c_sku or not c_precio: return None, None, None
        
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        # Limpieza de precio robusta
        df['PRECIO_NUM'] = df[c_precio].apply(lambda x: float(str(x).replace('$','').replace(',','').strip()) if str(x).replace('$','').replace(',','').strip().replace('.','',1).isdigit() else 0.0)
        
        return df, c_sku, c_desc
    except Exception as e:
        print(f"Error cargando catálogo: {e}")
        return None, None, None

df_db, col_sku_db, col_desc_db = cargar_catalogo()

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
                m = re.search(patron_vin, val)
                if m: metadata['VIN'] = m.group(0)
            
            if 'ORDEN' not in metadata:
                if any(k in val for k in keywords['ORDEN']):
                    m = re.search(patron_orden_8, val)
                    if m: metadata['ORDEN'] = m.group(0)
                    else:
                        try:
                            vecino = str(df.iloc[r_idx, df.columns.get_loc(c_idx)+1])
                            m2 = re.search(patron_orden_8, vecino)
                            if m2: metadata['ORDEN'] = m2.group(0)
                        except: pass
            
            if 'ASESOR' not in metadata and any(k in val for k in keywords['ASESOR']):
                cont = re.sub(r'(?:ASESOR|SA|ATENDIO|ADVISOR)[\:\.\-\s]*', '', val).strip()
                if len(cont)>4 and not re.search(r'\d', cont): metadata['ASESOR'] = cont
                else:
                    try:
                        vec = str(df.iloc[r_idx, df.columns.get_loc(c_idx)+1]).strip()
                        if len(vec)>4 and not re.search(r'\d', vec): metadata['ASESOR'] = vec
                    except: pass
            
            if 'CLIENTE' not in metadata and any(k in val for k in keywords['CLIENTE']):
                cont = re.sub(r'(?:CLIENTE|ATTN|NOMBRE)[\:\.\-\s]*', '', val).strip()
                if len(cont)>4: metadata['CLIENTE'] = cont
                else:
                    try:
                        vec = str(df.iloc[r_idx, df.columns.get_loc(c_idx)+1]).strip()
                        if len(vec)>4: metadata['CLIENTE'] = vec
                    except: pass
            
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
                m = re.search(patron_orden_8, str(val))
                if m: metadata['ORDEN'] = m.group(0); break
            if 'ORDEN' in metadata: break
            
    return hallazgos, metadata

def agregar_item_callback(sku, desc_raw, precio_base, cant, tipo, prioridad="Medio", abasto="⚠️ REVISAR", traducir=True):
    if traducir:
        try: desc = GoogleTranslator(source='en', target='es').translate(str(desc_raw))
        except: desc = str(desc_raw)
    else:
        desc = str(desc_raw)
    
    iva_monto = (precio_base * cant) * 0.16
    total_linea = (precio_base * cant) + iva_monto
    precio_unitario_con_iva = precio_base * 1.16
    
    st.session_state.carrito.append({
        "SKU": sku,
        "Descripción": desc,
        "Prioridad": prioridad,
        "Abasto": abasto,
        "Tiempo Entrega": "",
        "Cantidad": cant,
        "Precio Base": precio_base,
        "Precio Unitario (c/IVA)": precio_unitario_con_iva,
        "IVA": iva_monto,
        "Importe Total": total_linea,
        "Estatus": "Disponible",
        "Tipo": tipo
    })

def cargar_en_manual(sku, desc, precio):
    st.session_state.temp_sku = sku
    try: st.session_state.temp_desc = GoogleTranslator(source='en', target='es').translate(str(desc))
    except: st.session_state.temp_desc = str(desc)
    st.session_state.temp_precio = precio

def toggle_preview(): st.session_state.ver_preview = not st.session_state.ver_preview

def toggle_nieve(): st.session_state.nieve_activa = not st.session_state.nieve_activa

# ==========================================
# 4. GENERADOR PDF (LÓGICA COLOR ACTUALIZADA)
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
            "2. PEDIDOS ESPECIALES: Para partes no disponibles en stock, se requiere un anticipo del 100%. En caso de cancelación por causas imputables al consumidor, "
            "se aplicará una pena convencional del 20% sobre el anticipo por gastos administrativos (Art. 92 LFPC).\n"
            "3. GARANTÍA: 12 meses en refacciones genuinas Toyota y 30 días en mano de obra. La garantía de partes eléctricas está sujeta a diagnóstico técnico "
            "para descartar daños por instalación externa (Art. 77 LFPC). Las partes eléctricas no admiten devolución si se encuentran en buen estado funcional.\n"
            "4. CONSENTIMIENTO DIGITAL: De conformidad con los Art. 89 bis y 93 del Código de Comercio, la aceptación de este presupuesto a través de medios electrónicos "
            "(WhatsApp, Correo) produce los mismos efectos jurídicos que la firma autógrafa.\n"
            "5. PRIVACIDAD: Sus datos personales son tratados conforme a la Ley Federal de Protección de Datos Personales en Posesión de los Particulares."
        )
        self.multi_cell(0, 2.5, legales, 0, 'J')
        self.ln(5)
        y_firma = self.get_y()
        self.line(10, y_firma, 80, y_firma); self.line(110, y_firma, 190, y_firma)
        self.set_font('Arial', 'B', 6)
        self.cell(90, 3, "TOYOTA LOS FUERTES (ASESOR)", 0, 0, 'C')
        self.cell(90, 3, "NOMBRE Y FIRMA DE CONFORMIDAD DEL CLIENTE", 0, 1, 'C')
        self.set_y(-12); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

def generar_pdf():
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=80)
    
    # Header Info
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9)
    cli_safe = str(st.session_state.cliente.upper()).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(100, 5, cli_safe, 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'FECHA:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, obtener_hora_mx().strftime("%d/%m/%Y"), 0, 1)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'VIN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(100, 5, str(st.session_state.vin.upper()), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'ORDEN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, str(st.session_state.orden.upper()), 0, 1)
    
    pdf.set_x(10); pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'ASESOR:', 0, 0); pdf.set_font('Arial', '', 9)
    ase_safe = str(st.session_state.asesor.upper()).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(100, 5, ase_safe, 0, 1)
    pdf.ln(8)

    # Tabla Header
    pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 6)
    cols = [20, 45, 15, 18, 25, 10, 20, 17, 20]
    headers = ['CÓDIGO', 'DESCRIPCIÓN', 'PRIORIDAD', 'ESTATUS', 'TIEMPO ENTREGA', 'CANT', 'UNITARIO', 'IVA', 'TOTAL']
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
    pdf.ln()

    # Tabla Body
    pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    sub = 0; iva_total = 0
    hay_pedido = False
    hay_backorder = False

    for item in st.session_state.carrito:
        sub += item['Precio Base'] * item['Cantidad']
        iva_total += item['IVA']
        abasto = item.get('Abasto', '⚠️ REVISAR')
        
        if "Pedido" in abasto or "Back" in abasto: hay_pedido = True
        if "Back" in abasto: hay_backorder = True

        sku_txt = item['SKU'][:15]
        desc_txt = str(item['Descripción']).encode('latin-1', 'replace').decode('latin-1')
        prio = item.get('Prioridad', 'Medio')
        st_txt = abasto.replace("⚠️ ", "").upper()
        te_txt = str(item['Tiempo Entrega'])[:12]
        
        text_width = pdf.get_string_width(desc_txt)
        col_width = cols[1] - 2
        lines = int(math.ceil(text_width / col_width))
        if lines < 1: lines = 1
        line_height = 4
        row_height = max(6, lines * line_height)
        
        if pdf.get_y() + row_height > 260:
            pdf.add_page()
            pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 6)
            for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
            pdf.ln()
            pdf.set_text_color(0); pdf.set_font('Arial', '', 7)

        y_start = pdf.get_y()
        x_start = pdf.get_x()

        # SKU
        pdf.cell(cols[0], row_height, sku_txt, 1, 0, 'C')
        
        # Descripcion
        x_desc = pdf.get_x()
        y_desc = pdf.get_y()
        pdf.rect(x_desc, y_desc, cols[1], row_height)
        pdf.multi_cell(cols[1], line_height, desc_txt, 0, 'L')
        pdf.set_xy(x_desc + cols[1], y_desc)
        
        # --- COLOREADO PRIORIDAD (FONDO) - NUEVA PALETA ---
        if prio == 'Urgente':
            pdf.set_fill_color(211, 47, 47) # ROJO
            pdf.set_text_color(255, 255, 255)
        elif prio == 'Medio':
            pdf.set_fill_color(25, 118, 210) # AZUL REY (Distinto a Naranja)
            pdf.set_text_color(255, 255, 255)
        else: # Bajo
            pdf.set_fill_color(117, 117, 117) # GRIS (Neutro)
            pdf.set_text_color(255, 255, 255)

        pdf.cell(cols[2], row_height, prio.upper(), 1, 0, 'C', True)
        
        # Reset color
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(0, 0, 0)
        
        # --- COLOREADO ESTATUS (FONDO) - NUEVA PALETA ---
        if "Disponible" in abasto:
            pdf.set_fill_color(56, 142, 60) # Verde
            pdf.set_text_color(255, 255, 255)
        elif "Pedido" in abasto:
            pdf.set_fill_color(245, 124, 0) # Naranja (Único naranja)
            pdf.set_text_color(255, 255, 255)
        elif "Back" in abasto:
            pdf.set_fill_color(33, 33, 33) # Negro
            pdf.set_text_color(255, 255, 255)
        else: # Revisar
            pdf.set_fill_color(136, 14, 79) # Magenta/Vino (Distinto a Rojo Urgente)
            pdf.set_text_color(255, 255, 255)

        pdf.cell(cols[3], row_height, st_txt, 1, 0, 'C', True)

        # Reset Color
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(0, 0, 0)
        
        # Resto Columnas
        pdf.cell(cols[4], row_height, te_txt, 1, 0, 'C')
        pdf.cell(cols[5], row_height, str(item['Cantidad']), 1, 0, 'C')
        pdf.cell(cols[6], row_height, f"${item['Precio Base']:,.2f}", 1, 0, 'R')
        pdf.cell(cols[7], row_height, f"${item['IVA'] / item['Cantidad']:,.2f}", 1, 0, 'R')
        pdf.cell(cols[8], row_height, f"${item['Importe Total']:,.2f}", 1, 1, 'R')

    pdf.ln(5)
    total = sub + iva_total
    
    if hay_pedido:
        pdf.set_x(130)
        pdf.set_font('Arial', 'B', 8); pdf.set_text_color(230, 100, 0)
        pdf.cell(60, 4, "** REQUIERE ANTICIPO DEL 100% POR PEDIDO ESPECIAL **", 0, 1, 'R')

    if hay_backorder:
        pdf.set_x(110)
        pdf.set_font('Arial', 'B', 7); pdf.set_text_color(50, 50, 50)
        pdf.cell(80, 4, "** NOTA: REVISAR CON SU ASESOR EL TIEMPO DE ENTREGA (BACK ORDER) **", 0, 1, 'R')

    pdf.set_x(130); pdf.set_font('Arial', '', 9); pdf.set_text_color(0)
    pdf.cell(30, 5, 'SUBTOTAL:', 0, 0, 'R'); pdf.cell(30, 5, f"${sub:,.2f}", 0, 1, 'R')
    pdf.set_x(130)
    pdf.cell(30, 5, 'IVA 16%:', 0, 0, 'R'); pdf.cell(30, 5, f"${iva_total:,.2f}", 0, 1, 'R')
    pdf.set_x(130); pdf.set_font('Arial', 'B', 11); pdf.set_text_color(235, 10, 30)
    pdf.cell(30, 7, 'GRAN TOTAL:', 0, 0, 'R'); pdf.cell(30, 7, f"${total:,.2f}", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL
# ==========================================
if df_db is None: st.error("Falta lista_precios.zip"); st.stop()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    
    # --- BOTÓN DE NIEVE (ON/OFF) ---
    btn_txt = "⬜ Apagar Nieve" if st.session_state.nieve_activa else "❄️ Modo Ventisca"
    if st.button(btn_txt, type="secondary", use_container_width=True):
        toggle_nieve()
        st.rerun()
    # ------------------------------------

    st.divider()
    
    st.markdown("### 🚘 Datos del Servicio")
    st.session_state.orden = st.text_input("Orden", st.session_state.orden)
    st.session_state.vin = st.text_input("VIN", st.session_state.vin)
    st.session_state.cliente = st.text_input("Cliente", st.session_state.cliente)
    st.session_state.asesor = st.text_input("Asesor", st.session_state.asesor)
    
    st.divider()
    st.markdown("### 🤖 Carga Inteligente")
    uploaded_file = st.file_uploader("Excel / CSV", type=['xlsx', 'csv'], label_visibility="collapsed")
    if uploaded_file and st.button("Analizar Archivo", type="primary"):
        with st.status("Procesando...", expanded=False) as status:
            try:
                df_up = pd.read_csv(uploaded_file, encoding='latin-1', on_bad_lines='skip') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                items, meta = analizador_inteligente_archivos(df_up)
                if 'CLIENTE' in meta: st.session_state.cliente = meta['CLIENTE']
                if 'VIN' in meta: st.session_state.vin = meta['VIN']
                if 'ORDEN' in meta: st.session_state.orden = meta['ORDEN']
                if 'ASESOR' in meta: st.session_state.asesor = meta['ASESOR']
                
                exitos, fallos = 0, []
                for it in items:
                    clean = str(it['sku']).upper().replace('-', '').strip()
                    match = df_db[df_db['SKU_CLEAN'] == clean]
                    if not match.empty:
                        row = match.iloc[0]
                        agregar_item_callback(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], it['cant'], "Refacción", "Medio", "⚠️ REVISAR", traducir=True)
                        exitos += 1
                    else: fallos.append(it['sku'])
                status.update(label=f"✅ {exitos} items importados", state="complete")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

    st.divider()
    if st.button("🗑️ Limpieza Total (Nuevo Cliente)", type="secondary", use_container_width=True):
        limpiar_todo()
        st.rerun()

# --- MAIN ---
st.title("Toyota Los Fuertes")
st.caption("Sistema de Cotización de Servicios y Refacciones")

with st.expander("🔎 Agregar Ítems (Refacciones o Mano de Obra)", expanded=True):
    tipo_add = st.radio("Tipo de Ítem:", ["Refacción 🔧", "Mano de Obra 🛠️"], horizontal=True, label_visibility="collapsed")
    
    if tipo_add == "Refacción 🔧":
        col_l, col_r = st.columns([1.2, 1])
        with col_l:
            q = st.text_input("Buscar SKU o Nombre", key="search_q", placeholder="Ej. Filtro, Balatas...")
            if q:
                b_raw = q.upper().strip().replace('-', '')
                mask = df_db.apply(lambda x: x.astype(str).str.contains(q, case=False)).any(axis=1) | df_db['SKU_CLEAN'].str.contains(b_raw, na=False)
                for _, row in df_db[mask].head(3).iterrows():
                    c1, c2 = st.columns([3, 1])
                    sku_db = row[col_sku_db]; pr_db = row['PRECIO_NUM']
                    c1.markdown(f"**{sku_db}**\n${pr_db:,.2f}")
                    c2.button("➕ Agregar", key=f"ad_{sku_db}", type="primary", on_click=agregar_item_callback, args=(sku_db, row[col_desc_db], pr_db, 1, "Refacción"))
        with col_r:
            with st.form("manual"):
                st.markdown("**Agregar Manual (Refacción)**")
                c_s, c_p = st.columns([1, 1])
                m_sku = c_s.text_input("SKU", value=st.session_state.temp_sku)
                m_pr = c_p.number_input("Precio Base", 0.0, value=float(st.session_state.temp_precio))
                m_desc = st.text_input("Descripción", value=st.session_state.temp_desc)
                if st.form_submit_button("Agregar Manual"):
                    agregar_item_callback(m_sku.upper(), m_desc, m_pr, 1, "Refacción", "Medio", "⚠️ REVISAR", traducir=False)
                    st.session_state.temp_sku = ""; st.session_state.temp_desc = ""; st.session_state.temp_precio = 0.0
                    st.rerun()
    else:
        st.markdown("**Agregar Mano de Obra (Servicio)**")
        with st.form("form_mo"):
            c1, c2, c3 = st.columns([2, 1, 1])
            mo_desc = c1.text_input("Descripción del Servicio", placeholder="Ej. Afinación Mayor, Diagnóstico...")
            mo_hrs = c2.number_input("Horas", min_value=0.1, value=1.0, step=0.1)
            mo_cost = c3.number_input("Costo por Hora", min_value=0.0, value=600.0, step=50.0)
            if st.form_submit_button("Agregar Servicio 🛠️"):
                total_mo = mo_hrs * mo_cost
                desc_final = f"{mo_desc} ({mo_hrs} hrs)"
                agregar_item_callback("MO-TALLER", desc_final, total_mo, 1, "Mano de Obra", "Medio", "Disponible", traducir=False)
                st.toast("Mano de Obra Agregada", icon="✅")
                st.rerun()

st.divider()

# ==========================================
# SECCIÓN CARRITO (DISEÑO TARJETAS MINIMALISTAS)
# ==========================================
st.subheader(f"🛒 Carrito ({len(st.session_state.carrito)})")

if st.session_state.carrito:
    
    # --- FUNCIONES DE ACCIÓN DEL CARRITO ---
    def actualizar_cantidad(idx, delta):
        """Suma o resta cantidad asegurando que no baje de 1"""
        nueva_cant = st.session_state.carrito[idx]['Cantidad'] + delta
        if nueva_cant < 1: nueva_cant = 1
        st.session_state.carrito[idx]['Cantidad'] = nueva_cant
        
        # Recalcular montos internos
        item = st.session_state.carrito[idx]
        item['IVA'] = (item['Precio Base'] * item['Cantidad']) * 0.16
        item['Importe Total'] = (item['Precio Base'] * item['Cantidad']) + item['IVA']

    def eliminar_item(idx):
        """Elimina el ítem del carrito"""
        st.session_state.carrito.pop(idx)

    def actualizar_propiedad(idx, clave, key_widget):
        """Actualiza Prioridad o Abasto cuando cambia el Selectbox"""
        valor = st.session_state[key_widget]
        valor_limpio = valor.replace("🔴 ", "").replace("🔵 ", "").replace("⚪ ", "")\
                            .replace("✅ ", "").replace("📦 ", "").replace("⚫ ", "").replace("⚠️ ", "")
        st.session_state.carrito[idx][clave] = valor_limpio

    def actualizar_tiempo_entrega(idx, key_widget):
        """Actualiza el campo de Tiempo de Entrega"""
        st.session_state.carrito[idx]['Tiempo Entrega'] = st.session_state[key_widget]

    # --- ITERACIÓN DE ÍTEMS EN TARJETAS ---
    for i, item in enumerate(st.session_state.carrito):
        
        # Usamos st.container con borde para crear el efecto de "Tarjeta"
        with st.container(border=True):
            
            # --- FILA SUPERIOR: DESCRIPCIÓN Y PRECIO TOTAL ---
            top_col1, top_col2, top_col3 = st.columns([3, 1, 0.3])
            
            with top_col1:
                st.markdown(f"**{item['Descripción']}**")
                st.caption(f"SKU: {item['SKU']} • P.Unit: ${item['Precio Unitario (c/IVA)']:,.2f}")
            
            with top_col2:
                # Precio total alineado y destacado
                st.markdown(f"<div style='text-align:right; color:#eb0a1e; font-weight:bold; font-size:1.1em;'>${item['Importe Total']:,.2f}</div>", unsafe_allow_html=True)
            
            with top_col3:
                st.button("🗑️", key=f"del_{i}", on_click=eliminar_item, args=(i,), type="tertiary", help="Eliminar")

            # --- FILA INFERIOR: CONTROLES OPERATIVOS ---
            # Ajustamos las columnas para que quepan bien los controles
            c_prio, c_stat, c_time, c_qty = st.columns([1.3, 1.3, 1.5, 1.8])
            
            # 1. Prioridad
            opts_prio = ["🔴 Urgente", "🔵 Medio", "⚪ Bajo"]
            idx_prio = 1
            if item['Prioridad'] == "Urgente": idx_prio = 0
            elif item['Prioridad'] == "Bajo": idx_prio = 2
            
            c_prio.selectbox(
                "Prioridad", opts_prio, index=idx_prio, key=f"prio_{i}", label_visibility="collapsed",
                on_change=actualizar_propiedad, args=(i, 'Prioridad', f"prio_{i}")
            )

            # 2. Abasto
            opts_abasto = ["✅ Disponible", "📦 Por Pedido", "⚫ Back Order", "⚠️ REVISAR"]
            idx_abasto = 3
            if "Disponible" in item['Abasto']: idx_abasto = 0
            elif "Pedido" in item['Abasto']: idx_abasto = 1
            elif "Back" in item['Abasto']: idx_abasto = 2
            
            c_stat.selectbox(
                "Abasto", opts_abasto, index=idx_abasto, key=f"abasto_{i}", label_visibility="collapsed",
                on_change=actualizar_propiedad, args=(i, 'Abasto', f"abasto_{i}")
            )

            # 3. Tiempo
            c_time.text_input(
                "Tiempo", value=item['Tiempo Entrega'], placeholder="Tiempo Entrega...", key=f"time_{i}", label_visibility="collapsed",
                on_change=actualizar_tiempo_entrega, args=(i, f"time_{i}")
            )

            # 4. Cantidad (+/-)
            with c_qty:
                sub_c1, sub_c2, sub_c3 = st.columns([1, 1, 1])
                sub_c1.button("➖", key=f"btn_rest_{i}", on_click=actualizar_cantidad, args=(i, -1), use_container_width=True)
                sub_c2.markdown(f"<div style='text-align:center; font-weight:bold; padding-top:8px;'>{item['Cantidad']}</div>", unsafe_allow_html=True)
                sub_c3.button("➕", key=f"btn_sum_{i}", on_click=actualizar_cantidad, args=(i, 1), use_container_width=True)

    # --- TOTALES ---
    subtotal = sum(i['Precio Base'] * i['Cantidad'] for i in st.session_state.carrito)
    total_gral = subtotal * 1.16

    # ============================================================
    # LÓGICA DE BLOQUEO (VALIDACIÓN DE CAMPOS INCOMPLETOS)
    # ============================================================
    pendientes = [i for i in st.session_state.carrito if "REVISAR" in str(i['Abasto'])]

    if pendientes:
        st.error(f"🛑 ACCIÓN REQUERIDA: Tienes {len(pendientes)} partida(s) con estatus '⚠️ REVISAR'.")
        st.markdown("""
        <div style="background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeeba;">
            <strong>⚠️ No se puede continuar:</strong><br>
            Por favor, revisa las tarjetas arriba marcadas con '⚠️ REVISAR' y selecciona el estatus correcto.
        </div>
        """, unsafe_allow_html=True)
        
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("👁️ Vista Previa / Cerrar", type="secondary", use_container_width=True):
                toggle_preview(); st.rerun()
        with c2:
            pdf_bytes = generar_pdf()
            st.download_button("📄 Descargar PDF", pdf_bytes, f"Cot_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)
        with c3:
            items_wa = ""
            for i in st.session_state.carrito:
                items_wa += f"▪️ {i['Cantidad']}x {i['Descripción']} (${i['Precio Unitario (c/IVA)']:,.2f} c/u)\n"
            
            ase_firma = st.session_state.asesor if st.session_state.asesor else "Asesor de Servicio"
            msg_raw = (
                f"Estimado/a *{st.session_state.cliente}*,\n\n"
                f"Por medio del presente, le compartimos el presupuesto solicitado para su vehículo en *Toyota Los Fuertes*:\n\n"
                f"🔹 VIN: {st.session_state.vin}\n"
                f"🔹 Orden: {st.session_state.orden}\n\n"
                f"*DETALLE DEL PRESUPUESTO:*\n"
                f"{items_wa}\n"
                f"--------------------\n"
                f"💰 *GRAN TOTAL: ${total_gral:,.2f} (IVA Incluido)*\n"
                f"--------------------\n\n"
                f"Quedamos atentos a su amable autorización.\n\n"
                f"Atentamente,\n"
                f"*{ase_firma}*\n"
                f"Toyota Los Fuertes"
            )
            msg_enc = urllib.parse.quote(msg_raw)
            st.markdown(f'<a href="https://wa.me/?text={msg_enc}" target="_blank" class="wa-btn">📱 Enviar WhatsApp Formal</a>', unsafe_allow_html=True)

# --- VISTA PREVIA ADAPTATIVA (CON COLORES COMPLETOS) ---
if st.session_state.ver_preview and st.session_state.carrito:
    rows_html = ""
    hay_pedido_prev = False
    hay_revisar_prev = False

    for item in st.session_state.carrito:
        # Lógica colores Prioridad
        p = item['Prioridad']
        p_class = "badge-base " + ("badge-urg" if p == "Urgente" else ("badge-med" if p == "Medio" else "badge-baj"))
        
        # Lógica colores Estatus
        a_val = item.get('Abasto', '⚠️ REVISAR')
        a_class = "status-base " + ("status-disp" if "Disponible" in a_val else ("status-ped" if "Pedido" in a_val else ("status-bo" if "Back" in a_val else "status-rev")))
        
        if "Pedido" in a_val or "Back" in a_val: hay_pedido_prev = True
        if "REVISAR" in a_val: hay_revisar_prev = True
        
        rows_html += f"""<tr>
<td>{item['SKU']}</td>
<td style="max-width: 280px;">{item['Descripción']}</td>
<td><span class="{p_class}">{p}</span></td>
<td><span class="{a_class}">{a_val}</span></td>
<td>{item['Tiempo Entrega']}</td>
<td style="text-align:center">{item['Cantidad']}</td>
<td style="text-align:right">${item['Precio Unitario (c/IVA)']:,.2f}</td>
<td style="text-align:right">${item['Importe Total']:,.2f}</td>
</tr>"""

    anticipo_html = '<div class="anticipo-warning">⚠️ REQUIERE ANTICIPO DEL 100% POR PEDIDO ESPECIAL</div>' if hay_pedido_prev else ''
    revisar_html = '<div class="revisar-warning">⚠️ ATENCIÓN: EXISTEN PARTES PENDIENTES DE VALIDAR PRECIO/DISPONIBILIDAD</div>' if hay_revisar_prev else ''

    html_preview = f"""<div class="preview-container">
<div class="preview-paper">
<div class="preview-header">
<div>
<h1 class="preview-title">TOYOTA LOS FUERTES</h1>
<div class="preview-subtitle">Presupuesto de Servicios y Refacciones</div>
</div>
</div>
<div class="info-grid">
<div>
<div class="info-item"><span class="info-label">CLIENTE:</span> {st.session_state.cliente}</div>
<div class="info-item"><span class="info-label">VIN:</span> {st.session_state.vin}</div>
</div>
<div>
<div class="info-item"><span class="info-label">ORDEN:</span> {st.session_state.orden}</div>
<div class="info-item"><span class="info-label">FECHA:</span> {obtener_hora_mx().strftime("%d/%m/%Y")}</div>
<div class="info-item"><span class="info-label">ASESOR:</span> {st.session_state.asesor}</div>
</div>
</div>
<table class="custom-table">
<thead>
<tr>
<th style="width:12%">CÓDIGO</th>
<th style="width:35%">DESCRIPCIÓN</th>
<th>PRIORIDAD</th>
<th>ESTATUS</th>
<th>T.ENT</th>
<th style="text-align:center">CANT</th>
<th style="text-align:right">PRECIO UNITARIO (CON IVA)</th>
<th style="text-align:right">TOTAL</th>
</tr>
</thead>
<tbody>{rows_html}</tbody>
</table>
<div class="total-box">
<div class="total-final">TOTAL: ${total_gral:,.2f}</div>
{anticipo_html}
{revisar_html}
</div>
</div>
</div>"""
    st.markdown(html_preview, unsafe_allow_html=True)
