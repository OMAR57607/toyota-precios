import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import urllib.parse
from datetime import datetime
import streamlit.components.v1 as components

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
        /* Ocultar todo lo que no sea la hoja de factura */
        .stButton, .stTextInput, .stNumberInput, div[data-testid="stToolbar"], 
        div[data-testid="stDecoration"], footer, header, .no-print {
            display: none !important;
        }
        [data-testid="stSidebar"] { display: none !important; }
        
        body, .stApp { background-color: white !important; color: black !important; }
        .block-container { padding: 0rem 1rem !important; }
        
        /* Forzar que la firma se vea bien al imprimir */
        .signature-section { display: block !important; break-inside: avoid; }
    }
    
    /* Encabezado Factura */
    .invoice-header {
        text-align: center; margin-bottom: 20px; padding-bottom: 10px;
        border-bottom: 2px solid #eb0a1e;
    }
    .invoice-title { font-size: 24px; font-weight: bold; color: #eb0a1e; margin: 0; }
    
    /* Sección de Firma */
    .signature-section {
        margin-top: 50px;
        text-align: center;
        page-break-inside: avoid;
    }
    .signature-line {
        border-top: 1px solid #000;
        width: 250px;
        margin: 0 auto;
        padding-top: 5px;
        font-weight: bold;
    }
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
fecha_hoy = datetime.now().strftime("%d/%m/%Y")

# --- MODO NORMAL (EDICIÓN) ---
if not st.session_state.modo_impresion:
    c_titulo, c_fecha = st.columns([3, 1])
    with c_titulo:
        st.title("🚗 Consulta de Precios")
        st.markdown("**Toyota Los Fuertes** | Sistema de Cotización Oficial")
    with c_fecha:
        st.markdown(f"### 📅 {fecha_hoy}")
    
    st.write("---")

    # 1. SECCIÓN: BUSCADOR DE REFACCIONES
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

    # 2. SECCIÓN: AGREGAR MANO DE OBRA (EXTRA)
    st.markdown("### 🛠️ Agregar Mano de Obra / Extras")
    with st.expander("Clic aquí para agregar conceptos manuales", expanded=False):
        ce1, ce2, ce3 = st.columns([2, 1, 1])
        with ce1:
            desc_man = st.text_input("Descripción del servicio:", value="Mano de Obra")
        with ce2:
            precio_man = st.number_input("Costo (Antes de IVA):", min_value=0.0, format="%.2f")
        with ce3:
            st.write("") # Espacio
            st.write("")
            if st.button("Agregar Extra 🔧"):
                st.session_state.carrito.append({
                    "SKU": "SERV-EXT", "Descripción": desc_man, "Precio Base": precio_man,
                    "Cantidad": 1, "Importe": precio_man
                })
                st.rerun()

    # 3. SECCIÓN: CARRITO Y ACCIONES
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

        # BOTONES
        col_btns = st.columns([1, 1, 2])
        with col_btns[0]:
            if st.button("🖨️ Vista Previa"):
                st.session_state.modo_impresion = True
                st.rerun()
        with col_btns[1]:
            if st.button("🗑️ Vaciar Todo"):
                st.session_state.carrito = []
                st.rerun()
        with col_btns[2]:
            # WHATSAPP
            msg = f"*COTIZACIÓN TOYOTA LOS FUERTES*\n📅 Fecha: {fecha_hoy}\n\n"
            for _, row in df_carro.iterrows():
                msg += f"▪ {row['Cantidad']}x {row['Descripción']}\n   Base: ${row['Importe']:,.2f}\n"
            msg += f"\nSubtotal: ${subtotal:,.2f}"
            msg += f"\nIVA (16%): ${iva:,.2f}"
            msg += f"\n*TOTAL: ${gran_total:,.2f} MXN*"
            link = f"https://wa.me/?text={urllib.parse.quote(msg)}"
            st.link_button("📲 Enviar WhatsApp", link, type="primary")

# --- MODO VISTA PREVIA (IMPRESIÓN) ---
else:
    fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Encabezado Oficial
    st.markdown(f"""
        <div class="invoice-header">
            <p class="invoice-title">TOYOTA LOS FUERTES</p>
            <p class="invoice-details">
                <strong>COTIZACIÓN DE SERVICIO Y REFACCIONES</strong><br>
                Fecha de emisión: {fecha_hora}<br>
                Distribuidor Autorizado
            </p>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.carrito:
        df_carro = pd.DataFrame(st.session_state.carrito)
        subtotal = df_carro['Importe'].sum()
        iva = subtotal * 0.16
        gran_total = subtotal + iva

        # Tabla limpia
        st.table(df_carro[['Cantidad', 'SKU', 'Descripción', 'Precio Base', 'Importe']])

        # Totales
        st.markdown(f"""
        <div style="text-align: right; margin-top: 10px;">
            <p><strong>Subtotal:</strong> ${subtotal:,.2f}</p>
            <p><strong>IVA (16%):</strong> ${iva:,.2f}</p>
            <h3 style="color: #eb0a1e;">TOTAL: ${gran_total:,.2f} MXN</h3>
        </div>
        """, unsafe_allow_html=True)

        # Área de Firma (Solo visible en esta vista y en papel)
        st.markdown("""
        <div class="signature-section">
            <br><br><br>
            <div class="signature-line">Firma del Asesor / Cliente</div>
        </div>
        """, unsafe_allow_html=True)

        # Footer Legal
        st.markdown("""
        <div style='text-align: center; font-size: 10px; color: gray; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 10px;'>
            <p>Precios sujetos a cambio sin previo aviso. Vigencia inmediata. 
            Mano de obra y refacciones cotizadas bajo estándares Toyota.</p>
        </div>
        """, unsafe_allow_html=True)

        # --- BOTONES DE ACCIÓN (Se ocultan al imprimir gracias al CSS) ---
        st.markdown("<div class='no-print'>", unsafe_allow_html=True) # Inicio bloque No-Print
        c_volver, c_print = st.columns([1, 4])
        
        with c_volver:
            if st.button("⬅️ Editar"):
                st.session_state.modo_impresion = False
                st.rerun()
        
        with c_print:
            # BOTÓN JAVASCRIPT PARA IMPRIMIR
            components.html("""
            <script>
            function printPage() {
                window.print();
            }
            </script>
            <button onclick="printPage()" style="
                background-color: #eb0a1e; 
                color: white; 
                padding: 10px 20px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer;
                font-family: sans-serif;
                font-weight: bold;
                font-size: 16px;">
                🖨️ Imprimir / Guardar como PDF
            </button>
            """, height=60)
            
        st.markdown("</div>", unsafe_allow_html=True) # Fin bloque No-Print

    else:
        st.warning("Carrito vacío.")
        if st.button("Volver"):
            st.session_state.modo_impresion = False
            st.rerun()
