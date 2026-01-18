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
    .group-header { background-color: #f1f1f1; font-weight: bold; padding: 8px; border-left: 5px solid #eb0a1e; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; font-size: 11px; display: flex; justify-content: space-between;}
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 25px; padding: 15px; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; }
    table.custom-table { width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 5px; table-layout: fixed; }
    table.custom-table th { background-color: #eb0a1e !important; color: white !important; padding: 10px 8px; text-align: left; font-weight: bold; text-transform: uppercase; }
    table.custom-table td { border-bottom: 1px solid #eee; padding: 8px; color: #333 !important; vertical-align: top; }
    .total-box { margin-left: auto; width: 300px; }
    .total-final { font-size: 24px; font-weight: 900; color: #eb0a1e; border-top: 2px solid #ccc; padding-top: 10px; margin-top: 10px; text-align: right; }
    .subtotal-group { text-align: right; font-weight: bold; font-size: 10px; padding: 5px; background: #fff; border-bottom: 1px dashed #ccc; margin-bottom: 10px; }
    .badge-base { padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; display: inline-block; color: white; }
    .badge-urg { background: #d32f2f; }
    .badge-med { background: #1976D2; }
    .badge-baj { background: #757575; }
    .status-base { padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; display: inline-block; }
    .status-disp { color: #1b5e20; background: #c8e6c9; border: 1px solid #1b5e20; }
    .status-ped { color: #e65100; background: #ffe0b2; border: 1px solid #e65100; }
    .status-bo { color: #ffffff; background: #212121; border: 1px solid #000000; }
    .status-rev { color: #880E4F; background: #f8bbd0; border: 1px solid #880E4F; }
    .snowflake { color: #fff; font-size: 1em; font-family: Arial, sans-serif; text-shadow: 0 0 5px #000; position: fixed; top: -10%; z-index: 9999; user-select: none; cursor: default; animation-name: snowflakes-fall, snowflakes-shake; animation-duration: 10s, 3s; animation-timing-function: linear, ease-in-out; animation-iteration-count: infinite, infinite; animation-play-state: running, running; }
    @keyframes snowflakes-fall { 0% { top: -10%; } 100% { top: 100%; } }
    @keyframes snowflakes-shake { 0%, 100% { transform: translateX(0); } 50% { transform: translateX(80px); } }
    .snowflake:nth-of-type(0) { left: 1%; animation-delay: 0s, 0s; } .snowflake:nth-of-type(1) { left: 10%; animation-delay: 1s, 1s; } .snowflake:nth-of-type(2) { left: 20%; animation-delay: 6s, .5s; } .snowflake:nth-of-type(3) { left: 30%; animation-delay: 4s, 2s; }
    </style>
    """, unsafe_allow_html=True)

if st.session_state.nieve_activa:
    st.markdown("".join([f'<div class="snowflake">{c}</div>' for c in ['❅','❆']*6]), unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS
# ==========================================
@st.cache_data(show_spinner="Cargando base de datos maestra...")
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

def analizador_inteligente_archivos(df_raw):
    hallazgos = []; metadata = {}
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    patron_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    patron_orden = r'\b\d{8}\b'
    patron_sku = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b'
    for r_idx, row in df.iterrows():
        for c_idx, val in row.items():
            if 'VIN' not in metadata and re.search(patron_vin, val): metadata['VIN'] = re.search(patron_vin, val).group(0)
            if 'ORDEN' not in metadata and re.search(patron_orden, val): metadata['ORDEN'] = re.search(patron_orden, val).group(0)
            if re.match(patron_sku, val):
                cant = 1
                try: 
                    vecino = df.iloc[r_idx, df.columns.get_loc(c_idx)+1].replace('.0', '')
                    if vecino.isdigit(): cant = int(vecino)
                except: pass
                hallazgos.append({'sku': val, 'cant': cant})
    return hallazgos, metadata

def agregar_item_callback(sku, desc_raw, precio_base, cant, tipo, prioridad="Medio", abasto="⚠️ REVISAR", traducir=True):
    if traducir:
        try: desc = GoogleTranslator(source='en', target='es').translate(str(desc_raw))
        except: desc = str(desc_raw)
    else: desc = str(desc_raw)
    iva_monto = (precio_base * cant) * 0.16
    total_linea = (precio_base * cant) + iva_monto
    # NOTA: Agregamos 'Seleccionado': True por defecto
    st.session_state.carrito.append({
        "SKU": sku, "Descripción": desc, "Prioridad": prioridad, "Abasto": abasto, "Tiempo Entrega": "",
        "Cantidad": cant, "Precio Base": precio_base, "Precio Unitario (c/IVA)": precio_base * 1.16,
        "IVA": iva_monto, "Importe Total": total_linea, "Estatus": "Disponible", "Tipo": tipo,
        "Seleccionado": True
    })

def toggle_preview(): st.session_state.ver_preview = not st.session_state.ver_preview
def toggle_nieve(): st.session_state.nieve_activa = not st.session_state.nieve_activa

# ==========================================
# 4. GENERADOR PDF (AGRUPADO POR PRIORIDAD)
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
        self.cell(0, 4, 'CONTRATO DE ADHESIÓN (NOM-174-SCFI-2007)', 0, 1, 'L')
        self.set_font('Arial', '', 5); self.set_text_color(60)
        legales = "1. VIGENCIA: 24 horas.\n2. PEDIDOS: Anticipo 100%.\n3. GARANTÍA: 12 meses genuinas.\n4. Firma electrónica válida."
        self.multi_cell(0, 3, legales, 0, 'J')
        self.ln(5); y_firma = self.get_y()
        self.line(10, y_firma, 80, y_firma); self.line(110, y_firma, 190, y_firma)
        self.cell(90, 3, "ASESOR", 0, 0, 'C'); self.cell(90, 3, "CLIENTE", 0, 1, 'C')
        self.set_y(-12); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

def generar_pdf():
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=80)
    
    # Datos Cliente
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(100, 5, str(st.session_state.cliente)[:50], 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'FECHA:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, obtener_hora_mx().strftime("%d/%m/%Y"), 0, 1)
    pdf.cell(20, 5, 'VIN:', 0, 0); pdf.cell(100, 5, str(st.session_state.vin), 0, 0)
    pdf.cell(20, 5, 'ORDEN:', 0, 0); pdf.cell(40, 5, str(st.session_state.orden), 0, 1)
    pdf.ln(5)

    # Filtrar solo seleccionados
    items_activos = [i for i in st.session_state.carrito if i.get('Seleccionado', True)]
    
    # Definir Orden y Agrupación
    orden_prioridad = ['Urgente', 'Medio', 'Bajo']
    cols = [20, 55, 18, 25, 10, 20, 17, 20] # Anchos de columna
    headers = ['CÓDIGO', 'DESCRIPCIÓN', 'ESTATUS', 'T.ENTREGA', 'CANT', 'UNITARIO', 'IVA', 'TOTAL']

    total_gral_pdf = 0
    hay_pedido = False

    for prio in orden_prioridad:
        grupo = [i for i in items_activos if i['Prioridad'] == prio]
        if not grupo: continue

        # Encabezado de Grupo
        pdf.ln(2)
        pdf.set_fill_color(240, 240, 240); pdf.set_font('Arial', 'B', 8); pdf.set_text_color(235, 10, 30)
        pdf.cell(0, 6, f"--- PRIORIDAD: {prio.upper()} ---", 0, 1, 'L', True)
        
        # Encabezado Tabla
        pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 6)
        for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
        pdf.ln(); pdf.set_text_color(0); pdf.set_font('Arial', '', 7)

        subtotal_grupo = 0
        
        for item in grupo:
            subtotal_grupo += item['Importe Total']
            if "Pedido" in item['Abasto'] or "Back" in item['Abasto']: hay_pedido = True
            
            # Renderizado Fila
            sku = item['SKU'][:15]; desc = str(item['Descripción']).encode('latin-1','replace').decode('latin-1')
            st_txt = item['Abasto'].replace("⚠️ ", "")
            
            y_ini = pdf.get_y()
            pdf.cell(cols[0], 6, sku, 1, 0, 'C')
            x_desc = pdf.get_x()
            pdf.multi_cell(cols[1], 6, desc[:35], 1, 'L') # Cortar desc si es muy larga
            pdf.set_xy(x_desc + cols[1], y_ini)
            
            pdf.cell(cols[2], 6, st_txt, 1, 0, 'C')
            pdf.cell(cols[3], 6, str(item['Tiempo Entrega'])[:12], 1, 0, 'C')
            pdf.cell(cols[4], 6, str(item['Cantidad']), 1, 0, 'C')
            pdf.cell(cols[5], 6, f"${item['Precio Base']:,.2f}", 1, 0, 'R')
            pdf.cell(cols[6], 6, f"${item['IVA']/item['Cantidad']:,.2f}", 1, 0, 'R')
            pdf.cell(cols[7], 6, f"${item['Importe Total']:,.2f}", 1, 1, 'R')

        # Subtotal del Grupo
        pdf.set_font('Arial', 'B', 7)
        pdf.cell(165, 5, f"SUBTOTAL {prio.upper()}:", 0, 0, 'R')
        pdf.cell(20, 5, f"${subtotal_grupo:,.2f}", 0, 1, 'R')
        total_gral_pdf += subtotal_grupo

    pdf.ln(5)
    if hay_pedido: 
        pdf.set_text_color(230, 100, 0); pdf.set_font('Arial', 'B', 8)
        pdf.cell(0, 4, "** REQUIERE ANTICIPO DEL 100% POR PIEZAS DE PEDIDO **", 0, 1, 'R')
    
    pdf.set_text_color(235, 10, 30); pdf.set_font('Arial', 'B', 12)
    pdf.cell(165, 8, 'GRAN TOTAL:', 0, 0, 'R')
    pdf.cell(20, 8, f"${total_gral_pdf:,.2f}", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL
# ==========================================
if df_db is None: st.warning(f"⚠️ Atención: No se encontró base de datos.")

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
    uploaded_file = st.file_uploader("Excel / CSV", type=['xlsx', 'csv'], label_visibility="collapsed")
    if uploaded_file and st.button("Analizar Archivo", type="primary"):
        try:
            df_up = pd.read_csv(uploaded_file, encoding='latin-1', on_bad_lines='skip') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            items, meta = analizador_inteligente_archivos(df_up)
            if 'CLIENTE' in meta: st.session_state.cliente = meta['CLIENTE']
            if 'VIN' in meta: st.session_state.vin = meta['VIN']
            for it in items:
                clean = str(it['sku']).upper().replace('-', '').strip()
                if df_db is not None:
                    match = df_db[df_db['SKU_CLEAN'] == clean]
                    if not match.empty:
                        row = match.iloc[0]
                        agregar_item_callback(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], it['cant'], "Refacción")
            st.rerun()
        except: st.error("Error al procesar archivo.")
    st.divider()
    if st.button("🗑️ Limpieza Total", type="secondary", use_container_width=True): limpiar_todo(); st.rerun()

st.title("Toyota Los Fuertes"); st.caption("Sistema de Cotización (Agrupado por Prioridad)")

with st.expander("🔎 Agregar Ítems", expanded=True):
    col_l, col_r = st.columns([1.2, 1])
    with col_l:
        q = st.text_input("Buscar SKU o Nombre", placeholder="Ej. Filtro...")
        if q and df_db is not None:
            mask = df_db.apply(lambda x: x.astype(str).str.contains(q, case=False)).any(axis=1)
            for _, row in df_db[mask].head(3).iterrows():
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{row[col_sku_db]}**\n${row['PRECIO_NUM']:,.2f}")
                c2.button("➕", key=f"add_{row[col_sku_db]}", on_click=agregar_item_callback, args=(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], 1, "Refacción"))
    with col_r:
        with st.form("manual"):
            m_sku = st.text_input("SKU Manual"); m_pr = st.number_input("Precio", 0.0)
            if st.form_submit_button("Agregar"): agregar_item_callback(m_sku, "Item Manual", m_pr, 1, "Refacción", traducir=False); st.rerun()

st.divider(); st.subheader(f"🛒 Carrito ({len(st.session_state.carrito)})")

if st.session_state.carrito:
    # Funciones de actualización
    def actualizar_cantidad(idx, delta):
        st.session_state.carrito[idx]['Cantidad'] = max(1, st.session_state.carrito[idx]['Cantidad'] + delta)
        it = st.session_state.carrito[idx]
        it['IVA'] = (it['Precio Base'] * it['Cantidad']) * 0.16
        it['Importe Total'] = (it['Precio Base'] * it['Cantidad']) + it['IVA']
    def eliminar_item(idx): st.session_state.carrito.pop(idx)
    def update_val(idx, k, w): st.session_state.carrito[idx][k] = st.session_state[w].replace("🔴 ", "").replace("🔵 ", "").replace("⚪ ", "").replace("✅ ", "").replace("📦 ", "").replace("⚫ ", "").replace("⚠️ ", "")
    def update_chk(idx, k): st.session_state.carrito[idx]['Seleccionado'] = st.session_state[k]

    for i, item in enumerate(st.session_state.carrito):
        # Asegurar clave Seleccionado
        if 'Seleccionado' not in item: item['Seleccionado'] = True
        
        with st.container(border=True):
            # Layout con Checkbox a la izquierda
            c_check, c_desc, c_tot, c_del = st.columns([0.2, 3, 1, 0.3])
            
            # 1. Checkbox de Selección
            c_check.checkbox("", value=item['Seleccionado'], key=f"sel_{i}", on_change=update_chk, args=(i, f"sel_{i}"))
            
            # 2. Detalles
            with c_desc: st.markdown(f"**{item['Descripción']}** | {item['SKU']}"); st.caption(f"Unit: ${item['Precio Unitario (c/IVA)']:,.2f}")
            
            # 3. Total Item
            with c_tot: 
                color_tot = "#eb0a1e" if item['Seleccionado'] else "#ccc"
                st.markdown(f"<div style='text-align:right; color:{color_tot}; font-weight:bold;'>${item['Importe Total']:,.2f}</div>", unsafe_allow_html=True)
            
            # 4. Eliminar
            c_del.button("🗑️", key=f"d_{i}", on_click=eliminar_item, args=(i,), type="tertiary")
            
            # Controles Inferiores
            if item['Seleccionado']:
                cp, cs, ct, cq = st.columns([1.3, 1.3, 1.5, 1.8])
                idx_p = 0 if item['Prioridad']=="Urgente" else (2 if item['Prioridad']=="Bajo" else 1)
                cp.selectbox("Prio", ["🔴 Urgente", "🔵 Medio", "⚪ Bajo"], index=idx_p, key=f"p_{i}", label_visibility="collapsed", on_change=update_val, args=(i, 'Prioridad', f"p_{i}"))
                
                idx_a = 0 if "Disponible" in item['Abasto'] else (1 if "Pedido" in item['Abasto'] else (2 if "Back" in item['Abasto'] else 3))
                cs.selectbox("Abasto", ["✅ Disponible", "📦 Pedido", "⚫ Back Order", "⚠️ REVISAR"], index=idx_a, key=f"a_{i}", label_visibility="collapsed", on_change=update_val, args=(i, 'Abasto', f"a_{i}"))
                
                ct.text_input("T.Ent", value=item['Tiempo Entrega'], key=f"t_{i}", label_visibility="collapsed", on_change=lambda idx=i: st.session_state.carrito[idx].update({'Tiempo Entrega': st.session_state[f"t_{idx}"]}))
                
                sc1, sc2, sc3 = cq.columns([1, 1, 1])
                sc1.button("➖", key=f"m_{i}", on_click=actualizar_cantidad, args=(i, -1), use_container_width=True)
                sc2.markdown(f"<div style='text-align:center; padding-top:5px;'>{item['Cantidad']}</div>", unsafe_allow_html=True)
                sc3.button("➕", key=f"pl_{i}", on_click=actualizar_cantidad, args=(i, 1), use_container_width=True)
            else:
                st.caption("🚫 *Ítem excluido de la cotización*")

    # Cálculos Totales (Solo activos)
    items_activos = [i for i in st.session_state.carrito if i.get('Seleccionado', True)]
    total_gral = sum(i['Importe Total'] for i in items_activos)
    
    # Alerta Bloqueante (Solo si items activos tienen warning)
    pendientes = [i for i in items_activos if "REVISAR" in str(i['Abasto'])]
    
    st.divider()
    if pendientes:
        st.error(f"🛑 Hay {len(pendientes)} partida(s) marcadas como 'REVISAR' activas. Desmárcalas o corrige su estatus.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1: 
            if st.button("👁️ Vista Previa", use_container_width=True): toggle_preview(); st.rerun()
        with c2: 
            if items_activos:
                st.download_button("📄 Generar PDF", generar_pdf(), f"Cot_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)
        with c3:
            msg = urllib.parse.quote(f"Hola {st.session_state.cliente},\nCotización Toyota: ${total_gral:,.2f}")
            st.markdown(f'<a href="https://wa.me/?text={msg}" target="_blank" class="wa-btn">📱 WhatsApp</a>', unsafe_allow_html=True)

# Vista Previa HTML Agrupada
if st.session_state.ver_preview and st.session_state.carrito:
    html_content = ""
    total_preview = 0
    
    # Loop Agrupado
    for prio in ['Urgente', 'Medio', 'Bajo']:
        grupo = [i for i in st.session_state.carrito if i.get('Seleccionado', True) and i['Prioridad'] == prio]
        if not grupo: continue
        
        subtotal_html = sum(i['Importe Total'] for i in grupo)
        total_preview += subtotal_html
        
        # Header Grupo
        html_content += f"<div class='group-header'><span>{prio}</span><span>SUB: ${subtotal_html:,.2f}</span></div>"
        html_content += "<table class='custom-table'><thead><tr><th>SKU</th><th>DESC</th><th>ABASTO</th><th>CANT</th><th>TOTAL</th></tr></thead><tbody>"
        
        for item in grupo:
            a_c = "status-disp" if "Disponible" in item['Abasto'] else ("status-ped" if "Pedido" in item['Abasto'] else "status-bo")
            html_content += f"<tr><td>{item['SKU']}</td><td>{item['Descripción']}</td><td><span class='status-base {a_c}'>{item['Abasto']}</span></td><td style='text-align:center'>{item['Cantidad']}</td><td style='text-align:right'>${item['Importe Total']:,.2f}</td></tr>"
        
        html_content += "</tbody></table>"

    st.markdown(f"""
    <div class='preview-container'>
        <div class='preview-paper'>
            <div class='preview-header'><h1 class='preview-title'>VISTA PREVIA</h1></div>
            {html_content}
            <div class='total-final'>TOTAL: ${total_preview:,.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
