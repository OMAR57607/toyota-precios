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
    table.custom-table th { background-color: #eb0a1e !important; color: white !important; padding: 10px 8px; text-align: left; font-weight: bold; text-transform: uppercase; }
    table.custom-table td { border-bottom: 1px solid #eee; padding: 8px; color: #333 !important; vertical-align: top; word-wrap: break-word; }
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
    Versión Robusta: Funciona para DataFrames estructurados (Excel) y No Estructurados (PDF/OCR)
    """
    hallazgos = []; metadata = {}
    
    # Pre-procesamiento: Convertir todo a string mayúscula
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    
    # Patrones Regex
    patron_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    patron_orden_8 = r'\b\d{8}\b'
    # Patrón SKU: Busca "XXXXX-XXXXX" O "XXXXXXXXXX" (10-12 chars)
    patron_sku_fmt = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b'
    patron_sku_pln = r'\b[A-Z0-9]{10,12}\b'
    
    keywords = {'ORDEN': ['ORDEN', 'FOLIO', 'OT', 'OS'], 'ASESOR': ['ASESOR', 'SA', 'ATENDIO', 'ADVISOR'], 'CLIENTE': ['CLIENTE', 'ATTN', 'NOMBRE']}

    es_texto_plano = df.shape[1] == 1 # Si solo tiene 1 columna, es PDF o Imagen OCR

    for r_idx, row in df.iterrows():
        for c_idx, val in row.items():
            val_str = str(val)
            
            # --- BÚSQUEDA METADATA ---
            if 'VIN' not in metadata:
                m = re.search(patron_vin, val_str)
                if m: metadata['VIN'] = m.group(0)
            
            if 'ORDEN' not in metadata:
                m = re.search(patron_orden_8, val_str)
                if m and any(k in val_str for k in keywords['ORDEN']): metadata['ORDEN'] = m.group(0)
                elif m and not any(k in val_str for k in keywords['ORDEN']):
                    # Si encontramos un numero de 8 digitos pero sin label, lo guardamos tentativo
                    if not metadata.get('ORDEN'): metadata['ORDEN'] = m.group(0)
            
            # --- BÚSQUEDA SKU ---
            sku_encontrado = None
            
            # 1. Intentar encontrar formato con guion (XXXXX-XXXXX) dentro del texto
            m_fmt = re.search(patron_sku_fmt, val_str)
            if m_fmt:
                sku_encontrado = m_fmt.group(0)
            else:
                # 2. Intentar encontrar formato plano (XXXXXXXXXX)
                m_pln = re.search(patron_sku_pln, val_str)
                # Validar que no sea un número de teléfono o VIN (usualmente VIN es 17, SKU es 10 o 12)
                if m_pln and not val_str.isdigit() and len(m_pln.group(0)) in [10, 12]:
                    sku_encontrado = m_pln.group(0)

            if sku_encontrado:
                cant = 1
                
                # LÓGICA EXCEL (Busca en columna vecina)
                if not es_texto_plano:
                    try:
                        idx_actual = df.columns.get_loc(c_idx)
                        if idx_actual + 1 < len(df.columns):
                            vecino = str(df.iloc[r_idx, idx_actual + 1]).replace('.0', '').strip()
                            if vecino.isdigit(): cant = int(vecino)
                    except: pass
                
                # LÓGICA PDF/IMAGEN (Busca número suelto en la misma línea)
                else:
                    # Quitamos el SKU de la línea para no confundirlo con cantidad
                    linea_sin_sku = val_str.replace(sku_encontrado, "")
                    # Buscamos números pequeños (1-99) que indiquen cantidad
                    nums = re.findall(r'\b\d{1,2}\b', linea_sin_sku)
                    if nums:
                        # Tomamos el primer número que parezca cantidad (a veces hay precios, esto es heurístico)
                        for n in nums:
                            if n.isdigit() and 0 < int(n) < 100: 
                                cant = int(n)
                                break

                hallazgos.append({'sku': sku_encontrado, 'cant': cant})
    
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
    st.markdown("### 🤖 Carga Inteligente")
    uploaded_file = st.file_uploader("Excel / CSV / PDF / IMG", type=['xlsx', 'csv', 'pdf', 'png', 'jpg', 'jpeg'], label_visibility="collapsed")
    
    if uploaded_file and st.button("Analizar Archivo", type="primary"):
        with st.status("Procesando...", expanded=True) as status:
            try:
                df_up = None
                fname = uploaded_file.name.lower()
                
                # 1. CARGA EXCEL / CSV
                if fname.endswith('.csv'):
                    df_up = pd.read_csv(uploaded_file, encoding='latin-1', on_bad_lines='skip')
                elif fname.endswith('.xlsx') or fname.endswith('.xls'):
                    df_up = pd.read_excel(uploaded_file)
                
                # 2. CARGA PDF
                elif fname.endswith('.pdf'):
                    text_content = []
                    with pdfplumber.open(uploaded_file) as pdf:
                        for page in pdf.pages:
                            # Extract tables si existen, si no texto
                            text_content.append(page.extract_text())
                    full_text = "\n".join(filter(None, text_content))
                    lines = full_text.split('\n')
                    df_up = pd.DataFrame(lines, columns=['Content'])
                
                # 3. CARGA IMAGEN (OCR)
                elif fname.endswith(('.png', '.jpg', '.jpeg')):
                    try:
                        image = Image.open(uploaded_file)
                        text = pytesseract.image_to_string(image)
                        lines = text.split('\n')
                        df_up = pd.DataFrame(lines, columns=['Content'])
                    except Exception as e:
                        st.error("Error OCR. Verifique Tesseract instalado.")
                        df_up = None

                # 4. PROCESAMIENTO
                if df_up is not None:
                    items, meta = analizador_inteligente_archivos(df_up)
                    
                    # Actualizar metadata si falta
                    if not st.session_state.cliente and 'CLIENTE' in meta: st.session_state.cliente = meta['CLIENTE']
                    if not st.session_state.vin and 'VIN' in meta: st.session_state.vin = meta['VIN']
                    if not st.session_state.orden and 'ORDEN' in meta: st.session_state.orden = meta['ORDEN']
                    if not st.session_state.asesor and 'ASESOR' in meta: st.session_state.asesor = meta['ASESOR']
                    
                    exitos = 0
                    fallos = []
                    
                    for it in items:
                        # Limpieza para match DB (sin guiones)
                        clean = str(it['sku']).upper().replace('-', '').strip()
                        match = df_db[df_db['SKU_CLEAN'] == clean]
                        
                        if not match.empty:
                            row = match.iloc[0]
                            # Verificar si ya existe en carrito para sumar cantidad en vez de duplicar
                            existe = False
                            for prod in st.session_state.carrito:
                                if prod['SKU'] == row[col_sku_db]:
                                    prod['Cantidad'] += it['cant']
                                    prod['IVA'] = (prod['Precio Base'] * prod['Cantidad']) * 0.16
                                    prod['Importe Total'] = (prod['Precio Base'] * prod['Cantidad']) + prod['IVA']
                                    existe = True
                                    break
                            
                            if not existe:
                                agregar_item_callback(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], it['cant'], "Refacción", "Medio", "⚠️ REVISAR", traducir=True)
                            
                            exitos += 1
                        else:
                            fallos.append(it['sku'])
                    
                    status.update(label=f"✅ {exitos} items importados correctamente.", state="complete")
                    if fallos: st.warning(f"No encontrados en catálogo: {', '.join(fallos)}")
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
st.caption("Sistema Integrado de Cotización (OCR + AI Regex)")

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

# VISTA PREVIA (Simplificada para mantener código corto)
if st.session_state.ver_preview:
    st.markdown("---")
    st.markdown(f"### Vista Previa: {st.session_state.cliente}")
    st.info("Visualización HTML activa (similar al PDF generado).")
