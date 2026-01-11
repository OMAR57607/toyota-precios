import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import urllib.parse
from datetime import datetime
from fpdf import FPDF
import base64

# 1. Configuración de página
st.set_page_config(page_title="Toyota Los Fuertes", page_icon="🚗", layout="wide")

# Inicializar variables
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 2. ESTILOS CSS (Limpios, ya no necesitamos el hack de impresión)
st.markdown("""
    <style>
    h1 { color: #eb0a1e !important; }
    .stButton button { width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- CLASE PARA GENERAR EL PDF ---
class PDF(FPDF):
    def header(self):
        # Título
        self.set_font('Arial', 'B', 16)
        self.set_text_color(235, 10, 30) # Rojo Toyota
        self.cell(0, 10, 'TOYOTA LOS FUERTES', 0, 1, 'C')
        # Subtítulo
        self.set_font('Arial', '', 10)
        self.set_text_color(0, 0, 0)
        self.cell(0, 5, 'COTIZACION DE REFACCIONES Y SERVICIOS', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.multi_cell(0, 4, 'Precios en Moneda Nacional (MXN). Sujetos a cambio sin previo aviso. Descripciones traducidas bajo NOM-050-SCFI-2004. Esta cotizacion tiene vigencia inmediata.', 0, 'C')

# Función para crear el PDF y devolver los bytes
def generar_pdf_bytes(carrito, subtotal, iva, total):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=30)
    
    # Fecha
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(0)
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 10, f'Fecha de Emision: {fecha}', 0, 1, 'R')
    pdf.ln(5)

    # Encabezados de Tabla
    pdf.set_fill_color(235, 10, 30) # Fondo Rojo
    pdf.set_text_color(255) # Texto Blanco
    pdf.set_font('Arial', 'B', 10)
    
    # Anchos: Cant(15), SKU(35), Desc(80), Unit(30), Importe(30) = 190 total
    pdf.cell(15, 8, 'Cant.', 1, 0, 'C', True)
    pdf.cell(35, 8, 'SKU', 1, 0, 'C', True)
    pdf.cell(85, 8, 'Descripcion', 1, 0, 'C', True)
    pdf.cell(25, 8, 'P. Base', 1, 0, 'C', True)
    pdf.cell(30, 8, 'Importe', 1, 1, 'C', True)

    # Filas
    pdf.set_text_color(0) # Texto Negro
    pdf.set_font('Arial', '', 9)
    
    for item in carrito:
        desc = item['Descripción'][:45] # Recortar si es muy largo para que quepa
        
        pdf.cell(15, 8, str(int(item['Cantidad'])), 1, 0, 'C')
        pdf.cell(35, 8, item['SKU'], 1, 0, 'C')
        pdf.cell(85, 8, desc, 1, 0, 'L')
        pdf.cell(25, 8, f"${item['Precio Base']:,.2f}", 1, 0, 'R')
        pdf.cell(30, 8, f"${item['Importe']:,.2f}", 1, 1, 'R')

    pdf.ln(5)

    # Totales
    pdf.set_font('Arial', '', 10)
    pdf.cell(130) # Mover a la derecha
    pdf.cell(30, 6, 'Subtotal:', 0, 0, 'R')
    pdf.cell(30, 6, f"${subtotal:,.2f}", 0, 1, 'R')
    
    pdf.cell(130)
    pdf.cell(30, 6, 'IVA (16%):', 0, 0, 'R')
    pdf.cell(30, 6, f"${iva:,.2f}", 0, 1, 'R')
    
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(235, 10, 30)
    pdf.cell(130)
    pdf.cell(30, 8, 'TOTAL:', 0, 0, 'R')
    pdf.cell(30, 8, f"${total:,.2f}", 0, 1, 'R')

    # Línea de Firma
    pdf.ln(25)
    pdf.set_draw_color(0)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y()) # Línea centrada
    pdf.set_text_color(0)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 5, 'Firma de Autorizacion / Asesor', 0, 1, 'C')

    # Retornar el PDF como string binario
    return pdf.output(dest='S').encode('latin-1')

# Traducción
@st.cache_data
def traducir_profe(texto):
    try:
        if pd.isna(texto) or texto == "": return "Sin descripción"
        return GoogleTranslator(source='en', target='es').translate(str(texto))
    except:
        return texto

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
fecha_hoy = datetime.now().strftime("%d/%m/%Y")

# --- INTERFAZ PRINCIPAL ---

c_titulo, c_fecha = st.columns([3, 1])
with c_titulo:
    st.title("🚗 Consulta de Precios")
    st.markdown("**Toyota Los Fuertes** | Sistema de Cotización Oficial")
with c_fecha:
    st.markdown(f"### 📅 {fecha_hoy}")

st.write("---")

# 1. BUSCADOR
if df is not None:
    busqueda = st.text_input("🔍 Buscar Refacción (SKU o Nombre):", placeholder="Ej. Filtro, 90430...")

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
                except ValueError: precio_val = 0.0

                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**{desc_es}**")
                        st.caption(f"SKU: {sku_val} | Base: ${precio_val:,.2f}")
                    with c2:
                        cantidad = st.number_input("Cant.", min_value=1, value=1, key=f"cant_{i}", label_visibility="collapsed")
                    with c3:
                        if st.button(f"Añadir ➕", key=f"add_{i}"):
                            st.session_state.carrito.append({
                                "SKU": sku_val, "Descripción": desc_es, "Precio Base": precio_val,
                                "Cantidad": cantidad, "Importe": precio_val * cantidad
                            })
                            st.toast("✅ Agregado")
                    st.divider() 
        else:
            st.warning("No se encontraron resultados.")

# 2. SECCIÓN: SERVICIOS Y EXTRAS (Predefinidos)
st.markdown("### 🛠️ Agregar Servicios / Mano de Obra")
with st.expander("Clic aquí para agregar servicios", expanded=False):
    st.info("💡 Ingresa el precio **sin IVA**. El sistema agregará el 16% al final.")
    
    ce1, ce2, ce3 = st.columns([2, 1, 1])
    with ce1:
        opciones = ["Mano de Obra", "Pintura", "Hojalatería", "Instalación", "Servicio Foráneo", "Diagnóstico", "Otro"]
        tipo_servicio = st.selectbox("Tipo de Servicio:", opciones)
        if tipo_servicio == "Otro":
            desc_final = st.text_input("Escribe el nombre del servicio:", value="Servicio General")
        else:
            desc_final = tipo_servicio

    with ce2:
        precio_manual = st.number_input("Costo (Antes de IVA):", min_value=0.0, format="%.2f")
    
    with ce3:
        st.write("") 
        st.write("")
        if st.button("Agregar Servicio 🔧"):
            if precio_manual > 0:
                st.session_state.carrito.append({
                    "SKU": "SERVICIO", 
                    "Descripción": desc_final, 
                    "Precio Base": precio_manual,
                    "Cantidad": 1, 
                    "Importe": precio_manual 
                })
                st.rerun()
            else:
                st.error("El costo debe ser mayor a 0")

# 3. CARRITO
if st.session_state.carrito:
    st.write("---")
    st.subheader(f"🛒 Carrito ({fecha_hoy})")
    
    df_carro = pd.DataFrame(st.session_state.carrito)
    st.dataframe(df_carro, hide_index=True, use_container_width=True)
    
    # CÁLCULOS
    subtotal = df_carro['Importe'].sum()
    iva = subtotal * 0.16
    gran_total = subtotal + iva

    col_sub, col_iva, col_tot = st.columns(3)
    col_sub.metric("Subtotal", f"${subtotal:,.2f}")
    col_iva.metric("IVA (16%)", f"${iva:,.2f}")
    col_tot.metric("Total Neto", f"${gran_total:,.2f}")

    # BOTONES DE ACCIÓN
    col_pdf, col_borrar, col_wa = st.columns([1, 1, 2])
    
    with col_pdf:
        # GENERACIÓN DEL PDF
        try:
            pdf_bytes = generar_pdf_bytes(st.session_state.carrito, subtotal, iva, gran_total)
            st.download_button(
                label="📄 Descargar PDF",
                data=pdf_bytes,
                file_name=f"Cotizacion_Toyota_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                type="primary"
            )
        except Exception as e:
            st.error(f"Error PDF: {e}")

    with col_borrar:
        if st.button("🗑️ Vaciar Todo"):
            st.session_state.carrito = []
            st.rerun()
            
    with col_wa:
        msg = f"*COTIZACIÓN TOYOTA LOS FUERTES*\n📅 Fecha: {fecha_hoy}\n\n"
        for _, row in df_carro.iterrows():
            msg += f"▪ {row['Cantidad']}x {row['Descripción']}\n   Base: ${row['Importe']:,.2f}\n"
        msg += f"\nSubtotal: ${subtotal:,.2f}"
        msg += f"\nIVA (16%): ${iva:,.2f}"
        msg += f"\n*TOTAL: ${gran_total:,.2f} MXN*"
        link = f"https://wa.me/?text={urllib.parse.quote(msg)}"
        st.link_button("📲 Enviar WhatsApp", link, type="secondary")
