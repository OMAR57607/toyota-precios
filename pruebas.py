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

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(page_title="Toyota Asesores AI", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

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
# 2. ESTILOS CSS (RESPONSIVE & ADAPTATIVO)
# ==========================================
st.markdown("""
    <style>
    /* Ajuste general */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    
    /* Botón WhatsApp */
    .wa-btn {
        display: inline-flex; align-items: center; justify-content: center;
        background-color: #25D366; color: white !important;
        padding: 0.6rem 1rem; border-radius: 8px; text-decoration: none;
        font-weight: 700; width: 100%; margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
    }
    .wa-btn:hover { background-color: #128C7E; transform: translateY(-2px); box-shadow: 0 6px 8px rgba(0,0,0,0.15); }

    /* VISTA PREVIA (HOJA DE PAPEL RESPONSIVA) */
    .preview-container {
        background-color: #525659; /* Fondo gris oscuro neutro */
        padding: 20px;
        border-radius: 8px;
        display: flex;
        justify-content: center;
        margin-top: 20px;
        overflow-x: auto; /* Scroll horizontal si la pantalla es muy pequeña */
    }
    .preview-paper {
        background-color: white !important; /* Siempre blanco */
        color: black !important; /* Texto siempre negro */
        width: 100%;
        max-width: 900px;
        min-width: 600px; /* Ancho mínimo para mantener formato tabla */
        padding: 40px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        font-family: 'Helvetica', 'Arial', sans-serif;
    }
    
    /* Elementos de la Cotización */
    .preview-header { border-bottom: 3px solid #eb0a1e; padding-bottom: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end; }
    .preview-title { font-size: 26px; font-weight: 900; color: #eb0a1e; margin: 0; line-height: 1.2; }
    .preview-subtitle { font-size: 14px; color: #444; text-transform: uppercase; letter-spacing: 1px; }
    
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 25px; padding: 15px; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; }
    .info-item { font-size: 12px; margin-bottom: 6px; color: #333; }
    .info-label { font-weight: 700; color: #555; display: inline-block; width: 70px; }

    /* Tabla Formal */
    table.custom-table { width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 20px; }
    table.custom-table th { background-color: #eb0a1e !important; color: white !important; padding: 10px 8px; text-align: left; font-weight: bold; text-transform: uppercase; }
    table.custom-table td { border-bottom: 1px solid #eee; padding: 8px; color: #333 !important; vertical-align: middle; }
    table.custom-table tr:last-child td { border-bottom: 2px solid #eb0a1e; }
    
    /* Totales */
    .total-box { margin-left: auto; width: 300px; }
    .total-row { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; color: #333; }
    .total-final { font-size: 20px; font-weight: 800; color: #eb0a1e; border-top: 2px solid #ccc; padding-top: 8px; margin-top: 8px; }

    /* Etiquetas */
    .badge-urg { background: #d32f2f; color: white; padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; }
    .status-disp { color: #2e7d32; background: #e8f5e9; border: 1px solid #2e7d32; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; }
    .status-ped { color: #e65100; background: #fff3e0; border: 1px solid #e65100; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; }
    .status-bo { color: #fff; background: #000; border: 1px solid #000; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; }
    .anticipo-warning { color: #ef6c00; font-weight: bold; font-size: 11px; text-align: right; margin-top: 5px; border: 1px dashed #ef6c00; padding: 5px; border-radius: 4px; background-color: #fff3e0; }

    /* Media Query para Móviles */
    @media only screen and (max-width: 600px) {
        .preview-paper { padding: 15px; min-width: 100%; } /* Quita padding extra en móvil */
        .preview-title { font-size: 18px; }
        .info-grid { grid-template-columns: 1fr; gap: 10px; }
        .total-box { width: 100%; }
        /* La tabla hará scroll horizontal gracias a overflow-x en el contenedor padre */
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE NEGOCIO (DB & ANALIZADOR)
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

# --- LÓGICA DE ANALIZADOR RESTAURADA COMPLETAMENTE ---
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

def agregar_item_callback(sku, desc_raw, precio, cant, tipo, prioridad="Medio", abasto="⚠️ REVISAR"):
    try: desc = GoogleTranslator(source='en', target='es').translate(str(desc_raw))
    except: desc = str(desc_raw)
    iva = (precio * cant) * 0.16
    st.session_state.carrito.append({
        "SKU": sku, "Descripción": desc, "Prioridad": prioridad, "Abasto": abasto,
        "Tiempo Entrega": "",
        "Cantidad": cant, "Precio Base": precio, "IVA": iva, 
        "Importe Total": (precio * cant) + iva, "Estatus": "Disponible", "Tipo": tipo
    })

def cargar_en_manual(sku, desc, precio):
    st.session_state.temp_sku = sku
    try: st.session_state.temp_desc = GoogleTranslator(source='en', target='es').translate(str(desc))
    except: st.session_state.temp_desc = str(desc)
    st.session_state.temp_precio = precio

def toggle_preview(): st.session_state.ver_preview = not st.session_state.ver_preview

# ==========================================
# 4. GENERADOR PDF (FORMATO FORMAL)
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
        self.set_y(-70)
        self.set_font('Arial', 'B', 7)
        self.set_text_color(0)
        self.cell(0, 4, 'TÉRMINOS, CONDICIONES Y CONSENTIMIENTO DIGITAL', 0, 1, 'L')
        self.set_font('Arial', '', 5) 
        self.set_text_color(60)
        legales = (
            "1. PEDIDOS ESPECIALES: Requieren el 100% DE PAGO ANTICIPADO. No cancelaciones ni devoluciones.\n"
            "2. PARTES ELECTRICAS: No se aceptan CAMBIOS ni DEVOLUCIONES. Garantia sujeta a dictamen tecnico del fabricante.\n"
            "3. PROFECO: Servicio conforme a la NOM-174-SCFI-2007 (Informacion en servicios). Contrato de Adhesion registrado.\n"
            "4. ACEPTACION DIGITAL: De conformidad con el Art. 89 y 93 del Codigo de Comercio, la aceptacion de este presupuesto por medios "
            "electronicos, opticos o de cualquier otra tecnologia (ej. WhatsApp, Correo), produce los mismos efectos juridicos que la firma autografa.\n"
            "5. PRIVACIDAD: El tratamiento de sus datos personales se realiza conforme a la Ley Federal de Proteccion de Datos Personales en "
            "Posesion de los Particulares (LFPDPPP). Aviso de Privacidad disponible en mostrador.\n"
            "6. GARANTIA: 30 dias MO / 12 meses Refacciones. Vigencia: 24 horas."
        )
        self.multi_cell(0, 2.5, legales, 0, 'J')
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

def generar_pdf():
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=85)
    
    pdf.set_fill_color(245); pdf.rect(10, 35, 190, 22, 'F')
    pdf.set_xy(12, 38); pdf.set_font('Arial', 'B', 9)
    pdf.cell(18, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9)
    cli_safe = str(st.session_state.cliente.upper()).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(90, 5, cli_safe, 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(15, 5, 'FECHA:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, obtener_hora_mx().strftime("%d/%m/%Y"), 0, 1)
    
    pdf.set_x(12); pdf.set_font('Arial', 'B', 9)
    pdf.cell(18, 5, 'VIN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(90, 5, st.session_state.vin.upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(15, 5, 'ORDEN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, st.session_state.orden.upper(), 0, 1)
    
    pdf.set_x(12); pdf.set_font('Arial', 'B', 9)
    pdf.cell(18, 5, 'ASESOR:', 0, 0); pdf.set_font('Arial', '', 9)
    ase_safe = str(st.session_state.asesor.upper()).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(90, 5, ase_safe, 0, 1)
    pdf.ln(8)
    
    pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 8)
    # Ajuste de columnas para que se vea como el CSS
    cols = [22, 40, 12, 15, 20, 8, 18, 18, 18, 12]
    headers = ['CODIGO', 'DESCRIPCION', 'PRIOR', 'STAT', 'T.ENT', 'CT', 'UNIT', 'IVA', 'TOTAL', 'TP']
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
    pdf.ln()
    
    pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    hay_pedido = False
    for item in st.session_state.carrito:
        prio = item.get('Prioridad', 'Medio')
        abasto = item.get('Abasto', '⚠️ REVISAR')
        t_ent = item.get('Tiempo Entrega', '')
        if abasto == "Por Pedido" or abasto == "Back Order": hay_pedido = True
        
        pdf.set_text_color(0)
        pdf.cell(cols[0], 6, item['SKU'][:15], 'B', 0, 'C')
        desc_safe = str(item['Descripción'][:40]).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(cols[1], 6, desc_safe, 'B', 0, 'L')
        
        if prio == 'Urgente': pdf.set_text_color(200, 0, 0); pdf.set_font('Arial', 'B', 7)
        pdf.cell(cols[2], 6, prio.upper(), 'B', 0, 'C')
        pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
        
        if abasto == "⚠️ REVISAR": pdf.set_text_color(200, 0, 0); pdf.set_font('Arial', 'B', 7)
        elif abasto == "Por Pedido": pdf.set_text_color(230, 100, 0); pdf.set_font('Arial', 'B', 7)
        elif abasto == "Back Order": pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', 'B', 7)
        
        st_txt = abasto.replace("⚠️ ", "").upper()
        st_txt = st_txt.replace("POR PEDIDO", "PED").replace("DISPONIBLE", "DISP").replace("BACK ORDER", "BO")
        st_txt = st_txt.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(cols[3], 6, st_txt, 'B', 0, 'C')
        
        pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
        te_safe = str(t_ent[:12]).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(cols[4], 6, te_safe, 'B', 0, 'C')
        pdf.cell(cols[5], 6, str(item['Cantidad']), 'B', 0, 'C')
        pdf.cell(cols[6], 6, f"${item['Precio Base']:,.2f}", 'B', 0, 'R')
        
        iva_unit = (item['Precio Base'] * 0.16) * item['Cantidad']
        pdf.cell(cols[7], 6, f"${iva_unit:,.2f}", 'B', 0, 'R')
        pdf.cell(cols[8], 6, f"${item['Importe Total']:,.2f}", 'B', 0, 'R')
        pdf.cell(cols[9], 6, "MO" if "MO" in item['SKU'] else "REF", 'B', 1, 'C')

    pdf.ln(5)
    sub = sum(i['Precio Base'] * i['Cantidad'] for i in st.session_state.carrito)
    iva = sum(i['IVA'] for i in st.session_state.carrito)
    total = sub + iva
    
    if hay_pedido:
        pdf.set_x(130)
        pdf.set_font('Arial', 'B', 8); pdf.set_text_color(230, 100, 0)
        pdf.cell(60, 5, "** REQUIERE 100% ANTICIPO **", 0, 1, 'R')
        
    pdf.set_x(130); pdf.set_font('Arial', '', 9); pdf.set_text_color(0)
    pdf.cell(30, 6, 'Subtotal:', 0, 0, 'R'); pdf.cell(30, 6, f"${sub:,.2f}", 0, 1, 'R')
    pdf.set_x(130); pdf.cell(30, 6, 'IVA (16%):', 0, 0, 'R'); pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    pdf.set_x(130); pdf.set_font('Arial', 'B', 11); pdf.set_text_color(235, 10, 30)
    pdf.cell(30, 8, 'TOTAL:', 0, 0, 'R'); pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL
# ==========================================
if df_db is None: st.error("⚠️ Error crítico: No se encontró 'lista_precios.zip'"); st.stop()

# --- SIDEBAR (CON SUBIDA DE ARCHIVO RESTAURADA) ---
with st.sidebar:
    st.markdown("### 🚘 Datos del Servicio")
    st.session_state.orden = st.text_input("Orden / Folio", st.session_state.orden)
    st.session_state.vin = st.text_input("VIN (17 Dígitos)", st.session_state.vin, max_chars=17)
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
                
                # Cargar Metadatos
                if 'CLIENTE' in meta: st.session_state.cliente = meta['CLIENTE']
                if 'VIN' in meta: st.session_state.vin = meta['VIN']
                if 'ORDEN' in meta: st.session_state.orden = meta['ORDEN']
                if 'ASESOR' in meta: st.session_state.asesor = meta['ASESOR']
                
                # Cargar Items vs DB
                exitos, fallos = 0, []
                for it in items:
                    clean = str(it['sku']).upper().replace('-', '').strip()
                    match = df_db[df_db['SKU_CLEAN'] == clean]
                    if not match.empty:
                        row = match.iloc[0]
                        agregar_item_callback(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], it['cant'], "Refacción", "Medio", "⚠️ REVISAR")
                        exitos += 1
                    else: fallos.append(it['sku'])
                st.session_state.errores_carga = fallos
                status.update(label=f"✅ {exitos} piezas importadas", state="complete")
                if fallos: st.warning(f"{len(fallos)} códigos no encontrados")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    
    st.divider()
    if st.button("🗑️ Limpieza Total (Nuevo Cliente)", type="secondary", width="stretch"):
        limpiar_todo()
        st.rerun()

# --- MAIN UI ---
st.title("Cotizador Los Fuertes")
col_left, col_right = st.columns([1.2, 2])

with col_left:
    st.subheader("Agregar Ítems")
    tipo_add = st.radio("Tipo:", ["Refacción", "Mano de Obra"], horizontal=True, label_visibility="collapsed")
    if tipo_add == "Refacción":
        tab_bus, tab_man = st.tabs(["🔍 Búsqueda", "✍️ Manual"])
        with tab_bus:
            q = st.text_input("Buscar SKU o Nombre", placeholder="Filtro de aire...")
            if q:
                b_raw = q.upper().strip().replace('-', '')
                mask = df_db.apply(lambda x: x.astype(str).str.contains(q, case=False)).any(axis=1) | df_db['SKU_CLEAN'].str.contains(b_raw, na=False)
                for _, row in df_db[mask].head(3).iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 0.7, 0.7])
                        sku_db = row[col_sku_db]; pr_db = row['PRECIO_NUM']; desc_ori = row[col_desc_db]
                        c1.markdown(f"**{sku_db}**\n\n${pr_db:,.2f}")
                        if c2.button("✏️", key=f"edit_{sku_db}", help="Editar en manual"):
                            cargar_en_manual(sku_db, desc_ori, pr_db)
                            st.rerun()
                        c3.button("➕", key=f"add_{sku_db}", on_click=agregar_item_callback, args=(sku_db, desc_ori, pr_db, 1, "Refacción", "Medio", "⚠️ REVISAR"))
        with tab_man:
            val_sku = st.session_state.temp_sku if st.session_state.temp_sku else "GENERICO"
            val_desc = st.session_state.temp_desc if st.session_state.temp_desc else "Refacción General"
            val_prec = st.session_state.temp_precio if st.session_state.temp_precio else 0.0
            with st.form("manual_part"):
                c1, c2 = st.columns(2)
                m_sku = c1.text_input("SKU", value=val_sku)
                m_pr = c2.number_input("Precio", min_value=0.0, value=float(val_prec))
                m_desc = st.text_input("Descripción", value=val_desc)
                if st.form_submit_button("Agregar Manual"):
                    agregar_item_callback(m_sku.upper(), m_desc, m_pr, 1, "Refacción", "Medio", "⚠️ REVISAR")
                    st.session_state.temp_sku = ""; st.session_state.temp_desc = ""; st.session_state.temp_precio = 0.0
                    st.toast("Agregado", icon="✅")
                    st.rerun()
    else: # Mano de Obra
        with st.container(border=True):
            s_desc = st.text_input("Servicio", placeholder="Ej. Afinación Mayor")
            c1, c2 = st.columns(2)
            s_hrs = c1.number_input("Horas", 1.0, step=0.5)
            s_mo = c2.number_input("Costo Hora", value=600.0)
            if st.button("Agregar Servicio", type="primary"):
                agregar_item_callback("MO-TALLER", f"{s_desc} ({s_hrs}hrs)", s_hrs * s_mo, 1, "Mano de Obra", "Medio", "Disponible")
                st.toast("Servicio Agregado", icon="🛠️")

with col_right:
    st.subheader(f"Presupuesto ({len(st.session_state.carrito)})")
    if st.session_state.carrito:
        df_c = pd.DataFrame(st.session_state.carrito)
        
        edited = st.data_editor(
            df_c,
            column_config={
                "Prioridad": st.column_config.SelectboxColumn("Prioridad", options=["Urgente", "Medio", "Bajo"], required=True, width="small"),
                "Abasto": st.column_config.SelectboxColumn("Abasto", options=["Disponible", "Por Pedido", "Back Order", "⚠️ REVISAR"], required=True, width="small"),
                "Tiempo Entrega": st.column_config.TextColumn("Tiempo Entrega", width="medium"),
                "Precio Base": None, # OCULTO
                "IVA": None, # OCULTO
                "Importe Total": st.column_config.NumberColumn(format="$%.2f", disabled=True),
                "Estatus": None, "Tipo": None, 
                "Cantidad": st.column_config.NumberColumn(min_value=1, step=1, width="small"),
                "Descripción": st.column_config.TextColumn(width="medium", disabled=True),
                "SKU": st.column_config.TextColumn(width="small", disabled=True),
            },
            width="stretch",
            num_rows="dynamic", key="editor_cart"
        )
        if not edited.equals(df_c):
            new_cart = edited.to_dict('records')
            for r in new_cart:
                r['IVA'] = (r['Precio Base'] * r['Cantidad']) * 0.16
                r['Importe Total'] = (r['Precio Base'] * r['Cantidad']) + r['IVA']
            st.session_state.carrito = new_cart
            st.rerun()

        sub = sum(x['Precio Base'] * x['Cantidad'] for x in st.session_state.carrito)
        tot = sub * 1.16
        c_p, c_d, c_w = st.columns([1, 1, 1])
        with c_p:
            if st.button("👁️ Vista Previa" if not st.session_state.ver_preview else "🚫 Cerrar", on_click=toggle_preview, width="stretch"): pass
        with c_d:
            pdf_bytes = generar_pdf()
            st.download_button("📄 PDF", pdf_bytes, f"Cot_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)
        
        with c_w:
            # --- WHATSAPP CON FORMATO DE LISTA SOLICITADO ---
            items_wa = ""
            for i in st.session_state.carrito:
                # Formato: ▪️ 1x AMORTIGUADOR ($1,200.00)
                items_wa += f"▪️ {i['Cantidad']}x {i['Descripción']} (${i['Precio Base']:,.2f})\n"
            
            msg_wa = (
                f"Hola *{st.session_state.cliente}*, envío presupuesto:\n\n"
                f"🚘 VIN: {st.session_state.vin}\n"
                f"📄 Orden: {st.session_state.orden}\n\n"
                f"*REFACCIONES:*\n{items_wa}\n"
                f"💰 *TOTAL: ${tot:,.2f}*\n\n"
                f"Atte: {st.session_state.asesor}\nToyota Los Fuertes"
            )
            msg_enc = urllib.parse.quote(msg_wa)
            wa_link = f"https://wa.me/?text={msg_enc}"
            st.markdown(f'<a href="{wa_link}" target="_blank" class="wa-btn">📱 WhatsApp</a>', unsafe_allow_html=True)

    else: st.info("Carrito vacío.")

# --- VISTA PREVIA MEJORADA (RESPONSIVA) ---
if st.session_state.ver_preview and st.session_state.carrito:
    sub = sum(x['Precio Base'] * x['Cantidad'] for x in st.session_state.carrito)
    tot = sub * 1.16
    rows = ""
    hay_pedido_prev = False
    for item in st.session_state.carrito:
        p_cl = "badge-urg" if item['Prioridad'] == "Urgente" else ("badge-med" if item['Prioridad'] == "Medio" else "badge-baj")
        s_val = item.get('Abasto', '⚠️ REVISAR')
        if s_val == "Disponible": s_cl = "status-disp"
        elif s_val == "Por Pedido": s_cl = "status-ped"; hay_pedido_prev = True
        elif s_val == "Back Order": s_cl = "status-bo"; hay_pedido_prev = True
        else: s_cl = "status-rev"
        te_val = item.get('Tiempo Entrega', '')
        iva_linea = (item['Precio Base'] * 0.16) * item['Cantidad']
        rows += f"<tr><td>{item['SKU']}</td><td>{item['Descripción']}</td><td><span class='{p_cl}'>{item['Prioridad'].upper()}</span></td><td><span class='{s_cl}'>{s_val.upper()}</span></td><td>{te_val}</td><td style='text-align:center'>{item['Cantidad']}</td><td style='text-align:right'>${item['Precio Base']:,.2f}</td><td style='text-align:right'>${iva_linea:,.2f}</td><td style='text-align:right'>${item['Importe Total']:,.2f}</td></tr>"

    anticipo_html = '<div class="anticipo-warning">⚠️ ATENCIÓN: Esta cotización incluye piezas BAJO PEDIDO o BACK ORDER. Se requiere el 100% de anticipo.</div>' if hay_pedido_prev else ''

    html_preview = f"""
    <div class="preview-container">
        <div class="preview-paper">
            <div class="preview-header">
                <div><h1 class="preview-title">TOYOTA LOS FUERTES</h1><div class="preview-subtitle">Presupuesto de Servicios y Refacciones</div></div>
                <div style="text-align:right;"><div style="font-size:24px; font-weight:bold; color:#eb0a1e;">MXN ${tot:,.2f}</div><div style="font-size:11px; color:#666;">TOTAL ESTIMADO</div></div>
                </div>
            <div class="info-grid">
                <div><div class="info-item"><span class="info-label">CLIENTE:</span> {st.session_state.cliente}</div><div class="info-item"><span class="info-label">VIN:</span> {st.session_state.vin}</div></div>
                <div><div class="info-item"><span class="info-label">FECHA:</span> {obtener_hora_mx().strftime("%d/%m/%Y")}</div><div class="info-item"><span class="info-label">ORDEN:</span> {st.session_state.orden}</div><div class="info-item"><span class="info-label">ASESOR:</span> {st.session_state.asesor}</div></div>
            </div>
            <table class="custom-table">
                <thead><tr><th>CÓDIGO</th><th>DESCRIPCIÓN</th><th>PRIORIDAD</th><th>STATUS</th><th>T.ENT</th><th style="text-align:center">CANT</th><th style="text-align:right">UNITARIO</th><th style="text-align:right">IVA</th><th style="text-align:right">TOTAL</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
            <div class="total-box">
                <div class="total-row"><span>Subtotal:</span><span>${sub:,.2f}</span></div>
                <div class="total-row"><span>IVA (16%):</span><span>${sub*0.16:,.2f}</span></div>
                <div class="total-row total-final"><span>TOTAL:</span><span>${tot:,.2f}</span></div>
                {anticipo_html}
            </div>
        </div>
    </div>"""
    st.markdown(html_preview, unsafe_allow_html=True)
