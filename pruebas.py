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
st.set_page_config(page_title="Toyota Asesores AI", page_icon="🤖", layout="wide")

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
if 'cliente' not in st.session_state: st.session_state.cliente = ""
if 'vin' not in st.session_state: st.session_state.vin = ""
if 'orden' not in st.session_state: st.session_state.orden = ""
if 'asesor' not in st.session_state: st.session_state.asesor = ""  # Nuevo campo

# Estilos CSS
st.markdown("""
    <style>
    h1 { color: #eb0a1e !important; text-align: center; font-family: 'Arial Black', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px 5px 0 0; gap: 1px; padding-top: 10px; padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] { background-color: #eb0a1e; color: white; }
    .legal-footer { text-align: center; font-size: 10px; color: #666; margin-top: 50px; border-top: 1px solid #ddd; padding-top: 10px; }
    
    /* Estilo para el Botón de IA */
    div[data-testid="stButton"] > button {
        transition: all 0.4s ease;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE IA (BÚSQUEDA PROFUNDA)
# ==========================================
def analizador_inteligente_archivos(df_raw):
    """ 
    IA LOCAL: Escanea celdas buscando patrones de:
    1. Partes Toyota (SKU)
    2. VIN (17 Dígitos)
    3. Orden de Trabajo (OT/Folio)
    4. Nombre del Asesor
    """
    hallazgos = []
    metadata = {}
    
    # Convertimos todo a string, mayúsculas y quitamos espacios extra
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    
    # --- PATRONES REGEX ---
    patron_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    patron_sku_fmt = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b' 
    patron_sku_pln = r'\b[A-Z0-9]{10,12}\b'
    
    # Palabras clave para metadatos
    keywords_orden = ['ORDEN', 'FOLIO', 'OT', 'OS', 'PEDIDO']
    keywords_asesor = ['ASESOR', 'SA', 'ATENDIO', 'ADVISOR']

    for row_idx, row in df.iterrows():
        for col_idx, cell_value in row.items():
            
            # A. DETECCIÓN DE VIN
            if re.search(patron_vin, cell_value):
                match = re.search(patron_vin, cell_value)
                metadata['VIN'] = match.group(0)
                continue 

            # B. DETECCIÓN DE ORDEN / FOLIO
            # 1. En la misma celda (ej: "Orden: 12345")
            if any(k in cell_value for k in keywords_orden):
                match_ord = re.search(r'(?:ORDEN|FOLIO|OT|OS|PEDIDO)[\:\.\-\s#]*([A-Z0-9\-]{4,10})', cell_value)
                if match_ord:
                    metadata['ORDEN'] = match_ord.group(1)
                else:
                    # 2. En la celda vecina (ej: Celda A: "Orden", Celda B: "12345")
                    try:
                        idx_pos = df.columns.get_loc(col_idx)
                        if idx_pos + 1 < len(df.columns):
                            vecino = df.iloc[row_idx, idx_pos + 1]
                            if len(vecino) > 3 and len(vecino) < 12: # Filtro básico
                                metadata['ORDEN'] = vecino
                    except: pass

            # C. DETECCIÓN DE ASESOR
            if any(k in cell_value for k in keywords_asesor):
                # 1. Misma celda (ej: "Asesor: Juan Perez")
                match_ase = re.search(r'(?:ASESOR|SA|ATENDIO)[\:\.\-\s]+([A-Z\s\.]{4,30})', cell_value)
                if match_ase:
                    metadata['ASESOR'] = match_ase.group(1).strip()
                else:
                    # 2. Celda vecina
                    try:
                        idx_pos = df.columns.get_loc(col_idx)
                        if idx_pos + 1 < len(df.columns):
                            vecino = df.iloc[row_idx, idx_pos + 1]
                            # Validar que no sea un número ni fecha, sino texto (nombre)
                            if len(vecino) > 3 and not re.search(r'\d', vecino):
                                metadata['ASESOR'] = vecino
                    except: pass

            # D. DETECCIÓN DE PARTES (SKU)
            es_sku = False
            sku_detectado = None
            
            if re.match(patron_sku_fmt, cell_value):
                sku_detectado = cell_value
                es_sku = True
            elif re.match(patron_sku_pln, cell_value):
                if not cell_value.isdigit(): # Evitar telefonos
                    sku_detectado = cell_value
                    es_sku = True
            
            if es_sku:
                # Buscar Cantidad en vecindad (derecha)
                cantidad = 1
                try:
                    idx_pos = df.columns.get_loc(col_idx)
                    if idx_pos + 1 < len(df.columns):
                        vecino = df.iloc[row_idx, idx_pos + 1]
                        # Limpieza para detectar numero "1.0", "2", etc
                        clean_vecino = vecino.replace('.0', '')
                        if clean_vecino.isdigit():
                            cantidad = int(clean_vecino)
                except: pass
                
                hallazgos.append({'sku': sku_detectado, 'cant': cantidad})

    return hallazgos, metadata

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

def procesar_skus(lista_items):
    if df_db is None: return 0, [x['sku'] for x in lista_items]
    exitos = 0
    fallos = []
    
    for item in lista_items:
        raw = str(item['sku']).upper().strip()
        clean = raw.replace('-', '')
        cant = int(item['cant']) if item['cant'] > 0 else 1
        
        match = df_db[df_db['SKU_CLEAN'] == clean]
        if not match.empty:
            row = match.iloc[0]
            desc = traducir_profe(row[col_desc_db]) if col_desc_db else "Refacción Original"
            precio = row['PRECIO_NUM']
            iva = (precio * cant) * 0.16
            
            st.session_state.carrito.append({
                "SKU": row[col_sku_db],
                "Descripción": desc,
                "Cantidad": cant,
                "Precio Base": precio,
                "IVA": iva,
                "Importe Total": (precio * cant) + iva,
                "Estatus": "Disponible",
                "Tipo": "Refacción"
            })
            exitos += 1
        else:
            fallos.append(raw)
    return exitos, fallos

# ==========================================
# 3. GENERACIÓN DE PDF
# ==========================================
class PDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            try: self.image("logo.png", 10, 8, 33)
            except: pass
        self.set_font('Arial', 'B', 16)
        self.set_text_color(235, 10, 30)
        self.cell(0, 10, 'TOYOTA LOS FUERTES', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.set_text_color(0)
        self.cell(0, 5, 'PRESUPUESTO DE SERVICIOS Y REFACCIONES', 0, 1, 'C')
        self.ln(15)

    def footer(self):
        self.set_y(-55)
        self.set_font('Arial', 'B', 7)
        self.set_text_color(0)
        self.cell(0, 4, 'TÉRMINOS Y CONDICIONES', 0, 1, 'L')
        self.set_font('Arial', '', 6)
        self.set_text_color(80)
        legales = (
            "1. VIGENCIA: 24 horas. Precios en MXN con IVA incluido (16%). Sujeto a cambios sin previo aviso.\n"
            "2. PARTES ELÉCTRICAS: No tienen garantía ni devolución.\n"
            "3. PEDIDOS ESPECIALES: Requieren 50% de anticipo. No reembolsable en cancelación.\n"
            "4. MANO DE OBRA: Garantía de servicio de 30 días o 1,000 km.\n"
            "5. DEVOLUCIONES: Cargo administrativo del 20%. Máximo 5 días naturales.\n"
            "6. AVISO: Refacciones bajo NOM-050-SCFI-2004."
        )
        self.multi_cell(0, 3, legales, 0, 'J')
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

def generar_pdf_completo(carrito, subtotal, iva, total, cliente, vin, orden, asesor):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=60)
    
    fecha_mx = obtener_hora_mx().strftime("%d/%m/%Y %H:%M")
    
    # Datos Header (Gris)
    pdf.set_draw_color(200); pdf.set_fill_color(245)
    pdf.rect(10, 35, 190, 28, 'FD') # Rectangulo más alto para incluir Asesor
    pdf.set_xy(12, 38)
    
    # Fila 1: Cliente y Fecha
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(90, 5, str(cliente).upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'FECHA:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(40, 5, fecha_mx, 0, 1)
    
    # Fila 2: VIN y Orden
    pdf.set_x(12)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'VIN:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(90, 5, str(vin).upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'ORDEN:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(40, 5, str(orden).upper(), 0, 1)

    # Fila 3: Asesor
    pdf.set_x(12)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'ASESOR:', 0, 0); pdf.set_font('Arial', '', 9)
    pdf.cell(150, 5, str(asesor).upper(), 0, 1)
    pdf.ln(10)

    # Tabla
    pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 8)
    cols = [25, 80, 15, 25, 25, 20]
    headers = ['CÓDIGO', 'DESCRIPCIÓN', 'CANT', 'UNITARIO', 'TOTAL', 'TIPO']
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 1, 0, 'C', True)
    pdf.ln()

    pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    for item in carrito:
        desc = item['Descripción'][:60]
        tipo = "REF" if "Refac" in item.get('Tipo', 'Refacción') else "SERV"
        
        pdf.cell(cols[0], 6, item['SKU'][:15], 'B', 0, 'C')
        pdf.cell(cols[1], 6, desc, 'B', 0, 'L')
        pdf.cell(cols[2], 6, str(item['Cantidad']), 'B', 0, 'C')
        pdf.cell(cols[3], 6, f"${item['Precio Base']:,.2f}", 'B', 0, 'R')
        pdf.cell(cols[4], 6, f"${item['Importe Total']:,.2f}", 'B', 0, 'R')
        pdf.set_font('Arial', 'B', 6)
        pdf.cell(cols[5], 6, tipo, 'B', 1, 'C')
        pdf.set_font('Arial', '', 7)

    pdf.ln(5)
    
    # Totales
    pdf.set_font('Arial', '', 10)
    x_total = 140
    pdf.set_x(x_total); pdf.cell(30, 6, 'Subtotal:', 0, 0, 'R'); pdf.cell(30, 6, f"${subtotal:,.2f}", 0, 1, 'R')
    pdf.set_x(x_total); pdf.cell(30, 6, 'IVA (16%):', 0, 0, 'R'); pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    pdf.set_x(x_total); pdf.set_font('Arial', 'B', 12); pdf.set_text_color(235, 10, 30)
    pdf.cell(30, 8, 'TOTAL MXN:', 0, 0, 'R'); pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')
    
    # Firma
    pdf.set_y(pdf.get_y() + 15)
    pdf.set_draw_color(0); pdf.line(80, pdf.get_y(), 130, pdf.get_y())
    pdf.set_font('Arial', '', 7); pdf.set_text_color(100)
    pdf.cell(0, 4, 'FIRMA DEL ASESOR', 0, 1, 'C')
    if asesor: pdf.cell(0, 4, asesor.upper(), 0, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. INTERFAZ GRÁFICA (TABS)
# ==========================================
if df_db is None:
    st.error("⚠️ ERROR: Falta 'lista_precios.zip'.")
    st.stop()

st.title("TOYOTA LOS FUERTES")
st.markdown(f"**{obtener_hora_mx().strftime('%d/%m/%Y')}**", unsafe_allow_html=True)

# PESTAÑAS PRINCIPALES
tab1, tab2, tab3, tab4 = st.tabs([
    "📂 1. Datos & IA", 
    "🔍 2. Refacciones", 
    "🎨 3. Mano de Obra", 
    "🛒 4. Carrito Final"
])

# --- TAB 1: DATOS & IA ---
with tab1:
    st.markdown("### 📝 Encabezado de Orden")
    
    # Fila de datos editables
    c1, c2, c3, c4 = st.columns(4)
    st.session_state.cliente = c1.text_input("Cliente", value=st.session_state.cliente, key="txt_cli")
    st.session_state.vin = c2.text_input("VIN (17 Dígitos)", value=st.session_state.vin, max_chars=17, key="txt_vin")
    st.session_state.orden = c3.text_input("Orden / Folio", value=st.session_state.orden, key="txt_ord")
    st.session_state.asesor = c4.text_input("Asesor", value=st.session_state.asesor, key="txt_ase")
    
    st.divider()
    st.markdown("### 🧠 Carga Masiva (IA Inteligente)")
    st.info("Sube tu archivo. La IA buscará automáticamente: Partes, VIN, Orden y Asesor.")
    
    uploaded_file = st.file_uploader("Arrastra Excel o CSV aquí", type=['xlsx', 'xls', 'csv'])
    
    if uploaded_file:
        # BOTÓN DE IA ADAPTATIVO (VISUAL)
        if st.button("✨ EJECUTAR ANÁLISIS IA", type="primary"):
            
            # Contenedor de estado interactivo (Simula que el sistema "piensa")
            with st.status("🤖 La IA está analizando el documento...", expanded=True) as status:
                st.write("📂 Leyendo estructura del archivo...")
                try:
                    if uploaded_file.name.endswith('.csv'): 
                        df_up = pd.read_csv(uploaded_file, encoding='latin-1', on_bad_lines='skip')
                    else: 
                        df_up = pd.read_excel(uploaded_file)
                    
                    st.write("🔍 Escaneando celdas buscando patrones Toyota...")
                    items, meta = analizador_inteligente_archivos(df_up)
                    
                    # Actualización de Metadatos
                    if 'VIN' in meta: 
                        st.session_state.vin = meta['VIN']
                        st.write(f"✅ VIN Detectado: {meta['VIN']}")
                    
                    if 'ORDEN' in meta: 
                        st.session_state.orden = meta['ORDEN']
                        st.write(f"✅ Orden Detectada: {meta['ORDEN']}")
                        
                    if 'ASESOR' in meta:
                        st.session_state.asesor = meta['ASESOR']
                        st.write(f"✅ Asesor Detectado: {meta['ASESOR']}")
                    
                    st.write("🔧 Verificando números de parte...")
                    if items:
                        ok, err = procesar_skus(items)
                        st.session_state.errores_carga = err
                        
                        # Estado Final
                        status.update(label=f"✅ Análisis Completado: {ok} piezas encontradas.", state="complete", expanded=False)
                        st.success(f"Proceso finalizado. {ok} partes agregadas al carrito.")
                        if err: st.warning(f"⚠️ {len(err)} códigos no se encontraron en catálogo.")
                    else:
                        status.update(label="⚠️ Análisis finalizado sin refacciones.", state="error")
                        st.warning("Se detectaron datos, pero no refacciones con formato válido.")
                        
                except Exception as e:
                    status.update(label="❌ Error en el análisis", state="error")
                    st.error(f"Error crítico: {e}")

    if st.session_state.errores_carga:
        with st.expander("⚠️ Ver códigos desconocidos"):
            st.table(st.session_state.errores_carga)
            if st.button("Limpiar Errores"): st.session_state.errores_carga = []; st.rerun()

# --- TAB 2: REFACCIONES ---
with tab2:
    col_search, col_add_manual = st.columns([2, 1])
    
    with col_search:
        st.markdown("#### 🔎 Búsqueda en Catálogo")
        busqueda = st.text_input("SKU o Descripción:", placeholder="Ej. 90915...")
        if busqueda:
            b_raw = busqueda.upper().strip().replace('-', '')
            mask = df_db.apply(lambda x: x.astype(str).str.contains(busqueda, case=False)).any(axis=1) | df_db['SKU_CLEAN'].str.contains(b_raw, na=False)
            res = df_db[mask].head(5)
            
            if not res.empty:
                for i, row in res.iterrows():
                    with st.container():
                        c_tx, c_num, c_bt = st.columns([3, 1, 1])
                        sku_v = row[col_sku_db]; desc_v = traducir_profe(row[col_desc_db]); prec_v = row['PRECIO_NUM']
                        c_tx.markdown(f"**{desc_v}**\n\n`{sku_v}` - ${prec_v:,.2f}")
                        cant_v = c_num.number_input("Cant", 1, key=f"s_{i}")
                        if c_bt.button("Agregar", key=f"b_{i}"):
                            iva_v = (prec_v * cant_v) * 0.16
                            st.session_state.carrito.append({
                                "SKU": sku_v, "Descripción": desc_v, "Cantidad": cant_v,
                                "Precio Base": prec_v, "IVA": iva_v, "Importe Total": (prec_v * cant_v) + iva_v,
                                "Estatus": "Disponible", "Tipo": "Refacción"
                            })
                            st.toast("✅ Agregado")
            else: st.info("No encontrado en catálogo.")

    with col_add_manual:
        st.markdown("#### 🛠️ Ítem Libre / Manual")
        with st.form("form_manual"):
            m_sku = st.text_input("Código", value="GENERICO")
            m_desc = st.text_input("Descripción", value="Pieza Especial")
            m_price = st.number_input("Precio Unitario", min_value=0.0)
            m_cant = st.number_input("Cantidad", min_value=1, value=1)
            
            if st.form_submit_button("Agregar Manual"):
                iva_m = (m_price * m_cant) * 0.16
                st.session_state.carrito.append({
                    "SKU": m_sku.upper(), "Descripción": m_desc, "Cantidad": m_cant,
                    "Precio Base": m_price, "IVA": iva_m, "Importe Total": (m_price * m_cant) + iva_m,
                    "Estatus": "Disponible", "Tipo": "Refacción"
                })
                st.success("Item agregado.")

# --- TAB 3: MANO DE OBRA ---
with tab3:
    st.markdown("### 🎨 Servicios de Taller y Pintura")
    c_serv1, c_serv2 = st.columns(2)
    with c_serv1:
        with st.form("form_servicio"):
            s_desc = st.text_input("Descripción del Servicio", placeholder="Ej. Pintura Facia Delantera")
            col_h, col_p = st.columns(2)
            s_horas = col_h.number_input("Horas / Unidades", min_value=0.5, step=0.5, format="%.1f")
            s_precio = col_p.number_input("Precio por Hora/Unidad", min_value=0.0, value=500.0)
            
            s_total_calc = s_horas * s_precio
            st.markdown(f"**Total Servicio:** ${s_total_calc:,.2f} + IVA")
            
            if st.form_submit_button("Agregar Servicio"):
                iva_s = s_total_calc * 0.16
                st.session_state.carrito.append({
                    "SKU": "SERV-TALLER", 
                    "Descripción": f"{s_desc} ({s_horas} Hrs/Uds)", 
                    "Cantidad": 1,
                    "Precio Base": s_total_calc, 
                    "IVA": iva_s, 
                    "Importe Total": s_total_calc + iva_s,
                    "Estatus": "Servicio", "Tipo": "Mano de Obra"
                })
                st.toast("🛠️ Servicio agregado")

# --- TAB 4: CARRITO ---
with tab4:
    if st.session_state.carrito:
        st.markdown("### 🛒 Resumen Final")
        df_c = pd.DataFrame(st.session_state.carrito)
        
        edited_df = st.data_editor(
            df_c,
            column_config={
                "Importe Total": st.column_config.NumberColumn(format="$%.2f", disabled=True),
                "IVA": st.column_config.NumberColumn(format="$%.2f", disabled=True),
                "Tipo": st.column_config.TextColumn(disabled=True),
            },
            num_rows="dynamic", key="cart_editor"
        )
        
        if not edited_df.equals(df_c):
            regs = edited_df.to_dict('records')
            for r in regs:
                r['IVA'] = (r['Precio Base'] * r['Cantidad']) * 0.16
                r['Importe Total'] = (r['Precio Base'] * r['Cantidad']) + r['IVA']
            st.session_state.carrito = regs
            st.rerun()

        sub = sum(i['Precio Base'] * i['Cantidad'] for i in st.session_state.carrito)
        iva = sum(i['IVA'] for i in st.session_state.carrito)
        tot = sub + iva
        
        cm1, cm2, cm3 = st.columns(3)
        cm1.metric("Subtotal", f"${sub:,.2f}")
        cm2.metric("IVA (16%)", f"${iva:,.2f}")
        cm3.metric("TOTAL", f"${tot:,.2f}")
        
        cb1, cb2 = st.columns(2)
        with cb1:
            pdf_data = generar_pdf_completo(
                st.session_state.carrito, sub, iva, tot, 
                st.session_state.cliente, st.session_state.vin, 
                st.session_state.orden, st.session_state.asesor
            )
            st.download_button("📄 Descargar PDF Oficial", pdf_data, f"Cotizacion_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)
        with cb2:
            if st.button("🗑️ Limpiar Todo", type="secondary", use_container_width=True):
                st.session_state.carrito = []
                st.session_state.cliente = ""; st.session_state.vin = ""; st.session_state.orden = ""; st.session_state.asesor = ""
                st.rerun()
    else: st.info("El carrito está vacío.")

st.markdown('<div class="legal-footer">Sistema Toyota Los Fuertes v6.0 AI | Refacciones & Servicios</div>', unsafe_allow_html=True)
