import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
from fpdf import FPDF
import pytz
import re
import os
import base64

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(page_title="Toyota Asesores AI", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

# Configurar Zona Horaria
tz_cdmx = pytz.timezone('America/Mexico_City') if 'America/Mexico_City' in pytz.all_timezones else None
def obtener_hora_mx(): return datetime.now(tz_cdmx) if tz_cdmx else datetime.now()

# Inicializar Sesión
defaults = {
    'carrito': [], 'errores_carga': [], 'cliente': "", 'vin': "", 'orden': "", 'asesor': "",
    'temp_sku': "", 'temp_desc': "", 'temp_precio': 0.0, 
    'ver_preview': False
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# Estilos CSS
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3 { font-family: 'Helvetica', sans-serif; font-weight: 700; color: #333; }
    .stButton button { width: 100%; border-radius: 6px; font-weight: 600; }
    .stButton button:hover { transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e9ecef; }
    
    /* Estilos de la Vista Previa (Hoja de Papel) */
    .preview-paper {
        background-color: white;
        padding: 40px;
        border: 1px solid #ddd;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-radius: 4px;
        color: #333;
        font-family: 'Arial', sans-serif;
        margin-top: 20px;
    }
    .preview-header { border-bottom: 2px solid #eb0a1e; padding-bottom: 10px; margin-bottom: 20px; }
    .preview-title { color: #eb0a1e; font-size: 24px; font-weight: bold; text-align: center; }
    .preview-subtitle { text-align: center; font-size: 14px; color: #666; }
    .preview-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; font-size: 12px; }
    .preview-label { font-weight: bold; color: #555; }
    .preview-table { width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 20px; }
    .preview-table th { background-color: #eb0a1e; color: white; padding: 8px; text-align: left; }
    .preview-table td { border-bottom: 1px solid #eee; padding: 8px; }
    .preview-total { text-align: right; font-size: 14px; margin-top: 10px; }
    .preview-total-final { font-size: 18px; font-weight: bold; color: #eb0a1e; }
    .prio-urgente { color: #d32f2f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. LÓGICA DE NEGOCIO (IA & DB)
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
    hallazgos = []; metadata = {}
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    
    patron_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    patron_orden_8 = r'\b\d{8}\b'
    patron_sku_fmt = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b'
    patron_sku_pln = r'\b[A-Z0-9]{10,12}\b'
    
    keywords = {
        'ORDEN': ['ORDEN', 'FOLIO', 'OT', 'OS'],
        'ASESOR': ['ASESOR', 'SA', 'ATENDIO', 'ADVISOR'],
        'CLIENTE': ['CLIENTE', 'ATTN', 'NOMBRE']
    }

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

def agregar_item_callback(sku, desc_raw, precio, cant, tipo, prioridad="Medio"):
    try: desc = GoogleTranslator(source='en', target='es').translate(str(desc_raw))
    except: desc = str(desc_raw)
        
    iva = (precio * cant) * 0.16
    st.session_state.carrito.append({
        "SKU": sku, "Descripción": desc, "Prioridad": prioridad,
        "Cantidad": cant, "Precio Base": precio, "IVA": iva, 
        "Importe Total": (precio * cant) + iva, "Estatus": "Disponible", "Tipo": tipo
    })

def cargar_en_manual(sku, desc, precio):
    st.session_state.temp_sku = sku
    try: st.session_state.temp_desc = GoogleTranslator(source='en', target='es').translate(str(desc))
    except: st.session_state.temp_desc = str(desc)
    st.session_state.temp_precio = precio

def toggle_preview():
    st.session_state.ver_preview = not st.session_state.ver_preview

# ==========================================
# 3. GENERADOR PDF
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
        self.set_y(-35); self.set_font('Arial', '', 6); self.set_text_color(100)
        self.multi_cell(0, 3, "VIGENCIA: 24h. Precios incluyen IVA. Partes eléctricas sin garantía. 50% anticipo en pedidos especiales. Mano de Obra garantizada.", 0, 'C')
        self.set_y(-15); self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

def generar_pdf():
    pdf = PDF(); pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=40)
    
    # Header Datos
    pdf.set_fill_color(245); pdf.rect(10, 35, 190, 22, 'F')
    pdf.set_xy(12, 38); pdf.set_font('Arial', 'B', 9)
    pdf.cell(18, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(90, 5, st.session_state.cliente.upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(15, 5, 'FECHA:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, obtener_hora_mx().strftime("%d/%m/%Y"), 0, 1)
    
    pdf.set_x(12); pdf.set_font('Arial', 'B', 9)
    pdf.cell(18, 5, 'VIN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(90, 5, st.session_state.vin.upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(15, 5, 'ORDEN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(40, 5, st.session_state.orden.upper(), 0, 1)
    
    pdf.set_x(12); pdf.set_font('Arial', 'B', 9)
    pdf.cell(18, 5, 'ASESOR:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(90, 5, st.session_state.asesor.upper(), 0, 1)
    pdf.ln(8)

    # Tabla
    pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 8)
    cols = [25, 65, 20, 15, 25, 25, 15]
    headers = ['CÓDIGO', 'DESCRIPCIÓN', 'PRIORIDAD', 'CANT', 'UNIT', 'TOTAL', 'TIPO']
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
    pdf.ln()

    pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    for item in st.session_state.carrito:
        prio = item.get('Prioridad', 'Medio')
        pdf.set_font('Arial', 'B' if prio == 'Urgente' else '', 7)
        if prio == 'Urgente': pdf.set_text_color(200, 0, 0)
        else: pdf.set_text_color(0)
        
        pdf.cell(cols[0], 6, item['SKU'][:15], 'B', 0, 'C')
        pdf.cell(cols[1], 6, item['Descripción'][:50], 'B', 0, 'L')
        pdf.cell(cols[2], 6, prio.upper(), 'B', 0, 'C')
        
        pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
        pdf.cell(cols[3], 6, str(item['Cantidad']), 'B', 0, 'C')
        pdf.cell(cols[4], 6, f"${item['Precio Base']:,.2f}", 'B', 0, 'R')
        pdf.cell(cols[5], 6, f"${item['Importe Total']:,.2f}", 'B', 0, 'R')
        pdf.cell(cols[6], 6, "MO" if "MO" in item['SKU'] else "REF", 'B', 1, 'C')

    # Totales
    pdf.ln(5)
    sub = sum(i['Precio Base'] * i['Cantidad'] for i in st.session_state.carrito)
    iva = sum(i['IVA'] for i in st.session_state.carrito)
    total = sub + iva

    pdf.set_x(130); pdf.set_font('Arial', '', 9); pdf.cell(30, 6, 'Subtotal:', 0, 0, 'R'); pdf.cell(30, 6, f"${sub:,.2f}", 0, 1, 'R')
    pdf.set_x(130); pdf.cell(30, 6, 'IVA (16%):', 0, 0, 'R'); pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    pdf.set_x(130); pdf.set_font('Arial', 'B', 11); pdf.set_text_color(235, 10, 30)
    pdf.cell(30, 8, 'TOTAL:', 0, 0, 'R'); pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. INTERFAZ GRÁFICA (UI)
# ==========================================
if df_db is None: st.error("⚠️ Error crítico: No se encontró 'lista_precios.zip'"); st.stop()

# --- SIDEBAR ---
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
                        agregar_item_callback(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], it['cant'], "Refacción", "Medio")
                        exitos += 1
                    else: fallos.append(it['sku'])
                
                st.session_state.errores_carga = fallos
                status.update(label=f"✅ {exitos} piezas importadas", state="complete")
                if fallos: st.warning(f"{len(fallos)} códigos no encontrados")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

# --- MAIN ---
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
                        c3.button("➕", key=f"add_{sku_db}", on_click=agregar_item_callback, args=(sku_db, desc_ori, pr_db, 1, "Refacción", "Medio"))
        
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
                    agregar_item_callback(m_sku.upper(), m_desc, m_pr, 1, "Refacción", "Medio")
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
                agregar_item_callback("MO-TALLER", f"{s_desc} ({s_hrs}hrs)", s_hrs * s_mo, 1, "Mano de Obra", "Medio")
                st.toast("Servicio Agregado", icon="🛠️")

with col_right:
    st.subheader(f"Presupuesto ({len(st.session_state.carrito)})")
    
    if st.session_state.carrito:
        df_c = pd.DataFrame(st.session_state.carrito)
        
        edited = st.data_editor(
            df_c,
            column_config={
                "Prioridad": st.column_config.SelectboxColumn("Prioridad", options=["Urgente", "Medio", "Bajo"], required=True, width="small"),
                "Precio Base": st.column_config.NumberColumn(format="$%.2f", disabled=True),
                "IVA": st.column_config.NumberColumn(format="$%.2f", disabled=True),
                "Importe Total": st.column_config.NumberColumn(format="$%.2f", disabled=True),
                "Estatus": None, "Tipo": None, 
                "Cantidad": st.column_config.NumberColumn(min_value=1, step=1, width="small"),
                "Descripción": st.column_config.TextColumn(width="medium", disabled=True),
                "SKU": st.column_config.TextColumn(width="small", disabled=True),
            },
            use_container_width=True, num_rows="dynamic", key="editor_cart"
        )
        
        if not edited.equals(df_c):
            new_cart = edited.to_dict('records')
            for r in new_cart:
                r['IVA'] = (r['Precio Base'] * r['Cantidad']) * 0.16
                r['Importe Total'] = (r['Precio Base'] * r['Cantidad']) + r['IVA']
                r['Estatus'] = "Servicio" if "MO" in r['SKU'] else "Disponible"
                r['Tipo'] = "Mano de Obra" if "MO" in r['SKU'] else "Refacción"
            st.session_state.carrito = new_cart
            st.rerun()

        sub = sum(x['Precio Base'] * x['Cantidad'] for x in st.session_state.carrito)
        tot = sub * 1.16
        
        st.divider()
        c_tot, c_act = st.columns([1, 1])
        with c_tot:
            st.markdown(f"<div style='text-align:right; font-size:1.5em; font-weight:bold; color:#eb0a1e'>Total: ${tot:,.2f}</div>", unsafe_allow_html=True)
            st.caption(f"Subtotal: ${sub:,.2f} + IVA")
        
        with c_act:
            pdf_bytes = generar_pdf()
            
            c_p, c_d, c_l = st.columns([1, 1, 0.5])
            
            with c_p:
                if st.button("👁️ Vista Previa" if not st.session_state.ver_preview else "🚫 Cerrar", on_click=toggle_preview, use_container_width=True):
                    pass
            with c_d:
                st.download_button("📄 PDF", pdf_bytes, f"Cot_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)
            with c_l:
                if st.button("🗑️", help="Limpiar carrito"):
                    st.session_state.carrito = []
                    st.rerun()

            # --- VISTA PREVIA HTML (NO PDF EMBEBIDO) ---
            if st.session_state.ver_preview:
                
                rows_html = ""
                for item in st.session_state.carrito:
                    p_class = "prio-urgente" if item['Prioridad'] == "Urgente" else ""
                    rows_html += f"""
                    <tr>
                        <td>{item['SKU']}</td>
                        <td>{item['Descripción']}</td>
                        <td class="{p_class}">{item['Prioridad'].upper()}</td>
                        <td style="text-align:center">{item['Cantidad']}</td>
                        <td style="text-align:right">${item['Precio Base']:,.2f}</td>
                        <td style="text-align:right">${item['Importe Total']:,.2f}</td>
                    </tr>
                    """

                st.markdown(f"""
                <div class="preview-paper">
                    <div class="preview-header">
                        <div class="preview-title">TOYOTA LOS FUERTES</div>
                        <div class="preview-subtitle">PRESUPUESTO DE SERVICIOS Y REFACCIONES</div>
                    </div>
                    <div class="preview-grid">
                        <div>
                            <div><span class="preview-label">CLIENTE:</span> {st.session_state.cliente}</div>
                            <div><span class="preview-label">VIN:</span> {st.session_state.vin}</div>
                        </div>
                        <div>
                            <div><span class="preview-label">FECHA:</span> {obtener_hora_mx().strftime("%d/%m/%Y")}</div>
                            <div><span class="preview-label">ORDEN:</span> {st.session_state.orden}</div>
                            <div><span class="preview-label">ASESOR:</span> {st.session_state.asesor}</div>
                        </div>
                    </div>
                    <table class="preview-table">
                        <thead>
                            <tr>
                                <th>CÓDIGO</th>
                                <th>DESCRIPCIÓN</th>
                                <th>PRIORIDAD</th>
                                <th>CANT</th>
                                <th style="text-align:right">UNITARIO</th>
                                <th style="text-align:right">TOTAL</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                    <div class="preview-total">Subtotal: ${sub:,.2f}</div>
                    <div class="preview-total">IVA (16%): ${sub*0.16:,.2f}</div>
                    <div class="preview-total preview-total-final">TOTAL: ${tot:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Carrito vacío.")

