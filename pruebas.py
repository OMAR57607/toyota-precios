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

# --- CONFIGURACIÓN INICIAL ---
LOGO_FILE = "logo.png"  # Asegúrate de que este archivo esté en la misma carpeta

st.set_page_config(page_title="Toyota Asesores", page_icon="🔧", layout="wide")

# --- FUNCIONES DE SOPORTE ---
def obtener_hora_mx():
    try:
        tz = pytz.timezone('America/Mexico_City')
        return datetime.now(tz)
    except:
        return datetime.now()

@st.cache_resource
def cargar_lector_ocr():
    return easyocr.Reader(['en'], gpu=False)

@st.cache_data
def traducir_profe(texto):
    try:
        if pd.isna(texto) or texto == "": return "Sin descripción"
        return GoogleTranslator(source='en', target='es').translate(str(texto))
    except: return texto

# --- VARIABLES DE SESIÓN ---
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'errores_carga' not in st.session_state: st.session_state.errores_carga = []
if 'auto_cliente' not in st.session_state: st.session_state.auto_cliente = ""
if 'auto_vin' not in st.session_state: st.session_state.auto_vin = ""
if 'auto_orden' not in st.session_state: st.session_state.auto_orden = ""

# --- ESTILOS CSS CORREGIDOS (VISIBILIDAD GARANTIZADA) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    
    /* TÍTULO PRINCIPAL: Forzamos color para que se vea en fondo oscuro */
    h1 {
        color: #eb0a1e !important; /* Rojo Toyota siempre visible */
        font-weight: 800 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
    }
    
    /* Subtítulos y textos */
    h2, h3 { color: var(--text-color) !important; }
    .stMarkdown div { color: var(--text-color); }
    
    /* Botones */
    .stButton button { 
        width: 100%; 
        border-radius: 4px; 
        font-weight: bold; 
        text-transform: uppercase; 
    }
    
    /* Footer */
    .legal-footer { 
        text-align: center; font-size: 11px; color: var(--text-color); opacity: 0.6;
        margin-top: 50px; padding-top: 20px; border-top: 1px solid rgba(128, 128, 128, 0.2); 
    }
    </style>
    """, unsafe_allow_html=True)

# --- CLASE PDF ---
class PDF(FPDF):
    def header(self):
        # Logo local en el PDF
        if os.path.exists(LOGO_FILE):
            try:
                self.image(LOGO_FILE, 10, 8, 25)
                offset_x_title = 40
            except:
                offset_x_title = 10
        else:
            offset_x_title = 10

        self.set_font('Arial', 'B', 16)
        self.set_text_color(0) # Negro
        self.set_xy(offset_x_title, 10) 
        self.cell(0, 10, 'TOYOTA LOS FUERTES', 0, 1, 'L')
        
        self.set_xy(offset_x_title, 18)
        self.set_font('Arial', '', 9)
        self.set_text_color(100)
        self.cell(0, 5, 'COTIZACION OFICIAL DE REFACCIONES', 0, 1, 'L')
        
        self.set_draw_color(235, 10, 30)
        self.set_line_width(0.5)
        self.line(10, 30, 200, 30)
        self.ln(15)

    def footer(self):
        self.set_y(-30)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.multi_cell(0, 4, 'Precios en MXN. Incluyen IVA (16%). VIGENCIA: 24 HORAS.', 0, 'C')

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

    # Tabla
    pdf.set_fill_color(50, 50, 50); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 8)
    w_sku = 30; w_desc = 60; w_cant = 10; w_base = 25; w_iva = 20; w_total = 25; w_estatus = 20
    pdf.cell(w_sku, 8, 'SKU', 0, 0, 'C', True); pdf.cell(w_desc, 8, 'DESCRIPCION', 0, 0, 'C', True)
    pdf.cell(w_cant, 8, 'CANT', 0, 0, 'C', True); pdf.cell(w_base, 8, 'P. UNIT', 0, 0, 'C', True)
    pdf.cell(w_iva, 8, 'IVA', 0, 0, 'C', True); pdf.cell(w_total, 8, 'TOTAL', 0, 0, 'C', True)
    pdf.cell(w_estatus, 8, 'ESTATUS', 0, 1, 'C', True)

    pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    for i, item in enumerate(carrito):
        fill = (i % 2 == 0)
        pdf.set_fill_color(248, 248, 248) if fill else pdf.set_fill_color(255, 255, 255)
        desc = item['Descripción'][:40]
        pdf.cell(w_sku, 7, item['SKU'], 0, 0, 'C', fill); pdf.cell(w_desc, 7, desc, 0, 0, 'L', fill)
        pdf.cell(w_cant, 7, str(int(item['Cantidad'])), 0, 0, 'C', fill)
        pdf.cell(w_base, 7, f"${item['Precio Base']:,.2f}", 0, 0, 'R', fill)
        pdf.cell(w_iva, 7, f"${item['IVA']:,.2f}", 0, 0, 'R', fill)
        pdf.cell(w_total, 7, f"${item['Importe Total']:,.2f}", 0, 0, 'R', fill)
        st_txt = item['Estatus']
        if "Back Order" in st_txt: pdf.set_text_color(200, 0, 0)
        else: pdf.set_text_color(0, 100, 0)
        pdf.cell(w_estatus, 7, st_txt, 0, 1, 'C', fill)
        pdf.set_text_color(0)

    pdf.ln(5); pdf.set_font('Arial', '', 10)
    offset_x = 135
    pdf.cell(offset_x); pdf.cell(25, 6, 'Subtotal:', 0, 0, 'R'); pdf.cell(30, 6, f"${subtotal:,.2f}", 0, 1, 'R')
    pdf.cell(offset_x); pdf.cell(25, 6, 'IVA (16%):', 0, 0, 'R'); pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    pdf.set_font('Arial', 'B', 12); pdf.set_text_color(235, 10, 30)
    pdf.cell(offset_x); pdf.cell(25, 8, 'TOTAL:', 0, 0, 'R'); pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')
    
    pdf.ln(25); pdf.set_draw_color(0); pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.set_text_color(0); pdf.set_font('Arial', 'B', 8); pdf.cell(0, 5, 'Firma de Autorizacion', 0, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')

# --- LOGICA DE CARGA DE DATOS ---
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

# --- INTERFAZ SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, use_column_width=True)
    else:
        st.header("TOYOTA")
    st.markdown("---")
    modo = st.radio("Modo:", ["🔍 Cotizador Manual", "📂 Importador Masivo"])

# --- HEADER PRINCIPAL ---
col_h1, col_h2 = st.columns([1, 6])
with col_h1:
    if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=90)
with col_h2:
    st.title("TOYOTA LOS FUERTES")
    st.caption(f"Sistema Integral de Refacciones | {obtener_hora_mx().strftime('%d/%m/%Y %H:%M')}")
st.divider()

# --- LÓGICA DE APLICACIÓN ---
def agregar_item(sku, desc, precio, cant, estatus="Disponible"):
    st.session_state.carrito.append({
        "SKU": sku, "Descripción": desc, "Cantidad": cant,
        "Precio Base": precio, "IVA": (precio * cant) * 0.16,
        "Importe Total": (precio * cant) * 1.16, "Estatus": estatus
    })

if modo == "🔍 Cotizador Manual":
    c1, c2, c3 = st.columns(3)
    with c1: cliente_input = st.text_input("Cliente", placeholder="Nombre")
    with c2: vin_input = st.text_input("VIN", max_chars=17)
    with c3: orden_input = st.text_input("Orden", placeholder="Folio")
    
    st.markdown("### 🔎 Búsqueda")
    sku_busqueda = st.text_input("Ingresa SKU o Nombre:", key="search_box")

    if sku_busqueda and df is not None:
        b_clean = sku_busqueda.upper().strip().replace('-', '')
        mask = df.apply(lambda x: x.astype(str).str.contains(sku_busqueda, case=False)).any(axis=1) | df['SKU_CLEAN'].str.contains(b_clean, na=False)
        res = df[mask].head(5)
        
        if not res.empty:
            st.info(f"Encontrados: {len(res)}")
            for i, row in res.iterrows():
                with st.container():
                    col_res1, col_res2, col_res3 = st.columns([4, 1, 1])
                    desc_es = traducir_profe(row[col_desc_db])
                    col_res1.markdown(f"**{desc_es}**\nSKU: `{row[col_sku_db]}` | ${row['PRECIO_NUM']:,.2f}")
                    cant = col_res2.number_input("Cant", 1, key=f"q_{i}", label_visibility="collapsed")
                    if col_res3.button("Agregar", key=f"add_{i}"):
                        agregar_item(row[col_sku_db], desc_es, row['PRECIO_NUM'], cant)
                        st.toast("✅ Agregado")
                        st.rerun()
                    st.divider()
        else:
            st.warning("No encontrado.")
            with st.expander("Crear Manualmente"):
                m_sku = st.text_input("SKU Manual")
                m_desc = st.text_input("Descripción")
                m_price = st.number_input("Precio", 0.0)
                if st.button("Agregar Manual"):
                    agregar_item(m_sku, m_desc, m_price, 1)
                    st.rerun()

elif modo == "📂 Importador Masivo":
    c1, c2, c3 = st.columns(3)
    st.session_state.auto_cliente = c1.text_input("Cliente", st.session_state.auto_cliente)
    st.session_state.auto_vin = c2.text_input("VIN", st.session_state.auto_vin)
    st.session_state.auto_orden = c3.text_input("Orden", st.session_state.auto_orden)
    
    txt_blob = st.text_area("Pega lista de SKUs:")
    if st.button("Procesar Lista"):
        lines = [l.strip() for l in txt_blob.split('\n') if len(l.strip()) > 3]
        for l in lines:
            clean = l.upper().replace('-', '')
            match = df[df['SKU_CLEAN'] == clean]
            if not match.empty:
                r = match.iloc[0]
                agregar_item(r[col_sku_db], traducir_profe(r[col_desc_db]), r['PRECIO_NUM'], 1)
            else:
                st.session_state.errores_carga.append(l)
        st.rerun()
        
    if st.session_state.errores_carga:
        st.error(f"No encontrados: {st.session_state.errores_carga}")
        if st.button("Borrar Errores"):
            st.session_state.errores_carga = []
            st.rerun()

# --- CARRITO Y TOTALES (SECCIÓN LIMPIA) ---
if st.session_state.carrito:
    st.write("---")
    st.subheader("🛒 Detalle de Cotización")
    
    # Encabezados Tabla
    h1, h2, h3, h4, h5, h6, h7 = st.columns([1.5, 3, 0.8, 1.2, 1.2, 1.2, 0.5])
    h1.write("**SKU**"); h2.write("**Descripción**"); h3.write("**Cant**")
    h4.write("**Unitario**"); h5.write("**IVA**"); h6.write("**Total**")

    idx_del = None
    for i, item in enumerate(st.session_state.carrito):
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 3, 0.8, 1.2, 1.2, 1.2, 0.5])
        c1.write(item['SKU'])
        c2.write(item['Descripción'])
        
        # Lógica de actualización de cantidad
        new_q = c3.number_input("##", 1, value=int(item['Cantidad']), key=f"c_edit_{i}", label_visibility="collapsed")
        if new_q != item['Cantidad']:
            item['Cantidad'] = new_q
            item['IVA'] = (item['Precio Base'] * new_q) * 0.16
            item['Importe Total'] = (item['Precio Base'] * new_q) * 1.16
            st.rerun()

        c4.write(f"${item['Precio Base']:,.2f}")
        c5.write(f"${item['IVA']:,.2f}")
        c6.write(f"**${item['Importe Total']:,.2f}**")
        if c7.button("❌", key=f"del_btn_{i}"): idx_del = i
    
    if idx_del is not None:
        st.session_state.carrito.pop(idx_del)
        st.rerun()

    st.divider()

    # Totales
    df_c = pd.DataFrame(st.session_state.carrito)
    t_sub = (df_c['Precio Base'] * df_c['Cantidad']).sum()
    t_iva = df_c['IVA'].sum()
    t_tot = df_c['Importe Total'].sum()

    k1, k2, k3 = st.columns(3)
    k1.metric("Subtotal", f"${t_sub:,.2f}")
    k2.metric("IVA (16%)", f"${t_iva:,.2f}")
    k3.metric("TOTAL NETO", f"${t_tot:,.2f}")

    # --- ZONA DE DESCARGA (SIN NONE) ---
    st.markdown("---")
    col_d_1, col_d_2 = st.columns([3, 1])
    
    with col_d_1:
        # Variables finales
        cli_f = st.session_state.auto_cliente if modo == "📂 Importador Masivo" else cliente_input
        vin_f = st.session_state.auto_vin if modo == "📂 Importador Masivo" else vin_input
        ord_f = st.session_state.auto_orden if modo == "📂 Importador Masivo" else orden_input
        
        # Generar PDF
        pdf_data = generar_pdf_bytes(st.session_state.carrito, t_sub, t_iva, t_tot, cli_f, vin_f, ord_f)
        
        # BOTÓN ÚNICO
        st.download_button(
            label="📄 DESCARGAR PDF OFICIAL",
            data=pdf_data,
            file_name=f"Cotizacion_{ord_f if ord_f else 'Toyota'}.pdf",
            mime="application/pdf",
            type="primary"
        )

    with col_d_2:
        if st.button("🗑️ Limpiar Todo"):
            st.session_state.carrito = []
            st.session_state.errores_carga = []
            st.rerun()

# --- FOOTER ---
st.markdown("""
    <div class="legal-footer">
        <strong>TOYOTA LOS FUERTES</strong> | Sistema de Cotización v6.0 (Stable)
    </div>
""", unsafe_allow_html=True)
