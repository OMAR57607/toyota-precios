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

# NUEVAS LIBRERIAS PARA PDF E IMAGENES
import pdfplumber
import pytesseract
from PIL import Image

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
        'ver_preview': False
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

    /* VISTA PREVIA */
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
    
    /* BADGES */
    .badge-base { padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; display: inline-block; color: white; }
    .badge-urg { background: #d32f2f; } 
    .badge-med { background: #f57c00; } 
    .badge-baj { background: #0288d1; } 

    .status-base { padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; display: inline-block; }
    .status-disp { color: #1b5e20; background: #c8e6c9; border: 1px solid #1b5e20; }
    .status-ped { color: #e65100; background: #ffe0b2; border: 1px solid #e65100; }
    .status-bo { color: #ffffff; background: #212121; border: 1px solid #000000; }
    .status-rev { color: #b71c1c; background: #ffcdd2; border: 1px solid #b71c1c; }

    .anticipo-warning { color: #ef6c00; font-weight: bold; font-size: 11px; text-align: right; margin-top: 5px; border: 1px dashed #ef6c00; padding: 5px; border-radius: 4px; background-color: #fff3e0; }
    
    @media only screen and (max-width: 600px) {
        .preview-paper { padding: 15px; min-width: 100%; }
        .info-grid { grid-template-columns: 1fr; gap: 10px; }
        .total-box { width: 100%; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS
# ==========================================
@st.cache_data
def cargar_catalogo():
    if not os.path.exists("lista_precios.zip"): return None, None, None
    try:
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        c_sku = next((c for c in df.columns if 'PART' in c or 'NUM' in c), None)
        c_desc = next((c for c in df.columns if 'DESC' in c), None)
        c_precio = next((c for c in df.columns if 'PRICE' in c or 'PRECIO' in c), None)
        if not c_sku or not c_precio: return None, None, None
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        df['PRECIO_NUM'] = df[c_precio].apply(lambda x: float(str(x).replace('$','').replace(',','').strip()) if str(x).replace('$','').replace(',','').strip().replace('.','',1).isdigit() else 0.0)
        return df, c_sku, c_desc
    except: return None, None, None

df_db, col_sku_db, col_desc_db = cargar_catalogo()

def analizador_inteligente_archivos(df_raw):
    """
    Analiza texto estructurado (Excel) o NO estructurado (PDF/IMG).
    Extrae: SKU (Ignorando guiones), Precio, y Descripción (Traducida).
    """
    hallazgos = []; metadata = {}
    
    # Preprocesamiento
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    
    # --- PATRONES REGEX ---
    patron_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    patron_orden_8 = r'\b\d{8}\b'
    
    # SKU: Busca formato XXXXX-XXXXX o XXXXXXXXXX (ignoraremos el guion al procesar)
    patron_sku_fmt = r'\b[A-Z0-9]{5}-?[A-Z0-9]{5}\b'
    patron_sku_pln = r'\b[A-Z0-9]{10,12}\b'
    
    # Precio: Busca formatos como 1,200.50 o 150.00
    patron_precio = r'\$?\s?(\d{1,3}(?:,\d{3})*\.\d{2})'
    
    keywords = {'ORDEN': ['ORDEN', 'FOLIO', 'OT', 'OS'], 'ASESOR': ['ASESOR', 'SA', 'ATENDIO', 'ADVISOR'], 'CLIENTE': ['CLIENTE', 'ATTN', 'NOMBRE']}

    # Detectar modo Texto Plano (PDF/IMG suelen venir en 1 columna)
    es_texto_plano = df.shape[1] < 2 

    for r_idx, row in df.iterrows():
        for c_idx, val in row.items():
            val_str = str(val)
            
            # 1. METADATA (Encabezados)
            if 'VIN' not in metadata:
                m = re.search(patron_vin, val_str)
                if m: metadata['VIN'] = m.group(0)
            
            if 'ORDEN' not in metadata:
                m = re.search(patron_orden_8, val_str)
                if m and (any(k in val_str for k in keywords['ORDEN']) or not metadata.get('ORDEN')): 
                    metadata['ORDEN'] = m.group(0)
            
            if 'ASESOR' not in metadata and any(k in val_str for k in keywords['ASESOR']):
                cont = re.sub(r'(?:ASESOR|SA|ATENDIO|ADVISOR)[\:\.\-\s]*', '', val_str).strip()
                if len(cont)>4 and not re.search(r'\d', cont): metadata['ASESOR'] = cont
            
            if 'CLIENTE' not in metadata and any(k in val_str for k in keywords['CLIENTE']):
                cont = re.sub(r'(?:CLIENTE|ATTN|NOMBRE)[\:\.\-\s]*', '', val_str).strip()
                if len(cont)>4: metadata['CLIENTE'] = cont

            # 2. EXTRACCIÓN DE SKU, PRECIO Y DESCRIPCIÓN
            sku_encontrado = None
            
            # Buscar SKU (Prioridad formato con guión)
            m_fmt = re.search(patron_sku_fmt, val_str)
            if m_fmt: sku_encontrado = m_fmt.group(0)
            else:
                m_pln = re.search(patron_sku_pln, val_str)
                if m_pln and not val_str.isdigit(): sku_encontrado = m_pln.group(0)
            
            if sku_encontrado:
                cant = 1
                precio_detectado = 0.0
                desc_detectada = ""
                
                if not es_texto_plano:
                    # LÓGICA EXCEL (Columna vecina)
                    try: 
                        idx_num = df.columns.get_loc(c_idx)
                        if idx_num + 1 < len(df.columns):
                            vecino = str(df.iloc[r_idx, idx_num+1]).replace('.0', '').strip()
                            if vecino.isdigit(): cant = int(vecino)
                    except: pass
                else:
                    # LÓGICA PDF/IMG (Separar texto en la misma línea)
                    linea_limpia = val_str
                    
                    # A. Extraer Precio
                    m_precio = re.search(patron_precio, linea_limpia)
                    if m_precio:
                        try:
                            precio_str = m_precio.group(1).replace(',', '')
                            precio_detectado = float(precio_str)
                            linea_limpia = linea_limpia.replace(m_precio.group(0), "") # Quitar precio de la linea
                        except: pass
                    
                    # B. Quitar SKU de la línea
                    linea_limpia = linea_limpia.replace(sku_encontrado, "")
                    
                    # C. Buscar Cantidad (num pequeño restante)
                    numeros = re.findall(r'\b\d{1,2}\b', linea_limpia)
                    for n in numeros:
                        if n.isdigit() and 0 < int(n) < 100:
                            cant = int(n)
                            linea_limpia = re.sub(r'\b'+n+r'\b', '', linea_limpia, 1) # Quitar cant de la linea
                            break
                    
                    # D. Lo que queda es Descripción -> Traducir
                    desc_sucia = re.sub(r'[^\w\s]', '', linea_limpia).strip() # Quitar simbolos raros
                    if len(desc_sucia) > 3:
                        try:
                            # Traducción al vuelo
                            desc_detectada = GoogleTranslator(source='auto', target='es').translate(desc_sucia)
                        except:
                            desc_detectada = desc_sucia

                hallazgos.append({
                    'sku': sku_encontrado, 
                    'cant': cant,
                    'precio_ext': precio_detectado,
                    'desc_ext': desc_detectada
                })
            
    return hallazgos, metadata

def agregar_item_callback(sku, desc_raw, precio_base, cant, tipo, prioridad="Medio", abasto="⚠️ REVISAR", traducir=True):
    if traducir and desc_raw:
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
            "1. VIGENCIA Y PRECIOS: Presupuesto válido por 24 horas. Precios en MXN incluyen IVA. Sujetos a cambio sin previo aviso.\n"
            "2. PEDIDOS ESPECIALES: Para partes no disponibles en stock, se requiere un anticipo del 100%.\n"
            "3. GARANTÍA: 12 meses en refacciones genuinas Toyota y 30 días en mano de obra.\n"
            "4. CONSENTIMIENTO DIGITAL: La aceptación por medios electrónicos produce efectos jurídicos.\n"
            "5. PRIVACIDAD: Sus datos personales son tratados conforme a la Ley."
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
    
    # Datos Header
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(100, 5, str(st.session_state.cliente)[:40], 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'FECHA:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, obtener_hora_mx().strftime("%d/%m/%Y"), 0, 1)
    
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'VIN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(100, 5, str(st.session_state.vin), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'ORDEN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, str(st.session_state.orden), 0, 1)
    
    pdf.ln(5)
    # Tabla
    pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 6)
    cols = [20, 45, 15, 18, 25, 10, 20, 17, 20] 
    headers = ['CÓDIGO', 'DESCRIPCIÓN', 'PRIORIDAD', 'ESTATUS', 'TIEMPO ENTREGA', 'CANT', 'UNITARIO', 'IVA', 'TOTAL']
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
    pdf.ln()

    pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    sub = 0; iva_total = 0; hay_pedido = False
    
    for item in st.session_state.carrito:
        sub += item['Precio Base'] * item['Cantidad']
        iva_total += item['IVA']
        if "Pedido" in item.get('Abasto','') or "Back" in item.get('Abasto',''): hay_pedido = True
        
        # Filas
        sku = item['SKU'][:15]
        desc = str(item['Descripción'])[:50]
        # Validar altura
        if pdf.get_y() > 250: pdf.add_page(); pdf.ln(10)
        
        pdf.cell(cols[0], 6, sku, 1, 0, 'C')
        pdf.cell(cols[1], 6, desc, 1, 0, 'L')
        pdf.cell(cols[2], 6, item['Prioridad'][:9], 1, 0, 'C')
        pdf.cell(cols[3], 6, item['Abasto'].replace("⚠️ ","")[:10], 1, 0, 'C')
        pdf.cell(cols[4], 6, str(item['Tiempo Entrega'])[:12], 1, 0, 'C')
        pdf.cell(cols[5], 6, str(item['Cantidad']), 1, 0, 'C')
        pdf.cell(cols[6], 6, f"${item['Precio Base']:,.2f}", 1, 0, 'R')
        pdf.cell(cols[7], 6, f"${item['IVA']/item['Cantidad']:,.2f}", 1, 0, 'R')
        pdf.cell(cols[8], 6, f"${item['Importe Total']:,.2f}", 1, 1, 'R')

    total = sub + iva_total
    pdf.ln(5)
    pdf.set_x(120)
    pdf.cell(40, 5, 'SUBTOTAL:', 0, 0, 'R'); pdf.cell(30, 5, f"${sub:,.2f}", 0, 1, 'R')
    pdf.set_x(120)
    pdf.cell(40, 5, 'IVA 16%:', 0, 0, 'R'); pdf.cell(30, 5, f"${iva_total:,.2f}", 0, 1, 'R')
    pdf.set_x(120); pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 6, 'TOTAL:', 0, 0, 'R'); pdf.cell(30, 6, f"${total:,.2f}", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL
# ==========================================
if df_db is None: st.error("⚠️ Falta lista_precios.zip en el directorio."); st.stop()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.markdown("### 🚘 Datos del Servicio")
    st.session_state.orden = st.text_input("Orden", st.session_state.orden)
    st.session_state.vin = st.text_input("VIN", st.session_state.vin)
    st.session_state.cliente = st.text_input("Cliente", st.session_state.cliente)
    st.session_state.asesor = st.text_input("Asesor", st.session_state.asesor)
    
    st.divider()
    st.markdown("### 🤖 Carga Inteligente (OCR/PDF)")
    uploaded_file = st.file_uploader("Excel / CSV / PDF / IMG", type=['xlsx', 'csv', 'pdf', 'png', 'jpg', 'jpeg'], label_visibility="collapsed")
    
    if uploaded_file and st.button("Analizar Archivo", type="primary"):
        with st.status("Analizando contenido y traduciendo...", expanded=True) as status:
            try:
                df_up = None
                fname = uploaded_file.name.lower()
                
                # CARGA SEGÚN EXTENSIÓN
                if fname.endswith('.csv'):
                    df_up = pd.read_csv(uploaded_file, encoding='latin-1', on_bad_lines='skip')
                elif fname.endswith(('.xlsx', '.xls')):
                    df_up = pd.read_excel(uploaded_file)
                elif fname.endswith('.pdf'):
                    text_content = []
                    with pdfplumber.open(uploaded_file) as pdf:
                        for page in pdf.pages:
                            text_content.append(page.extract_text())
                    full_text = "\n".join(filter(None, text_content))
                    lines = full_text.split('\n')
                    df_up = pd.DataFrame(lines, columns=['Content'])
                elif fname.endswith(('.png', '.jpg', '.jpeg')):
                    try:
                        image = Image.open(uploaded_file)
                        text = pytesseract.image_to_string(image)
                        lines = text.split('\n')
                        df_up = pd.DataFrame(lines, columns=['Content'])
                    except Exception as e:
                        st.error("Error OCR. Verifique Tesseract instalado.")
                        df_up = None

                # PROCESAMIENTO
                if df_up is not None:
                    items, meta = analizador_inteligente_archivos(df_up)
                    
                    # Cargar Metadata encontrada
                    if 'CLIENTE' in meta and not st.session_state.cliente: st.session_state.cliente = meta['CLIENTE']
                    if 'VIN' in meta and not st.session_state.vin: st.session_state.vin = meta['VIN']
                    if 'ORDEN' in meta and not st.session_state.orden: st.session_state.orden = meta['ORDEN']
                    if 'ASESOR' in meta and not st.session_state.asesor: st.session_state.asesor = meta['ASESOR']
                    
                    exitos = 0
                    
                    for it in items:
                        # 1. Limpieza SKU para buscar en Catálogo
                        sku_raw = str(it['sku']).upper().strip()
                        sku_clean = sku_raw.replace('-', '') # IGNORAR GUIONES EN LA BUSQUEDA
                        
                        match = df_db[df_db['SKU_CLEAN'] == sku_clean]
                        
                        # Definir qué datos usar (DB vs Detectados en PDF)
                        if not match.empty:
                            # Encontrado en catálogo: Usamos datos oficiales
                            row = match.iloc[0]
                            sku_final = row[col_sku_db]
                            desc_final = row[col_desc_db]
                            precio_final = row['PRECIO_NUM']
                            es_traduccion = True # Traducir la del catalogo
                        else:
                            # NO Encontrado: Usamos datos extraídos del PDF/IMG
                            sku_final = sku_raw # Usamos el SKU original leido
                            desc_final = it['desc_ext'] if it['desc_ext'] else "Refacción (Sin descripción)"
                            precio_final = it['precio_ext']
                            es_traduccion = False # Ya viene traducida del analizador

                        # 2. Verificar duplicados en carrito
                        existe = False
                        for prod in st.session_state.carrito:
                            # Comparar limpiando guiones
                            if prod['SKU'].replace('-','') == sku_final.replace('-',''):
                                prod['Cantidad'] += it['cant']
                                prod['IVA'] = (prod['Precio Base'] * prod['Cantidad']) * 0.16
                                prod['Importe Total'] = (prod['Precio Base'] * prod['Cantidad']) + prod['IVA']
                                existe = True
                                break
                        
                        if not existe:
                            agregar_item_callback(
                                sku_final, 
                                desc_final, 
                                precio_final, 
                                it['cant'], 
                                "Refacción", 
                                "Medio", 
                                "⚠️ REVISAR", 
                                traducir=es_traduccion
                            )
                        exitos += 1
                    
                    status.update(label=f"✅ {exitos} items procesados (Catálogo + PDF)", state="complete")
                    if exitos > 0: st.rerun()
                else:
                    st.error("No se pudo leer el archivo.")
            except Exception as e: 
                st.error(f"Error crítico: {str(e)}")

    st.divider()
    if st.button("🗑️ Limpieza Total", type="secondary", use_container_width=True):
        limpiar_todo()
        st.rerun()

# --- MAIN ---
st.title("Toyota Los Fuertes")
st.caption("Sistema Integrado de Cotización")

with st.expander("🔎 Agregar Ítems Manualmente", expanded=True):
    col_l, col_r = st.columns([1.2, 1])
    with col_l:
        q = st.text_input("Buscar SKU o Nombre", key="search_q", placeholder="Ej. 04152...")
        if q:
            b_raw = q.upper().strip().replace('-', '')
            mask = df_db.apply(lambda x: x.astype(str).str.contains(q, case=False)).any(axis=1) | df_db['SKU_CLEAN'].str.contains(b_raw, na=False)
            for _, row in df_db[mask].head(3).iterrows():
                c1, c2, c3 = st.columns([3, 0.7, 1])
                sku_db = row[col_sku_db]; pr_db = row['PRECIO_NUM']
                c1.markdown(f"**{sku_db}**\n${pr_db:,.2f}")
                if c3.button("➕", key=f"ad_{sku_db}"):
                    agregar_item_callback(sku_db, row[col_desc_db], pr_db, 1, "Refacción")
                    st.toast("Agregado", icon="✅"); st.rerun()

    with col_r:
        # Formulario Manual
        with st.form("manual"):
            st.markdown("**Agregar Item Manual**")
            c_s, c_p = st.columns([1, 1])
            m_sku = c_s.text_input("SKU", value=st.session_state.temp_sku)
            m_pr = c_p.number_input("Precio Base", 0.0, value=float(st.session_state.temp_precio))
            m_desc = st.text_input("Descripción", value=st.session_state.temp_desc)
            if st.form_submit_button("Agregar"):
                agregar_item_callback(m_sku.upper(), m_desc, m_pr, 1, "Refacción", "Medio", "⚠️ REVISAR", traducir=False)
                st.session_state.temp_sku = ""; st.session_state.temp_desc = ""; st.session_state.temp_precio = 0.0
                st.rerun()

st.divider()
st.subheader(f"🛒 Carrito ({len(st.session_state.carrito)})")

if st.session_state.carrito:
    df_c = pd.DataFrame(st.session_state.carrito)
    edited = st.data_editor(
        df_c,
        column_config={
            "Prioridad": st.column_config.SelectboxColumn(options=["Urgente", "Medio", "Bajo"], width="small", required=True),
            "Abasto": st.column_config.SelectboxColumn(options=["Disponible", "Por Pedido", "Back Order", "⚠️ REVISAR"], width="small", required= True),
            "Precio Unitario (c/IVA)": st.column_config.NumberColumn("P. Unit. (Neto)", format="$%.2f", disabled=True),
            "Importe Total": st.column_config.NumberColumn("Total Línea", format="$%.2f", disabled=True),
            "Cantidad": st.column_config.NumberColumn(min_value=1, step=1, width="small"),
            "SKU": st.column_config.TextColumn(width="small", disabled=True),
        },
        use_container_width=True, num_rows="dynamic", key="editor_cart"
    )

    if not edited.equals(df_c):
        new_cart = edited.to_dict('records')
        for r in new_cart:
            r['IVA'] = (r['Precio Base'] * r['Cantidad']) * 0.16
            r['Importe Total'] = (r['Precio Base'] * r['Cantidad']) + r['IVA']
        st.session_state.carrito = new_cart
        st.rerun()

    subtotal = sum(i['Precio Base'] * i['Cantidad'] for i in st.session_state.carrito)
    total_gral = subtotal * 1.16

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("👁️ Vista Previa", type="secondary", use_container_width=True): toggle_preview(); st.rerun()
    with c2:
        pdf_bytes = generar_pdf()
        st.download_button("📄 PDF", pdf_bytes, f"Cot_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)
    with c3:
        # Botón WhatsApp Restaurado
        ase_firma = st.session_state.asesor if st.session_state.asesor else "Asesor"
        msg_raw = f"Hola *{st.session_state.cliente}*, su cotización (Orden {st.session_state.orden}) por ${total_gral:,.2f} está lista."
        msg_enc = urllib.parse.quote(msg_raw)
        st.markdown(f'<a href="https://wa.me/?text={msg_enc}" target="_blank" class="wa-btn">📱 WhatsApp</a>', unsafe_allow_html=True)

# VISTA PREVIA
if st.session_state.ver_preview and st.session_state.carrito:
    st.markdown("---")
    # Reutilizando lógica de tabla HTML
    rows_html = ""
    for item in st.session_state.carrito:
        p_class = "badge-base " + ("badge-urg" if item['Prioridad'] == "Urgente" else "badge-med")
        rows_html += f"<tr><td>{item['SKU']}</td><td>{item['Descripción']}</td><td><span class='{p_class}'>{item['Prioridad']}</span></td><td style='text-align:right'>${item['Importe Total']:,.2f}</td></tr>"
    
    st.markdown(f"""
    <div class="preview-container"><div class="preview-paper">
    <h1 class="preview-title">VISTA PREVIA</h1>
    <table class="custom-table"><thead><tr><th>SKU</th><th>DESC</th><th>PRIORIDAD</th><th>TOTAL</th></tr></thead>
    <tbody>{rows_html}</tbody></table>
    <div class="total-final">TOTAL: ${total_gral:,.2f}</div>
    </div></div>
    """, unsafe_allow_html=True)
