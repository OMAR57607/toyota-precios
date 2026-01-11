import streamlit as st
import pandas as pd
from deep_translator import GoogleTranslator
import urllib.parse

# 1. Configuración de página
st.set_page_config(page_title="Toyota Los Fuertes", page_icon="🚗", layout="wide")

# Inicializar carrito
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 2. ESTILOS
st.markdown("""
    <style>
    h1 { color: #eb0a1e !important; }
    .profeco-text { font-size: 0.8rem; color: gray; text-align: center; }
    
    /* Ajuste para que el selector de cantidad se vea bien alineado */
    div[data-testid="stNumberInput"] { margin-bottom: 0px; }
    </style>
    """, unsafe_allow_html=True)

# Función de traducción
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

# 4. Carga de datos
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

if df is not None:
    # --- BUSCADOR ---
    busqueda = st.text_input("🔍 Escribe SKU o Nombre:", placeholder="Ej. Filtro, 90430...")

    if busqueda:
        busqueda = busqueda.upper().strip()
        mask = df.apply(lambda x: x.astype(str).str.contains(busqueda, case=False)).any(axis=1)
        resultados = df[mask].head(10).copy() 

        if not resultados.empty:
            c_sku = [c for c in resultados.columns if 'PART' in c or 'NUM' in c][0]
            c_desc = [c for c in resultados.columns if 'DESC' in c][0]
            c_precio = [c for c in resultados.columns if 'PRICE' in c or 'PRECIO' in c][0]

            st.success(f"Resultados:")

            for i, row in resultados.iterrows():
                desc_es = traducir_profe(row[c_desc])
                precio_val = float(row[c_precio]) # Aseguramos que sea número
                sku_val = row[c_sku]

                # --- TARJETA DE PRODUCTO CON SELECTOR ---
                with st.container():
                    # Dividimos en 3 columnas: Info | Cantidad | Botón
                    c1, c2, c3 = st.columns([3, 1, 1])
                    
                    with c1:
                        st.markdown(f"**{desc_es}**")
                        st.caption(f"SKU: {sku_val} | Unitario: ${precio_val:,.2f}")
                    
                    with c2:
                        # Selector de cantidad
                        cantidad = st.number_input("Cant.", min_value=1, value=1, key=f"cant_{i}", label_visibility="collapsed")
                    
                    with c3:
                        if st.button(f"Añadir ➕", key=f"add_{i}"):
                            # Añadimos al carrito con la cantidad seleccionada
                            st.session_state.carrito.append({
                                "SKU": sku_val, 
                                "Descripción": desc_es, 
                                "Precio Unit.": precio_val,
                                "Cantidad": cantidad,
                                "Importe": precio_val * cantidad
                            })
                            st.toast(f"✅ Se agregaron {cantidad} piezas")
                    st.divider() 
        else:
            st.warning("No se encontraron resultados.")

    # --- CARRITO Y DESGLOSE ---
    if st.session_state.carrito:
        st.write("---")
        st.subheader(f"🛒 Cotización")
        
        df_carro = pd.DataFrame(st.session_state.carrito)
        
        # Mostramos tabla editada para que se vea limpio
        st.dataframe(
            df_carro, 
            column_config={
                "Precio Unit.": st.column_config.NumberColumn(format="$%.2f"),
                "Importe": st.column_config.NumberColumn(format="$%.2f")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # --- CÁLCULOS FINANCIEROS (IVA 16%) ---
        gran_total = df_carro['Importe'].sum()
        subtotal = gran_total / 1.16
        iva = gran_total - subtotal
        
        # Mostramos el desglose en columnas métricas
        col_sub, col_iva, col_tot = st.columns(3)
        col_sub.metric("Subtotal (Antes de IVA)", f"${subtotal:,.2f}")
        col_iva.metric("IVA (16%)", f"${iva:,.2f}")
        col_tot.metric("Gran Total (Neto)", f"${gran_total:,.2f}")
        
        # --- WHATSAPP CON DESGLOSE ---
        msg = "*COTIZACIÓN OFICIAL - TOYOTA*\n\n"
        for index, row in df_carro.iterrows():
            msg += f"▪ {row['Cantidad']}x {row['Descripción']}\n   SKU: {row['SKU']} | Imp: ${row['Importe']:,.2f}\n"
        
        msg += "\n----------------------------------"
        msg += f"\nSubtotal: ${subtotal:,.2f}"
        msg += f"\nIVA (16%): ${iva:,.2f}"
        msg += f"\n*TOTAL A PAGAR: ${gran_total:,.2f} MXN*"
        
        msg_encoded = urllib.parse.quote(msg)
        whatsapp_link = f"https://wa.me/?text={msg_encoded}"

        c_wa, c_del = st.columns([2, 1])
        with c_wa:
            st.link_button("📲 Enviar Cotización Completa", whatsapp_link, type="primary")
        with c_del:
            if st.button("🗑️ Borrar Carrito"):
                st.session_state.carrito = []
                st.rerun()

else:
    st.error("⚠️ Error: No se encuentra 'lista_precios.zip'.")

# Footer Profeco
st.write("---")
st.markdown("""
    <div class='profeco-text'>
    <p><strong>INFORMACIÓN LEGAL:</strong> Precios en Moneda Nacional (MXN). El desglose de IVA se calcula automáticamente (Tasa 16%).
    Las descripciones son traducidas bajo la NOM-050-SCFI-2004.</p>
    </div>
    """, unsafe_allow_html=True)
