import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
from datetime import datetime
from fpdf import FPDF
import pytz
import re
import os
import io

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
if 'cliente' not in st.session_state: st.session_state.cliente = ""
if 'vin' not in st.session_state: st.session_state.vin = ""
if 'orden' not in st.session_state: st.session_state.orden = ""

# Estilos CSS Profesionales
st.markdown("""
    <style>
    h1 { color: #eb0a1e !important; text-align: center; font-family: 'Arial Black', sans-serif; }
    h3 { color: #333; border-bottom: 2px solid #eb0a1e; padding-bottom: 10px; }
    .stButton button { 
        width: 100%; border-radius: 5px; font-weight: bold; 
        background-color: #f0f0f0; border: 1px solid #ccc;
        transition: all 0.3s;
    }
    .stButton button:hover {
        border-color: #eb0a1e; color: #eb0a1e;
    }
    .legal-footer { 
        text-align: center; font-size: 10px; color: #666; 
        margin-top: 50px; border-top: 1px solid #ddd; padding-top: 10px;
    }
    .success-box { background-color: #d1fae5; padding: 10px; border-radius: 5px; border-left: 5px solid #10b981; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE RECONOCIMIENTO INTELIGENTE (AI LOCAL)
# ==========================================
def analizador_inteligente_archivos(df_raw):
    """
    Escanea cada celda del archivo buscando patrones de Toyota (Partes y VINs)
    sin importar el nombre de la columna o el orden.
    """
    hallazgos = []
    metadata = {}
    
    # Convertimos todo a string y mayúsculas
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    
    # Expresiones Regulares (Patrones)
    # Patrón SKU Toyota: 5 letras/num - 5 letras/num (ej. 90915-YZZF1) o 10-12 seguidos
    patron_sku_format = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b' 
    patron_sku_plain = r'\b[A-Z0-9]{10,12}\b'
    # Patrón VIN: 17 caracteres (excluyendo I,O,Q tipicos, pero flexible)
    patron_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    
    for row_idx, row in df.iterrows():
        for col_idx, cell_value in row.items():
            
            # 1. BUSCAR VIN
            if re.match(patron_vin, cell_value):
                metadata['VIN'] = cell_value
                continue # Si es VIN, no es parte

            # 2. BUSCAR SKU (Con o sin guión)
            es_sku = False
            sku_detectado = None
            
            if re.match(patron_sku_format, cell_value):
                sku_detectado = cell_value
                es_sku = True
            elif re.match(patron_sku_plain, cell_value):
                # Filtro anti-falsos positivos (ej. telefonos)
                if not cell_value.isdigit(): # Toyota SKUs suelen tener letras
                    sku_detectado = cell_value
                    es_sku = True
            
            if es_sku:
                # INTELIGENCIA DE CANTIDAD:
                # Si encontramos un SKU, buscamos en las celdas adyacentes (derecha) un número
                cantidad = 1
                try:
                    # Intentar buscar en la siguiente columna
                    idx_pos = df.columns.get_loc(col_idx)
                    if idx_pos + 1 < len(df.columns):
                        vecino = df.iloc[row_idx, idx_pos + 1]
                        if vecino.replace('.','',1).isdigit():
                            cantidad = int(float(vecino))
                except:
                    pass # Se queda en 1
                
                hallazgos.append({'sku': sku_detectado, 'cant': cantidad})

    return hallazgos, metadata

# ==========================================
# 3. GENERACIÓN DE PDF CON LEGALES
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
        self.cell(0, 5, 'PRESUPUESTO FORMAL DE REFACCIONES', 0, 1, 'C')
        self.ln(15)

    def footer(self):
        self.set_y(-55) # Espacio para legales
        self.set_font('Arial', 'B', 7)
        self.set_text_color(0)
        self.cell(0, 4, 'TÉRMINOS Y CONDICIONES COMERCIALES', 0, 1, 'L')
        
        self.set_font('Arial', '', 6)
        self.set_text_color(80)
        legales = (
            "1. PRECIOS Y VIGENCIA: Los precios están expresados en Moneda Nacional (MXN) e incluyen IVA (16%). "
            "Esta cotización tiene una vigencia de 24 horas o hasta agotar existencias. Sujeto a cambios sin previo aviso por parte de Toyota de México.\n"
            "2. PARTES ELÉCTRICAS: En partes eléctricas y electrónicas NO HAY GARANTÍA NI DEVOLUCIONES, sin excepción alguna, "
            "debido a la naturaleza sensible de los componentes.\n"
            "3. PEDIDOS ESPECIALES: Para refacciones bajo pedido (Back Order) se requiere un anticipo del 50% no reembolsable en caso de cancelación por parte del cliente. "
            "Los tiempos de entrega son estimados y dependen de la logística de planta.\n"
            "4. GARANTÍA: La garantía de refacciones instaladas en taller autorizado es de 12 meses o 20,000 km (lo que ocurra primero). "
            "Refacciones vendidas por mostrador cuentan con garantía limitada contra defectos de fábrica, sujeta a dictamen técnico.\n"
            "5. DEVOLUCIONES: Toda devolución causa un 20% de cargo administrativo. No se aceptan devoluciones después de 5 días naturales, ni en material maltratado o sin empaque original.\n"
            "6. AVISO LEGAL: Las partes descritas cumplen con la NOM-050-SCFI-2004."
        )
        self.multi_cell(0, 3, legales, 0, 'J')
        
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

def generar_pdf_completo(carrito, subtotal, iva, total, cliente, vin, orden):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=60) # Margen alto para no pisar el footer legal
    
    fecha_mx = obtener_hora_mx().strftime("%d/%m/%Y %H:%M")
    
    # --- BLOQUE DE INFORMACIÓN ---
    pdf.set_draw_color(200)
    pdf.set_fill_color(250)
    pdf.rect(10, 35, 190, 22, 'FD')
    
    pdf.set_xy(12, 38)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'CLIENTE:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(90, 5, str(cliente).upper() if cliente else "MOSTRADOR / PÚBLICO GENERAL", 0, 0)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'FECHA:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, 5, fecha_mx, 0, 1)
    
    pdf.set_x(12)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'VIN:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(90, 5, str(vin).upper() if vin else "N/A", 0, 0)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'ORDEN:', 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, 5, str(orden).upper() if orden else "S/N", 0, 1)

    pdf.ln(10)

    # --- TABLA ---
    pdf.set_fill_color(235, 10, 30)
    pdf.set_text_color(255)
    pdf.set_font('Arial', 'B', 8)
    
    cols = [30, 75, 15, 25, 25, 20] # Anchos
    headers = ['NÚMERO PARTE', 'DESCRIPCIÓN', 'CANT', 'UNITARIO', 'TOTAL', 'ESTATUS']
    
    for i, h in enumerate(headers):
        pdf.cell(cols[i], 8, h, 1, 0, 'C', True)
    pdf.ln()

    pdf.set_text_color(0)
    pdf.set_font('Arial', '', 7)
    
    for item in carrito:
        desc = item['Descripción'][:55]
        pdf.cell(cols[0], 6, item['SKU'], 'B', 0, 'C')
        pdf.cell(cols[1], 6, desc, 'B', 0, 'L')
        pdf.cell(cols[2], 6, str(int(item['Cantidad'])), 'B', 0, 'C')
        pdf.cell(cols[3], 6, f"${item['Precio Base']:,.2f}", 'B', 0, 'R')
        pdf.cell(cols[4], 6, f"${item['Importe Total']:,.2f}", 'B', 0, 'R')
        
        # Estatus con color condicional
        st_txt = item['Estatus']
        if "Back" in st_txt: pdf.set_text_color(200, 0, 0)
        else: pdf.set_text_color(0)
        pdf.cell(cols[5], 6, st_txt, 'B', 1, 'C')
        pdf.set_text_color(0)

    pdf.ln(5)
    
    # --- TOTALES ---
    pdf.set_font('Arial', '', 10)
    x_total = 140
    pdf.set_x(x_total)
    pdf.cell(30, 6, 'Subtotal:', 0, 0, 'R')
    pdf.cell(30, 6, f"${subtotal:,.2f}", 0, 1, 'R')
    
    pdf.set_x(x_total)
    pdf.cell(30, 6, 'IVA (16%):', 0, 0, 'R')
    pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    
    pdf.set_x(x_total)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(235, 10, 30)
    pdf.cell(30, 8, 'TOTAL MXN:', 0, 0, 'R')
    pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')
    
    # Firma
    pdf.set_y(pdf.get_y() + 15)
    pdf.set_draw_color(0)
    pdf.line(80, pdf.get_y(), 130, pdf.get_y())
    pdf.set_font('Arial', '', 7)
    pdf.set_text_color(100)
    pdf.cell(0, 4, 'FIRMA DEL ASESOR', 0, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. CARGA DE BASE DE DATOS
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
        
        c_sku = next((c for c in df.columns if 'PART' in c or 'NUM' in c), None)
        c_desc = next((c for c in df.columns if 'DESC' in c), None)
        c_precio = next((c for c in df.columns if 'PRICE' in c or 'PRECIO' in c), None)
        
        if not c_sku or not c_precio: return None, None, None
        
        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        
        def clean_price(x):
            try: return float(str(x).replace('$', '').replace(',', '').strip())
            except: return 0.0
            
        df['PRECIO_NUM'] = df[c_precio].apply(clean_price)
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
# 5. INTERFAZ DE USUARIO (FRONTEND)
# ==========================================

# Sidebar
st.sidebar.title("Asesor Toyota")
if os.path.exists("logo.png"): st.sidebar.image("logo.png", use_container_width=True)

menu = st.sidebar.selectbox("Herramientas", ["📂 Carga Inteligente (Excel/CSV)", "🔍 Búsqueda Manual"])

# Main Header
col_h1, col_h2 = st.columns([3, 1])
col_h1.title("TOYOTA LOS FUERTES")
col_h2.markdown(f"**{obtener_hora_mx().strftime('%d/%m/%Y')}**")

if df_db is None:
    st.error("⚠️ ERROR CRÍTICO: No se encuentra 'lista_precios.zip'. El sistema no puede cotizar.")
    st.stop()

# --- DATOS GENERALES ---
with st.container():
    st.markdown("### 📄 Datos de la Orden")
    c1, c2, c3 = st.columns(3)
    st.session_state.cliente = c1.text_input("Cliente / Aseguradora", value=st.session_state.cliente)
    st.session_state.vin = c2.text_input("VIN (17 Dígitos)", value=st.session_state.vin, max_chars=17)
    st.session_state.orden = c3.text_input("Orden / Folio", value=st.session_state.orden)
    st.write("---")

# --- LÓGICA DE HERRAMIENTAS ---
if menu == "📂 Carga Inteligente (Excel/CSV)":
    st.markdown("""
    **Instrucciones:** Arrastra cualquier archivo (Excel, CSV). El sistema detectará automáticamente:
    * Números de Parte (con o sin guiones)
    * Cantidades (si están en la celda de la derecha)
    * VINs dentro del archivo
    """)
    
    uploaded_file = st.file_uploader("Sube tu archivo aquí", type=['xlsx', 'xls', 'csv'])
    
    if uploaded_file:
        if st.button("🧠 ANALIZAR ARCHIVO CON IA LOCAL"):
            with st.spinner("Escaneando celdas..."):
                try:
                    # Carga agnóstica
                    if uploaded_file.name.endswith('.csv'):
                        df_upload = pd.read_csv(uploaded_file, encoding='latin-1', on_bad_lines='skip')
                    else:
                        df_upload = pd.read_excel(uploaded_file)
                    
                    # EJECUTAR MOTOR INTELIGENTE
                    items_detectados, meta_detectada = analizador_inteligente_archivos(df_upload)
                    
                    # Actualizar metadata si se encuentra
                    if 'VIN' in meta_detectada: 
                        st.session_state.vin = meta_detectada['VIN']
                        st.toast(f"VIN Detectado: {meta_detectada['VIN']}")
                    
                    # Procesar items
                    if items_detectados:
                        ok, err = procesar_skus(items_detectados)
                        st.session_state.errores_carga = err
                        
                        msg = f"✅ Procesado Exitoso: {ok} partes agregadas."
                        if err: msg += f" | ⚠️ {len(err)} desconocidos."
                        st.success(msg)
                        st.rerun()
                    else:
                        st.warning("No se detectaron patrones de números de parte Toyota en el archivo.")
                        
                except Exception as e:
                    st.error(f"Error al leer archivo: {e}")

    # Mostrar errores de carga
    if st.session_state.errores_carga:
        with st.expander("Ver códigos no encontrados en catálogo"):
            st.table(pd.DataFrame(st.session_state.errores_carga, columns=["SKU Desconocido"]))
            if st.button("Limpiar lista de errores"):
                st.session_state.errores_carga = []
                st.rerun()

elif menu == "🔍 Búsqueda Manual":
    busqueda = st.text_input("Escribe SKU o Nombre de la pieza:", placeholder="Ej. Filtro aceite o 90915...")
    
    if busqueda:
        b_raw = busqueda.upper().strip()
        b_clean = b_raw.replace('-', '')
        mask = df_db.apply(lambda x: x.astype(str).str.contains(b_raw, case=False)).any(axis=1) | \
               df_db['SKU_CLEAN'].str.contains(b_clean, na=False)
        res = df_db[mask].head(10)
        
        if not res.empty:
            st.markdown("#### Resultados")
            for i, row in res.iterrows():
                with st.form(key=f"form_{i}"):
                    c_desc, c_cant, c_btn = st.columns([3, 1, 1])
                    desc_es = traducir_profe(row[col_desc_db])
                    sku = row[col_sku_db]
                    price = row['PRECIO_NUM']
                    
                    c_desc.markdown(f"**{desc_es}**\n\n`{sku}` - ${price:,.2f}")
                    cant = c_cant.number_input("Cant", 1, key=f"n_{i}")
                    
                    if c_btn.form_submit_button("Agregar"):
                        iva = (price * cant) * 0.16
                        st.session_state.carrito.append({
                            "SKU": sku, "Descripción": desc_es, "Cantidad": cant,
                            "Precio Base": price, "IVA": iva, "Importe Total": (price * cant) + iva,
                            "Estatus": "Disponible"
                        })
                        st.toast("Agregado")
                        st.rerun()
        else:
            st.warning("No encontrado.")
            with st.expander("Agregar Manualmente (Item libre)"):
                m_sku = st.text_input("SKU Manual")
                m_desc = st.text_input("Descripción")
                m_price = st.number_input("Precio", 0.0)
                if st.button("Guardar Manual"):
                    iva = m_price * 0.16
                    st.session_state.carrito.append({
                        "SKU": m_sku, "Descripción": m_desc, "Cantidad": 1,
                        "Precio Base": m_price, "IVA": iva, "Importe Total": m_price + iva,
                        "Estatus": "Disponible"
                    })
                    st.rerun()

# --- RESUMEN Y PDF ---
if st.session_state.carrito:
    st.markdown("### 🛒 Cotización Actual")
    
    df_c = pd.DataFrame(st.session_state.carrito)
    
    # Edición directa en tabla (Streamlit moderno)
    edited_df = st.data_editor(
        df_c,
        column_config={
            "Importe Total": st.column_config.NumberColumn(format="$%.2f", disabled=True),
            "IVA": st.column_config.NumberColumn(format="$%.2f", disabled=True),
            "Precio Base": st.column_config.NumberColumn(format="$%.2f", disabled=True),
            "Estatus": st.column_config.SelectboxColumn(options=["Disponible", "Back Order", "Sin Stock"]),
        },
        num_rows="dynamic",
        key="editor_carrito"
    )

    # Recalcular totales basados en la edición
    if not edited_df.equals(df_c):
        # Actualizar sesión si hubo cambios
        registros = edited_df.to_dict('records')
        for reg in registros:
            reg['IVA'] = (reg['Precio Base'] * reg['Cantidad']) * 0.16
            reg['Importe Total'] = (reg['Precio Base'] * reg['Cantidad']) + reg['IVA']
        st.session_state.carrito = registros
        st.rerun()

    # Calcular Totales Finales
    subtotal = sum(item['Precio Base'] * item['Cantidad'] for item in st.session_state.carrito)
    iva_total = sum(item['IVA'] for item in st.session_state.carrito)
    total_gral = subtotal + iva_total

    c_tot1, c_tot2, c_tot3 = st.columns(3)
    c_tot1.metric("Subtotal", f"${subtotal:,.2f}")
    c_tot2.metric("IVA (16%)", f"${iva_total:,.2f}")
    c_tot3.metric("GRAN TOTAL", f"${total_gral:,.2f}")

    # Botones finales
    col_fin1, col_fin2 = st.columns(2)
    
    with col_fin1:
        pdf_bytes = generar_pdf_completo(
            st.session_state.carrito, subtotal, iva_total, total_gral,
            st.session_state.cliente, st.session_state.vin, st.session_state.orden
        )
        st.download_button(
            label="📄 DESCARGAR PDF OFICIAL",
            data=pdf_bytes,
            file_name=f"Cotizacion_{st.session_state.orden if st.session_state.orden else 'Cliente'}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

    with col_fin2:
        if st.button("🗑️ Borrar Todo", type="secondary", use_container_width=True):
            st.session_state.carrito = []
            st.session_state.cliente = ""
            st.session_state.vin = ""
            st.session_state.orden = ""
            st.session_state.errores_carga = []
            st.rerun()

st.markdown('<div class="legal-footer">© 2024 Toyota Los Fuertes | Sistema de Gestión de Refacciones v4.0 AI</div>', unsafe_allow_html=True)
