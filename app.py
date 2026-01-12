import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import urllib.parse
from datetime import datetime
from fpdf import FPDF
from PIL import Image
from pyzbar.pyzbar import decode
import pytz  # Librería necesaria para la zona horaria

# 1. CONFIGURACIÓN DE PÁGINA Y ZONA HORARIA
st.set_page_config(page_title="Toyota Los Fuertes", page_icon="🚗", layout="wide")

# Configurar Zona Horaria CDMX
try:
    tz_cdmx = pytz.timezone('America/Mexico_City')
except:
    # Fallback si pytz falla
    tz_cdmx = None 

def obtener_hora_mx():
    if tz_cdmx:
        return datetime.now(tz_cdmx)
    return datetime.now()

# Inicializar variables
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 2. ESTILOS CSS
st.markdown("""
    <style>
    h1 { color: #eb0a1e !important; text-align: center; }
    .stButton button { width: 100%; border-radius: 5px; font-weight: bold; }
    .legal-footer {
        text-align: center;
        font-size: 11px;
        opacity: 0.7;
        margin-top: 50px;
        padding-top: 20px;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        font-family: sans-serif;
    }
    /* Estilo para los inputs de datos del cliente */
    .datos-cliente {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CLASE PDF (GENERADOR DE DOCUMENTO) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(235, 10, 30) # Rojo Toyota
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
    
    # --- DATOS DE FECHA Y CLIENTE ---
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0)
    
    fecha_mx = obtener_hora_mx().strftime("%d/%m/%Y %H:%M")
    
    # Bloque de información del cliente
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(10, 35, 190, 25, 'F') # Caja gris de fondo
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

    # Encabezados de Tabla
    pdf.set_fill_color(235, 10, 30)
    pdf.set_text_color(255)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(15, 8, 'Cant.', 1, 0, 'C', True)
    pdf.cell(35, 8, 'SKU', 1, 0, 'C', True)
    pdf.cell(85, 8, 'Descripcion', 1, 0, 'C', True)
    pdf.cell(25, 8, 'P. Base', 1, 0, 'C', True)
    pdf.cell(30, 8, 'Importe', 1, 1, 'C', True)

    # Contenido
    pdf.set_text_color(0)
    pdf.set_font('Arial', '', 8)
    for item in carrito:
        desc = item['Descripción'][:50]
        pdf.cell(15, 8, str(int(item['Cantidad'])), 1, 0, 'C')
        pdf.cell(35, 8, item['SKU'], 1, 0, 'C')
        pdf.cell(85, 8, desc, 1, 0, 'L')
        pdf.cell(25, 8, f"${item['Precio Base']:,.2f}", 1, 0, 'R')
        pdf.cell(30, 8, f"${item['Importe']:,.2f}", 1, 1, 'R')

    pdf.ln(5)
    
    # Totales
    pdf.set_font('Arial', '', 10)
    pdf.cell(135)
    pdf.cell(25, 6, 'Subtotal:', 0, 0, 'R')
    pdf.cell(30, 6, f"${subtotal:,.2f}", 0, 1, 'R')
    
    pdf.cell(135)
    pdf.cell(25, 6, 'IVA (16%):', 0, 0, 'R')
    pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(235, 10, 30)
    pdf.cell(135)
    pdf.cell(25, 8, 'TOTAL:', 0, 0, 'R')
    pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')

    # Firma
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

# Carga de datos
@st.cache_data
def cargar_catalogo():
    try:
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        df.columns = [c.strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return None

df = cargar_catalogo()
# Obtener fecha hora CDMX
fecha_actual_mx = obtener_hora_mx()
fecha_hoy_str = fecha_actual_mx.strftime("%d/%m/%Y")
hora_hoy_str = fecha_actual_mx.strftime("%H:%M")

# --- INTERFAZ PRINCIPAL ---

st.title("TOYOTA LOS FUERTES")
st.markdown("<h4 style='text-align: center; opacity: 0.6;'>Sistema de Cotización y Consulta de Precios</h4>", unsafe_allow_html=True)
st.write("---")

# 0. DATOS DEL CLIENTE Y VEHÍCULO (NUEVA SECCIÓN)
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

# 1. SECCIÓN DE ESCÁNER Y BÚSQUEDA
sku_detectado = ""

# Checkbox para activar cámara
if st.checkbox("📸 Activar Escáner de Código de Barras"):
    st.info("Apunta la cámara al código de barras de la caja.")
    img_file = st.camera_input("Toma una foto clara del código", label_visibility="collapsed")
    if img_file is not None:
        try:
            imagen = Image.open(img_file)
            codigos = decode(imagen)
            if codigos:
                sku_detectado = codigos[0].data.decode("utf-8")
                st.success(f"✅ Código detectado: **{sku_detectado}**")
            else:
                st.warning("⚠️ No se detectó código. Intenta mejorar la luz.")
        except Exception as e:
            st.error(f"Error: {e}")

if df is not None:
    valor_inicial = sku_detectado if sku_detectado else ""
    
    col_search, col_date = st.columns([4, 1])
    with col_search:
        busqueda = st.text_input("🔍 Buscar Refacción (SKU o Nombre):", value=valor_inicial, placeholder="Ej. Filtro, 90430...")
    with col_date:
        # Mostramos la hora de CDMX
        st.markdown(f"**CDMX:**\n{fecha_hoy_str}\n{hora_hoy_str}")

    if busqueda:
        busqueda = busqueda.upper().strip()
        mask = df.apply(lambda x: x.astype(str).str.contains(busqueda, case=False)).any(axis=1)
        resultados = df[mask].head(10).copy() 

        if not resultados.empty:
            c_sku = [c for c in resultados.columns if 'PART' in c or 'NUM' in c][0]
            c_desc = [c for c in resultados.columns if 'DESC' in c][0]
            c_precio = [c for c in resultados.columns if 'PRICE' in c or 'PRECIO' in c][0]

            st.success("Resultados encontrados:")
            for i, row in resultados.iterrows():
                desc_es = traducir_profe(row[c_desc])
                sku_val = row[c_sku]
                try:
                    precio_texto = str(row[c_precio]).replace(',', '').replace('$', '').strip()
                    precio_val = float(precio_texto)
                except: precio_val = 0.0

                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**{desc_es}**")
                        st.caption(f"SKU: {sku_val} | Base: ${precio_val:,.2f}")
                    with c2:
                        cantidad = st.number_input("Cant.", min_value=1, value=1, key=f"cant_{i}", label_visibility="collapsed")
                    with c3:
                        if st.button("Añadir ➕", key=f"add_{i}"):
                            st.session_state.carrito.append({
                                "SKU": sku_val, "Descripción": desc_es, "Precio Base": precio_val,
                                "Cantidad": cantidad, "Importe": precio_val * cantidad
                            })
                            st.toast("✅ Agregado")
                    st.divider() 
        else:
            st.warning("No se encontraron resultados.")

# 2. SECCIÓN DE SERVICIOS
st.markdown("### 🛠️ Agregar Servicios / Mano de Obra")
with st.expander("Clic aquí para agregar servicios", expanded=False):
    st.info("💡 Ingresa el precio **sin IVA**. El sistema agregará el 16% al final.")
    ce1, ce2, ce3 = st.columns([2, 1, 1])
    with ce1:
        opciones = ["Mano de Obra", "Pintura", "Hojalatería", "Instalación", "Servicio Foráneo", "Diagnóstico", "Otro"]
        tipo = st.selectbox("Tipo:", opciones)
        desc_final = st.text_input("Descripción:", value="Servicio General") if tipo == "Otro" else tipo
    with ce2:
        precio_manual = st.number_input("Costo (Base):", min_value=0.0, format="%.2f")
    with ce3:
        st.write("")
        st.write("")
        if st.button("Agregar 🔧"):
            if precio_manual > 0:
                st.session_state.carrito.append({
                    "SKU": "SERV", "Descripción": desc_final, "Precio Base": precio_manual,
                    "Cantidad": 1, "Importe": precio_manual
                })
                st.rerun()

# 3. CARRITO DE COMPRAS
if st.session_state.carrito:
    st.write("---")
    st.subheader(f"🛒 Carrito de Cotización")
    
    df_carro = pd.DataFrame(st.session_state.carrito)
    st.dataframe(df_carro, hide_index=True, use_container_width=True)
    
    subtotal = df_carro['Importe'].sum()
    iva = subtotal * 0.16
    gran_total = subtotal + iva

    c_sub, c_iva, c_tot = st.columns(3)
    c_sub.metric("Subtotal", f"${subtotal:,.2f}")
    c_iva.metric("IVA (16%)", f"${iva:,.2f}")
    c_tot.metric("TOTAL NETO", f"${gran_total:,.2f}")

    col_pdf, col_del, col_wa = st.columns([1, 1, 2])
    
    with col_pdf:
        try:
            # Enviamos también los datos del cliente al generador PDF
            pdf_bytes = generar_pdf_bytes(
                st.session_state.carrito, subtotal, iva, gran_total,
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
        if st.button("🗑️ Vaciar"):
            st.session_state.carrito = []
            st.rerun()
            
    with col_wa:
        # Mensaje WhatsApp mejorado con datos del cliente
        msg = f"*COTIZACIÓN TOYOTA LOS FUERTES*\n📅 {fecha_hoy_str} {hora_hoy_str}\n"
        if cliente_input: msg += f"👤 Cliente: {cliente_input}\n"
        if vin_input: msg += f"🚗 VIN: {vin_input}\n"
        if orden_input: msg += f"📄 Orden: {orden_input}\n"
        msg += "\n"
        
        for _, row in df_carro.iterrows():
            msg += f"▪ {row['Cantidad']}x {row['Descripción']} (${row['Importe']:,.2f})\n"
        msg += f"\nSubtotal: ${subtotal:,.2f}\nIVA: ${iva:,.2f}\n*TOTAL: ${gran_total:,.2f}*"
        msg += "\n\n_Vigencia: 24 horas_"
        link = f"https://wa.me/?text={urllib.parse.quote(msg)}"
        st.link_button("📲 Enviar WhatsApp", link)

# FOOTER LEGAL
st.markdown(f"""
    <div class="legal-footer">
        <strong>TOYOTA LOS FUERTES - INFORMACIÓN AL CONSUMIDOR</strong><br>
        1. Precios vigentes al día: <strong>{fecha_hoy_str}</strong> (Hora CDMX).<br>
        2. Todos los montos incluyen IVA (16%).<br>
        3. Esta consulta cumple con la obligación de exhibición de precios conforme al <strong>Art. 7 de la LFPC</strong>.<br>
        4. Las descripciones de productos cumplen con la <strong>NOM-050-SCFI-2004</strong>.<br>
        5. <strong>IMPORTANTE:</strong> Esta cotización tiene una vigencia de <strong>24 horas</strong> a partir de su emisión.
    </div>
""", unsafe_allow_html=True)
