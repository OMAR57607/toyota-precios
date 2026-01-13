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
import os

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(page_title="Toyota Asesores Pro", page_icon="🔧", layout="wide")

# Configurar Zona Horaria CDMX
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    tz_cdmx = None 

def obtener_hora_mx():
    if tz_cdmx: return datetime.now(tz_cdmx)
    return datetime.now()

# Inicializar variables de sesión
if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'errores_carga' not in st.session_state: st.session_state.errores_carga = [] 
    
# Variables para autocompletado (VIN, Cliente, Orden)
if 'auto_cliente' not in st.session_state: st.session_state.auto_cliente = ""
if 'auto_vin' not in st.session_state: st.session_state.auto_vin = ""
if 'auto_orden' not in st.session_state: st.session_state.auto_orden = ""

@st.cache_resource
def cargar_lector_ocr():
    # Carga el modelo en memoria una sola vez
    return easyocr.Reader(['en', 'es'], gpu=False) 

# Estilos CSS
st.markdown("""
    <style>
    h1 { color: #eb0a1e !important; text-align: center; }
    .stButton button { width: 100%; border-radius: 5px; font-weight: bold; }
    .metric-box { border: 1px solid #ddd; padding: 10px; border-radius: 5px; text-align: center; }
    .legal-footer { text-align: center; font-size: 10px; opacity: 0.6; margin-top: 40px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CLASE PDF (Con Logo y Formato)
# ==========================================
class PDF(FPDF):
    def header(self):
        # LOGO INTELIGENTE
        if os.path.exists("logo.png"):
            try:
                self.image("logo.png", 10, 8, 33)
            except: pass
        
        self.set_font('Arial', 'B', 16)
        self.set_text_color(235, 10, 30) # Rojo Toyota
        self.cell(0, 10, 'TOYOTA LOS FUERTES', 0, 1, 'C')
        
        self.set_font('Arial', '', 10)
        self.set_text_color(0)
        self.cell(0, 5, 'PRESUPUESTO DE REFACCIONES Y SERVICIOS', 0, 1, 'C')
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
    
    # Limpieza de "None" para el PDF
    orden_safe = str(orden) if orden and orden != "None" else "S/N"
    cliente_safe = str(cliente) if cliente and cliente != "None" else "Mostrador"
    vin_safe = str(vin) if vin and vin != "None" else "N/A"
    
    # Bloque de Datos del Cliente
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(10, 35, 190, 25, 'F')
    pdf.set_xy(12, 38)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 6, 'Fecha:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 6, fecha_mx, 0, 0)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 6, 'Orden:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 6, orden_safe, 0, 1)
    
    pdf.set_x(12)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 6, 'Cliente:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(100, 6, cliente_safe, 0, 1)

    pdf.set_x(12)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 6, 'VIN:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(100, 6, vin_safe, 0, 1)
    pdf.ln(10)

    # Tabla de Productos
    pdf.set_fill_color(235, 10, 30)
    pdf.set_text_color(255)
    pdf.set_font('Arial', 'B', 8)
    
    # Anchos de columna
    w = [30, 60, 12, 25, 20, 25, 18] # SKU, Desc, Cant, Unit, IVA, Total, Estatus
    headers = ['SKU', 'Descripción', 'Cant.', 'P. Base', 'IVA', 'Total', 'Estatus']
    
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, h, 1, 0, 'C', True)
    pdf.ln()

    pdf.set_text_color(0)
    pdf.set_font('Arial', '', 7)
    
    for item in carrito:
        desc = item['Descripción'][:38] # Truncar si es muy largo
        pdf.cell(w[0], 8, item['SKU'], 1, 0, 'C')
        pdf.cell(w[1], 8, desc, 1, 0, 'L')
        pdf.cell(w[2], 8, str(int(item['Cantidad'])), 1, 0, 'C')
        pdf.cell(w[3], 8, f"${item['Precio Base']:,.2f}", 1, 0, 'R')
        pdf.cell(w[4], 8, f"${item['IVA']:,.2f}", 1, 0, 'R')
        pdf.cell(w[5], 8, f"${item['Importe Total']:,.2f}", 1, 0, 'R')
        
        st_txt = item['Estatus']
        if "Back Order" in st_txt: pdf.set_text_color(200, 0, 0)
        else: pdf.set_text_color(0)
        
        pdf.cell(w[6], 8, st_txt, 1, 1, 'C')
        pdf.set_text_color(0)

    pdf.ln(5)
    
    # Totales
    pdf.set_font('Arial', '', 10)
    offset_x = 130
    
    pdf.cell(offset_x)
    pdf.cell(30, 6, 'Subtotal:', 0, 0, 'R')
    pdf.cell(30, 6, f"${subtotal:,.2f}", 0, 1, 'R')
    
    pdf.cell(offset_x)
    pdf.cell(30, 6, 'IVA (16%):', 0, 0, 'R')
    pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(235, 10, 30)
    pdf.cell(offset_x)
    pdf.cell(30, 8, 'TOTAL:', 0, 0, 'R')
    pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. LÓGICA DE DATOS Y BÚSQUEDA
# ==========================================

@st.cache_data
def traducir_profe(texto):
    try:
        if pd.isna(texto) or str(texto).strip() == "": return "Sin descripción"
        return GoogleTranslator(source='en', target='es').translate(str(texto))
    except: return str(texto)

@st.cache_data
def cargar_catalogo():
    if not os.path.exists("lista_precios.zip"): return None, None, None
    try:
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        
        # Detectar columnas clave dinámicamente
        c_sku = next((c for c in df.columns if 'PART' in c or 'NUM' in c), None)
        c_desc = next((c for c in df.columns if 'DESC' in c), None)
        c_precio = next((c for c in df.columns if 'PRICE' in c or 'PRECIO' in c), None)
        
        if not c_sku or not c_precio: return None, None, None
        
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        
        # Limpieza robusta de precio
        def clean_price(x):
            try:
                s = str(x).replace('$', '').replace(',', '').strip()
                return float(s)
            except: return 0.0
            
        df['PRECIO_NUM'] = df[c_precio].apply(clean_price)
        return df, c_sku, c_desc
    except: return None, None, None

df, col_sku_db, col_desc_db = cargar_catalogo()

def buscar_metadatos(texto_completo):
    """ Busca VIN, Orden y Cliente en texto crudo (OCR o Excel) """
    datos = {}
    texto_upper = str(texto_completo).upper()
    
    # VIN: 17 caracteres (evitando I, O, Q típicamente, pero siendo flexible)
    match_vin = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', texto_upper)
    if match_vin: datos['VIN'] = match_vin.group(0)

    # ORDEN: Formatos típicos "Orden: 12345", "Folio 12345" o solo números de 5-6 dígitos aislados
    match_orden = re.search(r'(?:ORDEN|FOLIO|PEDIDO|REF)[\.\:\s#]*([A-Z0-9\-]{4,10})', texto_upper)
    if match_orden: 
        datos['ORDEN'] = match_orden.group(1).strip()
    else:
        # Intento de encontrar números de orden aislados si no hay etiqueta
        nums = re.findall(r'\b\d{5,6}\b', texto_upper)
        if nums: datos['ORDEN'] = nums[0] # Tomar el primer número de 5-6 cifras

    # CLIENTE: Busca etiquetas comunes
    match_cliente = re.search(r'(?:CLIENTE|NOMBRE|ASEGURADORA)[:\.\-\s]+([A-Z\s\.]{4,40})', texto_upper)
    if match_cliente: datos['CLIENTE'] = match_cliente.group(1).strip()
    
    return datos

def procesar_sku_logic(lista_items):
    """ Busca los SKUs en la BD y calcula precios """
    if df is None: return 0, [x['sku'] for x in lista_items]
    
    exitos = 0
    fallos = []
    
    for item in lista_items:
        raw = str(item['sku']).upper().strip()
        clean = raw.replace('-', '')
        cant = int(item['cant'])
        
        match = df[df['SKU_CLEAN'] == clean]
        if not match.empty:
            row = match.iloc[0]
            desc = traducir_profe(row[col_desc_db]) if col_desc_db else "Refacción Original"
            precio = row['PRECIO_NUM']
            iva = (precio * cant) * 0.16
            total = (precio * cant) + iva
            
            st.session_state.carrito.append({
                "SKU": row[col_sku_db],
                "Descripción": desc,
                "Cantidad": cant,
                "Precio Base": precio,
                "IVA": iva,
                "Importe Total": total,
                "Estatus": "Disponible"
            })
            exitos += 1
        else:
            fallos.append(raw)
    return exitos, fallos

# ==========================================
# 4. INTERFAZ DE USUARIO (FRONTEND)
# ==========================================

# Sidebar
st.sidebar.title("Asesor Toyota")
if os.path.exists("logo.png"): st.sidebar.image("logo.png", use_container_width=True)
modo = st.sidebar.radio("Modo de Trabajo:", ["🔍 Cotizador Manual / Escáner", "📂 Carga Masiva (Excel)"])

# Título Principal
st.title("TOYOTA LOS FUERTES")
fecha_str = obtener_hora_mx().strftime("%d/%m/%Y %H:%M")
st.markdown(f"<div style='text-align: right; color: gray;'>{fecha_str}</div>", unsafe_allow_html=True)

if df is None:
    st.error("⚠️ Base de datos no encontrada. Carga 'lista_precios.zip'.")

# ---------------------------------------------------------
# BLOQUE 1: DATOS DEL ENCABEZADO (Común para ambos modos)
# ---------------------------------------------------------
with st.container():
    st.markdown("#### 📋 Datos de la Orden de Trabajo")
    
    # Botón Especial para Escanear la "Hoja Viajera" (Header)
    with st.expander("📷 Escanear Encabezado (Código de Barras / QR / Texto)", expanded=False):
        cam_header = st.camera_input("Escanear Orden/VIN", key="cam_header")
        if cam_header:
            img = Image.open(cam_header)
            detectados = {}
            
            # 1. Intentar Barcode (pyzbar) - Es lo más rápido y preciso para órdenes
            codigos = decode(img)
            for codigo in codigos:
                txt_code = codigo.data.decode("utf-8")
                detectados.update(buscar_metadatos(txt_code))
                # A veces el código de barras es directo el VIN o la Orden
                if len(txt_code) == 17: detectados['VIN'] = txt_code
                if len(txt_code) in [5, 6] and txt_code.isdigit(): detectados['ORDEN'] = txt_code
            
            # 2. Si no hay barcode, usar OCR (easyocr)
            if not detectados:
                reader = cargar_lector_ocr()
                res = reader.readtext(np.array(img), detail=0)
                full_text = " ".join(res)
                detectados = buscar_metadatos(full_text)
            
            # Actualizar campos
            if detectados:
                if 'VIN' in detectados: st.session_state.auto_vin = detectados['VIN']
                if 'ORDEN' in detectados: st.session_state.auto_orden = detectados['ORDEN']
                if 'CLIENTE' in detectados: st.session_state.auto_cliente = detectados['CLIENTE']
                st.success(f"Datos detectados: {detectados}")
                st.rerun()
            else:
                st.warning("No se detectaron datos legibles.")

    # Campos de Texto (Se llenan manual o auto)
    c1, c2, c3 = st.columns(3)
    val_cli = st.text_input("Cliente", value=st.session_state.auto_cliente, key="in_cli")
    val_vin = st.text_input("VIN", value=st.session_state.auto_vin, max_chars=17, key="in_vin")
    val_ord = st.text_input("No. Orden", value=st.session_state.auto_orden, key="in_ord")
    
    # Sincronizar session state
    st.session_state.auto_cliente = val_cli
    st.session_state.auto_vin = val_vin
    st.session_state.auto_orden = val_ord

st.write("---")

# ---------------------------------------------------------
# BLOQUE 2: LÓGICA SEGÚN MODO
# ---------------------------------------------------------

if modo == "🔍 Cotizador Manual / Escáner":
    
    # Buscador Manual
    busqueda = st.text_input("🔍 Buscar SKU o Descripción:", placeholder="Escribe para buscar...")
    
    if busqueda and df is not None:
        b_raw = busqueda.upper().strip()
        b_clean = b_raw.replace('-', '')
        
        # Filtro
        mask = df.apply(lambda x: x.astype(str).str.contains(b_raw, case=False)).any(axis=1) | \
               df['SKU_CLEAN'].str.contains(b_clean, na=False)
        res = df[mask].head(8)
        
        if not res.empty:
            # Encabezados visuales
            hc1, hc2, hc3, hc4 = st.columns([3, 1, 1, 1])
            hc1.markdown("**Refacción**")
            hc2.markdown("**Cant**")
            hc3.markdown("**Estatus**")
            hc4.markdown("**Acción**")
            st.divider()
            
            for i, row in res.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    desc = traducir_profe(row[col_desc_db])
                    sku = row[col_sku_db]
                    precio = row['PRECIO_NUM']
                    
                    with col1:
                        st.markdown(f"**{desc}**")
                        st.caption(f"{sku} | Unit: ${precio:,.2f}")
                    
                    cant = col2.number_input("C", 1, key=f"n_{i}", label_visibility="collapsed")
                    est = col3.selectbox("S", ["Disponible", "Back Order", "No Disp."], key=f"s_{i}", label_visibility="collapsed")
                    
                    if col4.button("➕", key=f"b_{i}"):
                        iva_u = (precio * cant) * 0.16
                        tot_u = (precio * cant) + iva_u
                        st.session_state.carrito.append({
                            "SKU": sku, "Descripción": desc, "Cantidad": cant,
                            "Precio Base": precio, "IVA": iva_u, "Importe Total": tot_u, "Estatus": est
                        })
                        st.toast("Agregado al carrito")
                    st.divider()
        else:
            st.warning("Producto no encontrado.")
            # Agregar Manual
            with st.expander("🛠️ Agregar Manualmente"):
                with st.form("manual_add"):
                    mc1, mc2, mc3 = st.columns(3)
                    m_sku = mc1.text_input("SKU", value=busqueda.upper())
                    m_desc = mc2.text_input("Descripción", value="Refacción Manual")
                    m_precio = mc3.number_input("Precio Base", min_value=0.0)
                    if st.form_submit_button("Agregar"):
                        iva_m = m_precio * 0.16
                        st.session_state.carrito.append({
                            "SKU": m_sku, "Descripción": m_desc, "Cantidad": 1,
                            "Precio Base": m_precio, "IVA": iva_m, "Importe Total": m_precio + iva_m, "Estatus": "Disponible"
                        })
                        st.rerun()

elif modo == "📂 Carga Masiva (Excel)":
    st.info("Sube tu archivo Excel. El sistema buscará VIN y Orden automáticamente.")
    uploaded_file = st.file_uploader("Arrastra tu Excel aquí", type=['xlsx', 'xls'])
    
    if uploaded_file:
        try:
            # Leer Excel
            df_excel = pd.read_excel(uploaded_file)
            
            # 1. ESCANEO PROFUNDO DE METADATOS (Header)
            # Convertimos todo el dataframe a texto para buscar VINs/Ordenes que estén "flotando" en celdas
            full_text_excel = df_excel.to_string()
            meta_excel = buscar_metadatos(full_text_excel)
            
            # Actualizar si encontramos algo nuevo y los campos están vacíos
            if not st.session_state.auto_vin and 'VIN' in meta_excel: st.session_state.auto_vin = meta_excel['VIN']
            if not st.session_state.auto_orden and 'ORDEN' in meta_excel: st.session_state.auto_orden = meta_excel['ORDEN']
            
            # 2. ENCONTRAR COLUMNAS DE PRODUCTOS
            # Normalizar nombres de columnas para ser flexibles
            df_excel.columns = [str(c).upper().strip() for c in df_excel.columns]
            
            # Posibles nombres para SKU y Cantidad
            col_sku_ex = next((c for c in df_excel.columns if c in ['SKU', 'PART NUMBER', 'NO. PARTE', 'NUMERO DE PARTE', 'ITEM', 'PARTE']), None)
            col_cant_ex = next((c for c in df_excel.columns if c in ['QTY', 'CANTIDAD', 'CANT', 'UNIDADES', 'PIEZAS']), None)
            
            if col_sku_ex:
                st.success(f"Columna de partes detectada: {col_sku_ex}")
                if st.button("Procesar Excel"):
                    items_a_procesar = []
                    for _, row in df_excel.iterrows():
                        if pd.notna(row[col_sku_ex]):
                            qty = 1
                            if col_cant_ex and pd.notna(row[col_cant_ex]):
                                try: qty = int(row[col_cant_ex])
                                except: qty = 1
                            items_a_procesar.append({'sku': row[col_sku_ex], 'cant': qty})
                    
                    ok, errores = procesar_sku_logic(items_a_procesar)
                    st.session_state.errores_carga = errores
                    st.success(f"✅ Se cargaron {ok} partidas correctamente.")
                    if errores: st.warning(f"⚠️ {len(errores)} códigos no encontrados.")
                    st.rerun()
            else:
                st.error("No encontré una columna que parezca 'Número de Parte' o 'SKU'. Revisa tu Excel.")
                st.write("Columnas detectadas:", df_excel.columns.tolist())
                
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")

    # Visualización de errores de carga masiva
    if st.session_state.errores_carga:
        with st.expander(f"⚠️ Resolver {len(st.session_state.errores_carga)} No Encontrados", expanded=True):
            st.write(", ".join(st.session_state.errores_carga))
            if st.button("Limpiar Errores"):
                st.session_state.errores_carga = []
                st.rerun()

# ---------------------------------------------------------
# BLOQUE 3: CARRITO Y FINALIZACIÓN
# ---------------------------------------------------------
if st.session_state.carrito:
    st.write("---")
    st.subheader("🛒 Resumen de Cotización")
    
    # Encabezado Tabla
    h1, h2, h3, h4, h5, h6, h7 = st.columns([1.5, 3, 0.8, 1.2, 1.2, 1.2, 0.5])
    h1.markdown("**SKU**")
    h2.markdown("**Desc**")
    h3.markdown("**Cant**")
    h4.markdown("**Unit**")
    h5.markdown("**IVA**")
    h6.markdown("**Total**")
    h7.markdown("**X**")
    
    idx_del = None
    for i, item in enumerate(st.session_state.carrito):
        with st.container():
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 3, 0.8, 1.2, 1.2, 1.2, 0.5])
            c1.write(item['SKU'])
            c2.write(item['Descripción'])
            
            # Edición de cantidad
            new_q = c3.number_input("C", 1, value=int(item['Cantidad']), key=f"cq_{i}", label_visibility="collapsed")
            if new_q != item['Cantidad']:
                item['Cantidad'] = new_q
                item['IVA'] = (item['Precio Base'] * new_q) * 0.16
                item['Importe Total'] = (item['Precio Base'] * new_q) + item['IVA']
                st.rerun()
                
            c4.write(f"${item['Precio Base']:,.2f}")
            c5.write(f"${item['IVA']:,.2f}")
            c6.write(f"${item['Importe Total']:,.2f}")
            if c7.button("🗑️", key=f"d_{i}"): idx_del = i
    
    if idx_del is not None:
        st.session_state.carrito.pop(idx_del)
        st.rerun()
        
    st.divider()
    
    # Totales
    df_c = pd.DataFrame(st.session_state.carrito)
    sub = (df_c['Precio Base'] * df_c['Cantidad']).sum()
    iva = df_c['IVA'].sum()
    tot = df_c['Importe Total'].sum()
    
    mt1, mt2, mt3 = st.columns(3)
    mt1.metric("Subtotal", f"${sub:,.2f}")
    mt2.metric("IVA (16%)", f"${iva:,.2f}")
    mt3.metric("GRAN TOTAL", f"${tot:,.2f}")
    
    # Acciones Finales
    b1, b2 = st.columns([1, 1])
    with b1:
        pdf_data = generar_pdf_bytes(st.session_state.carrito, sub, iva, tot, 
                                     st.session_state.auto_cliente, 
                                     st.session_state.auto_vin, 
                                     st.session_state.auto_orden)
        st.download_button("📄 Descargar PDF Oficial", data=pdf_data, file_name="Cotizacion_Toyota.pdf", mime="application/pdf", type="primary")
    with b2:
        if st.button("🗑️ Nueva Cotización (Limpiar)"):
            st.session_state.carrito = []
            st.session_state.auto_vin = ""
            st.session_state.auto_orden = ""
            st.session_state.auto_cliente = ""
            st.rerun()

st.markdown('<div class="legal-footer">Sistema Interno Toyota Los Fuertes - v3.0 All-In-One</div>', unsafe_allow_html=True)
