import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
from fpdf import FPDF
import pytz
import re
import os

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(page_title="Toyota Asesores AI", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

# Configurar Zona Horaria
tz_cdmx = pytz.timezone('America/Mexico_City') if 'America/Mexico_City' in pytz.all_timezones else None
def obtener_hora_mx(): return datetime.now(tz_cdmx) if tz_cdmx else datetime.now()

# Inicializar Sesión
defaults = {'carrito': [], 'errores_carga': [], 'cliente': "", 'vin': "", 'orden': "", 'asesor': ""}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# Estilos CSS Minimalistas
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3 { font-family: 'Helvetica', sans-serif; font-weight: 700; color: #333; }
    .stButton button { width: 100%; border-radius: 6px; font-weight: 600; }
    .stButton button:hover { transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e9ecef; }
    .metric-card { background: white; padding: 15px; border-radius: 8px; border: 1px solid #eee; text-align: center; }
    .sku-tag { background: #eb0a1e; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
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
    patron_sku_fmt = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b'
    keywords = {'ORDEN': ['ORDEN', 'FOLIO', 'OT'], 'ASESOR': ['ASESOR', 'SA', 'ATENDIO'], 'CLIENTE': ['CLIENTE', 'ATTN', 'NOMBRE']}

    for r_idx, row in df.iterrows():
        for c_idx, val in row.items():
            # VIN
            if re.search(patron_vin, val): metadata['VIN'] = re.search(patron_vin, val).group(0)
            
            # Metadatos Genéricos
            for key, words in keywords.items():
                if any(w in val for w in words):
                    match = re.search(fr'(?:{"|".join(words)})[\:\.\-\s#]*([A-Z0-9\-\.\s]{{4,40}})', val)
                    if match: metadata[key] = match.group(1).strip()
                    else:
                        try: # Vecino derecha
                            vecino = df.iloc[r_idx, df.columns.get_loc(c_idx) + 1]
                            if len(vecino) > 3 and (key != 'ORDEN' or len(vecino) < 12): metadata[key] = vecino
                        except: pass

            # SKUs
            es_sku = False; sku_det = None
            if re.match(patron_sku_fmt, val): sku_det = val; es_sku = True
            elif re.match(r'\b[A-Z0-9]{10,12}\b', val) and not val.isdigit(): sku_det = val; es_sku = True
            
            if es_sku:
                cant = 1
                try: 
                    vecino = df.iloc[r_idx, df.columns.get_loc(c_idx) + 1].replace('.0', '')
                    if vecino.isdigit(): cant = int(vecino)
                except: pass
                hallazgos.append({'sku': sku_det, 'cant': cant})
    return hallazgos, metadata

def agregar_item(sku, desc, precio, cant, tipo, estatus="Disponible"):
    iva = (precio * cant) * 0.16
    st.session_state.carrito.append({
        "SKU": sku, "Descripción": desc, "Cantidad": cant,
        "Precio Base": precio, "IVA": iva, "Importe Total": (precio * cant) + iva,
        "Estatus": estatus, "Tipo": tipo
    })

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
        self.set_y(-40); self.set_font('Arial', '', 6); self.set_text_color(100)
        self.multi_cell(0, 3, "TÉRMINOS: Vigencia 24h. Precios con IVA. Partes eléctricas sin garantía. Pedidos especiales requieren 50% anticipo. Mano de obra garantizada 30 días.", 0, 'C')
        self.set_y(-15); self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

def generar_pdf():
    pdf = PDF(); pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=45)
    
    # Encabezado Datos
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
    cols = [25, 85, 15, 25, 25, 15]; headers = ['CÓDIGO', 'DESCRIPCIÓN', 'CANT', 'UNITARIO', 'TOTAL', 'TIPO']
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
    pdf.ln()

    pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    for item in st.session_state.carrito:
        pdf.cell(cols[0], 6, item['SKU'][:15], 'B', 0, 'C')
        pdf.cell(cols[1], 6, item['Descripción'][:65], 'B', 0, 'L')
        pdf.cell(cols[2], 6, str(item['Cantidad']), 'B', 0, 'C')
        pdf.cell(cols[3], 6, f"${item['Precio Base']:,.2f}", 'B', 0, 'R')
        pdf.cell(cols[4], 6, f"${item['Importe Total']:,.2f}", 'B', 0, 'R')
        pdf.cell(cols[5], 6, "REF" if "Ref" in item['Tipo'] else "MO", 'B', 1, 'C')

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

# --- SIDEBAR: DATOS & CARGA ---
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
                
                # Actualizar Sidebar
                if 'CLIENTE' in meta: st.session_state.cliente = meta['CLIENTE']
                if 'VIN' in meta: st.session_state.vin = meta['VIN']
                if 'ORDEN' in meta: st.session_state.orden = meta['ORDEN']
                if 'ASESOR' in meta: st.session_state.asesor = meta['ASESOR']
                
                # Procesar Piezas
                exitos, fallos = 0, []
                for it in items:
                    clean = str(it['sku']).upper().replace('-', '').strip()
                    match = df_db[df_db['SKU_CLEAN'] == clean]
                    if not match.empty:
                        row = match.iloc[0]
                        desc_t = GoogleTranslator(source='en', target='es').translate(str(row[col_desc_db])) if col_desc_db else "Refacción"
                        agregar_item(row[col_sku_db], desc_t, row['PRECIO_NUM'], it['cant'], "Refacción")
                        exitos += 1
                    else: fallos.append(it['sku'])
                
                st.session_state.errores_carga = fallos
                status.update(label=f"✅ {exitos} piezas importadas", state="complete")
                if fallos: st.warning(f"{len(fallos)} códigos no encontrados")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

# --- MAIN: CUERPO PRINCIPAL ---
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
                        c1, c2 = st.columns([3, 1])
                        sku_db = row[col_sku_db]
                        pr_db = row['PRECIO_NUM']
                        c1.markdown(f"**{sku_db}**\n\n${pr_db:,.2f}")
                        if c2.button("➕", key=f"add_{sku_db}"):
                            desc_db = GoogleTranslator(source='en', target='es').translate(str(row[col_desc_db]))
                            agregar_item(sku_db, desc_db, pr_db, 1, "Refacción")
                            st.toast(f"Agregado: {sku_db}", icon="✅")
        
        with tab_man:
            with st.form("manual_part"):
                c1, c2 = st.columns(2)
                m_sku = c1.text_input("SKU", "GENERICO")
                m_pr = c2.number_input("Precio", min_value=0.0)
                m_desc = st.text_input("Descripción", "Refacción General")
                if st.form_submit_button("Agregar Manual"):
                    agregar_item(m_sku.upper(), m_desc, m_pr, 1, "Refacción")
                    st.toast("Agregado Manualmente", icon="✅")

    else: # Mano de Obra
        with st.container(border=True):
            s_desc = st.text_input("Servicio", placeholder="Ej. Afinación Mayor")
            c1, c2 = st.columns(2)
            s_hrs = c1.number_input("Horas", 1.0, step=0.5)
            s_mo = c2.number_input("Costo Hora", value=500.0)
            if st.button("Agregar Servicio", type="primary"):
                agregar_item("MO-TALLER", f"{s_desc} ({s_hrs}hrs)", s_hrs * s_mo, 1, "Mano de Obra", "Servicio")
                st.toast("Servicio Agregado", icon="🛠️")

with col_right:
    st.subheader(f"Presupuesto Actual ({len(st.session_state.carrito)})")
    
    if st.session_state.carrito:
        df_c = pd.DataFrame(st.session_state.carrito)
        
        # Editor limpio
        edited = st.data_editor(
            df_c,
            column_config={
                "Precio Base": st.column_config.NumberColumn(format="$%.2f", disabled=True),
                "Importe Total": st.column_config.NumberColumn(format="$%.2f", disabled=True),
                "IVA": None, "Estatus": None, "Tipo": None, # Ocultar visualmente para limpieza
                "Cantidad": st.column_config.NumberColumn(min_value=1, step=1, width="small"),
                "Descripción": st.column_config.TextColumn(width="medium", disabled=True),
                "SKU": st.column_config.TextColumn(width="small", disabled=True),
            },
            use_container_width=True,
            num_rows="dynamic",
            key="editor_cart"
        )
        
        # Lógica de recálculo al editar
        if not edited.equals(df_c):
            new_cart = edited.to_dict('records')
            for r in new_cart:
                r['IVA'] = (r['Precio Base'] * r['Cantidad']) * 0.16
                r['Importe Total'] = (r['Precio Base'] * r['Cantidad']) + r['IVA']
                r['Estatus'] = "Servicio" if "MO" in r['SKU'] else "Disponible"
                r['Tipo'] = "Mano de Obra" if "MO" in r['SKU'] else "Refacción"
            st.session_state.carrito = new_cart
            st.rerun()

        # Totales y Acciones
        sub = sum(x['Precio Base'] * x['Cantidad'] for x in st.session_state.carrito)
        tot = sub * 1.16
        
        st.divider()
        c_tot, c_act = st.columns([1, 1])
        with c_tot:
            st.markdown(f"<div style='text-align:right; font-size:1.5em; font-weight:bold; color:#eb0a1e'>Total: ${tot:,.2f}</div>", unsafe_allow_html=True)
            st.caption(f"Subtotal: ${sub:,.2f} + IVA")
        
        with c_act:
            pdf_bytes = generar_pdf()
            st.download_button("📄 Descargar PDF", pdf_bytes, f"Presupuesto_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)
            if st.button("Limpiar", type="secondary", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()
    else:
        st.info("El carrito está vacío. Busca piezas o sube un archivo.")
