import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
from fpdf import FPDF
import pytz
import re
import os
import urllib.parse
import math
import zipfile

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(page_title="Toyota Los Fuertes - Cotizador Pro", page_icon="🚘", layout="wide", initial_sidebar_state="expanded")

# Configurar Zona Horaria
tz_cdmx = pytz.timezone('America/Mexico_City') if 'America/Mexico_City' in pytz.all_timezones else None
def obtener_hora_mx(): return datetime.now(tz_cdmx) if tz_cdmx else datetime.now()

# Inicialización de Sesión
def init_session():
    defaults = {
        'carrito': [],
        'cliente': "", 'vin': "", 'orden': "", 'asesor': "",
        'temp_sku': "", 'temp_desc': "", 'temp_precio': 0.0,
        'ver_preview': False, 'nieve_activa': False
    }
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

def limpiar_todo():
    for k in ['carrito', 'cliente', 'vin', 'orden', 'asesor', 'temp_sku', 'temp_desc', 'temp_precio']:
        st.session_state[k] = [] if k == 'carrito' else (0.0 if 'precio' in k else "")
    st.session_state.ver_preview = False

init_session()

# ==========================================
# 2. ESTILOS CSS (CORREGIDO PARA VISIBILIDAD)
# ==========================================
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .wa-btn {
        display: inline-flex; align-items: center; justify-content: center;
        background-color: #25D366; color: white !important; padding: 0.6rem 1rem; border-radius: 8px;
        text-decoration: none; font-weight: 700; width: 100%; margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
    }
    .wa-btn:hover { background-color: #128C7E; transform: translateY(-2px); }
    
    .stCheckbox { padding-top: 10px; transform: scale(1.1); } 
    
    /* Colores de Prioridad (Borde Izquierdo) */
    .prio-urgente { border-left: 5px solid #d32f2f !important; background-color: rgba(211, 47, 47, 0.05); }
    .prio-medio { border-left: 5px solid #1976D2 !important; background-color: rgba(25, 118, 210, 0.05); }
    .prio-bajo { border-left: 5px solid #757575 !important; background-color: rgba(117, 117, 117, 0.05); }
    
    /* CAJA DE TOTALES (SOLUCIÓN TEXTO INVISIBLE) */
    .subtotal-box {
        background-color: #f8f9fa; 
        border: 1px solid #dee2e6; 
        border-radius: 8px; 
        padding: 15px; 
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        color: #000000 !important; /* Fuerza letras negras */
    }
    .subtotal-row { 
        display: flex; 
        justify-content: space-between; 
        font-size: 14px; 
        margin-bottom: 5px; 
        color: #000000 !important; /* Fuerza letras negras */
    }
    .gran-total { 
        font-size: 22px; 
        font-weight: 900; 
        color: #eb0a1e !important; 
        text-align: right; 
        border-top: 2px solid #ccc; 
        padding-top: 10px; 
        margin-top: 5px; 
    }
    
    /* Vista Previa */
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
    .total-box { margin-left: auto; width: 350px; }
    .total-line { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px; color: #333; }
    .total-final { font-size: 24px; font-weight: 900; color: #eb0a1e; border-top: 2px solid #ccc; padding-top: 10px; margin-top: 10px; text-align: right; }
    
    /* Etiquetas PDF/Preview */
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
    
    /* Nieve */
    .snowflake { color: #fff; font-size: 1em; font-family: Arial, sans-serif; text-shadow: 0 0 5px #000; position: fixed; top: -10%; z-index: 9999; user-select: none; cursor: default; animation-name: snowflakes-fall, snowflakes-shake; animation-duration: 10s, 3s; animation-timing-function: linear, ease-in-out; animation-iteration-count: infinite, infinite; animation-play-state: running, running; }
    @keyframes snowflakes-fall { 0% { top: -10%; } 100% { top: 100%; } }
    @keyframes snowflakes-shake { 0%, 100% { transform: translateX(0); } 50% { transform: translateX(80px); } }
    .snowflake:nth-of-type(0) { left: 1%; animation-delay: 0s, 0s; } .snowflake:nth-of-type(1) { left: 10%; animation-delay: 1s, 1s; } .snowflake:nth-of-type(2) { left: 20%; animation-delay: 6s, .5s; } .snowflake:nth-of-type(3) { left: 30%; animation-delay: 4s, 2s; } .snowflake:nth-of-type(4) { left: 40%; animation-delay: 2s, 2s; } .snowflake:nth-of-type(5) { left: 50%; animation-delay: 8s, 3s; }
    </style>
    """, unsafe_allow_html=True)

if st.session_state.nieve_activa:
    st.markdown("".join([f'<div class="snowflake">{c}</div>' for c in ['❅','❆']*6]), unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS
# ==========================================
@st.cache_data(show_spinner="Cargando base de datos maestra (970k items)...")
def cargar_catalogo():
    archivo_zip = "base_datos_2026.zip"
    archivo_parquet = "base_datos_2026.parquet"
    
    # 1. Parquet
    if os.path.exists(archivo_parquet):
        try:
            df = pd.read_parquet(archivo_parquet)
            c_sku = next((c for c in df.columns if c == 'ITEM'), None)
            if not c_sku: c_sku = next((c for c in df.columns if 'PART' in c or 'NUM' in c or 'SKU' in c), None)
            c_desc = next((c for c in df.columns if 'DESC' in c), None)
            return df, c_sku, c_desc
        except: pass

    # 2. ZIP
    if not os.path.exists(archivo_zip): return None, None, None

    try:
        with zipfile.ZipFile(archivo_zip, "r") as z:
            archivos_validos = [f for f in z.namelist() if (f.endswith('.xlsx') or f.endswith('.xls') or f.endswith('.csv')) and not f.startswith('~') and '__MACOSX' not in f]
            if not archivos_validos: return None, None, None
            archivo_elegido = archivos_validos[0]
            with z.open(archivo_elegido) as f:
                if archivo_elegido.endswith('.csv'):
                    try: df = pd.read_csv(f, dtype=str)
                    except: f.seek(0); df = pd.read_csv(f, dtype=str, encoding='latin-1')
                else: df = pd.read_excel(f, dtype=str)

        df.dropna(how='all', inplace=True)
        df.columns = [str(c).strip().upper() for c in df.columns]
        c_sku = next((c for c in df.columns if c == 'ITEM'), None)
        if not c_sku: c_sku = next((c for c in df.columns if 'PART' in c or 'NUM' in c or 'SKU' in c), None)
        c_desc = next((c for c in df.columns if 'DESC' in c), None)
        c_precio = next((c for c in df.columns if c == 'TOTAL_UNITARIO'), None)
        if not c_precio: c_precio = next((c for c in df.columns if 'TOTAL' in c or 'PRECIO' in c or 'PRICE' in c), None)

        if not c_sku or not c_precio: return None, None, None

        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()

        def limpiar_precio(x):
            try: return float(str(x).replace('$', '').replace(',', '').strip())
            except: return 0.0

        df['PRECIO_NUM'] = df[c_precio].apply(limpiar_precio)
        df.to_parquet(archivo_parquet) # Guardar optimizado
        return df, c_sku, c_desc
    except: return None, None, None

if 'df_maestro' not in st.session_state:
    st.session_state.df_maestro, st.session_state.col_sku_db, st.session_state.col_desc_db = cargar_catalogo()

df_db = st.session_state.df_maestro
col_sku_db = st.session_state.col_sku_db
col_desc_db = st.session_state.col_desc_db

# Analizador
def analizador_inteligente_archivos(df_raw):
    hallazgos = []; metadata = {}
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    patron_sku = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b'
    
    for r_idx, row in df.iterrows():
        for c_idx, val in row.items():
            if 'VIN' not in metadata and re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', val): metadata['VIN'] = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', val).group(0)
            if 'ORDEN' not in metadata and re.search(r'\b\d{8}\b', val): metadata['ORDEN'] = re.search(r'\b\d{8}\b', val).group(0)
            
            if re.match(patron_sku, val) or (re.match(r'\b[A-Z0-9]{10,12}\b', val) and not val.isdigit()):
                cant = 1
                try: 
                    vecino = df.iloc[r_idx, df.columns.get_loc(c_idx)+1].replace('.0', '')
                    if vecino.isdigit(): cant = int(vecino)
                except: pass
                hallazgos.append({'sku': val, 'cant': cant})
    return hallazgos, metadata

def agregar_item_callback(sku, desc_raw, precio_base, cant, tipo, prioridad="Medio", abasto="⚠️ REVISAR", traducir=True):
    desc = GoogleTranslator(source='en', target='es').translate(str(desc_raw)) if traducir else str(desc_raw)
    st.session_state.carrito.append({
        "SKU": sku, "Descripción": desc, "Prioridad": prioridad, "Abasto": abasto, "Tiempo Entrega": "",
        "Cantidad": cant, "Precio Base": precio_base, "Precio Unitario (c/IVA)": precio_base * 1.16,
        "IVA": (precio_base * cant) * 0.16, "Importe Total": (precio_base * cant) * 1.16, 
        "Tipo": tipo, "Seleccionado": True 
    })

def toggle_nieve(): st.session_state.nieve_activa = not st.session_state.nieve_activa
def toggle_preview(): st.session_state.ver_preview = not st.session_state.ver_preview

# ==========================================
# 4. GENERADOR PDF (DESGLOSE INTEGRADO)
# ==========================================
class PDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try: self.image("logo.png", 10, 8, 33)
            except: pass
        self.set_font('Arial', 'B', 16); self.set_text_color(235, 10, 30); self.cell(0, 10, 'TOYOTA LOS FUERTES', 0, 1, 'C')
        self.set_font('Arial', '', 10); self.set_text_color(0); self.cell(0, 5, 'PRESUPUESTO DE SERVICIOS Y REFACCIONES', 0, 1, 'C'); self.ln(15)
    def footer(self):
        self.set_y(-25); self.set_font('Arial', 'I', 7); self.set_text_color(100)
        self.cell(0, 10, 'Precios en MXN con IVA incluido. Presupuesto válido por 24 horas.', 0, 0, 'C')

def generar_pdf(items_filtrados, desglose):
    pdf = PDF(); pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=30)
    
    # Datos
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(100, 5, str(st.session_state.cliente), 0, 1)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'VIN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(100, 5, str(st.session_state.vin), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'ORDEN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, str(st.session_state.orden), 0, 1)
    pdf.ln(5)

    # Ordenar
    orden = {"Urgente": 1, "Medio": 2, "Bajo": 3}
    items_ord = sorted(items_filtrados, key=lambda x: orden.get(x['Prioridad'], 2))

    # Headers
    pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 7)
    cols = [25, 60, 20, 25, 15, 20, 25]
    headers = ['CÓDIGO', 'DESCRIPCIÓN', 'PRIORIDAD', 'ESTATUS', 'CANT', 'UNITARIO', 'TOTAL']
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
    pdf.ln()

    # Body
    pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    for item in items_ord:
        sku = item['SKU'][:15]; desc = str(item['Descripción'])[:35]
        prio = item['Prioridad']; stat = item['Abasto'].replace('⚠️ ', '')
        pdf.cell(cols[0], 6, sku, 1); pdf.cell(cols[1], 6, desc, 1)
        if prio == "Urgente": pdf.set_text_color(200, 0, 0); pdf.set_font('Arial', 'B', 7)
        pdf.cell(cols[2], 6, prio.upper(), 1, 0, 'C'); pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
        pdf.cell(cols[3], 6, stat, 1, 0, 'C'); pdf.cell(cols[4], 6, str(item['Cantidad']), 1, 0, 'C')
        pdf.cell(cols[5], 6, f"${item['Precio Unitario (c/IVA)']:,.2f}", 1, 0, 'R')
        pdf.cell(cols[6], 6, f"${item['Importe Total']:,.2f}", 1, 1, 'R')
    pdf.ln(5)

    # === DESGLOSE EN PDF ===
    pdf.set_x(100) 
    pdf.set_font('Arial', 'B', 8); pdf.cell(50, 6, "DESGLOSE POR PRIORIDAD", 'B', 1, 'R')
    pdf.set_font('Arial', '', 8)
    if desglose['Urgente'] > 0:
        pdf.set_x(100); pdf.cell(50, 5, "Total Urgente: ", 0, 0, 'R'); pdf.cell(40, 5, f"${desglose['Urgente']:,.2f}", 0, 1, 'R')
    if desglose['Medio'] > 0:
        pdf.set_x(100); pdf.cell(50, 5, "Total Medio: ", 0, 0, 'R'); pdf.cell(40, 5, f"${desglose['Medio']:,.2f}", 0, 1, 'R')
    if desglose['Bajo'] > 0:
        pdf.set_x(100); pdf.cell(50, 5, "Total Bajo: ", 0, 0, 'R'); pdf.cell(40, 5, f"${desglose['Bajo']:,.2f}", 0, 1, 'R')
    
    pdf.ln(2); pdf.set_x(100)
    pdf.set_font('Arial', 'B', 12); pdf.set_text_color(235, 10, 30)
    pdf.cell(50, 8, "GRAN TOTAL:", 0, 0, 'R'); pdf.cell(40, 8, f"${desglose['GranTotal']:,.2f}", 0, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL
# ==========================================
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    if st.button("⬜ Apagar Nieve" if st.session_state.nieve_activa else "❄️ Modo Ventisca", type="secondary"): toggle_nieve(); st.rerun()
    st.divider()
    st.session_state.orden = st.text_input("Orden", st.session_state.orden)
    st.session_state.vin = st.text_input("VIN", st.session_state.vin)
    st.session_state.cliente = st.text_input("Cliente", st.session_state.cliente)
    st.session_state.asesor = st.text_input("Asesor", st.session_state.asesor)
    st.divider(); st.write("📂 Carga Masiva")
    uploaded_file = st.file_uploader("Archivo", type=['xlsx', 'csv'], label_visibility="collapsed")
    if uploaded_file and st.button("Importar"):
        try:
            df_up = pd.read_csv(uploaded_file, encoding='latin-1', on_bad_lines='skip') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            items, meta = analizador_inteligente_archivos(df_up)
            if not st.session_state.cliente: st.session_state.cliente = meta.get('CLIENTE', '')
            if not st.session_state.vin: st.session_state.vin = meta.get('VIN', '')
            cont=0
            for it in items:
                if df_db is not None:
                    match = df_db[df_db['SKU_CLEAN'] == str(it['sku']).upper().replace('-','').strip()]
                    if not match.empty:
                        r = match.iloc[0]; agregar_item_callback(r[col_sku_db], r[col_desc_db], r['PRECIO_NUM'], it['cant'], "Refacción"); cont+=1
            st.success(f"{cont} items cargados."); st.rerun()
        except: st.error("Error al leer.")
    if st.button("🗑️ Vaciar Carrito", type="primary"): limpiar_todo(); st.rerun()

st.title("Toyota Los Fuertes"); st.caption("Cotizador Inteligente")
with st.expander("🔎 Buscador Manual", expanded=False):
    c1, c2 = st.columns([3,1]); q = c1.text_input("SKU / Nombre")
    if q and df_db is not None:
        mask = df_db.apply(lambda x: x.astype(str).str.contains(q, case=False)).any(axis=1)
        for _, r in df_db[mask].head(3).iterrows():
            st.write(f"**{r[col_sku_db]}** - ${r['PRECIO_NUM']:,.2f}"); st.button("Agregar", key=r[col_sku_db], on_click=agregar_item_callback, args=(r[col_sku_db], r[col_desc_db], r['PRECIO_NUM'], 1, "Refacción"))

st.divider(); st.subheader(f"🛒 Carrito ({len(st.session_state.carrito)} items)")

if st.session_state.carrito:
    # 1. LISTADO DE ITEMS
    for i, item in enumerate(st.session_state.carrito):
        prio_css = "prio-urgente" if item['Prioridad']=="Urgente" else ("prio-medio" if item['Prioridad']=="Medio" else "prio-bajo")
        with st.container():
            c_check, c_info, c_controls = st.columns([0.5, 4, 6])
            with c_check: item['Seleccionado'] = st.checkbox("", value=item['Seleccionado'], key=f"sel_{i}")
            with c_info: st.markdown(f"<div class='{prio_css}' style='padding-left:10px;'><strong>{item['SKU']}</strong><br><small>{item['Descripción'][:40]}</small></div>", unsafe_allow_html=True)
            with c_controls:
                cc1, cc2, cc3, cc4 = st.columns([1.5, 1.5, 1.5, 0.5])
                item['Prioridad'] = cc1.selectbox("Prio", ["Urgente", "Medio", "Bajo"], ["Urgente", "Medio", "Bajo"].index(item['Prioridad']), key=f"p_{i}", label_visibility="collapsed")
                item['Cantidad'] = cc2.number_input("Cant", 1, 100, item['Cantidad'], key=f"c_{i}", label_visibility="collapsed")
                item['Importe Total'] = (item['Precio Base'] * item['Cantidad']) * 1.16
                cc3.markdown(f"**${item['Importe Total']:,.2f}**")
                if cc4.button("❌", key=f"del_{i}"): st.session_state.carrito.pop(i); st.rerun()
        st.divider()

    # 2. CÁLCULO TOTALES
    items_act = [it for it in st.session_state.carrito if it['Seleccionado']]
    totales = {"Urgente": 0.0, "Medio": 0.0, "Bajo": 0.0}
    for it in items_act: totales[it['Prioridad']] += it['Importe Total']
    gran_total = sum(totales.values())
    totales['GranTotal'] = gran_total

    # 3. PANEL RESUMEN
    st.markdown("### 📊 Resumen Financiero")
    c_res, c_acc = st.columns([1, 1])
    
    with c_res:
        st.markdown(f"""
        <div class="subtotal-box">
            <div class="subtotal-row"><span style='color:#d32f2f; font-weight:bold;'>🔴 Total Urgente:</span> <span>${totales['Urgente']:,.2f}</span></div>
            <div class="subtotal-row"><span style='color:#1976D2; font-weight:bold;'>🔵 Total Medio:</span> <span>${totales['Medio']:,.2f}</span></div>
            <div class="subtotal-row"><span style='color:#757575; font-weight:bold;'>⚪ Total Bajo:</span> <span>${totales['Bajo']:,.2f}</span></div>
            <div class="gran-total">TOTAL: ${gran_total:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with c_acc:
        if items_act:
            if st.button("👁️ Vista Previa", type="secondary", use_container_width=True): toggle_preview(); st.rerun()
            pdf_bytes = generar_pdf(items_act, totales)
            st.download_button("📄 PDF Desglosado", pdf_bytes, f"Cot_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)
            
            txt_wa = f"Estimado *{st.session_state.cliente}*,\nCotización {st.session_state.orden}:\n\n"
            if totales['Urgente']>0: txt_wa += f"🔴 Urgente: ${totales['Urgente']:,.2f}\n"
            if totales['Medio']>0: txt_wa += f"🔵 Medio: ${totales['Medio']:,.2f}\n"
            txt_wa += f"\n💰 TOTAL: ${gran_total:,.2f}"
            st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(txt_wa)}" target="_blank" class="wa-btn">📱 WhatsApp</a>', unsafe_allow_html=True)
        else: st.warning("Selecciona items.")

# === VISTA PREVIA (DESGLOSE AGREGADO) ===
if st.session_state.ver_preview and st.session_state.carrito:
    items_prev = [it for it in st.session_state.carrito if it['Seleccionado']]
    if items_prev:
        rows = ""
        for item in items_prev:
            p_cls = "badge-urg" if item['Prioridad']=="Urgente" else ("badge-med" if item['Prioridad']=="Medio" else "badge-baj")
            rows += f"<tr><td>{item['SKU']}</td><td>{item['Descripción']}</td><td><span class='badge-base {p_cls}'>{item['Prioridad']}</span></td><td>{item['Abasto']}</td><td>{item['Tiempo Entrega']}</td><td>{item['Cantidad']}</td><td>${item['Precio Unitario (c/IVA)']:,.2f}</td><td>${item['Importe Total']:,.2f}</td></tr>"
        
        # HTML Desglose
        html_desglose = ""
        if totales['Urgente']>0: html_desglose += f"<div class='total-line'><span style='color:#d32f2f; font-weight:bold;'>🔴 Total Urgente:</span> <span>${totales['Urgente']:,.2f}</span></div>"
        if totales['Medio']>0: html_desglose += f"<div class='total-line'><span style='color:#1976D2; font-weight:bold;'>🔵 Total Medio:</span> <span>${totales['Medio']:,.2f}</span></div>"
        if totales['Bajo']>0: html_desglose += f"<div class='total-line'><span style='color:#757575; font-weight:bold;'>⚪ Total Bajo:</span> <span>${totales['Bajo']:,.2f}</span></div>"

        st.markdown(f"""
        <div class="preview-container"><div class="preview-paper">
            <div class="preview-header">
                <div><h1 class="preview-title">TOYOTA LOS FUERTES</h1><div class="preview-subtitle">Presupuesto</div></div>
            </div>
            <div class="info-grid">
                <div>CLIENTE: {st.session_state.cliente}<br>VIN: {st.session_state.vin}</div>
                <div>ORDEN: {st.session_state.orden}<br>ASESOR: {st.session_state.asesor}</div>
            </div>
            <table class="custom-table">
                <thead><tr><th>CÓDIGO</th><th>DESCRIPCIÓN</th><th>PRIORIDAD</th><th>ESTATUS</th><th>T.ENT</th><th>CANT</th><th>UNITARIO</th><th>TOTAL</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
            <div class="total-box">
                {html_desglose}
                <div class="total-final">TOTAL: ${gran_total:,.2f}</div>
            </div>
        </div></div>
        """, unsafe_allow_html=True)
