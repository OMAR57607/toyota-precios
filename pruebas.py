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
if 'carrito' not in st.session_state:
    st.session_state.carrito = []
if 'errores_carga' not in st.session_state:
    st.session_state.errores_carga = [] 

@st.cache_resource
def cargar_lector_ocr():
    return easyocr.Reader(['en'], gpu=False) 

# 2. ESTILOS CSS
st.markdown("""
    <style>
    h1 { color: #eb0a1e !important; text-align: center; }
    .stButton button { width: 100%; border-radius: 5px; font-weight: bold; }
    .error-box {
        background-color: #ffcccc;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #ff0000;
        margin-bottom: 10px;
        color: #333;
    }
    .legal-footer {
        text-align: center; font-size: 11px; opacity: 0.7;
        margin-top: 50px; padding-top: 20px;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        font-family: sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CLASE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(235, 10, 30)
        self.cell(0, 10, 'TOYOTA LOS FUERTES', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.set_text_color(0)
        self.cell(0, 5, 'COTIZACION DE REFACCIONES Y SERVICIOS', 0, 1, 'C')
        self.ln(5)

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
    pdf.rect(10, 35, 190, 25, 'F')
    pdf.set_xy(12, 38)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 6, 'Fecha:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 6, fecha_mx, 0, 0)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 6, 'No. Orden:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(60, 6, orden if orden else "S/N", 0, 1)
    
    pdf.set_x(12)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 6, 'Cliente:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(150, 6, cliente if cliente else "Mostrador", 0, 1)

    pdf.set_x(12)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 6, 'VIN:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(150, 6, vin if vin else "N/A", 0, 1)
    pdf.ln(10)

    # --- ENCABEZADOS DE TABLA ---
    pdf.set_fill_color(235, 10, 30)
    pdf.set_text_color(255)
    pdf.set_font('Arial', 'B', 8)
    
    w_sku = 30
    w_desc = 60
    w_cant = 10
    w_base = 25
    w_iva = 20
    w_total = 25
    w_estatus = 20

    pdf.cell(w_sku, 8, 'SKU', 1, 0, 'C', True)
    pdf.cell(w_desc, 8, 'Descripcion', 1, 0, 'C', True)
    pdf.cell(w_cant, 8, 'Cant.', 1, 0, 'C', True)
    pdf.cell(w_base, 8, 'P. Base', 1, 0, 'C', True)
    pdf.cell(w_iva, 8, 'IVA', 1, 0, 'C', True)
    pdf.cell(w_total, 8, 'Total', 1, 0, 'C', True)
    pdf.cell(w_estatus, 8, 'Estatus', 1, 1, 'C', True)

    # --- CONTENIDO DE TABLA ---
    pdf.set_text_color(0)
    pdf.set_font('Arial', '', 7)
    
    for item in carrito:
        desc = item['Descripción'][:40]
        pdf.cell(w_sku, 8, item['SKU'], 1, 0, 'C')
        pdf.cell(w_desc, 8, desc, 1, 0, 'L')
        pdf.cell(w_cant, 8, str(int(item['Cantidad'])), 1, 0, 'C')
        pdf.cell(w_base, 8, f"${item['Precio Base']:,.2f}", 1, 0, 'R')
        pdf.cell(w_iva, 8, f"${item['IVA']:,.2f}", 1, 0, 'R')
        pdf.cell(w_total, 8, f"${item['Importe Total']:,.2f}", 1, 0, 'R')
        
        st_txt = item['Estatus']
        pdf.set_font('Arial', 'B', 7)
        if "Back Order" in st_txt: pdf.set_text_color(200, 0, 0)
        elif "No" in st_txt: pdf.set_text_color(100, 100, 100)
        else: pdf.set_text_color(0, 100, 0)
        pdf.cell(w_estatus, 8, st_txt, 1, 1, 'C')
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
    pdf.set_text_color(235, 10, 30)
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
        
        # Limpiar precio
        df['PRECIO_NUM'] = df[c_precio].astype(str).str.replace('$', '').str.replace(',', '').apply(lambda x: float(x) if x.replace('.', '', 1).isdigit() else 0.0)
        
        return df, c_sku, c_desc
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return None, None, None

df, col_sku_db, col_desc_db = cargar_catalogo()
fecha_actual_mx = obtener_hora_mx()
fecha_hoy_str = fecha_actual_mx.strftime("%d/%m/%Y")
hora_hoy_str = fecha_actual_mx.strftime("%H:%M")

# --- FUNCIÓN AUXILIAR: PROCESAR MASIVO ---
def procesar_lista_sku(lista_skus):
    encontrados = 0
    errores = []
    
    for item in lista_skus:
        sku_raw = str(item['sku']).upper().strip()
        sku_clean = sku_raw.replace('-', '')
        cant = int(item['cant'])
        
        match = df[df['SKU_CLEAN'] == sku_clean]
        
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

st.sidebar.title("Menú Asesor")
modo = st.sidebar.radio("Selecciona una opción:", ["🔍 Cotizador Manual", "📂 Importador Masivo"])

st.title("TOYOTA LOS FUERTES")
st.markdown(f"<div style='text-align: right; opacity: 0.6;'>{fecha_hoy_str} {hora_hoy_str}</div>", unsafe_allow_html=True)

# ==========================================
# MODO 1: COTIZADOR MANUAL (MEJORADO CON ALTA MANUAL)
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
    
    # Escáner
    sku_detectado = ""
    if st.checkbox("📸 Activar Escáner"):
        img_file = st.camera_input("Foto", label_visibility="collapsed")
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
    # Buscador Manual
    busqueda = st.text_input("🔍 Buscar SKU o Nombre:", value=val_ini)
    
    if busqueda and df is not None:
        b_raw = busqueda.upper().strip()
        b_clean = b_raw.replace('-', '')
        mask = df.apply(lambda x: x.astype(str).str.contains(b_raw, case=False)).any(axis=1) | df['SKU_CLEAN'].str.contains(b_clean, na=False)
        res = df[mask].head(10)
        
        if not res.empty:
            # ---> CASO A: ENCONTRADO (Muestra Resultados)
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
                        if st.button("➕", key=f"a_{i}"):
                            iva = (precio_val * cant) * 0.16
                            tot = (precio_val * cant) + iva
                            st.session_state.carrito.append({
                                "SKU": sku_val, "Descripción": desc_es, "Cantidad": cant,
                                "Precio Base": precio_val, "IVA": iva, "Importe Total": tot, "Estatus": est
                            })
                            st.toast("Agregado")
                    st.divider()
        else:
            # ---> CASO B: NO ENCONTRADO (Muestra Formulario Manual)
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
                            "SKU": m_sku,
                            "Descripción": m_desc,
                            "Cantidad": 1,
                            "Precio Base": m_precio,
                            "IVA": iva_m,
                            "Importe Total": tot_m,
                            "Estatus": "Disponible"
                        })
                        st.toast("✅ Agregado Manualmente")
                        st.rerun()

# ==========================================
# MODO 2: IMPORTADOR MASIVO
# ==========================================
elif modo == "📂 Importador Masivo":
    st.markdown("### ⚡ Carga Rápida de Órdenes")
    st.info("Sube un archivo o pega una lista. Si un código no existe, podrás agregarlo manualmente.")
    
    col_m1, col_m2 = st.columns(2)
    with col_m1: cliente_input = st.text_input("👤 Cliente")
    with col_m2: orden_input = st.text_input("📄 Orden")
    vin_input = ""
    
    # MANEJO DE ERRORES MASIVOS
    if st.session_state.errores_carga:
        st.markdown(f"""
        <div class="error-box">
            <strong>⚠️ Faltantes:</strong> {', '.join(st.session_state.errores_carga)}
        </div>
        """, unsafe_allow_html=True)
        
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
                    
                    if m_sku in st.session_state.errores_carga:
                        st.session_state.errores_carga.remove(m_sku)
                    st.rerun()
            
            if st.button("Ignorar Restantes"):
                st.session_state.errores_carga = []
                st.rerun()

    # TABS
    tab1, tab2, tab3 = st.tabs(["📋 Pegar Lista", "📊 Excel", "📷 Foto"])
    
    with tab1:
        txt = st.text_area("SKUs:", height=100)
        if st.button("Procesar Lista"):
            lines = txt.split('\n')
            lst = [{'sku': l, 'cant': 1} for l in lines if len(l.strip()) > 4]
            ok, fail = procesar_lista_sku(lst)
            st.session_state.errores_carga = fail
            if ok > 0: st.success(f"✅ Agregados {ok}.")
            st.rerun()

    with tab2:
        upl = st.file_uploader("Excel", type=['xlsx'])
        if upl and st.button("Cargar Excel"):
            try:
                d = pd.read_excel(upl)
                d.columns = [c.upper().strip() for c in d.columns]
                c_s = next((c for c in d.columns if 'SKU' in c or 'PART' in c), None)
                c_q = next((c for c in d.columns if 'CANT' in c or 'QTY' in c), None)
                if c_s:
                    lst = [{'sku': r[c_s], 'cant': int(r[c_q]) if c_q and pd.notna(r[c_q]) else 1} for _, r in d.iterrows() if pd.notna(r[c_s])]
                    ok, fail = procesar_lista_sku(lst)
                    st.session_state.errores_carga = fail
                    st.success(f"✅ Agregados {ok}.")
                    st.rerun()
            except: st.error("Error leyendo Excel.")

    with tab3:
        cam = st.camera_input("Foto", key="cam_m")
        if cam:
            with st.spinner("Analizando..."):
                r = cargar_lector_ocr()
                res = r.readtext(np.array(Image.open(cam)), detail=0)
                lst = []
                for t in res:
                    t = t.upper().replace(' ', '')
                    if re.search(r'[A-Z0-9]{5}-?[A-Z0-9]{5}', t): lst.append({'sku': t, 'cant': 1})
                if lst:
                    if st.button("Agregar"):
                        ok, fail = procesar_lista_sku(lst)
                        st.session_state.errores_carga = fail
                        st.success(f"✅ Agregados {ok}.")
                        st.rerun()

# ==========================================
# CARRITO GLOBAL
# ==========================================
if st.session_state.carrito:
    st.write("---")
    st.subheader(f"🛒 Cotización Generada")
    
    df_c = pd.DataFrame(st.session_state.carrito)
    cols = ["SKU", "Descripción", "Cantidad", "Precio Base", "IVA", "Importe Total", "Estatus"]
    st.dataframe(df_c[cols], hide_index=True, use_container_width=True)
    
    sub = (df_c['Precio Base']*df_c['Cantidad']).sum()
    iva = df_c['IVA'].sum()
    tot = df_c['Importe Total'].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Subtotal", f"${sub:,.2f}")
    c2.metric("IVA", f"${iva:,.2f}")
    c3.metric("TOTAL", f"${tot:,.2f}")
    
    c_pdf, c_del = st.columns([1, 1])
    with c_pdf:
        cli = cliente_input
        ord_n = orden_input
        vin_n = vin_input if modo == "🔍 Cotizador Manual" else "N/A"
        pdf = generar_pdf_bytes(st.session_state.carrito, sub, iva, tot, cli, vin_n, ord_n)
        st.download_button("Descargar PDF", pdf, "Cotizacion.pdf", "application/pdf", type="primary")
    with c_del:
        if st.button("Limpiar Todo"):
            st.session_state.carrito = []
            st.session_state.errores_carga = []
            st.rerun()

# FOOTER
st.markdown(f"""
    <div class="legal-footer">
        <strong>TOYOTA LOS FUERTES - USO INTERNO ASESORES</strong><br>
        Sistema de Cotización Avanzado v2.2
    </div>
""", unsafe_allow_html=True)
