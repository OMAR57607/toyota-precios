import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import urllib.parse
from datetime import datetime
from PIL import Image
from pyzbar.pyzbar import decode
import pytz
import easyocr
import numpy as np

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Consulta Toyota", page_icon="🚗", layout="wide")

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
    
    /* Footer Legal Adaptativo */
    .legal-footer {
        text-align: center;
        font-size: 11px;
        opacity: 0.7;
        margin-top: 50px;
        padding-top: 20px;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        font-family: sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

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

# --- INTERFAZ CLIENTE ---

st.title("TOYOTA LOS FUERTES")
st.markdown("<h5 style='text-align: center; opacity: 0.8;'>Consulta de Precios y Refacciones Originales</h5>", unsafe_allow_html=True)
st.write("---")

# 0. INFORMACIÓN DE FECHA
with st.container():
    st.markdown(f"<div style='text-align: right;'><strong>Fecha consulta:</strong> {fecha_hoy_str} <span style='opacity:0.6'>({hora_hoy_str})</span></div>", unsafe_allow_html=True)

st.write("---")

# 1. ESCÁNER Y BÚSQUEDA
sku_detectado = ""

if st.checkbox("📸 Escanear Código de Caja"):
    st.info("Apunta tu cámara al código de barras o número de parte.")
    img_file = st.camera_input("Foto", label_visibility="collapsed")
    if img_file is not None:
        try:
            imagen_pil = Image.open(img_file)
            codigos = decode(imagen_pil)
            if codigos:
                sku_detectado = codigos[0].data.decode("utf-8")
                st.success(f"✅ Código: {sku_detectado}")
            else:
                with st.spinner("Leyendo texto..."):
                    reader = cargar_lector_ocr()
                    result = reader.readtext(np.array(imagen_pil))
                    possibles = [txt for (bbox, txt, prob) in result if len(txt) > 4 and prob > 0.4]
                    if possibles:
                        sku_detectado = possibles[0] 
                        st.success(f"👁️ Texto: {sku_detectado}")
                    else:
                        st.warning("No se detectó código.")
        except: pass

if df is not None:
    valor_inicial = sku_detectado if sku_detectado else ""
    
    st.markdown("🔍 **Buscar Refacción (Número de parte o nombre):**")
    busqueda = st.text_input("Búsqueda", value=valor_inicial, label_visibility="collapsed", placeholder="Ej. Filtro, Balatas, 90915...")

    if busqueda:
        busqueda_raw = busqueda.upper().strip()
        busqueda_clean = busqueda_raw.replace('-', '')
        
        mask_desc = df.apply(lambda x: x.astype(str).str.contains(busqueda_raw, case=False)).any(axis=1)
        mask_sku = df['SKU_CLEAN'].str.contains(busqueda_clean, na=False)
        resultados = df[mask_desc | mask_sku].head(10).copy() 

        if not resultados.empty:
            c_sku = [c for c in resultados.columns if 'PART' in c or 'NUM' in c][0]
            c_desc = [c for c in resultados.columns if 'DESC' in c][0]
            c_precio = [c for c in resultados.columns if 'PRICE' in c or 'PRECIO' in c][0]

            st.success("Resultados disponibles:")
            st.divider()

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
                        # --- CORRECCIÓN PROFECO: Mostrar Total con IVA en Grande ---
                        st.markdown(f"**SKU:** `{sku_val}`")
                        st.markdown(f"{desc_es}")
                        
                        precio_con_iva = precio_val * 1.16
                        # Precio grande = Total a pagar
                        st.markdown(f"#### **Precio: ${precio_con_iva:,.2f} MXN**")
                        # Desglose pequeño
                        st.caption(f"(Base: ${precio_val:,.2f} + IVA)") 
                        
                    with c2:
                        cantidad = st.number_input("Cant.", min_value=1, value=1, key=f"cant_{i}")
                    with c3:
                        st.write("")
                        if st.button("Agregar 🛒", key=f"add_{i}"):
                            monto_base = precio_val 
                            monto_iva = (monto_base * cantidad) * 0.16
                            monto_total = (monto_base * cantidad) + monto_iva
                            
                            st.session_state.carrito.append({
                                "SKU": sku_val,
                                "Descripción": desc_es,
                                "Cantidad": cantidad,
                                "Precio Base": precio_val, # Unitario sin IVA
                                "IVA": monto_iva,           # IVA Total
                                "Importe Total": monto_total # Total con IVA
                            })
                            st.toast("✅ Agregado")
                    st.divider() 
        else:
            st.warning("No encontramos esa pieza. Intenta verificar el número de parte.")

# 3. LISTA DE PEDIDO (CARRITO)
if st.session_state.carrito:
    st.subheader(f"🛒 Tu Pedido Preliminar")
    
    df_carro = pd.DataFrame(st.session_state.carrito)
    
    # --- ORDEN DE COLUMNAS SOLICITADO ---
    columnas_vista = ["SKU", "Descripción", "Cantidad", "Precio Base", "IVA", "Importe Total"]
    
    st.dataframe(df_carro[columnas_vista], hide_index=True, use_container_width=True)
    
    gran_total = df_carro['Importe Total'].sum()

    st.markdown(f"<h3 style='text-align: right; color: #eb0a1e;'>Total A Pagar: ${gran_total:,.2f}</h3>", unsafe_allow_html=True)
    st.caption(f"<div style='text-align: right;'>Incluye IVA (16%)</div>", unsafe_allow_html=True)

    col_vaciar, col_wa = st.columns([1, 2])
    
    with col_vaciar:
        if st.button("🗑️ Borrar Lista"):
            st.session_state.carrito = []
            st.rerun()
            
    with col_wa:
        msg = f"*CONSULTA CLIENTE - TOYOTA LOS FUERTES*\n📅 {fecha_hoy_str} {hora_hoy_str}\n\n"
        
        for _, row in df_carro.iterrows():
            # WhatsApp: SKU primero
            msg += f"▪ {row['SKU']} | {row['Descripción']}\n"
            msg += f"   Cant: {row['Cantidad']} | Total: ${row['Importe Total']:,.2f}\n"
        
        msg += f"\n*Valor Total Aprox: ${gran_total:,.2f}*"
        msg += "\n\n_Solicito confirmación de existencia._"
        link = f"https://wa.me/?text={urllib.parse.quote(msg)}"
        st.link_button("📲 Enviar Consulta por WhatsApp", link, use_container_width=True)

# --- FOOTER LEGAL Y NORMATIVO ---
st.markdown(f"""
    <div class="legal-footer">
        <strong>TOYOTA LOS FUERTES - INFORMACIÓN AL CONSUMIDOR</strong><br><br>
        1. <strong>Precios:</strong> Vigentes al <strong>{fecha_hoy_str} {hora_hoy_str}</strong> (Hora CDMX).<br>
        2. <strong>Impuestos:</strong> Todos los montos mostrados incluyen IVA (16%).<br>
        3. <strong>Marco Legal:</strong> Esta consulta cumple con la obligación de exhibición de precios conforme al <strong>Art. 7 de la Ley Federal de Protección al Consumidor (LFPC)</strong>.<br>
        4. <strong>Información Comercial:</strong> Las descripciones de productos se apegan a la <strong>NOM-050-SCFI-2004</strong>.<br>
        5. <strong>Vigencia:</strong> Los precios mostrados tienen una vigencia de 24 horas a partir de esta consulta.<br>
        6. <strong>Disponibilidad:</strong> La existencia de las refacciones está sujeta a validación final en mostrador.
    </div>
""", unsafe_allow_html=True)
