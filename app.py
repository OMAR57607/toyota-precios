import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import urllib.parse
from datetime import datetime

# 1. Configuración de página
st.set_page_config(page_title="Toyota Los Fuertes", page_icon="🚗", layout="wide")

# Inicializar variables
if 'carrito' not in st.session_state:
    st.session_state.carrito = []
if 'modo_impresion' not in st.session_state:
    st.session_state.modo_impresion = False

# 2. ESTILOS CSS
st.markdown("""
    <style>
    h1 { color: #eb0a1e !important; }
    
    /* CSS IMPRESIÓN */
    @media print {
        .stButton, .stTextInput, .stNumberInput, div[data-testid="stToolbar"], div[data-testid="stDecoration"], footer {
            display: none !important;
        }
        [data-testid="stSidebar"] { display: none !important; }
        body, .stApp { background-color: white !important; color: black !important; }
        .block-container { padding: 0rem 1rem !important; }
    }
    
    /* Encabezado Factura */
    .invoice-header {
        text-align: center; margin-bottom: 20px; padding-bottom: 10px;
        border-bottom: 2px solid #eb0a1e;
    }
    .invoice-title { font-size: 24px; font-weight: bold; color: #eb0a1e; margin: 0; }
    .invoice-details { font-size: 14px; color: #333; }
    </style>
    """, unsafe_allow_html=True)

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

# --- FECHA ACTUAL ---
fecha_hoy = datetime.now().strftime("%d/%m/%Y")

# --- MODO NORMAL ---
if not st.session_state.modo_impresion:
    c_titulo, c_fecha = st.columns([3, 1])
    with c_titulo:
        st.title("🚗 Consulta de Precios")
        st.markdown("**Toyota Los Fuertes** | Sistema de Cotización Oficial")
    with c_fecha:
        st.markdown(f"### 📅 {fecha_hoy}")
    
    st.write("---")

    if df is not None:
        busqueda = st.text_input("🔍 Escribe SKU o Nombre:", placeholder="Ej. Filtro, 90430...")

        if busqueda:
            busqueda = busqueda.upper().strip()
            mask = df.apply(lambda x: x.astype(str).str.contains(busqueda, case=False)).any(axis=1)
            resultados = df[mask].head(10).copy() 

            if not resultados.empty:
                c_sku = [c for c in resultados.columns if 'PART' in c or 'NUM' in c][0]
                c_desc = [c for c in resultados.columns if 'DESC' in c][0]
                c_precio = [c for c in resultados.columns if 'PRICE' in c or 'PRECIO' in c][0]

                st.success("Resultados:")
                for i, row in resultados.iterrows():
                    desc_es = traducir_profe(row[c_desc])
                    sku_val = row[c_sku]
                    try:
                        precio_texto = str(row[c_precio]).replace(',', '').replace('$', '').strip()
                        precio_val = float(precio_texto)
                    except ValueError:
                        precio_val = 0.0

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
                                    "SKU": sku_val, 
                                    "Descripción": desc_es, 
                                    "Precio Base": precio_val,
                                    "Cantidad": cantidad,
                                    "Importe": precio_val * cantidad
                                })
                                st.toast("✅ Agregado")
                        st.divider() 
            else:
                st.warning("No se encontraron resultados.")

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

            # BOTONES ACCIÓN
            col_btns = st.columns([1, 1, 2])
            with col_btns[0]:
                if st.button("🖨️ Generar Nota"):
                    st.session_state.modo_impresion = True
                    st.rerun()
            with col_btns[1]:
                if st.button("🗑️ Borrar"):
                    st.session_state.carrito = []
                    st.rerun()
            with col_btns[2]:
                # WHATSAPP CON FECHA
                msg = f"*COTIZACIÓN TOYOTA LOS FUERTES*\n📅 Fecha: {fecha_hoy}\n\n"
                for _, row in df_carro.iterrows():
                    msg += f"▪ {row['Cantidad']}x {row['Descripción']}\n   SKU: {row['SKU']} | Base: ${row['Importe']:,.2f}\n"
                msg += f"\nSubtotal: ${subtotal:,.2f}"
                msg += f"\nIVA (16%): ${iva:,.2f}"
                msg += f"\n*TOTAL: ${gran_total:,.2f} MXN*"
                
                link = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                st.link_button("📲 Enviar WhatsApp", link, type="primary")

# --- MODO IMPRESIÓN ---
else:
    fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    st.markdown(f"""
        <div class="invoice-header">
            <p class="invoice-title">TOYOTA LOS FUERTES</p>
            <p class="invoice-details">
                <strong>COTIZACIÓN DE REFACCIONES</strong><br>
                Fecha de emisión: {fecha_hora}<br>
                Distribuidor Autorizado Toyota
            </p>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.carrito:
        df_carro = pd.DataFrame(st.session_state.carrito)
        subtotal = df_carro['Importe'].sum()
        iva = subtotal * 0.16
        gran_total = subtotal + iva

        st.table(df_carro[['Cantidad', 'SKU', 'Descripción', 'Precio Base', 'Importe']])

        st.markdown(f"""
        <div style="text-align: right; margin-top: 20px;">
            <p><strong>Subtotal:</strong> ${subtotal:,.2f}</p>
            <p><strong>IVA (16%):</strong> ${iva:,.2f}</p>
            <h3 style="color: #eb0a1e;">TOTAL A PAGAR: ${gran_total:,.2f} MXN</h3>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='text-align: center; font-size: 10px; color: gray; margin-top: 50px; border-top: 1px solid #ddd; padding-top: 10px;'>
            <p>INFORMACIÓN LEGAL: Precios en Moneda Nacional. Vigencia inmediata. 
            Las descripciones han sido traducidas para cumplimiento de NOM-050-SCFI-2004.</p>
        </div>
        """, unsafe_allow_html=True)

        # Botones ocultos al imprimir
        c_volver, c_dummy = st.columns([1, 4])
        with c_volver:
            if st.button("⬅️ Volver a Editar"):
                st.session_state.modo_impresion = False
                st.rerun()

    else:
        st.warning("El carrito está vacío.")
        if st.button("Volver"):
            st.session_state.modo_impresion = False
            st.rerun()
