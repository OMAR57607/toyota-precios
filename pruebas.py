import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import urllib.parse
from datetime import datetime
from fpdf import FPDF
from PIL import Image
from pyzbar.pyzbar import decode
import pytz
import easyocr
import numpy as np
import re
import requests
import tempfile
import os

# --- URL DEL LOGO MODERNO (Alta Resolución) ---
LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Toyota_EU_2020_Logo.svg/1024px-Toyota_EU_2020_Logo.svg.png"

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

# 2. ESTILOS CSS (Mejorados con tipografía corporativa)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    h1 { color: #000000 !important; font-weight: 700; text-align: left; }
    .stButton button { width: 100%; border-radius: 4px; font-weight: bold; text-transform: uppercase; }
    
    /* Cajas de estado */
    .error-box { background-color: #fff0f0; padding: 15px; border-radius: 4px; border-left: 5px solid #eb0a1e; color: #333; }
    .success-box { background-color: #f0fff4; padding: 15px; border-radius: 4px; border-left: 5px solid #28a745; color: #155724; }
    
    /* Footer */
    .legal-footer { text-align: center; font-size: 10px; color: #666; margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- CLASE PDF ---
class PDF(FPDF):
    def header(self):
        # Intentar descargar el logo temporalmente para el PDF
        try:
            # Posición del Logo (x, y, ancho)
            self.image(LOGO_URL, 10, 8, 25) 
            offset_y_titulo = 0
        except:
            # Si falla la descarga, solo texto
            offset_y_titulo = 0
            pass

        self.set_font('Arial', 'B', 16)
        self.set_text_color(0) # Negro Corporativo
        # Ajustamos posición del titulo para que no choque con el logo
        self.set_xy(40, 10) 
        self.cell(0, 10, 'TOYOTA LOS FUERTES', 0, 1, 'L')
        
        self.set_xy(40, 18)
        self.set_font('Arial', '', 9)
        self.set_text_color(100)
        self.cell(0, 5, 'COTIZACION OFICIAL DE REFACCIONES', 0, 1, 'L')
        
        # Linea roja decorativa
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
    
    # Datos Cliente (Diseño limpio)
    pdf.set_fill_color(250, 250, 250)
    pdf.rect(10, 35, 190, 28, 'F')
    
    # Columna Izquierda
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

    # Columna Derecha (Datos de Control)
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

    # --- ENCABEZADOS DE TABLA (Negro/Gris Oscuro en lugar de rojo chillón) ---
    pdf.set_fill_color(50, 50, 50) 
    pdf.set_text_color(255)
    pdf.set_font('Arial', 'B', 8)
    
    w_sku = 30
    w_desc = 60
    w_cant = 10
    w_base = 25
    w_iva = 20
    w_total = 25
    w_estatus = 20

    pdf.cell(w_sku, 8, 'SKU', 0, 0, 'C', True)
    pdf.cell(w_desc, 8, 'DESCRIPCION', 0, 0, 'C', True)
    pdf.cell(w_cant, 8, 'CANT', 0, 0, 'C', True)
    pdf.cell(w_base, 8, 'P. UNIT', 0, 0, 'C', True)
    pdf.cell(w_iva, 8, 'IVA', 0, 0, 'C', True)
    pdf.cell(w_total, 8, 'TOTAL', 0, 0, 'C', True)
    pdf.cell(w_estatus, 8, 'ESTATUS', 0, 1, 'C', True)

    # --- CONTENIDO DE TABLA ---
    pdf.set_text_color(0)
    pdf.set_font('Arial', '', 7)
    
    for i, item in enumerate(carrito):
        fill = (i % 2 == 0) # Alternar color de filas
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
    
    # --- TOTALES ---
    pdf.set_font('Arial', '', 10)
    offset_x = 135
    pdf.cell(offset_x)
    pdf.cell(25, 6, 'Subtotal:', 0, 0, 'R')
    pdf.cell(30, 6, f"${subtotal:,.2f}", 0, 1, 'R')
    pdf.cell(offset_x)
    pdf.cell(25, 6, 'IVA (16%):', 0, 0, 'R')
    pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(235, 10, 30) # Rojo Toyota
    pdf.cell(offset_x)
    pdf.cell(25, 8, 'TOTAL:', 0, 0, 'R')
    pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')

    pdf.ln(25)
    pdf.set_draw_color(0)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.set_text_color(0)
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(0, 5, 'Firma de Autorizacion / Asesor', 0, 1, 'C')

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
    except Exception as e:
        # st.error(f"Error cargando datos: {e}") 
        # Comentado para que no ensucie la pantalla si no hay archivo, puedes descomentar
        return None, None, None

df, col_sku_db, col_desc_db = cargar_catalogo()
fecha_actual_mx = obtener_hora_mx()
fecha_hoy_str = fecha_actual_mx.strftime("%d/%m/%Y")
hora_hoy_str = fecha_actual_mx.strftime("%H:%M")

# --- FUNCIÓN: DETECTAR METADATOS (Scanner Profundo) ---
def escanear_texto_profundo(texto_completo):
    """ Busca VIN, Orden y Cliente en cualquier bloque de texto desordenado """
    datos = {}
    texto_upper = texto_completo.upper()
    
    # 1. VIN
    match_vin = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', texto_upper)
    if match_vin: datos['VIN'] = match_vin.group(0)

    # 2. CLIENTE
    match_cliente = re.search(r'(?:CLIENTE|ATN|ATENCIÓN|ASESOR|NOMBRE)[:\.\-\s]+([A-Z\s\.]{4,40})', texto_upper)
    if match_cliente: datos['CLIENTE'] = match_cliente.group(1).strip()
    
    # 3. ORDEN
    match_orden = re.search(r'(?:ORDEN|FOLIO|PEDIDO|COTIZACION)[:\.\-\s#]*([A-Z0-9\-]{4,12})', texto_upper)
    if match_orden:
        datos['ORDEN'] = match_orden.group(1).strip()
    else:
        posibles_nums = re.findall(r'\b\d{5,10}\b', texto_upper)
        if posibles_nums: datos['ORDEN'] = posibles_nums[0]

    return datos

# --- FUNCIÓN: PROCESAR LISTA ---
def procesar_lista_sku(lista_skus):
    encontrados = 0
    errores = []
    
    for item in lista_skus:
        sku_raw = str(item['sku']).upper().strip()
        sku_clean = sku_raw.replace('-', '')
        cant = int(item['cant'])
        
        match = df[df['SKU_CLEAN'] == sku_clean] if df is not None else pd.DataFrame()
        
        if not match.empty:
            row = match.iloc[0]
            desc = traducir_profe(row[col_desc_db])
            precio = row['PRECIO_NUM']
            monto_iva = (precio * cant) * 0.16
            monto_total = (precio * cant) + monto_iva
            
            st.session_state.carrito.append({
                "SKU": row[col_sku_db],
                "Descripción": desc,
                "Cantidad": cant,
                "Precio Base": precio,
                "IVA": monto_iva,
                "Importe Total": monto_total,
                "Estatus": "Disponible"
            })
            encontrados += 1
        else:
            errores.append(sku_raw)
            
    return encontrados, errores

# --- INTERFAZ PRINCIPAL ---

# Sidebar con Logo
with st.sidebar:
    st.image(LOGO_URL, use_column_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("Menú Asesor")
    modo = st.radio("Selecciona una opción:", ["🔍 Cotizador Manual", "📂 Importador Masivo"])

# Encabezado Principal (Logo pequeño + Titulo)
col_header_1, col_header_2 = st.columns([1, 6])
with col_header_1:
    st.image(LOGO_URL, width=80)
with col_header_2:
    st.title("TOYOTA LOS FUERTES")
    st.markdown(f"<div style='opacity: 0.6; font-size: 14px;'>Sistema Integral de Refacciones | {fecha_hoy_str} {hora_hoy_str}</div>", unsafe_allow_html=True)

st.divider()

# ==========================================
# MODO 1: COTIZADOR MANUAL
# ==========================================
if modo == "🔍 Cotizador Manual":
    st.markdown("### 📝 Datos de la Cotización")
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        cliente_input = st.text_input("👤 Nombre del Cliente", placeholder="Ej. Juan Pérez")
    with col_d2:
        vin_input = st.text_input("🚗 VIN (Número de Serie)", placeholder="17 Dígitos", max_chars=17)
    with col_d3:
        orden_input = st.text_input("📄 Número de Orden", placeholder="Ej. OR-12345")
    
    st.write("---")
    
    sku_detectado = ""
    with st.expander("📸 Escáner de Piezas (Cámara/Imagen)", expanded=False):
        img_file = st.camera_input("Tomar Foto")
        if img_file:
            try:
                img = Image.open(img_file)
                d = decode(img)
                if d: sku_detectado = d[0].data.decode("utf-8")
                else:
                    reader = cargar_lector_ocr()
                    res = reader.readtext(np.array(img))
                    possible = [txt for (_, txt, _) in res if len(txt)>4]
                    if possible: sku_detectado = possible[0]
            except: pass
    
    val_ini = sku_detectado if sku_detectado else ""
    busqueda = st.text_input("🔍 Buscar SKU o Nombre:", value=val_ini)
    
    if busqueda and df is not None:
        b_raw = busqueda.upper().strip()
        b_clean = b_raw.replace('-', '')
        mask = df.apply(lambda x: x.astype(str).str.contains(b_raw, case=False)).any(axis=1) | df['SKU_CLEAN'].str.contains(b_clean, na=False)
        res = df[mask].head(10)
        
        if not res.empty:
            cols_h = st.columns([3, 1, 1, 1])
            cols_h[0].markdown("**Descripción / SKU**")
            cols_h[1].markdown("**Cant.**")
            cols_h[2].markdown("**Estatus**") 
            cols_h[3].markdown("**Acción**")
            st.divider()

            for i, row in res.iterrows():
                desc_es = traducir_profe(row[col_desc_db])
                sku_val = row[col_sku_db]
                precio_val = row['PRECIO_NUM']

                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    with c1:
                        st.markdown(f"**{desc_es}**")
                        st.caption(f"SKU: {sku_val} | Unitario: ${precio_val:,.2f}")
                    with c2:
                        cant = st.number_input("Cant", 1, key=f"c_{i}", label_visibility="collapsed")
                    with c3:
                        est = st.selectbox("Estatus", ["Disponible", "No Disponible", "Back Order"], key=f"s_{i}", label_visibility="collapsed")
                    with c4:
                        if st.button("➕ Agregar", key=f"a_{i}"):
                            iva = (precio_val * cant) * 0.16
                            tot = (precio_val * cant) + iva
                            st.session_state.carrito.append({
                                "SKU": sku_val, "Descripción": desc_es, "Cantidad": cant,
                                "Precio Base": precio_val, "IVA": iva, "Importe Total": tot, "Estatus": est
                            })
                            st.toast("Agregado exitosamente")
                    st.divider()
        else:
            st.warning(f"⚠️ El producto **'{busqueda}'** no existe en el catálogo.")
            with st.expander("🛠️ ¿Deseas agregarlo manualmente?", expanded=True):
                with st.form(key="form_manual_single"):
                    c_m1, c_m2, c_m3 = st.columns([2, 2, 1])
                    m_sku = c_m1.text_input("SKU", value=busqueda.upper())
                    m_desc = c_m2.text_input("Descripción", value="Producto Manual")
                    m_precio = c_m3.number_input("Precio Base", min_value=0.0)
                    
                    if st.form_submit_button("Agregar al Carrito ✅"):
                        iva_m = m_precio * 0.16
                        tot_m = m_precio + iva_m
                        st.session_state.carrito.append({
                            "SKU": m_sku, "Descripción": m_desc, "Cantidad": 1,
                            "Precio Base": m_precio, "IVA": iva_m, "Importe Total": tot_m, "Estatus": "Disponible"
                        })
                        st.toast("✅ Agregado Manualmente")
                        st.rerun()

# ==========================================
# MODO 2: IMPORTADOR MASIVO
# ==========================================
elif modo == "📂 Importador Masivo":
    st.markdown("### ⚡ Carga Rápida de Órdenes")
    st.info("Sube tu archivo y detectaré automáticamente el Cliente, VIN y Orden.")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1: 
        val_cli = st.session_state.auto_cliente
        cliente_input = st.text_input("👤 Cliente", value=val_cli, key="in_cli_mas")
        st.session_state.auto_cliente = cliente_input

    with col_m2: 
        val_vin = st.session_state.auto_vin
        vin_input = st.text_input("🚗 VIN (17 Dígitos)", value=val_vin, max_chars=17, key="in_vin_mas")
        st.session_state.auto_vin = vin_input
        
    with col_m3: 
        val_ord = st.session_state.auto_orden
        orden_input = st.text_input("📄 Orden", value=val_ord, key="in_ord_mas")
        st.session_state.auto_orden = orden_input

    # MANEJO DE ERRORES MASIVOS
    if st.session_state.errores_carga:
        st.markdown(f"""<div class="error-box"><strong>⚠️ Faltantes ({len(st.session_state.errores_carga)}):</strong> {', '.join(st.session_state.errores_carga[:5])}...</div>""", unsafe_allow_html=True)
        with st.expander("🛠️ Cargar Faltantes Manualmente", expanded=True):
            with st.form("form_manual_masivo"):
                col_man1, col_man2, col_man3, col_man4 = st.columns([2, 3, 2, 1])
                sugerencia_sku = st.session_state.errores_carga[0] if st.session_state.errores_carga else ""
                m_sku = col_man1.text_input("SKU", value=sugerencia_sku)
                m_desc = col_man2.text_input("Descripción", value="Refacción Especial")
                m_precio = col_man3.number_input("Precio Base", min_value=0.0)
                m_cant = col_man4.number_input("Cant.", min_value=1, value=1)
                
                if st.form_submit_button("Agregar ✅"):
                    iva_m = (m_precio * m_cant) * 0.16
                    tot_m = (m_precio * m_cant) + iva_m
                    st.session_state.carrito.append({
                        "SKU": m_sku, "Descripción": m_desc, "Cantidad": m_cant,
                        "Precio Base": m_precio, "IVA": iva_m, "Importe Total": tot_m, "Estatus": "Disponible"
                    })
                    if m_sku in st.session_state.errores_carga: st.session_state.errores_carga.remove(m_sku)
                    st.rerun()
            if st.button("Ignorar Restantes"):
                st.session_state.errores_carga = []
                st.rerun()

    # TABS
    tab1, tab2, tab3 = st.tabs(["📋 Pegar Texto", "📊 Excel", "📷 Foto de Hoja"])
    
    with tab1:
        txt = st.text_area("Pega aquí los SKUs:", height=100)
        if st.button("Procesar Lista Texto"):
            lines = txt.split('\n')
            lst = [{'sku': l, 'cant': 1} for l in lines if len(l.strip()) > 4]
            ok, fail = procesar_lista_sku(lst)
            st.session_state.errores_carga = fail
            if ok > 0: st.success(f"✅ Agregados {ok}.")
            st.rerun()

    with tab2:
        upl = st.file_uploader("Arrastra tu Excel aquí", type=['xlsx'])
        if upl and st.button("Analizar Excel"):
            try:
                d = pd.read_excel(upl)
                
                texto_todo_excel = d.to_string()
                datos_intel = escanear_texto_profundo(texto_todo_excel)
                
                if 'VIN' in datos_intel: st.session_state.auto_vin = datos_intel['VIN']
                if 'CLIENTE' in datos_intel: st.session_state.auto_cliente = datos_intel['CLIENTE']
                if 'ORDEN' in datos_intel: st.session_state.auto_orden = datos_intel['ORDEN']
                
                d.columns = [c.upper().strip() for c in d.columns]
                col_sku = next((c for c in d.columns if 'SKU' in c or 'PART' in c or 'NUM' in c), None)
                col_cant = next((c for c in d.columns if 'CANT' in c or 'QTY' in c), None)
                
                if col_sku:
                    lst = [{'sku': r[col_sku], 'cant': int(r[col_cant]) if col_cant and pd.notna(r[col_cant]) else 1} for _, r in d.iterrows() if pd.notna(r[col_sku])]
                    ok, fail = procesar_lista_sku(lst)
                    st.session_state.errores_carga = fail
                    
                    msg_extra = ""
                    if datos_intel: msg_extra = f" | Datos detectados: {', '.join(datos_intel.keys())}"
                    st.success(f"✅ Importación exitosa: {ok} productos.{msg_extra}")
                    st.rerun()
                else:
                    st.error("No encontré columna de SKU.")
            except Exception as e: st.error(f"Error leyendo Excel: {e}")

    with tab3:
        cam = st.camera_input("Foto", key="cam_m")
        if cam:
            with st.spinner("Analizando Imagen y Buscando Datos..."):
                r = cargar_lector_ocr()
                raw_text_list = r.readtext(np.array(Image.open(cam)), detail=0)
                full_text = " ".join(raw_text_list)
                
                datos_intel = escanear_texto_profundo(full_text)
                
                if 'VIN' in datos_intel: st.session_state.auto_vin = datos_intel['VIN']
                if 'CLIENTE' in datos_intel: st.session_state.auto_cliente = datos_intel['CLIENTE']
                if 'ORDEN' in datos_intel: st.session_state.auto_orden = datos_intel['ORDEN']
                
                lst = []
                for t in raw_text_list:
                    t = t.upper().replace(' ', '')
                    if re.search(r'[A-Z0-9]{5}-?[A-Z0-9]{5}', t): lst.append({'sku': t, 'cant': 1})
                
                if lst:
                    if st.button("Agregar Detectados"):
                        ok, fail = procesar_lista_sku(lst)
                        st.session_state.errores_carga = fail
                        st.success(f"✅ Agregados {ok}.")
                        st.rerun()
                else:
                    st.warning("No detecté SKUs claros, pero revisé los datos de encabezado.")

# ==========================================
# CARRITO GLOBAL
# ==========================================
if st.session_state.carrito:
    st.write("---")
    st.subheader(f"🛒 Detalle de Cotización")
    
    # Encabezados de tabla visual
    cols = st.columns([1.5, 3, 1, 1.5, 1.5, 0.5])
    cols[0].markdown("**SKU**")
    cols[1].markdown("**Descripción**")
    cols[2].markdown("**Cant.**")
    cols[3].markdown("**P. Unit**")
    cols[4].markdown("**Total**")
    
    idx_borrar = None
    for i, item in enumerate(st.session_state.carrito):
        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([1.5, 3, 1, 1.5, 1.5, 0.5])
            c1.write(item['SKU'])
            c2.write(item['Descripción'])
            
            # Input de cantidad interactivo
            nueva_cant = c3.number_input("C", min_value=1, value=int(item['Cantidad']), key=f"ec_{i}", label_visibility="collapsed")
            if nueva_cant != item['Cantidad']:
                item['Cantidad'] = nueva_cant
                item['IVA'] = (item['Precio Base'] * nueva_cant) * 0.16
                item['Importe Total'] = (item['Precio Base'] * nueva_cant) + item['IVA']
                st.rerun()
                
            c4.write(f"${item['Precio Base']:,.2f}")
            c5.write(f"**${item['Importe Total']:,.2f}**")
            if c6.button("🗑️", key=f"del_{i}"): idx_borrar = i

    if idx_borrar is not None:
        st.session_state.carrito.pop(idx_borrar)
        st.rerun()

    st.divider()

    df_c = pd.DataFrame(st.session_state.carrito)
    sub = (df_c['Precio Base']*df_c['Cantidad']).sum()
    iva = df_c['IVA'].sum()
    tot = df_c['Importe Total'].sum()

    # Resumen financiero
    with st.container():
        c_tot1, c_tot2, c_tot3 = st.columns(3)
        c_tot1.metric("Subtotal", f"${sub:,.2f}")
        c_tot2.metric("IVA (16%)", f"${iva:,.2f}")
        c_tot3.metric("GRAN TOTAL", f"${tot:,.2f}", delta="MXN")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botones de acción
    c_pdf, c_del = st.columns([3, 1])
    with c_pdf:
        cli = st.session_state.auto_cliente if modo == "📂 Importador Masivo" else cliente_input
        vin = st.session_state.auto_vin if modo == "📂 Importador Masivo" else vin_input
        ord_n = st.session_state.auto_orden if modo == "📂 Importador Masivo" else orden_input
        
        # Generar PDF
        if st.button("📄 Generar Cotización Oficial PDF", type="primary"):
            pdf_bytes = generar_pdf_bytes(st.session_state.carrito, sub, iva, tot, cli, vin, ord_n)
            st.download_button("⬇️ Descargar Archivo", pdf_bytes, f"Cotizacion_{ord_n if ord_n else 'S/N'}.pdf", "application/pdf")
            
    with c_del:
        if st.button("Limpiar Todo"):
            st.session_state.carrito = []
            st.session_state.errores_carga = []
            st.session_state.auto_cliente = ""
            st.session_state.auto_vin = ""
            st.session_state.auto_orden = ""
            st.rerun()

# FOOTER
st.markdown(f"""
    <div class="legal-footer">
        <img src="{LOGO_URL}" width="30" style="vertical-align: middle; margin-right: 10px;">
        <strong>TOYOTA LOS FUERTES</strong> | Sistema de Cotización Inteligente v3.0<br>
        Desarrollado para uso interno.
    </div>
""", unsafe_allow_html=True)
