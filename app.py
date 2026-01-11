import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import urllib.parse  # Librería estándar para crear links de WhatsApp

# 1. Configuración de página
st.set_page_config(page_title="Toyota Los Fuertes", page_icon="🚗", layout="wide")

# Inicializar carrito
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 2. ESTILOS (Optimizados para Modo Oscuro/Claro)
st.markdown("""
    <style>
    h1 { color: #eb0a1e !important; } /* Rojo Toyota */
    
    /* Estilo para el aviso legal */
    .profeco-text {
        font-size: 0.8rem;
        color: gray;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# Función de traducción robusta
@st.cache_data
def traducir_profe(texto):
    try:
        if pd.isna(texto) or texto == "": return "Sin descripción"
        return GoogleTranslator(source='en', target='es').translate(str(texto))
    except:
        return texto

# 3. Encabezado
st.title("🚗 Consulta de Precios")
st.markdown("**Toyota Los Fuertes** | Sistema de Cotización Oficial")
st.write("---")

# 4. Carga segura del ZIP
@st.cache_data
def cargar_catalogo():
    try:
        df = pd.read_csv("lista_precios.zip", compression='zip', dtype=str, encoding='latin-1')
        df.dropna(how='all', inplace=True)
        # Limpieza de columnas
        df.columns = [c.strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return None

df = cargar_catalogo()

if df is not None:
    # --- BUSCADOR ---
    busqueda = st.text_input("🔍 Escribe SKU o Nombre:", placeholder="Ej. 90430...")

    if busqueda:
        busqueda = busqueda.upper().strip()
        # Buscamos coincidencias
        mask = df.apply(lambda x: x.astype(str).str.contains(busqueda, case=False)).any(axis=1)
        resultados = df[mask].head(10).copy() 

        if not resultados.empty:
            # Detectar columnas
            c_sku = [c for c in resultados.columns if 'PART' in c or 'NUM' in c][0]
            c_desc = [c for c in resultados.columns if 'DESC' in c][0]
            c_precio = [c for c in resultados.columns if 'PRICE' in c or 'PRECIO' in c][0]

            st.success(f"Resultados encontrados:")

            for i, row in resultados.iterrows():
                # Variables temporales
                desc_es = traducir_profe(row[c_desc])
                precio_val = row[c_precio]
                sku_val = row[c_sku]

                # --- TARJETA DE PRODUCTO ---
                with st.container():
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{desc_es}**")
                        st.caption(f"SKU: {sku_val}")
                    with c2:
                        st.markdown(f"**${precio_val}**")
                        if st.button(f"Añadir ➕", key=f"add_{i}"):
                            st.session_state.carrito.append({
                                "SKU": sku_val, 
                                "Descripción": desc_es, 
                                "Precio": precio_val
                            })
                            st.toast("✅ Agregado al carrito")
                    st.divider() 
        else:
            st.warning("No se encontraron resultados.")

    # --- CARRITO Y WHATSAPP ---
    if st.session_state.carrito:
        st.write("---")
        st.subheader(f"🛒 Cotización Actual")
        
        df_carro = pd.DataFrame(st.session_state.carrito)
        st.table(df_carro)
        
        # Calcular total
        suma = pd.to_numeric(df_carro['Precio'], errors='coerce').sum()
        st.metric("Total (IVA Incluido)", f"${suma:,.2f}")
        
        # --- LÓGICA WHATSAPP ---
        # 1. Construir el mensaje de texto
        msg = "*COTIZACIÓN - TOYOTA LOS FUERTES*\n\n"
        for index, row in df_carro.iterrows():
            msg += f"🔧 {row['Descripción']}\n   SKU: {row['SKU']} | ${row['Precio']}\n\n"
        msg += f"*TOTAL: ${suma:,.2f} MXN*"
        
        # 2. Codificar mensaje para URL (cambia espacios por %20, etc.)
        msg_encoded = urllib.parse.quote(msg)
        
        # 3. Crear Link
        whatsapp_link = f"https://wa.me/?text={msg_encoded}"

        # Botones de acción
        col_wa, col_borrar = st.columns([2,1])
        with col_wa:
            st.link_button("📲 Enviar Cotización por WhatsApp", whatsapp_link, type="primary")
        with col_borrar:
            if st.button("🗑️ Borrar Todo"):
                st.session_state.carrito = []
                st.rerun()

else:
    st.error("⚠️ Error de base de datos.")

# --- FOOTER PROFECO ---
st.write("---")
st.markdown("""
    <div class='profeco-text'>
    <p><strong>INFORMACIÓN AL CONSUMIDOR (PROFECO):</strong></p>
    <p>1. Todos los precios están expresados en Moneda Nacional (MXN) e incluyen el Impuesto al Valor Agregado (IVA).</p>
    <p>2. Las descripciones de los productos han sido traducidas al español para cumplimiento de la <strong>NOM-050-SCFI-2004</strong>.</p>
    <p>3. Los precios están sujetos a cambio sin previo aviso. La vigencia de esta cotización es inmediata.</p>
    </div>
    """, unsafe_allow_html=True)
