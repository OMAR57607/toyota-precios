import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
from fpdf import FPDF
from PIL import Image
from pyzbar.pyzbar import decode
import pytz
import easyocr
import numpy as np
import re
import os

# --- CONFIGURACIÓN DE ARCHIVO LOCAL ---
# Asegúrate de que tu imagen se llame 'logo.png' y esté junto a este script
LOGO_FILE = "logo.png"

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Toyota Asesores", page_icon="🔧", layout="wide")

# Configurar Zona Horaria CDMX
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    tz_cdmx = None 

def obtener_hora_mx():
    if tz_cdmx:
        return datetime.now(tz_cdmx)
    return datetime.now()

# Inicializar variables de sesión
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'errores_carga' not in st.session_state: st.session_state.errores_carga = [] 
if 'auto_cliente' not in st.session_state: st.session_state.auto_cliente = ""
if 'auto_vin' not in st.session_state: st.session_state.auto_vin = ""
if 'auto_orden' not in st.session_state: st.session_state.auto_orden = ""

@st.cache_resource
def cargar_lector_ocr():
    return easyocr.Reader(['en'], gpu=False) 

# 2. ESTILOS CSS INTELIGENTES (ADAPTATIVOS)
# Adaptamos el filtro para que funcione con el nombre del archivo local
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;500;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Roboto', sans-serif;
    }}
    
    /* Títulos y textos adaptativos */
    h1, h2, h3 {{ color: var(--text-color) !important; font-weight: 700; }}
    .stMarkdown div {{ color: var(--text-color); }}
    .stButton button {{ width: 100%; border-radius: 4px; font-weight: bold; text-transform: uppercase; }}
    
    /* Footer */
    .legal-footer {{ 
        text-align: center; font-size: 11px; color: var(--text-color); opacity: 0.6;
        margin-top: 50px; padding-top: 20px; border-top: 1px solid rgba(128, 128, 128, 0.2); 
    }}
    </style>
    """, unsafe_allow_html=True)

# --- CLASE PDF ---
class PDF(FPDF):
    def header(self):
        # LÓGICA PARA LOGO LOCAL
        if os.path.exists(LOGO_FILE):
            try:
                self.image(LOGO_FILE, 10, 8, 25)
                offset_x_title = 40
            except:
                offset_x_title = 10
        else:
            offset_x_title = 10

        self.set_font('Arial', 'B', 16)
        self.set_text_color(0) # Siempre negro en PDF
        self.set_xy(offset_x_title, 10) 
        self.cell(0, 10, 'TOYOTA LOS FUERTES', 0, 1, 'L')
        
        self.set_xy(offset_x_title, 18)
        self.set_font('Arial', '', 9)
        self.set_text_color(100)
        self.cell(0, 5, 'COTIZACION OFICIAL DE REFACCIONES', 0, 1, 'L')
        
        self.set_draw_color(235, 10, 30) # Rojo Toyota
        self.set_line_width(0.5)
        self.line(10, 30, 200, 30)
        self.ln(15)

    def footer(self):
        self.set_y(-30)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.multi_cell(0, 4, 'Precios en MXN. Incluyen IVA (16%). VIGENCIA: 24 HORAS. Descripciones bajo NOM-050-SCFI-2004.', 0, 'C')

def generar_pdf_bytes(carrito, subtotal, iva, total, cliente, vin, orden):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=30)
    
    fecha_mx = obtener_hora_mx().strftime("%d/%m/%Y %H:%M")
    
    # Datos Cliente
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(10, 35, 190, 28, 'F')
    
    pdf.set_xy(15, 38)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 6, 'CLIENTE:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(80, 6, cliente if cliente else "Mostrador", 0, 1)
    
    pdf.set_x(15)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 6, 'VIN:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(80, 6, vin if vin else "N/A", 0, 0)

    pdf.set_xy(120, 38)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 6, 'FECHA:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, 6, fecha_mx, 0, 1)

    pdf.set_xy(120, 44)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 6, 'ORDEN:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, 6, orden if orden else "S/N", 0, 1)

    pdf.ln(15)

    # Tabla PDF
    pdf.set_fill_color(50, 50, 50) 
    pdf.set_text_color(255)
    pdf.set_font('Arial', 'B', 8)
    
    # Anchos de columna
    w_sku = 30; w_desc = 60; w_cant = 10; w_base = 25; w_iva = 20; w_total = 25; w_estatus = 20

    pdf.cell(w_sku, 8, 'SKU', 0, 0, 'C', True)
    pdf.cell(w_desc, 8, 'DESCRIPCION', 0, 0, 'C', True)
    pdf.cell(w_cant, 8, 'CANT', 0, 0, 'C', True)
    pdf.cell(w_base, 8, 'P. UNIT', 0, 0, 'C', True)
    pdf.cell(w_iva, 8, 'IVA', 0, 0, 'C', True)
    pdf.cell(w_total, 8, 'TOTAL', 0, 0, 'C', True)
    pdf.cell(w_estatus, 8, 'ESTATUS', 0, 1, 'C', True)

    pdf.set_text_color(0)
    pdf.set_font('Arial', '', 7)
    
    for i, item in enumerate(carrito):
        fill = (i % 2 == 0)
        pdf.set_fill_color(248, 248, 248) if fill else pdf.set_fill_color(255, 255, 255)
        
        desc = item['Descripción'][:40]
        pdf.cell(w_sku, 7, item['SKU'], 0, 0, 'C', fill)
        pdf.cell(w_desc, 7, desc, 0, 0, 'L', fill)
        pdf.cell(w_cant, 7, str(int(item['Cantidad'])), 0, 0, 'C', fill)
        pdf.cell(w_base, 7, f"${item['Precio Base']:,.2f}", 0, 0, 'R', fill)
        pdf.cell(w_iva, 7, f"${item['IVA']:,.2f}", 0, 0, 'R', fill)
        pdf.cell(w_total, 7, f"${item['Importe Total']:,.2f}", 0, 0, 'R', fill)
        
        st_txt = item['Estatus']
        pdf.set_font('Arial', 'B', 7)
        if "Back Order" in st_txt: pdf.set_text_color(200, 0, 0)
        elif "No" in st_txt: pdf.set_text_color(100, 100, 100)
        else: pdf.set_text_color(0, 100, 0)
        pdf.cell(w_estatus, 7, st_txt, 0, 1, 'C', fill)
        pdf.set_text_color(0)
        pdf.set_font('Arial', '', 7)

    pdf.ln(5)
    pdf.set_font('Arial', '', 10)
    offset_x = 135
    pdf.cell(offset_x); pdf.cell(25, 6, 'Subtotal:', 0, 0, 'R'); pdf.cell(30, 6, f"${subtotal:,.2f}", 0, 1, 'R')
    pdf.cell(offset_x); pdf.cell(25, 6, 'IVA (16%):', 0, 0, 'R'); pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    pdf.set_font('Arial', 'B', 12); pdf.set_text_color(235, 10, 30)
    pdf.cell(offset_x); pdf.cell(25, 8, 'TOTAL:', 0, 0, 'R'); pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')

    pdf.ln(25); pdf.set_draw_color(0); pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.set_text_color(0); pdf.set_font('Arial', 'B', 8); pdf.cell(0, 5, 'Firma de Autorizacion / Asesor', 0, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')

# Traductor
@st.cache_data
def traducir_profe(texto):
    try:
        if pd.isna(texto) or texto == "": return "Sin descripción"
        return GoogleTranslator(source='en', target='es').translate(str(texto))
    except: return texto

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_catalogo():
    try:
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        c_sku = [c for c in df.columns if 'PART' in c or 'NUM' in c][0]
        c_desc = [c for c in df.columns if 'DESC' in c][0]
        c_precio = [c for c in df.columns if 'PRICE' in c or 'PRECIO' in c][0]
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        df['PRECIO_NUM'] = df[c_precio].astype(str).str.replace('$', '').str.replace(',', '').apply(lambda x: float(x) if x.replace('.', '', 1).isdigit() else 0.0)
        return df, c_sku, c_desc
    except: return None, None, None

df, col_sku_db, col_desc_db = cargar_catalogo()
fecha_actual_mx = obtener_hora_mx()
fecha_hoy_str = fecha_actual_mx.strftime("%d/%m/%Y"); hora_hoy_str = fecha_actual_mx.strftime("%H:%M")

def escanear_texto_profundo(texto_completo):
    datos = {}
    texto_upper = texto_completo.upper()
    match_vin = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', texto_upper)
    if match_vin: datos['VIN'] = match_vin.group(0)
    match_cliente = re.search(r'(?:CLIENTE|ATN|ATENCIÓN|ASESOR|NOMBRE)[:\.\-\s]+([A-Z\s\.]{4,40})', texto_upper)
    if match_cliente: datos['CLIENTE'] = match_cliente.group(1).strip()
    match_orden = re.search(r'(?:ORDEN|FOLIO|PEDIDO|COTIZACION)[:\.\-\s#]*([A-Z0-9\-]{4,12})', texto_upper)
    if match_orden: datos['ORDEN'] = match_orden.group(1).strip()
    else:
        posibles_nums = re.findall(r'\b\d{5,10}\b', texto_upper)
        if posibles_nums: datos['ORDEN'] = posibles_nums[0]
    return datos

def procesar_lista_sku(lista_skus):
    encontrados = 0; errores = []
    for item in lista_skus:
        sku_raw = str(item['sku']).upper().strip()
        sku_clean = sku_raw.replace('-', '')
        cant = int(item['cant'])
        match = df[df['SKU_CLEAN'] == sku_clean] if df is not None else pd.DataFrame()
        if not match.empty:
            row = match.iloc[0]
            st.session_state.carrito.append({
                "SKU": row[col_sku_db], "Descripción": traducir_profe(row[col_desc_db]), "Cantidad": cant,
                "Precio Base": row['PRECIO_NUM'], "IVA": (row['PRECIO_NUM'] * cant) * 0.16,
                "Importe Total": ((row['PRECIO_NUM'] * cant) * 1.16), "Estatus": "Disponible"
            })
            encontrados += 1
        else: errores.append(sku_raw)
    return encontrados, errores

# --- INTERFAZ ---

# Sidebar
with st.sidebar:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, use_column_width=True)
    else:
        st.write("🔧 Toyota Asesores")
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("Menú Asesor")
    modo = st.radio("Opción:", ["🔍 Cotizador Manual", "📂 Importador Masivo"])

# Encabezado (Logo + Título con manejo de error local)
col_header_1, col_header_2 = st.columns([1, 6])
with col_header_1:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=80)
    else:
        st.write("🔧")
with col_header_2:
    st.title("TOYOTA LOS FUERTES")
    st.markdown(f"<div style='opacity: 0.6; font-size: 14px; color: var(--text-color);'>Sistema Integral de Refacciones | {fecha_hoy_str} {hora_hoy_str}</div>", unsafe_allow_html=True)
st.divider()

# MODO MANUAL
if modo == "🔍 Cotizador Manual":
    st.markdown("### 📝 Datos de la Cotización")
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1: cliente_input = st.text_input("👤 Nombre del Cliente", placeholder="Ej. Juan Pérez")
    with col_d2: vin_input = st.text_input("🚗 VIN", max_chars=17)
    with col_d3: orden_input = st.text_input("📄 Orden", placeholder="Ej. OR-12345")
    
    st.write("---")
    sku_detectado = ""
    with st.expander("📸 Escáner (Cámara)", expanded=False):
        img_file = st.camera_input("Tomar Foto")
        if img_file:
            try:
                img = Image.open(img_file); d = decode(img)
                if d: sku_detectado = d[0].data.decode("utf-8")
                else:
                    res = cargar_lector_ocr().readtext(np.array(img))
                    poss = [txt for (_, txt, _) in res if len(txt)>4]
                    if poss: sku_detectado = poss[0]
            except: pass
    
    val_ini = sku_detectado if sku_detectado else ""
    busqueda = st.text_input("🔍 Buscar SKU:", value=val_ini)
    
    if busqueda and df is not None:
        b_clean = busqueda.upper().strip().replace('-', '')
        mask = df.apply(lambda x: x.astype(str).str.contains(busqueda, case=False)).any(axis=1) | df['SKU_CLEAN'].str.contains(b_clean, na=False)
        res = df[mask].head(10)
        
        if not res.empty:
            cols_h = st.columns([3, 1, 1, 1])
            cols_h[0].markdown("**Descripción**"); cols_h[1].markdown("**Cant.**"); cols_h[3].markdown("**Acción**")
            st.divider()
            for i, row in res.iterrows():
                sku_val = row[col_sku_db]; p_val = row['PRECIO_NUM']
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    with c1: st.markdown(f"**{traducir_profe(row[col_desc_db])}**"); st.caption(f"SKU: {sku_val} | Unit: ${p_val:,.2f}")
                    with c2: cant = st.number_input("C", 1, key=f"c_{i}", label_visibility="collapsed")
                    with c3: est = st.selectbox("E", ["Disponible", "Back Order"], key=f"s_{i}", label_visibility="collapsed")
                    with c4:
                        if st.button("➕", key=f"a_{i}"):
                            st.session_state.carrito.append({
                                "SKU": sku_val, "Descripción": traducir_profe(row[col_desc_db]), "Cantidad": cant,
                                "Precio Base": p_val, "IVA": (p_val*cant)*0.16, "Importe Total": (p_val*cant)*1.16, "Estatus": est
                            })
                            st.toast("Agregado"); st.rerun()
                    st.divider()
        else:
            st.warning("Producto no encontrado.")
            with st.expander("🛠️ Agregar Manual", expanded=True):
                with st.form("man_s"):
                    c_m1, c_m2, c_m3 = st.columns([2, 2, 1])
                    m_sku = c_m1.text_input("SKU", value=busqueda.upper())
                    m_desc = c_m2.text_input("Desc", value="Manual")
                    m_precio = c_m3.number_input("Precio", min_value=0.0)
                    if st.form_submit_button("Agregar"):
                        st.session_state.carrito.append({
                            "SKU": m_sku, "Descripción": m_desc, "Cantidad": 1, "Precio Base": m_precio,
                            "IVA": m_precio*0.16, "Importe Total": m_precio*1.16, "Estatus": "Disponible"
                        })
                        st.rerun()

# MODO MASIVO
elif modo == "📂 Importador Masivo":
    st.info("Carga inteligente activada.")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1: st.session_state.auto_cliente = st.text_input("Cliente", value=st.session_state.auto_cliente)
    with col_m2: st.session_state.auto_vin = st.text_input("VIN", value=st.session_state.auto_vin)
    with col_m3: st.session_state.auto_orden = st.text_input("Orden", value=st.session_state.auto_orden)

    if st.session_state.errores_carga:
        st.error(f"Faltantes: {', '.join(st.session_state.errores_carga)}")
        if st.button("Limpiar Errores"): st.session_state.errores_carga = []; st.rerun()

    t1, t2 = st.tabs(["Texto", "Excel"])
    with t1:
        txt = st.text_area("Lista SKUs:"); 
        if st.button("Procesar"): 
            lines = txt.split('\n'); lst = [{'sku': l, 'cant': 1} for l in lines if len(l.strip()) > 4]
            ok, fail = procesar_lista_sku(lst); st.session_state.errores_carga = fail
            if ok > 0: st.success(f"Agregados: {ok}"); st.rerun()

    with t2:
        upl = st.file_uploader("Excel", type=['xlsx'])
        if upl and st.button("Analizar"):
            try:
                d = pd.read_excel(upl); info = escanear_texto_profundo(d.to_string())
                if 'VIN' in info: st.session_state.auto_vin = info['VIN']
                if 'CLIENTE' in info: st.session_state.auto_cliente = info['CLIENTE']
                if 'ORDEN' in info: st.session_state.auto_orden = info['ORDEN']
                d.columns = [c.upper().strip() for c in d.columns]
                c_s = next((c for c in d.columns if 'SKU' in c or 'PART' in c), None)
                c_q = next((c for c in d.columns if 'CANT' in c or 'QTY' in c), None)
                if c_s:
                    l = [{'sku': r[c_s], 'cant': int(r[c_q]) if c_q and pd.notna(r[c_q]) else 1} for _, r in d.iterrows() if pd.notna(r[c_s])]
                    ok, fail = procesar_lista_sku(l); st.session_state.errores_carga = fail; st.rerun()
            except Exception as e: st.error(f"Error: {e}")

# CARRITO GLOBAL
if st.session_state.carrito:
    st.write("---")
    st.subheader(f"🛒 Detalle")
    
    # Columnas con IVA incluido
    cols = st.columns([1.5, 3, 0.8, 1.2, 1.2, 1.2, 0.5])
    cols[0].markdown("**SKU**")
    cols[1].markdown("**Descripción**")
    cols[2].markdown("**Cant.**")
    cols[3].markdown("**P. Unit**")
    cols[4].markdown("**IVA**")
    cols[5].markdown("**Total**")
    
    idx_borrar = None
    for i, item in enumerate(st.session_state.carrito):
        with st.container():
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 3, 0.8, 1.2, 1.2, 1.2, 0.5])
            c1.write(item['SKU'])
            c2.write(item['Descripción'])
            nueva_cant = c3.number_input("C", 1, value=int(item['Cantidad']), key=f"ec_{i}", label_visibility="collapsed")
            if nueva_cant != item['Cantidad']:
                item['Cantidad'] = nueva_cant
                item['IVA'] = (item['Precio Base'] * nueva_cant) * 0.16
                item['Importe Total'] = (item['Precio Base'] * nueva_cant) * 1.16
                st.rerun()
            
            c4.write(f"${item['Precio Base']:,.2f}")
            c5.write(f"${item['IVA']:,.2f}")
            c6.write(f"**${item['Importe Total']:,.2f}**")
            if c7.button("🗑️", key=f"del_{i}"): idx_borrar = i

    if idx_borrar is not None: st.session_state.carrito.pop(idx_borrar); st.rerun()
    st.divider()

    df_c = pd.DataFrame(st.session_state.carrito)
    sub = (df_c['Precio Base']*df_c['Cantidad']).sum()
    iva = df_c['IVA'].sum()
    tot = df_c['Importe Total'].sum()

    col_tot1, col_tot2, col_tot3 = st.columns(3)
    col_tot1.metric("Subtotal", f"${sub:,.2f}")
    col_tot2.metric("IVA (16%)", f"${iva:,.2f}")
    col_tot3.metric("TOTAL", f"${tot:,.2f}")
    
    c_pdf, c_del = st.columns([3, 1])
    with c_pdf:
        cli = st.session_state.auto_cliente if modo == "📂 Importador Masivo" else cliente_input
        vin = st.session_state.auto_vin if modo == "📂 Importador Masivo" else vin_input
        ord_n = st.session_state.auto_orden if modo == "📂 Importador Masivo" else orden_input
        
        pdf_bytes = generar_pdf_bytes(st.session_state.carrito, sub, iva, tot, cli, vin, ord_n)
        
        st.download_button(
            label="📄 Descargar Cotización PDF",
            data=pdf_bytes,
            file_name=f"Cotizacion_{ord_n if ord_n else 'SN'}.pdf",
            mime="application/pdf",
            type="primary"
        )
            
    with c_del:
        if st.button("Limpiar Todo"):
            st.session_state.carrito = []
            st.session_state.errores_carga = []
            st.rerun()

# FOOTER
st.markdown(f"""
    <div class="legal-footer">
        <strong>TOYOTA LOS FUERTES</strong> | Sistema de Cotización Local v5.0
    </div>
""", unsafe_allow_html=True)
