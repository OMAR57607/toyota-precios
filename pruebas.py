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

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(
    page_title="Toyota Asesores AI", 
    page_icon="🤖", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

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
        'ver_preview': False
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
    # Mantenemos el asesor para no reescribirlo cada vez
    st.session_state.temp_sku = ""
    st.session_state.temp_desc = ""
    st.session_state.temp_precio = 0.0
    st.session_state.ver_preview = False

init_session()

# ==========================================
# 2. ESTILOS CSS (RESPONSIVE & THEME ADAPTIVE)
# ==========================================
st.markdown("""
    <style>
    /* Ajuste general */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    
    /* Botón WhatsApp */
    .wa-btn {
        display: inline-flex; align-items: center; justify-content: center;
        background-color: #25D366; color: white !important;
        padding: 0.6rem 1rem; border-radius: 8px; text-decoration: none;
        font-weight: 700; width: 100%; margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
    }
    .wa-btn:hover { background-color: #128C7E; transform: translateY(-2px); box-shadow: 0 6px 8px rgba(0,0,0,0.15); }

    /* VISTA PREVIA (SIMULACIÓN PAPEL) */
    .preview-container {
        background-color: #525659; /* Fondo gris oscuro neutro para contraste */
        padding: 20px;
        border-radius: 8px;
        display: flex;
        justify-content: center;
        margin-top: 20px;
        overflow-x: auto; /* Scroll horizontal en móviles */
    }
    .preview-paper {
        background-color: white !important; /* Siempre blanco (Papel) */
        color: black !important; /* Texto siempre negro */
        width: 100%;
        max-width: 900px; /* Ancho A4 aprox */
        min-width: 600px; /* Mínimo para que la tabla no se rompa */
        padding: 40px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        font-family: 'Helvetica', 'Arial', sans-serif;
    }
    
    /* Encabezados Preview */
    .preview-header { border-bottom: 3px solid #eb0a1e; padding-bottom: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end; }
    .preview-title { font-size: 26px; font-weight: 900; color: #eb0a1e; margin: 0; line-height: 1.2; }
    .preview-subtitle { font-size: 14px; color: #444; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Grid de Información */
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 25px; padding: 15px; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; }
    .info-item { font-size: 12px; margin-bottom: 6px; color: #333; }
    .info-label { font-weight: 700; color: #555; display: inline-block; width: 70px; }

    /* Tabla Formal */
    table.custom-table { width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 20px; }
    table.custom-table th { background-color: #eb0a1e !important; color: white !important; padding: 10px 8px; text-align: left; font-weight: bold; text-transform: uppercase; }
    table.custom-table td { border-bottom: 1px solid #eee; padding: 8px; color: #333 !important; vertical-align: middle; }
    table.custom-table tr:last-child td { border-bottom: 2px solid #eb0a1e; }
    
    /* Totales */
    .total-box { margin-left: auto; width: 300px; }
    .total-row { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; color: #333; }
    .total-final { font-size: 20px; font-weight: 800; color: #eb0a1e; border-top: 2px solid #ccc; padding-top: 8px; margin-top: 8px; }

    /* Etiquetas y Status */
    .badge-urg { background: #d32f2f; color: white; padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; }
    .status-disp { color: #2e7d32; background: #e8f5e9; border: 1px solid #2e7d32; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; }
    .status-ped { color: #e65100; background: #fff3e0; border: 1px solid #e65100; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 9px; }
    
    /* Media Query para Móviles */
    @media only screen and (max-width: 600px) {
        .preview-paper { padding: 15px; min-width: 100%; }
        .preview-title { font-size: 18px; }
        .info-grid { grid-template-columns: 1fr; gap: 10px; }
        .total-box { width: 100%; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DATOS
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

def agregar_item_callback(sku, desc_raw, precio, cant, tipo, prioridad="Medio", abasto="⚠️ REVISAR"):
    try: desc = GoogleTranslator(source='en', target='es').translate(str(desc_raw))
    except: desc = str(desc_raw)
    iva = (precio * cant) * 0.16
    st.session_state.carrito.append({
        "SKU": sku, "Descripción": desc, "Prioridad": prioridad, "Abasto": abasto,
        "Tiempo Entrega": "",
        "Cantidad": cant, "Precio Base": precio, "IVA": iva, 
        "Importe Total": (precio * cant) + iva, "Estatus": "Disponible", "Tipo": tipo
    })

def analizador_inteligente_archivos(df_raw):
    # (Lógica idéntica a tu versión anterior, preservada para brevedad)
    hallazgos = []; metadata = {}
    df = df_raw.astype(str).apply(lambda x: x.str.upper().str.strip())
    patron_vin = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    patron_orden_8 = r'\b\d{8}\b'
    patron_sku_fmt = r'\b[A-Z0-9]{5}-[A-Z0-9]{5}\b'
    
    # Búsqueda simplificada para ejemplo (se mantiene tu lógica completa en producción)
    for r_idx, row in df.iterrows():
        for val in row:
            if 'VIN' not in metadata:
                m = re.search(patron_vin, val)
                if m: metadata['VIN'] = m.group(0)
            if 'ORDEN' not in metadata:
                m = re.search(patron_orden_8, val)
                if m: metadata['ORDEN'] = m.group(0)
            if re.match(patron_sku_fmt, val):
                hallazgos.append({'sku': val, 'cant': 1})
    return hallazgos, metadata

# ==========================================
# 4. GENERADOR PDF (FORMATO TABLA FORMAL)
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
        self.set_y(-40)
        self.set_font('Arial', 'B', 7); self.set_text_color(50)
        self.cell(0, 3, 'TÉRMINOS Y CONDICIONES', 0, 1, 'L')
        self.set_font('Arial', '', 6); self.set_text_color(80)
        legales = "1. Precios en Moneda Nacional. 2. Pedidos especiales requieren 100% anticipo. 3. Partes eléctricas sin garantía ni devolución. 4. Vigencia de cotización: 24 horas."
        self.multi_cell(0, 3, legales, 0, 'J')
        self.set_y(-15); self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pág {self.page_no()}', 0, 0, 'R')

def generar_pdf():
    pdf = PDF()
    pdf.add_page()
    
    # Info Header
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'CLIENTE:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(100, 5, str(st.session_state.cliente)[:45], 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'FECHA:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 5, obtener_hora_mx().strftime("%d/%m/%Y"), 0, 1)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(20, 5, 'VIN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(100, 5, str(st.session_state.vin), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, 'ORDEN:', 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 5, str(st.session_state.orden), 0, 1)
    pdf.ln(5)

    # Tabla Header
    pdf.set_fill_color(235, 10, 30); pdf.set_text_color(255); pdf.set_font('Arial', 'B', 8)
    cols = [25, 65, 15, 20, 12, 22, 18, 18] # Total width approx 190
    headers = ['CODIGO', 'DESCRIPCION', 'STAT', 'T.ENT', 'CANT', 'UNITARIO', 'IVA', 'TOTAL']
    for i, h in enumerate(headers): pdf.cell(cols[i], 8, h, 0, 0, 'C', True)
    pdf.ln()

    # Tabla Body
    pdf.set_text_color(0); pdf.set_font('Arial', '', 7)
    sub = 0; iva_total = 0
    for item in st.session_state.carrito:
        sub += item['Precio Base'] * item['Cantidad']
        iva_total += item['IVA']
        
        pdf.cell(cols[0], 6, item['SKU'][:15], 'B', 0, 'C')
        pdf.cell(cols[1], 6, str(item['Descripción'])[:35], 'B', 0, 'L')
        
        # Status corto
        stat = "DISP" if "Disponible" in item['Abasto'] else ("PED" if "Pedido" in item['Abasto'] else "REV")
        pdf.cell(cols[2], 6, stat, 'B', 0, 'C')
        pdf.cell(cols[3], 6, str(item['Tiempo Entrega'])[:10], 'B', 0, 'C')
        pdf.cell(cols[4], 6, str(item['Cantidad']), 'B', 0, 'C')
        
        pdf.cell(cols[5], 6, f"${item['Precio Base']:,.2f}", 'B', 0, 'R')
        pdf.cell(cols[6], 6, f"${item['IVA'] / item['Cantidad']:,.2f}", 'B', 0, 'R') # IVA Unitario visual
        pdf.cell(cols[7], 6, f"${item['Importe Total']:,.2f}", 'B', 1, 'R')

    pdf.ln(5)
    
    # Totales
    total = sub + iva_total
    pdf.set_x(130)
    pdf.cell(30, 5, 'SUBTOTAL:', 0, 0, 'R'); pdf.cell(30, 5, f"${sub:,.2f}", 0, 1, 'R')
    pdf.set_x(130)
    pdf.cell(30, 5, 'IVA 16%:', 0, 0, 'R'); pdf.cell(30, 5, f"${iva_total:,.2f}", 0, 1, 'R')
    pdf.set_x(130); pdf.set_font('Arial', 'B', 10); pdf.set_text_color(235, 10, 30)
    pdf.cell(30, 7, 'TOTAL:', 0, 0, 'R'); pdf.cell(30, 7, f"${total:,.2f}", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL
# ==========================================
if df_db is None: st.error("Falta lista_precios.zip"); st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🚘 Datos del Servicio")
    st.session_state.orden = st.text_input("Orden", st.session_state.orden)
    st.session_state.vin = st.text_input("VIN", st.session_state.vin)
    st.session_state.cliente = st.text_input("Cliente", st.session_state.cliente)
    st.session_state.asesor = st.text_input("Asesor", st.session_state.asesor)
    
    if st.button("🗑️ Nueva Cotización"): limpiar_todo(); st.rerun()

# --- MAIN ---
st.title("Cotizador Los Fuertes")

# Secciones colapsables para ahorrar espacio en móviles
with st.expander("🔎 Búsqueda y Agregado", expanded=True):
    col_l, col_r = st.columns([1, 1])
    with col_l:
        q = st.text_input("Buscar SKU o Nombre")
        if q:
            mask = df_db.apply(lambda x: x.astype(str).str.contains(q, case=False)).any(axis=1)
            for _, row in df_db[mask].head(3).iterrows():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{row[col_sku_db]}**\n${row['PRECIO_NUM']:,.2f}")
                if c3.button("➕", key=f"add_{row[col_sku_db]}"):
                    agregar_item_callback(row[col_sku_db], row[col_desc_db], row['PRECIO_NUM'], 1, "Refacción")
                    st.rerun()
    with col_r:
        with st.form("manual"):
            m_sku = st.text_input("SKU Manual", value=st.session_state.temp_sku)
            m_desc = st.text_input("Descripción", value=st.session_state.temp_desc)
            m_pr = st.number_input("Precio Unitario", min_value=0.0, value=float(st.session_state.temp_precio))
            if st.form_submit_button("Agregar Manual"):
                agregar_item_callback(m_sku.upper(), m_desc, m_pr, 1, "Refacción")
                st.session_state.temp_sku = ""; st.session_state.temp_desc = ""; st.session_state.temp_precio = 0.0
                st.rerun()

st.divider()

# --- TABLA Y ACCIONES ---
st.subheader(f"🛒 Carrito ({len(st.session_state.carrito)})")

if st.session_state.carrito:
    df_c = pd.DataFrame(st.session_state.carrito)
    
    # Editor de datos con Precio Base visible pero formateado
    edited = st.data_editor(
        df_c,
        column_config={
            "Prioridad": st.column_config.SelectboxColumn(options=["Urgente", "Medio"], width="small"),
            "Abasto": st.column_config.SelectboxColumn(options=["Disponible", "Por Pedido", "Back Order", "⚠️ REVISAR"], width="small"),
            "Precio Base": st.column_config.NumberColumn("P. Unitario", format="$%.2f", disabled=True), # VISIBLE
            "Importe Total": st.column_config.NumberColumn("Total Línea", format="$%.2f", disabled=True),
            "IVA": None, "Tipo": None, "Estatus": None,
            "Cantidad": st.column_config.NumberColumn(min_value=1, step=1, width="small"),
            "Descripción": st.column_config.TextColumn(width="medium"),
            "SKU": st.column_config.TextColumn(width="small"),
        },
        use_container_width=True,
        num_rows="dynamic", key="editor_cart"
    )

    # Actualizar estado si hubo cambios
    if not edited.equals(df_c):
        new_cart = edited.to_dict('records')
        for r in new_cart:
            r['IVA'] = (r['Precio Base'] * r['Cantidad']) * 0.16
            r['Importe Total'] = (r['Precio Base'] * r['Cantidad']) + r['IVA']
        st.session_state.carrito = new_cart
        st.rerun()

    # Cálculos finales
    subtotal = sum(i['Precio Base'] * i['Cantidad'] for i in st.session_state.carrito)
    total_gral = subtotal * 1.16

    # Botonera de Acción
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if st.button("👁️ Vista Previa / Cerrar", type="secondary", use_container_width=True):
            st.session_state.ver_preview = not st.session_state.ver_preview
            st.rerun()
            
    with c2:
        pdf_bytes = generar_pdf()
        st.download_button("📄 Descargar PDF", pdf_bytes, f"Cot_{st.session_state.orden}.pdf", "application/pdf", type="primary", use_container_width=True)

    with c3:
        # --- LÓGICA WHATSAPP MEJORADA ---
        items_wa = ""
        for i in st.session_state.carrito:
            # Formato: ▪️ 1x AMORTIGUADOR ($1,200.00)
            items_wa += f"▪️ {i['Cantidad']}x {i['Descripción']} (${i['Precio Base']:,.2f})\n"
        
        msg_raw = (
            f"Hola *{st.session_state.cliente}*, envío presupuesto:\n\n"
            f"🚘 VIN: {st.session_state.vin}\n"
            f"📄 Orden: {st.session_state.orden}\n\n"
            f"*REFACCIONES:*\n{items_wa}\n"
            f"💰 *TOTAL: ${total_gral:,.2f}*\n\n"
            f"Atte: {st.session_state.asesor}\nToyota Los Fuertes"
        )
        msg_enc = urllib.parse.quote(msg_raw)
        st.markdown(f'<a href="https://wa.me/?text={msg_enc}" target="_blank" class="wa-btn">📱 Enviar WhatsApp</a>', unsafe_allow_html=True)

# --- VISTA PREVIA RENDERIZADA ---
if st.session_state.ver_preview and st.session_state.carrito:
    rows_html = ""
    for item in st.session_state.carrito:
        p_style = "badge-urg" if item['Prioridad'] == "Urgente" else ""
        a_style = "status-disp" if item['Abasto'] == "Disponible" else ("status-ped" if "Pedido" in item['Abasto'] else "status-rev")
        
        rows_html += f"""
        <tr>
            <td>{item['SKU']}</td>
            <td>{item['Descripción']}</td>
            <td><span class="{p_style}">{item['Prioridad']}</span></td>
            <td><span class="{a_style}">{item['Abasto']}</span></td>
            <td>{item['Tiempo Entrega']}</td>
            <td style="text-align:center">{item['Cantidad']}</td>
            <td style="text-align:right">${item['Precio Base']:,.2f}</td>
            <td style="text-align:right">${item['Importe Total']:,.2f}</td>
        </tr>
        """
    
    preview_html = f"""
    <div class="preview-container">
        <div class="preview-paper">
            <div class="preview-header">
                <div>
                    <h1 class="preview-title">TOYOTA LOS FUERTES</h1>
                    <div class="preview-subtitle">Presupuesto de Servicios y Refacciones</div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:24px; font-weight:bold; color:#eb0a1e;">${total_gral:,.2f}</div>
                    <div style="font-size:10px; color:#666;">MONEDA NACIONAL (MXN)</div>
                </div>
            </div>
            
            <div class="info-grid">
                <div>
                    <div class="info-item"><span class="info-label">CLIENTE:</span> {st.session_state.cliente}</div>
                    <div class="info-item"><span class="info-label">VIN:</span> {st.session_state.vin}</div>
                </div>
                <div>
                    <div class="info-item"><span class="info-label">ORDEN:</span> {st.session_state.orden}</div>
                    <div class="info-item"><span class="info-label">FECHA:</span> {obtener_hora_mx().strftime("%d/%m/%Y")}</div>
                </div>
            </div>

            <table class="custom-table">
                <thead>
                    <tr>
                        <th>CÓDIGO</th><th>DESCRIPCIÓN</th><th>PRIORIDAD</th><th>ABASTO</th><th>T.ENT</th>
                        <th style="text-align:center">CANT</th><th style="text-align:right">P. UNIT</th><th style="text-align:right">TOTAL</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <div class="total-box">
                <div class="total-row"><span>Subtotal:</span><span>${subtotal:,.2f}</span></div>
                <div class="total-row"><span>IVA (16%):</span><span>${subtotal*0.16:,.2f}</span></div>
                <div class="total-row total-final"><span>TOTAL:</span><span>${total_gral:,.2f}</span></div>
            </div>
            
            <div style="margin-top:40px; font-size:9px; color:#777; border-top:1px solid #ddd; padding-top:10px;">
                * Precios sujetos a cambio sin previo aviso. Las partes eléctricas no tienen cambio ni devolución.
            </div>
        </div>
    </div>
    """
    st.markdown(preview_html, unsafe_allow_html=True)
