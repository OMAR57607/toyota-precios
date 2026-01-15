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
import zipfile

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Toyota Los Fuertes - Verificador", page_icon="🚗", layout="wide")

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

@st.cache_resource
def cargar_lector_ocr():
    return easyocr.Reader(['en'], gpu=False) 

# 2. ESTILOS CSS
st.markdown("""
    <style>
    h1 { color: #eb0a1e !important; text-align: center; }
    .stButton button { width: 100%; border-radius: 5px; font-weight: bold; }
    
    /* Estilo para el Precio Total Grande */
    .precio-total {
        font-size: 24px;
        font-weight: bold;
        color: #eb0a1e;
        text-align: right;
    }
    .desglose-impuestos {
        font-size: 12px;
        color: #666;
        text-align: right;
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

    # --- ENCABEZADOS DE TABLA PDF ---
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

    pdf.cell(w_sku, 8, 'ITEM', 1, 0, 'C', True)
    pdf.cell(w_desc, 8, 'Descripcion', 1, 0, 'C', True)
    pdf.cell(w_cant, 8, 'Cant.', 1, 0, 'C', True)
    pdf.cell(w_base, 8, 'P. Unit', 1, 0, 'C', True)
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

# --- CARGA DE DATOS (AJUSTADO PARA ITEM / DESCRIPCION / TOTAL_UNITARIO) ---
@st.cache_data
def cargar_catalogo():
    try:
        with zipfile.ZipFile("lista_precios.zip", "r") as z:
            archivos_dentro = [f for f in z.namelist() if f.endswith('.xlsx')]
            if not archivos_dentro:
                st.error("Error: El ZIP no tiene archivos .xlsx")
                return None
            nombre_archivo_excel = archivos_dentro[0]
            
            with z.open(nombre_archivo_excel) as f:
                df = pd.read_excel(f, dtype=str)

        # Limpieza
        df.dropna(how='all', inplace=True)
        # Convertimos todo a mayúsculas para evitar errores (Ej. Item vs ITEM)
        df.columns = [c.strip().upper() for c in df.columns]
        
        # --- BÚSQUEDA ESPECÍFICA DE TUS COLUMNAS ---
        # 1. Buscar ITEM (SKU)
        c_sku = [c for c in df.columns if 'ITEM' in c or 'PART' in c or 'SKU' in c]
        if not c_sku:
            st.error(f"Error: No se encontró columna 'ITEM'. Columnas detectadas: {list(df.columns)}")
            return None
        c_sku = c_sku[0]

        df.drop_duplicates(subset=[c_sku], keep='first', inplace=True)
        df['SKU_CLEAN'] = df[c_sku].astype(str).str.replace('-', '').str.strip().str.upper()
        
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return None

df = cargar_catalogo()
fecha_actual_mx = obtener_hora_mx()
fecha_hoy_str = fecha_actual_mx.strftime("%d/%m/%Y")
hora_hoy_str = fecha_actual_mx.strftime("%H:%M")

# --- INTERFAZ PRINCIPAL ---

st.title("TOYOTA LOS FUERTES")
st.markdown("<h4 style='text-align: center; opacity: 0.6;'>Verificador de Precios y Cotizador</h4>", unsafe_allow_html=True)
st.write("---")

# 0. DATOS DEL CLIENTE
with st.container():
    st.markdown("### 📝 Datos de la Cotización")
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        cliente_input = st.text_input("👤 Nombre del Cliente", placeholder="Ej. Juan Pérez")
    with col_d2:
        vin_input = st.text_input("🚗 VIN (Número de Serie)", placeholder="17 Dígitos", max_chars=17)
    with col_d3:
        orden_input = st.text_input("📄 Número de Orden", placeholder="Ej. OR-12345")

st.write("---")

# 1. ESCÁNER Y BÚSQUEDA
sku_detectado = ""

if st.checkbox("📸 Activar Escáner (Barras / Texto Caja)"):
    st.info("El sistema buscará código de barras. Si no encuentra, intentará leer el texto de la caja.")
    img_file = st.camera_input("Toma una foto clara", label_visibility="collapsed")
    if img_file is not None:
        try:
            imagen_pil = Image.open(img_file)
            codigos = decode(imagen_pil)
            if codigos:
                sku_detectado = codigos[0].data.decode("utf-8")
                st.success(f"✅ Código Barras: **{sku_detectado}**")
            else:
                with st.spinner("Escaneando texto (OCR)..."):
                    reader = cargar_lector_ocr()
                    result = reader.readtext(np.array(imagen_pil))
                    possibles = [txt for (bbox, txt, prob) in result if len(txt) > 4 and prob > 0.4]
                    if possibles:
                        sku_detectado = possibles[0] 
                        st.success(f"👁️ OCR Detectado: **{sku_detectado}**")
                    else:
                        st.warning("⚠️ No se detectó código ni texto legible.")
        except Exception as e: st.error(f"Error escáner: {e}")

if df is not None:
    valor_inicial = sku_detectado if sku_detectado else ""
    col_search, col_date = st.columns([4, 1])
    with col_search:
        st.markdown("Busca por ITEM/SKU (con/sin guiones) o Nombre:")
        busqueda = st.text_input("Input Búsqueda", value=valor_inicial, label_visibility="collapsed", placeholder="Ej. 90915YZZD1")
    with col_date:
        st.markdown(f"**CDMX:**\n{fecha_hoy_str}\n{hora_hoy_str}")

    if busqueda:
        busqueda_raw = busqueda.upper().strip()
        busqueda_clean = busqueda_raw.replace('-', '')
        
        mask_desc = df.apply(lambda x: x.astype(str).str.contains(busqueda_raw, case=False)).any(axis=1)
        mask_sku = df['SKU_CLEAN'].str.contains(busqueda_clean, na=False)
        resultados = df[mask_desc | mask_sku].head(10).copy() 

        if not resultados.empty:
            # --- MAPEADO DINÁMICO DE COLUMNAS (AQUÍ ESTABA EL ERROR) ---
            # Ahora buscamos explícitamente ITEM, DESCRIPCION y TOTAL_UNITARIO
            
            # 1. SKU / ITEM
            c_sku = [c for c in resultados.columns if 'ITEM' in c or 'PART' in c or 'SKU' in c][0]
            
            # 2. DESCRIPCION
            c_desc = [c for c in resultados.columns if 'DESC' in c][0]
            
            # 3. PRECIO (TOTAL_UNITARIO)
            # Buscamos 'TOTAL', 'UNITARIO', 'PRICE' o 'PRECIO'
            c_precios_posibles = [c for c in resultados.columns if 'TOTAL' in c or 'UNITARIO' in c or 'PRICE' in c or 'PRECIO' in c]
            
            if c_precios_posibles:
                c_precio = c_precios_posibles[0]
            else:
                st.error("No se encontró columna de precio (TOTAL_UNITARIO)")
                st.stop()

            st.success(f"Resultados encontrados:")
            
            for i, row in resultados.iterrows():
                desc_es = traducir_profe(row[c_desc])
                sku_val = row[c_sku]
                try:
                    precio_texto = str(row[c_precio]).replace(',', '').replace('$', '').strip()
                    precio_val = float(precio_texto)
                except: precio_val = 0.0

                # NOTA: Asumimos que "TOTAL_UNITARIO" es el Precio Lista (Base)
                # Si tu archivo ya tiene IVA incluido en esa columna, avísame para quitar esta suma.
                iva_unitario = precio_val * 0.16
                total_unitario = precio_val + iva_unitario

                with st.container():
                    c1, c2, c3 = st.columns([3, 1.5, 1])
                    
                    with c1:
                        st.markdown(f"**{desc_es}**")
                        st.caption(f"ITEM: {sku_val}")
                    
                    with c2:
                        st.markdown(f'<div class="precio-total">${total_unitario:,.2f}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="desglose-impuestos">Unitario: ${precio_val:,.2f} | IVA: ${iva_unitario:,.2f}</div>', unsafe_allow_html=True)
                    
                    with c3:
                        estatus = st.selectbox("Estatus", ["Disponible", "No Disponible", "Back Order"], key=f"st_{i}", label_visibility="collapsed")
                        if st.button("Agregar ➕", key=f"add_{i}"):
                            cantidad = 1 
                            st.session_state.carrito.append({
                                "SKU": sku_val,
                                "Descripción": desc_es,
                                "Cantidad": cantidad,
                                "Precio Base": precio_val,
                                "IVA": iva_unitario,
                                "Importe Total": total_unitario,
                                "Estatus": estatus
                            })
                            st.toast("✅ Agregado al carrito")
                    
                    st.divider() 
        else:
            st.warning("No se encontraron resultados.")

# 2. SECCIÓN DE SERVICIOS
st.markdown("### 🛠️ Agregar Servicios / Mano de Obra")
with st.expander("Clic aquí para agregar servicios", expanded=False):
    st.info("💡 Ingresa el precio base, el sistema agregará el IVA automáticamente.")
    ce1, ce2, ce3 = st.columns([3, 1, 1])
    
    with ce1:
        opciones = ["Mano de Obra", "Pintura", "Hojalatería", "Instalación", "Servicio Foráneo", "Diagnóstico", "Otro"]
        tipo = st.selectbox("Tipo:", opciones)
        desc_final = st.text_input("Descripción:", value="Servicio General") if tipo == "Otro" else tipo
    with ce2:
        precio_manual = st.number_input("Costo Base (Sin IVA):", min_value=0.0, format="%.2f")
        if precio_manual > 0:
             iva_manual = precio_manual * 0.16
             total_manual = precio_manual + iva_manual
             st.markdown(f"**Total c/IVA: ${total_manual:,.2f}**")
    with ce3:
        st.write("")
        st.write("")
        if st.button("Agregar 🔧"):
            if precio_manual > 0:
                iva_serv = precio_manual * 0.16
                total_serv = precio_manual + iva_serv
                
                st.session_state.carrito.append({
                    "SKU": "SERV",
                    "Descripción": desc_final,
                    "Cantidad": 1,
                    "Precio Base": precio_manual,
                    "IVA": iva_serv,
                    "Importe Total": total_serv,
                    "Estatus": "Disponible" 
                })
                st.rerun()

# 3. CARRITO DE COMPRAS
if st.session_state.carrito:
    st.write("---")
    st.subheader(f"🛒 Resumen de Cotización")
    
    df_carro = pd.DataFrame(st.session_state.carrito)
    
    st.dataframe(
        df_carro[["SKU", "Descripción", "Importe Total", "Estatus"]], 
        hide_index=True, 
        use_container_width=True,
        column_config={
            "Importe Total": st.column_config.NumberColumn(
                "Total (Neto)",
                format="$%.2f"
            )
        }
    )
    
    subtotal_sum = df_carro['Precio Base'].sum()
    iva_sum = df_carro['IVA'].sum()
    gran_total = df_carro['Importe Total'].sum()

    st.markdown(f"""
    <div style="background-color: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px solid #ddd; text-align: right;">
        <span style="font-size: 16px;">Subtotal: ${subtotal_sum:,.2f}</span><br>
        <span style="font-size: 16px;">IVA (16%): ${iva_sum:,.2f}</span><br>
        <hr style="margin: 10px 0;">
        <span style="font-size: 32px; font-weight: bold; color: #eb0a1e;">TOTAL NETO: ${gran_total:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")

    col_pdf, col_del, col_wa = st.columns([1, 1, 2])
    
    with col_pdf:
        try:
            pdf_bytes = generar_pdf_bytes(
                st.session_state.carrito, subtotal_sum, iva_sum, gran_total,
                cliente_input, vin_input, orden_input
            )
            st.download_button(
                label="📄 Descargar PDF",
                data=pdf_bytes,
                file_name=f"Cotizacion_{orden_input if orden_input else 'Toyota'}.pdf",
                mime="application/pdf",
                type="primary"
            )
        except Exception as e: st.error(f"Error PDF: {e}")

    with col_del:
        if st.button("🗑️ Nueva Consulta"):
            st.session_state.carrito = []
            st.rerun()
            
    with col_wa:
        msg = f"*COTIZACIÓN TOYOTA LOS FUERTES*\n📅 {fecha_hoy_str} {hora_hoy_str}\n"
        if cliente_input: msg += f"👤 Cliente: {cliente_input}\n"
        if vin_input: msg += f"🚗 VIN: {vin_input}\n"
        msg += "\n*PIEZAS (Precios Netos):*\n"
        
        for _, row in df_carro.iterrows():
            estatus_icon = "✅" if row['Estatus'] == "Disponible" else ("⏳" if "Back" in row['Estatus'] else "❌")
            msg += f"{estatus_icon} *{row['SKU']}* | ${row['Importe Total']:,.2f}\n"
            msg += f"   {row['Descripción']}\n"
            
        msg += f"\n*TOTAL A PAGAR: ${gran_total:,.2f}* (Incluye IVA)"
        msg += "\n\n_Vigencia: 24 horas_"
        link = f"https://wa.me/?text={urllib.parse.quote(msg)}"
        st.link_button("📲 Enviar Resumen WhatsApp", link)

# FOOTER
st.markdown(f"""
    <div class="legal-footer">
        <strong>TOYOTA LOS FUERTES - INFORMACIÓN AL CONSUMIDOR</strong><br>
        1. Precios vigentes al día: <strong>{fecha_hoy_str}</strong> (Hora CDMX).<br>
        2. Los precios mostrados en GRANDE ya incluyen IVA (16%).<br>
        3. Esta consulta cumple con la obligación de exhibición de precios conforme al <strong>Art. 7 de la LFPC</strong>.<br>
        4. <strong>IMPORTANTE:</strong> Esta cotización tiene una vigencia de <strong>24 horas</strong>.
    </div>
""", unsafe_allow_html=True)
