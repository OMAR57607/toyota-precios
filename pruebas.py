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
import zipfile  # Necesario para abrir el ZIP

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
    
    /* BADGES */
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
    
    /* NIEVE */
    .snowflake {
        color: #fff; font-size: 1em; font-family: Arial, sans-serif; text-shadow: 0 0 5px #000;
        position: fixed; top: -10%; z-index: 9999; user-select: none; cursor: default;
        animation-name: snowflakes-fall, snowflakes-shake; animation-duration: 10s, 3s;
        animation-timing-function: linear, ease-in-out; animation-iteration-count: infinite, infinite;
        animation-play-state: running, running;
    }
    @keyframes snowflakes-fall { 0% { top: -10%; } 100% { top: 100%; } }
    @keyframes snowflakes-shake { 0%, 100% { transform: translateX(0); } 50% { transform: translateX(80px); } }
    .snowflake:nth-of-type(0) { left: 1%; animation-delay: 0s, 0s; }
    .snowflake:nth-of-type(1) { left: 10%; animation-delay: 1s, 1s; }
    .snowflake:nth-of-type(2) { left: 20%; animation-delay: 6s, .5s; }
    .snowflake:nth-of-type(3) { left: 30%; animation-delay: 4s, 2s; }
    .snowflake:nth-of-type(4) { left: 40%; animation-delay: 2s, 2s; }
    .snowflake:nth-of-type(5) { left: 50%; animation-delay: 8s, 3s; }
    </style>
    """, unsafe_allow_html=True)

if st.session_state.nieve_activa:
    st.markdown('<div class="snowflake">❅</div>' * 10, unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS ROBUSTA
# ==========================================
@st.cache_data
def cargar_catalogo():
    archivo_zip = "base_datos_2026.zip"
    
    if not os.path.exists(archivo_zip): 
        st.error(f"❌ Error: No se encuentra '{archivo_zip}' en la carpeta del programa.")
        return None, None, None

    try:
        with zipfile.ZipFile(archivo_zip, "r") as z:
            # Buscar archivos válidos (ignorando temporales y macosx)
            archivos_validos = [
                f for f in z.namelist() 
                if (f.endswith('.xlsx') or f.endswith('.xls') or f.endswith('.csv'))
                and not f.startswith('~') 
                and '__MACOSX' not in f
            ]
            
            if not archivos_validos:
                st.error("❌ El ZIP está vacío o no contiene archivos Excel/CSV válidos.")
                st.write("Contenido del ZIP:", z.namelist())
                return None, None, None
            
            # Usar el primer archivo válido encontrado
            archivo_elegido = archivos_validos[0]
            
            with z.open(archivo_elegido) as f:
                if archivo_elegido.endswith('.csv'):
                    # Intentar leer CSV con diferentes encodings
                    try:
                        df = pd.read_csv(f, dtype=str)
                    except:
                        f.seek(0)
                        df = pd.read_csv(f, dtype=str, encoding='latin-1')
                else:
                    df = pd.read_excel(f, dtype=str)

        # Limpieza de columnas
        df.dropna(how='all', inplace=True)
        df.columns = [str(c).strip().upper() for c in df.columns]

        # --- Detección de columnas ---
        # 1. SKU (Buscamos 'ITEM' primero, luego variantes)
        c_sku = next((c for c in df.columns if c == 'ITEM'), None)
        if not c_sku:
            c_sku = next((c for c in df.columns if 'PART' in c or 'NUM' in c or 'SKU' in c), None)

        # 2. Descripción
        c_desc = next((c for c in df.columns if 'DESC' in c), None)

        # 3. Precio (Buscamos 'TOTAL_UNITARIO' primero, luego variantes)
        c_precio = next((c for c in df.columns if c == 'TOTAL_UNITARIO'), None)
        if not c_precio:
            c_precio = next((c for c in df.columns if 'TOTAL' in c or 'PRECIO' in c or 'PRICE' in c), None)

        if not c_sku or not c_precio: 
            st.error("❌ Error de Formato: No se encontraron las columnas 'ITEM' o 'TOTAL_UNITARIO'.")
            st.warning(f"Columnas detectadas: {list(df.columns)}")
            return None, None, None

        # Procesar datos
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()

        def limpiar_precio(x):
            try:
                txt = str(x).replace('$', '').replace(',', '').strip()
                return float(txt)
            except:
                return 0.0

        df['PRECIO_NUM'] = df[c_precio].apply(limpiar_precio)

        return df, c_sku, c_desc

    except Exception as e:
        st.error(f"❌ Error leyendo el archivo: {e}")
        return None, None, None

df_db, col_sku_db, col_desc_db = cargar_catalogo()

# --- Analizador de Archivos (Para carga masiva) ---
def analizador_inteligente_archivos(df_raw):
    hallazgos = []; metadata = {}
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    patron_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    patron_orden_8 = r'\b\d{8}\b'
    # Patrones para detectar SKUs de Toyota
    patron_sku_fmt = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b'
    patron_sku_pln = r'\b[A-Z0-9]{10,12}\b'
    
    keywords = {'ORDEN': ['ORDEN', 'FOLIO'], 'ASESOR': ['ASESOR', 'SA'], 'CLIENTE': ['CLIENTE', 'ATTN']}

    for r_idx, row in df.iterrows():
        for c_idx, val in row.items():
            if 'VIN' not in metadata:
                m = re.search(patron_vin, val)
                if m: metadata['VIN'] = m.group(0)
            
            if 'ORDEN' not in metadata:
                if any(k in val for k in keywords['ORDEN']):
                    m = re.search(patron_orden_8, val)
                    if m: metadata['ORDEN'] = m.group(0)
            
            # Detección de SKU
            es_sku = False; sku_det = None
            if re.match(patron_sku_fmt, val): sku_det = val; es_sku = True
            elif re.match(patron_sku_pln, val) and not val.isdigit(): sku_det = val; es_sku = True
            
            if es_sku:
                cant = 1
                try:
                    # Intenta buscar cantidad en la columna siguiente
                    vecino = df.iloc[r_idx, df.columns.get_loc(c_idx)+1].replace('.0', '')
                    if vecino.isdigit(): cant = int(vecino)
                except: pass
                hallazgos.append({'sku': sku_det, 'cant': cant})
            
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
        self.cell(0, 4, 'CONTRATO DE ADHESIÓN Y TÉRMINOS LEGALES', 0, 1, 'L')
        self.set_font('Arial', '', 5); self.set_text_color(60)
        legales = "Presupuesto válido por 24 horas. Precios en MXN incluyen IVA."
        self.multi_cell(0, 3, legales, 0, 'J')
        self.ln(5)
        y = self.get_y()
        self.line(10, y, 80, y); self.line(110, y, 190, y)
        self.cell(90, 3, "ASESOR", 0, 0, 'C'); self.cell(90, 3, "CLIENTE", 0, 1, 'C')

def generar_pdf():
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=80)
    
    # Datos Cliente
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(100, 5, str(st.session_state.cliente).upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'FECHA:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(40, 5, obtener_hora_mx().strftime("%d/%m/%Y"), 0, 1)
    
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'VIN:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(100, 5, str(st.session_state.vin).upper(), 0, 1)
    pdf.ln(5)

    # Tabla
    pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 7)
    cols = [25, 65, 20, 20, 15, 20, 25]
    headers = ['CÓDIGO', 'DESCRIPCIÓN', 'PRIORIDAD', 'ESTATUS', 'CANT', 'UNITARIO', 'TOTAL']
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
    pdf.ln()

    pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    sub = 0; iva_total = 0
    
    for item in st.session_state.carrito:
        sub += item['Precio Base'] * item['Cantidad']
        iva_total += item['IVA']
        
        # Colores PDF
        if item['Prioridad'] == 'Urgente': pdf.set_fill_color(211, 47, 47); pdf.set_text_color(255)
        elif item['Prioridad'] == 'Medio': pdf.set_fill_color(25, 118, 210); pdf.set_text_color(255)
        else: pdf.set_fill_color(255, 255, 255); pdf.set_text_color(0)
        
        desc = item['Descripción'][:35]
        
        pdf.cell(cols[0], 6, item['SKU'], 1, 0, 'C')
        pdf.cell(cols[1], 6, desc, 1, 0, 'L')
        pdf.cell(cols[2], 6, item['Prioridad'], 1, 0, 'C', True)
        
        pdf.set_fill_color(255); pdf.set_text_color(0) # Reset
        pdf.cell(cols[3], 6, item['Abasto'].replace("✅ ","").replace("⚠️ ",""), 1, 0, 'C')
        pdf.cell(cols[4], 6, str(item['Cantidad']), 1, 0, 'C')
        pdf.cell(cols[5], 6, f"${item['Precio Unitario (c/IVA)']:,.2f}", 1, 0, 'R')
        pdf.cell(cols[6], 6, f"${item['Importe Total']:,.2f}", 1, 1, 'R')

    total = sub + iva_total
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(160, 6, f"TOTAL: ${total:,.2f}", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL
# ==========================================
if df_db is None: 
    st.warning("⚠️ El sistema funciona pero no se cargó la base de datos. Verifica el archivo ZIP.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    
    if st.button("❄️ Nieve ON/OFF", use_container_width=True):
        toggle_nieve(); st.rerun()

    st.divider()
    st.markdown("### 🚘 Datos")
    st.session_state.orden = st.text_input("Orden", st.session_state.orden)
    st.session_state.vin = st.text_input("VIN", st.session_state.vin)
    st.session_state.cliente = st.text_input("Cliente", st.session_state.cliente)
    st.session_state.asesor = st.text_input("Asesor", st.session_state.asesor)
    
    st.divider()
    st.markdown("### 📥 Carga Masiva")
    uploaded_file = st.file_uploader("Excel/CSV con piezas", type=['xlsx', 'csv'])
    if uploaded_file and st.button("Procesar Archivo"):
        try:
            df_up = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            items, meta = analizador_inteligente_archivos(df_up)
            
            encontrados = 0
            for it in items:
                sku_clean = str(it['sku']).upper().replace('-', '').strip()
                match = df_db[df_db['SKU_CLEAN'] == sku_clean]
                if not match.empty:
                    row = match.iloc[0]
                    agregar_item_callback(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], it['cant'], "Refacción")
                    encontrados += 1
            st.success(f"Se agregaron {encontrados} ítems encontrados.")
            st.rerun()
        except Exception as e: st.error(f"Error: {e}")

    if st.button("🗑️ Limpiar Todo"): limpiar_todo(); st.rerun()

# --- MAIN ---
st.title("Toyota Los Fuertes")

# Búsqueda
c1, c2 = st.columns([2, 1])
with c1:
    q = st.text_input("🔍 Buscar pieza (SKU o Nombre)", placeholder="Ej. 04465...")
    if q:
        q_clean = q.upper().replace('-', '').strip()
        mask = df_db['SKU_CLEAN'].str.contains(q_clean, na=False) | df_db[col_desc_db].astype(str).str.contains(q, case=False, na=False)
        res = df_db[mask].head(5)
        
        if not res.empty:
            for _, r in res.iterrows():
                cc1, cc2 = st.columns([3, 1])
                cc1.markdown(f"**{r[col_sku_db]}** - {r[col_desc_db]}")
                cc1.caption(f"Precio Lista: ${r['PRECIO_NUM']:,.2f}")
                if cc2.button("➕", key=r[col_sku_db]):
                    agregar_item_callback(r[col_sku_db], r[col_desc_db], r['PRECIO_NUM'], 1, "Refacción")
                    st.rerun()
        else:
            st.info("No se encontraron resultados.")

with c2:
    with st.expander("🛠️ Manual / M.O."):
        m_sku = st.text_input("SKU/Código")
        m_desc = st.text_input("Descripción")
        m_price = st.number_input("Precio Base", 0.0)
        if st.button("Agregar Manual"):
            agregar_item_callback(m_sku, m_desc, m_price, 1, "Manual", "Medio", "Disponible", False)
            st.rerun()

# --- CARRITO ---
st.divider()
st.subheader(f"🛒 Presupuesto ({len(st.session_state.carrito)})")

if st.session_state.carrito:
    for i, item in enumerate(st.session_state.carrito):
        with st.container(border=True):
            tc1, tc2, tc3, tc4 = st.columns([0.5, 3, 1.5, 0.5])
            tc1.write(f"#{i+1}")
            tc2.markdown(f"**{item['SKU']}** - {item['Descripción']}")
            
            # Controles
            col_prio, col_stat = st.columns(2)
            nueva_prio = col_prio.selectbox("Prioridad", ["Urgente", "Medio", "Bajo"], index=["Urgente", "Medio", "Bajo"].index(item['Prioridad']), key=f"prio_{i}")
            item['Prioridad'] = nueva_prio
            
            nuevo_stat = col_stat.selectbox("Estatus", ["✅ Disponible", "📦 Pedido", "⚠️ REVISAR"], index=0 if "Disponible" in item['Abasto'] else 2, key=f"stat_{i}")
            item['Abasto'] = nuevo_stat

            tc3.markdown(f"**${item['Importe Total']:,.2f}**")
            if tc4.button("❌", key=f"del_{i}"):
                st.session_state.carrito.pop(i)
                st.rerun()

    # Totales y PDF
    total_gral = sum(x['Importe Total'] for x in st.session_state.carrito)
    st.markdown(f"<h2 style='text-align: right; color: #eb0a1e;'>Total: ${total_gral:,.2f}</h2>", unsafe_allow_html=True)
    
    if st.button("👁️ Vista Previa"): toggle_preview(); st.rerun()
    
    pdf_bytes = generar_pdf()
    st.download_button("📄 Descargar PDF", pdf_bytes, "presupuesto.pdf", "application/pdf", type="primary", use_container_width=True)

# VISTA PREVIA HTML
if st.session_state.ver_preview:
    html_rows = ""
    for it in st.session_state.carrito:
        p_color = "#d32f2f" if it['Prioridad'] == "Urgente" else "#1976D2"
        html_rows += f"<tr><td>{it['SKU']}</td><td>{it['Descripción']}</td><td><span style='color:white;background:{p_color};padding:2px 5px;border-radius:3px;'>{it['Prioridad']}</span></td><td style='text-align:right'>${it['Importe Total']:,.2f}</td></tr>"
    
    st.markdown(f"""
    <div class="preview-container"><div class="preview-paper">
        <h2 style='color:#eb0a1e;text-align:center;'>TOYOTA LOS FUERTES</h2>
        <table class="custom-table">
            <thead><tr style='background:#eb0a1e;color:white;'><th>SKU</th><th>DESCRIPCIÓN</th><th>PRIORIDAD</th><th>TOTAL</th></tr></thead>
            <tbody>{html_rows}</tbody>
        </table>
        <h3 style='text-align:right'>TOTAL: ${total_gral:,.2f}</h3>
    </div></div>
    """, unsafe_allow_html=True)
