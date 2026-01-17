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
    
    /* PREVIEW */
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
    
    /* TOTAL BOX */
    .total-box { margin-left: auto; width: 350px; }
    .subtotal-group { font-size: 11px; color: #555; text-align: right; padding: 2px 0; border-bottom: 1px dashed #eee; }
    .total-final { font-size: 24px; font-weight: 900; color: #eb0a1e; border-top: 2px solid #ccc; padding-top: 10px; margin-top: 10px; text-align: right; }
    
    /* PALETA */
    .badge-base { padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; display: inline-block; color: white; }
    .badge-urg { background: #d32f2f; }
    .badge-med { background: #1976D2; }
    .badge-baj { background: #757575; }
    
    /* GRUPOS EN TABLA */
    .group-header { background-color: #f0f0f0; font-weight: bold; font-size: 11px; padding: 5px 10px; border-left: 4px solid #333; margin-top: 10px; }
    .group-urg { border-left-color: #d32f2f; color: #d32f2f; background-color: #ffebee; }
    .group-med { border-left-color: #1976D2; color: #1565C0; background-color: #e3f2fd; }
    .group-baj { border-left-color: #757575; color: #616161; background-color: #f5f5f5; }

    /* NIEVE */
    .snowflake { color: #fff; font-size: 1em; position: fixed; top: -10%; z-index: 9999; animation-name: snowflakes-fall, snowflakes-shake; animation-duration: 10s, 3s; animation-iteration-count: infinite; }
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
    st.markdown("".join([f'<div class="snowflake">❅</div>' for _ in range(8)]), unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS
# ==========================================
@st.cache_data
def cargar_catalogo():
    archivo_zip = "base_datos_2026.zip"
    if not os.path.exists(archivo_zip): return None, None, None
    try:
        with zipfile.ZipFile(archivo_zip, "r") as z:
            validos = [f for f in z.namelist() if (f.endswith('.xlsx') or f.endswith('.csv')) and '__MACOSX' not in f]
            if not validos: return None, None, None
            with z.open(validos[0]) as f:
                if validos[0].endswith('.csv'):
                    try: df = pd.read_csv(f, dtype=str)
                    except: f.seek(0); df = pd.read_csv(f, dtype=str, encoding='latin-1')
                else: df = pd.read_excel(f, dtype=str)
        
        df.columns = [str(c).strip().upper() for c in df.columns]
        c_sku = next((c for c in df.columns if c in ['ITEM', 'PART', 'NUM', 'SKU']), None)
        c_desc = next((c for c in df.columns if 'DESC' in c), None)
        c_precio = next((c for c in df.columns if c in ['TOTAL_UNITARIO', 'PRECIO', 'PRICE']), None)
        
        if not c_sku or not c_precio: return None, None, None
        
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        
        def limpiar_precio(x):
            try: return float(str(x).replace('$', '').replace(',', '').strip())
            except: return 0.0
            
        df['PRECIO_NUM'] = df[c_precio].apply(limpiar_precio)
        return df, c_sku, c_desc
    except: return None, None, None

df_db, col_sku_db, col_desc_db = cargar_catalogo()

def analizador_inteligente_archivos(df_raw):
    hallazgos = []; metadata = {}
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    # ... (Código de regex igual al anterior, resumido por brevedad) ...
    # Se asume la misma lógica de extracción de VIN, Orden, SKU
    patron_sku = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b'
    for r_idx, row in df.iterrows():
        for c_idx, val in row.items():
            if re.match(patron_sku, val):
                cant = 1
                try: 
                    vec = df.iloc[r_idx, df.columns.get_loc(c_idx)+1]
                    if vec.replace('.0','').isdigit(): cant = int(vec.replace('.0',''))
                except: pass
                hallazgos.append({'sku': val, 'cant': cant})
    return hallazgos, metadata

def agregar_item_callback(sku, desc_raw, precio_base, cant, tipo, prioridad="Medio", abasto="⚠️ REVISAR", traducir=True):
    if traducir:
        try: desc = GoogleTranslator(source='en', target='es').translate(str(desc_raw))
        except: desc = str(desc_raw)
    else: desc = str(desc_raw)
    
    st.session_state.carrito.append({
        "SKU": sku, "Descripción": desc, "Prioridad": prioridad,
        "Abasto": abasto, "Tiempo Entrega": "", "Cantidad": cant,
        "Precio Base": precio_base,
        "Precio Unitario (c/IVA)": precio_base * 1.16,
        "IVA": (precio_base * cant) * 0.16,
        "Importe Total": (precio_base * cant) * 1.16,
        "Tipo": tipo,
        "Seleccionado": True # Nuevo campo para selección
    })

def toggle_preview(): st.session_state.ver_preview = not st.session_state.ver_preview
def toggle_nieve(): st.session_state.nieve_activa = not st.session_state.nieve_activa

# ==========================================
# 4. LÓGICA DE AGRUPACIÓN Y PDF
# ==========================================
def obtener_items_ordenados():
    # 1. Filtrar solo seleccionados
    items = [i for i in st.session_state.carrito if i.get('Seleccionado', True)]
    
    # 2. Definir orden de prioridades
    orden_map = {"Urgente": 1, "Medio": 2, "Bajo": 3}
    
    # 3. Ordenar
    items.sort(key=lambda x: orden_map.get(x['Prioridad'], 99))
    
    # 4. Agrupar
    grupos = {}
    for i in items:
        p = i['Prioridad']
        if p not in grupos: grupos[p] = []
        grupos[p].append(i)
        
    return grupos, items

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
        legales = "1. VIGENCIA Y PRECIOS: Validez 24 horas. Precios en MXN con IVA.\n2. PEDIDOS ESPECIALES: Requieren 100% anticipo. Penalización del 20% por cancelación (Art. 92 LFPC).\n3. GARANTÍA: 12 meses en partes genuinas. Partes eléctricas sujetas a diagnóstico (Art. 77 LFPC)."
        self.multi_cell(0, 3, legales, 0, 'J')
        self.ln(5)
        y_firma = self.get_y()
        self.line(10, y_firma, 80, y_firma); self.line(110, y_firma, 190, y_firma)
        self.set_font('Arial', 'B', 6)
        self.cell(90, 3, "TOYOTA LOS FUERTES (ASESOR)", 0, 0, 'C')
        self.cell(90, 3, "FIRMA DE CONFORMIDAD DEL CLIENTE", 0, 1, 'C')
        self.set_y(-12); self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

def generar_pdf_agrupado():
    grupos, items_activos = obtener_items_ordenados()
    if not items_activos: return None # Nada que imprimir

    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=80)
    
    # Encabezado Cliente
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(100, 5, str(st.session_state.cliente)[:50], 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'FECHA:', 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(40, 5, obtener_hora_mx().strftime("%d/%m/%Y"), 0, 1)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'VIN:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(100, 5, str(st.session_state.vin), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'ORDEN:', 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(40, 5, str(st.session_state.orden), 0, 1)
    pdf.ln(5)

    # Definición columnas
    cols = [25, 60, 20, 25, 10, 20, 30] # SKU, Desc, Estatus, Tiempo, Cant, Unit, Total
    headers = ['CÓDIGO', 'DESCRIPCIÓN', 'ESTATUS', 'TIEMPO', 'CT', 'UNITARIO', 'TOTAL']
    
    pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 7)
    for i, h in enumerate(headers): pdf.cell(cols[i], 6, h, 0, 0, 'C', True)
    pdf.ln()

    gran_total_base = 0
    gran_total_iva = 0

    # Iterar por grupos (Orden fijo)
    for prio in ["Urgente", "Medio", "Bajo"]:
        if prio in grupos:
            lista = grupos[prio]
            
            # Subtotales Grupo
            sub_g_base = sum(i['Precio Base'] * i['Cantidad'] for i in lista)
            sub_g_total = sum(i['Importe Total'] for i in lista)
            gran_total_base += sub_g_base
            gran_total_iva += sum(i['IVA'] for i in lista)

            # Encabezado Grupo
            pdf.set_font('Arial', 'B', 8); pdf.set_text_color(0)
            if prio == "Urgente": pdf.set_fill_color(255, 235, 238) # Rojo claro
            elif prio == "Medio": pdf.set_fill_color(227, 242, 253) # Azul claro
            else: pdf.set_fill_color(245, 245, 245) # Gris claro
            
            pdf.cell(sum(cols), 6, f"PRIORIDAD: {prio.upper()}", 1, 1, 'L', True)

            # Items
            pdf.set_font('Arial', '', 7); pdf.set_text_color(0)
            for item in lista:
                sku = item['SKU'][:15]
                desc = str(item['Descripción']).encode('latin-1', 'replace').decode('latin-1')
                est = item['Abasto'].replace("⚠️ ", "").replace("✅ ", "").replace("📦 ", "").replace("⚫ ", "")
                te = str(item['Tiempo Entrega'])[:12]
                
                # Altura dinámica
                nb = pdf.get_string_width(desc) / (cols[1] - 2)
                h = 5 * (int(nb) + 1)
                
                # Check page break
                if pdf.get_y() + h > 260: pdf.add_page()
                
                x = pdf.get_x(); y = pdf.get_y()
                pdf.cell(cols[0], h, sku, 1, 0)
                pdf.multi_cell(cols[1], 5, desc, 1, 'L')
                pdf.set_xy(x + cols[0] + cols[1], y)
                pdf.cell(cols[2], h, est, 1, 0, 'C')
                pdf.cell(cols[3], h, te, 1, 0, 'C')
                pdf.cell(cols[4], h, str(item['Cantidad']), 1, 0, 'C')
                pdf.cell(cols[5], h, f"${item['Precio Base']:,.2f}", 1, 0, 'R')
                pdf.cell(cols[6], h, f"${item['Importe Total']:,.2f}", 1, 1, 'R')

            # Subtotal Grupo Footer
            pdf.set_font('Arial', 'I', 7)
            pdf.cell(sum(cols)-30, 5, f"Total {prio}:", 0, 0, 'R')
            pdf.set_font('Arial', 'B', 7)
            pdf.cell(30, 5, f"${sub_g_total:,.2f}", 0, 1, 'R')

    # Totales Finales
    pdf.ln(5)
    pdf.set_x(130)
    pdf.set_font('Arial', '', 9)
    pdf.cell(30, 5, 'SUBTOTAL:', 0, 0, 'R'); pdf.cell(30, 5, f"${gran_total_base:,.2f}", 0, 1, 'R')
    pdf.set_x(130)
    pdf.cell(30, 5, 'IVA 16%:', 0, 0, 'R'); pdf.cell(30, 5, f"${gran_total_iva:,.2f}", 0, 1, 'R')
    pdf.set_x(130); pdf.set_font('Arial', 'B', 11); pdf.set_text_color(235, 10, 30)
    pdf.cell(30, 7, 'GRAN TOTAL:', 0, 0, 'R'); pdf.cell(30, 7, f"${gran_total_base + gran_total_iva:,.2f}", 0, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL
# ==========================================
if df_db is None: st.warning("⚠️ Modo Manual: Base de datos no encontrada.")

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    if st.button("❄️ Nieve On/Off", type="secondary"): toggle_nieve(); st.rerun()
    st.divider()
    st.session_state.orden = st.text_input("Orden", st.session_state.orden)
    st.session_state.vin = st.text_input("VIN", st.session_state.vin)
    st.session_state.cliente = st.text_input("Cliente", st.session_state.cliente)
    st.session_state.asesor = st.text_input("Asesor", st.session_state.asesor)
    
    st.divider()
    # Carga de archivo
    up_file = st.file_uploader("Cargar Excel/CSV", type=['xlsx', 'csv'], label_visibility="collapsed")
    if up_file and st.button("Procesar Archivo"):
        try:
            df_up = pd.read_csv(up_file, encoding='latin-1') if up_file.name.endswith('.csv') else pd.read_excel(up_file)
            items, meta = analizador_inteligente_archivos(df_up)
            # Actualizar datos meta
            for k, v in meta.items(): 
                if v: st.session_state[k.lower()] = v
            
            count = 0
            for it in items:
                clean = str(it['sku']).upper().replace('-', '').strip()
                if df_db is not None:
                    match = df_db[df_db['SKU_CLEAN'] == clean]
                    if not match.empty:
                        r = match.iloc[0]
                        agregar_item_callback(r[col_sku_db], r[col_desc_db], r['PRECIO_NUM'], it['cant'], "Refacción")
                        count += 1
                    else:
                        # Si no encuentra, agregar como manual vacío
                        agregar_item_callback(it['sku'], "NO ENCONTRADO EN CATALOGO", 0.0, it['cant'], "Refacción", "Medio", "⚠️ REVISAR", False)
            st.success(f"Procesados {count} items")
            st.rerun()
        except Exception as e: st.error(f"Error: {e}")

    if st.button("🗑️ Nuevo Cliente"): limpiar_todo(); st.rerun()

st.title("Toyota Los Fuertes")

# BUSCADOR
with st.expander("🔎 Agregar Ítems", expanded=True):
    col_l, col_r = st.columns([1.5, 1])
    with col_l:
        q = st.text_input("Buscar SKU/Nombre", key="search_q")
        if q and df_db is not None:
            mask = df_db.apply(lambda x: x.astype(str).str.contains(q, case=False)).any(axis=1)
            for _, row in df_db[mask].head(3).iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row[col_sku_db]}** - ${row['PRECIO_NUM']:,.2f}")
                c2.button("➕", key=f"add_{row[col_sku_db]}", on_click=agregar_item_callback, args=(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], 1, "Refacción"))
    
    with col_r:
        with st.form("manual"):
            m_sku = st.text_input("SKU Manual")
            m_pr = st.number_input("Precio", min_value=0.0)
            m_desc = st.text_input("Descripción")
            if st.form_submit_button("Agregar Manual"):
                agregar_item_callback(m_sku, m_desc, m_pr, 1, "Refacción", "Medio", "⚠️ REVISAR", False)
                st.rerun()

st.divider()

# ==========================================
# CARRITO CON SELECTOR Y AGRUPACIÓN
# ==========================================
st.subheader(f"🛒 Carrito ({len(st.session_state.carrito)})")

if st.session_state.carrito:
    # --- CABECERA DE LA TABLA ---
    h1, h2, h3, h4 = st.columns([0.5, 3, 2, 0.5])
    h1.write("✔")
    h2.write("**Descripción**")
    h3.write("**Detalles**")
    h4.write("🗑")
    st.markdown("<hr style='margin: 5px 0'>", unsafe_allow_html=True)

    def update_cart_val(idx, key, val): st.session_state.carrito[idx][key] = val
    def update_qty(idx, delta):
        n = st.session_state.carrito[idx]['Cantidad'] + delta
        if n < 1: n = 1
        st.session_state.carrito[idx]['Cantidad'] = n
        p = st.session_state.carrito[idx]['Precio Base']
        st.session_state.carrito[idx]['IVA'] = (p * n) * 0.16
        st.session_state.carrito[idx]['Importe Total'] = (p * n) * 1.16

    for i, item in enumerate(st.session_state.carrito):
        c_chk, c_desc, c_det, c_del = st.columns([0.5, 3, 2, 0.5])
        
        # 1. SELECTOR (CHECKBOX)
        sel = c_chk.checkbox("", value=item.get('Seleccionado', True), key=f"sel_{i}")
        if sel != item.get('Seleccionado', True):
            update_cart_val(i, 'Seleccionado', sel)
            st.rerun()

        # 2. DESCRIPCIÓN
        with c_desc:
            st.markdown(f"**{item['SKU']}**")
            st.caption(item['Descripción'])
            # Prioridad
            prioridades = ["🔴 Urgente", "🔵 Medio", "⚪ Bajo"]
            curr_p = "🔴 Urgente" if item['Prioridad']=="Urgente" else ("🔵 Medio" if item['Prioridad']=="Medio" else "⚪ Bajo")
            new_p = st.selectbox("Prio", prioridades, index=prioridades.index(curr_p), key=f"p_{i}", label_visibility="collapsed")
            clean_p = new_p.split(" ")[1]
            if clean_p != item['Prioridad']:
                update_cart_val(i, 'Prioridad', clean_p)
                st.rerun()

        # 3. DETALLES (Abasto, Cantidad, Precio)
        with c_det:
            # Abasto
            abastos = ["✅ Disponible", "📦 Por Pedido", "⚫ Back Order", "⚠️ REVISAR"]
            curr_a = next((x for x in abastos if item['Abasto'] in x), "⚠️ REVISAR")
            try: idx_a = abastos.index(curr_a)
            except: idx_a = 3
            new_a = st.selectbox("Estatus", abastos, index=idx_a, key=f"a_{i}", label_visibility="collapsed")
            clean_a = new_a.replace("✅ ", "").replace("📦 ", "").replace("⚫ ", "").replace("⚠️ ", "")
            if clean_a != item['Abasto']: update_cart_val(i, 'Abasto', clean_a)

            # Cantidad y Precio
            cc1, cc2, cc3 = st.columns([1, 1, 1.5])
            cc1.button("➖", key=f"mn_{i}", on_click=update_qty, args=(i, -1))
            cc2.markdown(f"<div style='text-align:center; font-weight:bold; padding-top:10px'>{item['Cantidad']}</div>", unsafe_allow_html=True)
            cc3.button("➕", key=f"pl_{i}", on_click=update_qty, args=(i, 1))
            
            st.markdown(f"<div style='text-align:right; font-weight:bold; color:#eb0a1e'>${item['Importe Total']:,.2f}</div>", unsafe_allow_html=True)

        # 4. ELIMINAR
        c_del.button("🗑️", key=f"del_{i}", on_click=lambda x: st.session_state.carrito.pop(x), args=(i,))
        st.markdown("<hr style='margin: 5px 0'>", unsafe_allow_html=True)

    # --- CÁLCULO DE TOTALES (Solo Seleccionados) ---
    grupos, items_activos = obtener_items_ordenados()
    
    pendientes_bloqueantes = [i for i in items_activos if "REVISAR" in i['Abasto']]
    
    if pendientes_bloqueantes:
        st.error(f"🛑 Hay {len(pendientes_bloqueantes)} ítems seleccionados con estatus 'REVISAR'. Desmárcalos o corrige su estatus.")
    else:
        # Mostrar resumen de totales
        tot_u = sum(i['Importe Total'] for i in grupos.get('Urgente', []))
        tot_m = sum(i['Importe Total'] for i in grupos.get('Medio', []))
        tot_b = sum(i['Importe Total'] for i in grupos.get('Bajo', []))
        gran_total = tot_u + tot_m + tot_b
        
        c_res, c_acts = st.columns([2, 1])
        with c_res:
            st.markdown(f"""
            <div style="background:#f9f9f9; padding:10px; border-radius:5px; border:1px solid #ddd;">
                <div style="display:flex; justify-content:space-between; color:#d32f2f"><span>Urgente:</span> <b>${tot_u:,.2f}</b></div>
                <div style="display:flex; justify-content:space-between; color:#1565C0"><span>Medio:</span> <b>${tot_m:,.2f}</b></div>
                <div style="display:flex; justify-content:space-between; color:#616161"><span>Bajo:</span> <b>${tot_b:,.2f}</b></div>
                <div style="display:flex; justify-content:space-between; font-size:1.2em; font-weight:bold; margin-top:5px; border-top:1px solid #ccc">
                    <span>TOTAL:</span> <span>${gran_total:,.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c_acts:
            if st.button("👁️ Vista Previa", type="secondary", use_container_width=True): toggle_preview()
            
            pdf_bytes = generar_pdf_agrupado()
            if pdf_bytes:
                st.download_button("📄 PDF Cotización", pdf_bytes, f"Cot_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)

# ==========================================
# 6. VISTA PREVIA (HTML)
# ==========================================
if st.session_state.ver_preview and st.session_state.carrito:
    grupos_pv, items_pv = obtener_items_ordenados()
    rows_html = ""
    total_pv = 0
    
    for prio in ["Urgente", "Medio", "Bajo"]:
        if prio in grupos_pv:
            items_g = grupos_pv[prio]
            sub_g = sum(i['Importe Total'] for i in items_g)
            total_pv += sub_g
            
            css_class = "group-urg" if prio=="Urgente" else ("group-med" if prio=="Medio" else "group-baj")
            
            # Encabezado Grupo
            rows_html += f"""<tr class="group-header {css_class}"><td colspan="8">PRIORIDAD: {prio.upper()}</td></tr>"""
            
            for item in items_g:
                estatus_cls = "status-disp" if "Disponible" in item['Abasto'] else ("status-ped" if "Pedido" in item['Abasto'] else "status-bo")
                rows_html += f"""<tr>
                <td>{item['SKU']}</td>
                <td>{item['Descripción']}</td>
                <td></td>
                <td><span class="status-base {estatus_cls}">{item['Abasto']}</span></td>
                <td>{item['Tiempo Entrega']}</td>
                <td align="center">{item['Cantidad']}</td>
                <td align="right">${item['Precio Base']*1.16:,.2f}</td>
                <td align="right"><b>${item['Importe Total']:,.2f}</b></td>
                </tr>"""
            
            # Subtotal Grupo
            rows_html += f"""<tr><td colspan="7" align="right" style="font-size:10px; color:#666">Total {prio}:</td><td align="right" style="font-size:11px; font-weight:bold">${sub_g:,.2f}</td></tr>"""

    html = f"""
    <div class="preview-container"><div class="preview-paper">
    <h2 class="preview-title">VISTA PREVIA DE COTIZACIÓN</h2>
    <table class="custom-table">
        <thead><tr><th>CÓDIGO</th><th>DESCRIPCIÓN</th><th></th><th>ESTATUS</th><th>TIEMPO</th><th>CANT</th><th>UNITARIO</th><th>TOTAL</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    <div class="total-final">GRAN TOTAL: ${total_pv:,.2f}</div>
    </div></div>
    """
    st.markdown(html, unsafe_allow_html=True)
