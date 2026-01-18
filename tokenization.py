import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
from fpdf import FPDF
import pytz
import re
import os
import zipfile
import urllib.parse
import math

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
        'cliente': "",
        'vin': "",
        'orden': "",
        'asesor': "",
        'ver_preview': False,
        'nieve_activa': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def limpiar_todo():
    st.session_state.carrito = []
    st.session_state.cliente = ""
    st.session_state.vin = ""
    st.session_state.orden = ""
    st.session_state.asesor = ""
    st.session_state.ver_preview = False
    st.session_state.nieve_activa = False

init_session()

# ==========================================
# 2. ESTILOS CSS (TOYOTA CLEAN UI/UX)
# ==========================================
st.markdown("""
    <style>
    .stApp { font-family: 'Helvetica', 'Arial', sans-serif; }
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 6px !important; font-weight: 600 !important; padding: 0.5rem !important;
    }
    label { font-weight: 700 !important; letter-spacing: 0.5px; }
    
    /* BOTONES */
    div.stButton > button, div[data-testid="stForm"] button {
        background-color: #eb0a1e !important; color: white !important; border: none !important;
        font-weight: 800 !important; text-transform: uppercase; letter-spacing: 1px;
        width: 100%; padding: 0.7rem 1rem; border-radius: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover, div[data-testid="stForm"] button:hover {
        background-color: #b70014 !important; transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }
    div.stButton > button[kind="secondary"] {
        background-color: #f0f2f6 !important; color: #31333F !important; border: 1px solid #d0d7de !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        border-color: #eb0a1e !important; color: #eb0a1e !important;
    }
    div.stButton > button[kind="tertiary"] { color: #666 !important; border: none !important; background: transparent !important; }
    div.stButton > button[kind="tertiary"]:hover { color: #eb0a1e !important; background: rgba(235, 10, 30, 0.1) !important; }

    /* WHATSAPP */
    .wa-btn {
        display: inline-flex; align-items: center; justify-content: center;
        background-color: #25D366; color: white !important; padding: 0.7rem 1rem; border-radius: 6px;
        text-decoration: none; font-weight: 800; width: 100%; margin-top: 5px; text-transform: uppercase;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .wa-btn:hover { background-color: #128C7E; transform: translateY(-1px); }

    /* VISTA PREVIA */
    .preview-container { background-color: #2b2b2b; padding: 25px; border-radius: 10px; display: flex; justify-content: center; margin-top: 20px; overflow-x: auto; border: 1px solid #444; }
    .preview-paper { background-color: white !important; color: black !important; width: 100%; max-width: 900px; min-width: 700px; padding: 40px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); font-family: 'Helvetica', 'Arial', sans-serif; }
    .preview-header { border-bottom: 4px solid #eb0a1e; padding-bottom: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end; }
    .preview-title { font-size: 28px; font-weight: 900; color: #eb0a1e !important; margin: 0; line-height: 1.2; text-transform: uppercase; }
    .group-header { background-color: #f8f9fa; color: #000 !important; font-weight: 900; padding: 10px; border: 1px solid #ddd; border-left: 8px solid #eb0a1e; margin-top: 25px; margin-bottom: 5px; text-transform: uppercase; font-size: 13px; display: flex; justify-content: space-between;}
    .legend-bar { display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 20px; padding: 12px; border: 1px solid #ddd; background: #f1f1f1; font-size: 11px; font-weight: bold; color: #333 !important; border-radius: 4px; }
    
    table.custom-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 5px; table-layout: fixed; border: 1px solid #000; }
    table.custom-table th { background-color: #000 !important; color: white !important; padding: 10px 8px; text-align: left; font-weight: 900; text-transform: uppercase; border: 1px solid #fff; }
    table.custom-table td { border-bottom: 1px solid #ddd; padding: 10px 8px; color: #000 !important; vertical-align: middle; font-weight: 600; }
    
    .total-box { margin-left: auto; width: 300px; border-top: 3px solid #000; padding-top: 15px; margin-top: 25px; }
    .total-final { font-size: 28px; font-weight: 900; color: #eb0a1e !important; text-align: right; }
    
    .badge-base { padding: 4px 8px; font-weight: 900; font-size: 10px; display: inline-block; color: white !important; text-transform: uppercase; border-radius: 3px;}
    .badge-urg { background: #d32f2f; } .badge-med { background: #1565C0; } .badge-baj { background: #424242; }
    .status-base { padding: 4px 8px; font-weight: 900; font-size: 10px; display: inline-block; text-transform: uppercase; border-radius: 3px;}
    .status-disp { color: #fff !important; background: #2E7D32; } .status-ped { color: #000 !important; background: #FFD600; } .status-bo { color: #fff !important; background: #000; }
    
    div[data-testid="stCheckbox"] { display: flex; align-items: center; justify-content: center; padding-top: 25px; }
    </style>
    """, unsafe_allow_html=True)

if st.session_state.nieve_activa:
    st.markdown("".join([f'<div class="snowflake">{c}</div>' for c in ['❅','❆']*6]), unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS
# ==========================================
@st.cache_data(show_spinner="Cargando catálogo...")
def cargar_catalogo():
    archivo_zip = "base_datos_2026.zip"
    archivo_parquet = "base_datos_2026.parquet"
    if os.path.exists(archivo_parquet):
        try:
            df = pd.read_parquet(archivo_parquet)
            c_sku = next((c for c in df.columns if c == 'ITEM' or 'PART' in c), None)
            c_desc = next((c for c in df.columns if 'DESC' in c), None)
            return df, c_sku, c_desc
        except: pass
    if not os.path.exists(archivo_zip): return None, None, None
    try:
        with zipfile.ZipFile(archivo_zip, "r") as z:
            archivos_validos = [f for f in z.namelist() if f.endswith(('.xlsx','.xls','.csv')) and not f.startswith('~')]
            if not archivos_validos: return None, None, None
            with z.open(archivos_validos[0]) as f:
                if archivos_validos[0].endswith('.csv'): df = pd.read_csv(f, dtype=str, encoding='latin-1')
                else: df = pd.read_excel(f, dtype=str)
        df.dropna(how='all', inplace=True)
        df.columns = [str(c).strip().upper() for c in df.columns]
        c_sku = next((c for c in df.columns if c == 'ITEM' or 'SKU' in c), None)
        c_desc = next((c for c in df.columns if 'DESC' in c), None)
        c_precio = next((c for c in df.columns if 'PRECIO' in c or 'TOTAL' in c), None)
        if not c_sku or not c_precio: return None, None, None
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        df['PRECIO_NUM'] = df[c_precio].apply(lambda x: float(str(x).replace('$','').replace(',','').strip()) if str(x).replace('$','').replace(',','').strip() else 0.0)
        df.to_parquet(archivo_parquet)
        return df, c_sku, c_desc
    except: return None, None, None

if 'df_maestro' not in st.session_state:
    st.session_state.df_maestro, st.session_state.col_sku_db, st.session_state.col_desc_db = cargar_catalogo()

df_db = st.session_state.df_maestro
col_sku_db = st.session_state.col_sku_db
col_desc_db = st.session_state.col_desc_db

# --- ANALIZADOR INTELIGENTE MEJORADO (Patrones Flexibles y Hoja Específica) ---
def analizador_inteligente_archivos(df_raw):
    hallazgos = []; metadata = {}
    # Convertir todo a string, quitar espacios y mayúsculas
    df = df_raw.fillna('').astype(str).apply(lambda x: x.str.upper().str.strip())
    
    # Patrones
    patron_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    patron_orden = r'\b\d{8}\b'
    # SKU TOYOTA FLEXIBLE: 10 o 12 caracteres alfanuméricos, con o sin guiones
    # Ej: 04465-0E010, 044650E010, 90915-YZZD1
    patron_sku_flex = r'\b[A-Z0-9]{5}-?[A-Z0-9]{5}(?:-?[A-Z0-9]{2})?\b' 
    
    for r_idx, row in df.iterrows():
        for c_idx, val in row.items():
            val_str = str(val)
            
            # Buscar VIN y Orden
            if 'VIN' not in metadata:
                m = re.search(patron_vin, val_str)
                if m: metadata['VIN'] = m.group(0)
            if 'ORDEN' not in metadata:
                m = re.search(patron_orden, val_str)
                if m: metadata['ORDEN'] = m.group(0)
            
            # Buscar SKU (Parte)
            # Validamos que no sea el VIN (porque el patrón SKU podría confundirse con partes de un VIN)
            if re.match(patron_sku_flex, val_str) and len(val_str.replace('-','')) in [10, 12] and val_str != metadata.get('VIN', ''):
                cant = 1
                try:
                    # Buscar cantidad en la columna inmediata derecha
                    col_pos = df.columns.get_loc(c_idx)
                    if col_pos + 1 < len(df.columns):
                        vecino = str(df.iloc[r_idx, col_pos + 1]).replace('.0', '').strip()
                        if vecino.isdigit(): cant = int(vecino)
                except: pass
                hallazgos.append({'sku': val_str, 'cant': cant})
                
    return hallazgos, metadata

def agregar_item_callback(sku, desc_raw, precio_base, cant, tipo, prioridad="Medio", abasto="⚠️ REVISAR", traducir=True):
    if traducir:
        try: desc = GoogleTranslator(source='en', target='es').translate(str(desc_raw))
        except: desc = str(desc_raw)
    else: desc = str(desc_raw)
    iva_monto = (precio_base * cant) * 0.16
    total_linea = (precio_base * cant) + iva_monto
    st.session_state.carrito.append({
        "SKU": sku, "Descripción": desc, "Prioridad": prioridad, "Abasto": abasto, "Tiempo Entrega": "",
        "Cantidad": cant, "Precio Base": precio_base, "Precio Unitario (c/IVA)": precio_base * 1.16,
        "IVA": iva_monto, "Importe Total": total_linea, "Estatus": "Disponible", "Tipo": tipo,
        "Seleccionado": True
    })

def toggle_preview(): st.session_state.ver_preview = not st.session_state.ver_preview

# ==========================================
# 4. GENERADOR PDF (ROBUSTO)
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
        self.cell(0, 4, 'TÉRMINOS, GARANTÍAS Y MARCO LEGAL (LFPC Y NOM-174-SCFI-2007)', 0, 1, 'L')
        self.set_font('Arial', '', 6); self.set_text_color(40)
        legales = (
            "1. PRECIOS: En Moneda Nacional (MXN) con IVA incluido (Art. 7 LFPC). Válido por 24 horas.\n"
            "2. GARANTÍA: 12 meses o 20,000 km en refacciones instaladas en taller (Art. 77 LFPC). "
            "Partes eléctricas sujetas a diagnóstico.\n"
            "3. PEDIDOS: Requieren 100% anticipo. Cancelaciones imputables al cliente aplican pena del 20%.\n"
            "4. CLÁUSULAS: Este contrato NO contiene cláusulas abusivas, inequitativas o desproporcionadas (Art. 85 LFPC).\n"
            "5. ACEPTACIÓN: La firma o confirmación vía electrónica (WhatsApp/Correo) constituye aceptación total."
        )
        self.multi_cell(0, 3, legales, 0, 'J')
        self.ln(5); y_firma = self.get_y()
        self.line(10, y_firma, 80, y_firma); self.line(110, y_firma, 190, y_firma)
        self.cell(90, 3, "ASESOR DE SERVICIO", 0, 0, 'C'); self.cell(90, 3, "CLIENTE (NOMBRE Y FIRMA)", 0, 1, 'C')
        self.set_y(-12); self.set_font('Arial', 'B', 8); self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

def generar_pdf():
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=80)
    
    cli_safe = str(st.session_state.cliente).encode('latin-1', 'replace').decode('latin-1')
    vin_safe = str(st.session_state.vin).encode('latin-1', 'replace').decode('latin-1')
    ord_safe = str(st.session_state.orden).encode('latin-1', 'replace').decode('latin-1')
    
    pdf.set_text_color(0,0,0); pdf.set_font('Arial', 'B', 10)
    pdf.cell(20, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(100, 5, cli_safe[:60], 0, 0)
    pdf.set_font('Arial', 'B', 10); pdf.cell(20, 5, 'FECHA:', 0, 0); pdf.set_font('Arial', '', 10); pdf.cell(40, 5, obtener_hora_mx().strftime("%d/%m/%Y"), 0, 1)
    pdf.cell(20, 5, 'VIN:', 0, 0); pdf.cell(100, 5, vin_safe, 0, 0)
    pdf.cell(20, 5, 'ORDEN:', 0, 0); pdf.cell(40, 5, ord_safe, 0, 1)
    pdf.ln(5)

    items_activos = [i for i in st.session_state.carrito if i.get('Seleccionado', True)]
    orden_prioridad = ['Urgente', 'Medio', 'Bajo']
    cols = [20, 55, 18, 25, 10, 20, 17, 20] 
    headers = ['CÓDIGO', 'DESCRIPCIÓN', 'ESTATUS', 'T.ENTREGA', 'CANT', 'UNITARIO', 'IVA', 'TOTAL']

    total_gral_pdf = 0; hay_pedido = False; hay_backorder = False

    for prio in orden_prioridad:
        grupo = [i for i in items_activos if i['Prioridad'] == prio]
        if not grupo: continue

        pdf.ln(2)
        if prio == "Urgente": pdf.set_fill_color(211, 47, 47) 
        elif prio == "Medio": pdf.set_fill_color(25, 118, 210)
        else: pdf.set_fill_color(117, 117, 117)
        
        pdf.set_font('Arial', 'B', 9); pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 6, f" {prio.upper()} ", 0, 1, 'L', True)
        
        pdf.set_fill_color(240, 240, 240); pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', 'B', 7)
        for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 1, 0, 'C', True)
        pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)

        subtotal_grupo = 0
        for item in grupo:
            subtotal_grupo += item['Importe Total']
            if "Pedido" in item['Abasto'] or "Back" in item['Abasto']: hay_pedido = True
            if "Back" in item['Abasto']: hay_backorder = True
            
            sku = item['SKU'][:15]
            desc = str(item['Descripción']).encode('latin-1','replace').decode('latin-1')
            st_txt = item['Abasto'].replace("⚠️ ", "").replace("✅ ", "").replace("📦 ", "").replace("⚫ ", "")
            
            col_desc_w = cols[1] - 2
            text_len = pdf.get_string_width(desc)
            lines_needed = int(math.ceil(text_len / col_desc_w))
            lines_needed = max(1, lines_needed)
            row_height = max(6, lines_needed * 4)
            
            if pdf.get_y() + row_height > 250:
                pdf.add_page()
                pdf.set_fill_color(240, 240, 240); pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', 'B', 7)
                for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 1, 0, 'C', True)
                pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)

            y_start = pdf.get_y(); x_start = pdf.get_x()
            pdf.cell(cols[0], row_height, sku, 1, 0, 'C')
            x_desc = pdf.get_x()
            pdf.multi_cell(cols[1], 4, desc, 1, 'L')
            pdf.set_xy(x_desc + cols[1], y_start)
            
            if "Disponible" in item['Abasto']: pdf.set_fill_color(200, 230, 201)
            elif "Pedido" in item['Abasto']: pdf.set_fill_color(255, 224, 178)
            elif "Back" in item['Abasto']: pdf.set_fill_color(33, 33, 33); pdf.set_text_color(255, 255, 255)
            else: pdf.set_fill_color(255, 205, 210)

            pdf.cell(cols[2], row_height, st_txt, 1, 0, 'C', True)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(cols[3], row_height, str(item['Tiempo Entrega'])[:12], 1, 0, 'C')
            pdf.cell(cols[4], row_height, str(item['Cantidad']), 1, 0, 'C')
            pdf.cell(cols[5], row_height, f"${item['Precio Base']:,.2f}", 1, 0, 'R')
            pdf.cell(cols[6], row_height, f"${item['IVA']/item['Cantidad']:,.2f}", 1, 0, 'R')
            pdf.cell(cols[7], row_height, f"${item['Importe Total']:,.2f}", 1, 1, 'R')

        pdf.set_font('Arial', 'B', 8)
        pdf.cell(165, 5, f"SUBTOTAL {prio.upper()}:", 0, 0, 'R')
        pdf.cell(20, 5, f"${subtotal_grupo:,.2f}", 1, 1, 'R')
        total_gral_pdf += subtotal_grupo

    pdf.ln(5)
    if hay_pedido: 
        pdf.set_text_color(230, 81, 0); pdf.set_font('Arial', 'B', 9)
        pdf.cell(0, 4, "** REQUIERE ANTICIPO DEL 100% POR PIEZAS DE PEDIDO **", 0, 1, 'R')
    if hay_backorder:
        pdf.set_text_color(183, 28, 28); pdf.set_font('Arial', 'B', 9)
        pdf.cell(0, 4, "(!) REFACCIONES EN BACK ORDER: CONSULTAR TIEMPO DE ESPERA CON ASESOR", 0, 1, 'R')

    pdf.ln(2); pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', 'B', 14)
    pdf.cell(165, 10, 'GRAN TOTAL:', 0, 0, 'R')
    pdf.cell(20, 10, f"${total_gral_pdf:,.2f}", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL
# ==========================================
if df_db is None: st.warning(f"⚠️ Atención: No se encontró base de datos.")

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider(); st.markdown("### 🚘 Datos del Servicio")
    st.session_state.orden = st.text_input("Orden", st.session_state.orden)
    st.session_state.vin = st.text_input("VIN", st.session_state.vin)
    st.session_state.cliente = st.text_input("Cliente", st.session_state.cliente)
    st.session_state.asesor = st.text_input("Asesor", st.session_state.asesor)
    
    st.divider(); st.markdown("### 🤖 Carga Inteligente (IA)")
    uploaded_file = st.file_uploader("Excel (XLSX, XLSM, XLS, CSV)", type=['xlsx', 'xlsm', 'xls', 'csv'], label_visibility="collapsed")
    if uploaded_file and st.button("ANALIZAR ARCHIVO", type="primary"):
        try:
            # Lógica para leer TODAS las hojas
            if uploaded_file.name.endswith('.csv'):
                df_dict = {'Hoja1': pd.read_csv(uploaded_file, encoding='latin-1', on_bad_lines='skip')}
            else:
                # sheet_name=None lee todas las hojas en un diccionario
                df_dict = pd.read_excel(uploaded_file, sheet_name=None)
            
            found_total = 0
            # Priorizar hoja "RESUMEN_DATOS" si existe
            hojas_ordenadas = list(df_dict.keys())
            if 'RESUMEN_DATOS' in df_dict:
                hojas_ordenadas.remove('RESUMEN_DATOS')
                hojas_ordenadas.insert(0, 'RESUMEN_DATOS') # Poner al inicio
            
            for sheet_name in hojas_ordenadas:
                df_sheet = df_dict[sheet_name]
                items, meta = analizador_inteligente_archivos(df_sheet)
                
                if 'CLIENTE' in meta and not st.session_state.cliente: st.session_state.cliente = meta['CLIENTE']
                if 'VIN' in meta and not st.session_state.vin: st.session_state.vin = meta['VIN']
                if 'ORDEN' in meta and not st.session_state.orden: st.session_state.orden = meta['ORDEN']
                
                for it in items:
                    clean = str(it['sku']).upper().replace('-', '').strip()
                    if df_db is not None:
                        match = df_db[df_db['SKU_CLEAN'] == clean]
                        if not match.empty:
                            row = match.iloc[0]
                            agregar_item_callback(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], it['cant'], "Refacción")
                            found_total += 1
            
            if found_total > 0:
                st.success(f"✅ Se importaron {found_total} partidas exitosamente.")
                st.rerun()
            else:
                st.warning("⚠️ No se detectaron números de parte válidos en ninguna hoja.")
                
        except Exception as e: 
            st.error(f"Error procesando archivo: {e}")
    
    st.divider()
    if st.button("LIMPIAR TODO", type="secondary"): limpiar_todo(); st.rerun()

st.title("Toyota Los Fuertes"); st.caption("Sistema de Cotización (UX Optimizada)")

with st.expander("🔎 AÑADIR CONCEPTOS", expanded=True):
    tab1, tab2, tab3 = st.tabs(["CATÁLOGO", "MANUAL", "MANO DE OBRA"])
    with tab1:
        c_search, c_btn = st.columns([3, 1])
        q = c_search.text_input("Buscar Refacción", placeholder="Nombre o SKU...", label_visibility="collapsed")
        if q and df_db is not None:
            mask = df_db.apply(lambda x: x.astype(str).str.contains(q, case=False)).any(axis=1)
            results = df_db[mask].head(3)
            if not results.empty:
                for _, row in results.iterrows():
                    rc1, rc2, rc3 = st.columns([2, 1, 1])
                    rc1.markdown(f"**{row[col_sku_db]}**")
                    rc2.markdown(f"${row['PRECIO_NUM']:,.2f}")
                    rc3.button("AGREGAR", key=f"add_{row[col_sku_db]}", type="primary", on_click=agregar_item_callback, args=(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], 1, "Refacción"))
            else:
                st.info("Sin resultados.")
    with tab2:
        with st.form("manual_ref"):
            c_m1, c_m2, c_m3 = st.columns([1.5, 1, 1])
            m_sku = c_m1.text_input("SKU / Código")
            m_pr = c_m2.number_input("Precio", 0.0)
            c_m3.markdown("<br>", unsafe_allow_html=True)
            if c_m3.form_submit_button("AGREGAR MANUAL", type="primary"): 
                agregar_item_callback(m_sku, "Refacción Manual", m_pr, 1, "Refacción", traducir=False); st.rerun()
    with tab3:
        with st.form("form_mo"):
            c_mo1, c_mo2, c_mo3 = st.columns([2, 1, 1])
            mo_desc = c_mo1.text_input("Servicio", placeholder="Ej. Afinación")
            mo_hrs = c_mo2.number_input("Horas", min_value=0.1, value=1.0, step=0.1)
            c_mo3.markdown("<br>", unsafe_allow_html=True)
            if c_mo3.form_submit_button("AGREGAR M.O.", type="primary"):
                costo_mo = 600.0 * mo_hrs
                agregar_item_callback("MO-TALLER", f"{mo_desc} ({mo_hrs} hrs @ $600)", costo_mo, 1, "Mano de Obra", "Medio", "Disponible", traducir=False)
                st.rerun()

st.divider()
st.subheader(f"🛒 Carrito ({len(st.session_state.carrito)})")

if st.session_state.carrito:
    def actualizar_cantidad_input(idx, key):
        val = st.session_state[key]
        st.session_state.carrito[idx]['Cantidad'] = val
        it = st.session_state.carrito[idx]
        it['IVA'] = (it['Precio Base'] * it['Cantidad']) * 0.16
        it['Importe Total'] = (it['Precio Base'] * it['Cantidad']) + it['IVA']
    def eliminar_item(idx): st.session_state.carrito.pop(idx)
    def update_val(idx, k, w): st.session_state.carrito[idx][k] = st.session_state[w].replace("🔴 ", "").replace("🔵 ", "").replace("⚪ ", "").replace("✅ ", "").replace("📦 ", "").replace("⚫ ", "").replace("⚠️ ", "")
    def update_chk(idx, k): st.session_state.carrito[idx]['Seleccionado'] = st.session_state[k]

    for i, item in enumerate(st.session_state.carrito):
        if 'Seleccionado' not in item: item['Seleccionado'] = True
        with st.container(border=True):
            c_check, c_desc, c_tot, c_del = st.columns([0.5, 3, 1, 0.3])
            c_check.checkbox("", value=item['Seleccionado'], key=f"sel_{i}", on_change=update_chk, args=(i, f"sel_{i}"))
            with c_desc: st.markdown(f"**{item['Descripción']}** | {item['SKU']}"); st.caption(f"Unit: ${item['Precio Unitario (c/IVA)']:,.2f}")
            with c_tot: 
                color_tot = "inherit" if item['Seleccionado'] else "#888" 
                st.markdown(f"<div style='text-align:right; color:{color_tot}; font-weight:900;'>${item['Importe Total']:,.2f}</div>", unsafe_allow_html=True)
            c_del.button("🗑️", key=f"d_{i}", on_click=eliminar_item, args=(i,), type="tertiary")
            if item['Seleccionado']:
                cp, cs, ct, cq = st.columns([1.3, 1.3, 1.5, 1.8])
                idx_p = 0 if item['Prioridad']=="Urgente" else (2 if item['Prioridad']=="Bajo" else 1)
                cp.selectbox("Prio", ["🔴 Urgente", "🔵 Medio", "⚪ Bajo"], index=idx_p, key=f"p_{i}", label_visibility="collapsed", on_change=update_val, args=(i, 'Prioridad', f"p_{i}"))
                idx_a = 0 if "Disponible" in item['Abasto'] else (1 if "Pedido" in item['Abasto'] else (2 if "Back" in item['Abasto'] else 3))
                cs.selectbox("Abasto", ["✅ Disponible", "📦 Pedido", "⚫ Back Order", "⚠️ REVISAR"], index=idx_a, key=f"a_{i}", label_visibility="collapsed", on_change=update_val, args=(i, 'Abasto', f"a_{i}"))
                ct.text_input("T.Ent", value=item['Tiempo Entrega'], key=f"t_{i}", label_visibility="collapsed", on_change=lambda idx=i: st.session_state.carrito[idx].update({'Tiempo Entrega': st.session_state[f"t_{idx}"]}))
                if item['Tipo'] == "Mano de Obra":
                    cq.markdown(f"<div style='text-align:center; padding-top:10px; font-weight:bold; color:#666;'>1</div>", unsafe_allow_html=True)
                else:
                    cq.number_input("Cant", min_value=1, value=int(item['Cantidad']), step=1, key=f"qn_{i}", label_visibility="collapsed", on_change=actualizar_cantidad_input, args=(i, f"qn_{i}"))
            else: st.caption("🚫 *Ítem excluido*")

    items_activos = [i for i in st.session_state.carrito if i.get('Seleccionado', True)]
    total_gral = sum(i['Importe Total'] for i in items_activos)
    pendientes = [i for i in items_activos if "REVISAR" in str(i['Abasto'])]
    
    st.divider()
    st.metric(label="GRAN TOTAL (IVA INCLUIDO)", value=f"${total_gral:,.2f}")
    
    if pendientes: st.error(f"🛑 Hay {len(pendientes)} partida(s) marcadas como 'REVISAR' activas.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1: 
            if st.button("VISTA PREVIA", type="secondary"): toggle_preview(); st.rerun()
        with c2: 
            if items_activos:
                st.download_button("GENERAR PDF", generar_pdf(), f"Cot_{st.session_state.orden}.pdf", "application/pdf", type="primary")
        with c3:
            msg = urllib.parse.quote(f"Hola {st.session_state.cliente},\nCotización Toyota: ${total_gral:,.2f}")
            st.markdown(f'<a href="https://wa.me/?text={msg}" target="_blank" class="wa-btn">📱 WhatsApp</a>', unsafe_allow_html=True)

if st.session_state.ver_preview:
    if not st.session_state.carrito: st.warning("⚠️ El carrito está vacío.")
    else:
        html_content = ""; total_preview = 0
        leyenda_html = "<div class='legend-bar'><span>LEYENDA:</span><span class='badge-base badge-urg'>URGENTE (Rojo)</span><span class='badge-base badge-med'>MEDIO (Azul)</span><span class='badge-base badge-baj'>BAJO (Gris)</span><span style='margin-left:10px;'>|</span><span class='status-base status-disp'>DISPONIBLE</span><span class='status-base status-ped'>POR PEDIDO</span><span class='status-base status-bo'>BACK ORDER</span></div>"
        
        for prio in ['Urgente', 'Medio', 'Bajo']:
            grupo = [i for i in st.session_state.carrito if i.get('Seleccionado', True) and i['Prioridad'] == prio]
            if not grupo: continue
            subtotal_html = sum(i['Importe Total'] for i in grupo); total_preview += subtotal_html
            html_content += f"<div class='group-header'><span>{prio}</span><span>SUB: ${subtotal_html:,.2f}</span></div><table class='custom-table'><thead><tr><th>SKU</th><th>DESC</th><th>ESTATUS</th><th>CANT</th><th>TOTAL</th></tr></thead><tbody>"
            for item in grupo:
                a_c = "status-disp" if "Disponible" in item['Abasto'] else ("status-ped" if "Pedido" in item['Abasto'] else "status-bo")
                html_content += f"<tr><td>{item['SKU']}</td><td>{item['Descripción']}</td><td><span class='status-base {a_c}'>{item['Abasto']}</span></td><td style='text-align:center'>{item['Cantidad']}</td><td style='text-align:right'>${item['Importe Total']:,.2f}</td></tr>"
            html_content += "</tbody></table>"

        final_html = f"<div class='preview-container'><div class='preview-paper'><div class='preview-header'><h1 class='preview-title'>TOYOTA LOS FUERTES</h1></div>{leyenda_html}{html_content}<div class='total-box'><div class='total-final'>TOTAL: ${total_preview:,.2f}</div></div></div></div>"
        st.markdown(final_html, unsafe_allow_html=True)
elif st.session_state.ver_preview and not st.session_state.carrito:
    st.session_state.ver_preview = False
