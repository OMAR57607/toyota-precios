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
                sku_val = row[c_sku]
                
                # --- LIMPIEZA DE PRECIO ---
                try:
                    precio_texto = str(row[c_precio]).replace(',', '').replace('$', '').strip()
                    precio_val = float(precio_texto)
                except ValueError:
                    precio_val = 0.0

                # --- TARJETA DE PRODUCTO ---
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    
                    with c1:
                        st.markdown(f"**{desc_es}**")
                        # Indicamos que es precio antes de IVA
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
                            st.toast(f"✅ Agregado")
                    st.divider() 
        else:
            st.warning("No se encontraron resultados.")

    # --- CARRITO Y CÁLCULOS CORREGIDOS ---
    if st.session_state.carrito:
        st.write("---")
        st.subheader(f"🛒 Cotización")
        
        df_carro = pd.DataFrame(st.session_state.carrito)
        
        st.dataframe(
            df_carro, 
            column_config={
                "Precio Base": st.column_config.NumberColumn(format="$%.2f"),
                "Importe": st.column_config.NumberColumn(format="$%.2f")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # --- NUEVA LÓGICA DE IVA ---
        # 1. El Subtotal es la suma directa de los importes
        subtotal = df_carro['Importe'].sum()
        # 2. El IVA se calcula SOBRE el subtotal
        iva = subtotal * 0.16
        # 3. El Total es la suma
        gran_total = subtotal + iva
        
        col_sub, col_iva, col_tot = st.columns(3)
        col_sub.metric("Subtotal", f"${subtotal:,.2f}")
        col_iva.metric("IVA (16%)", f"${iva:,.2f}")
        col_tot.metric("Total Neto", f"${gran_total:,.2f}")
        
        # --- WHATSAPP CORREGIDO ---
        msg = "*COTIZACIÓN OFICIAL - TOYOTA*\n\n"
        for index, row in df_carro.iterrows():
            msg += f"▪ {row['Cantidad']}x {row['Descripción']}\n   SKU: {row['SKU']} | Base: ${row['Importe']:,.2f}\n"
        
        msg += "\n----------------------------------"
        msg += f"\nSubtotal: ${subtotal:,.2f}"
        msg += f"\nIVA (16%): ${iva:,.2f}"
        msg += f"\n*TOTAL A PAGAR: ${gran_total:,.2f} MXN*"
        
        msg_encoded = urllib.parse.quote(msg)
        whatsapp_link = f"https://wa.me/?text={msg_encoded}"

        c_wa, c_del = st.columns([2, 1])
        with c_wa:
            st.link_button("📲 Enviar WhatsApp", whatsapp_link, type="primary")
        with c_del:
            if st.button("🗑️ Vaciar"):
                st.session_state.carrito = []
                st.rerun()

else:
    st.error("⚠️ Error: No se encuentra 'lista_precios.zip'.")

# Footer Profeco actualizado
st.write("---")
st.markdown("""
    <div class='profeco-text'>
    <p><strong>INFORMACIÓN LEGAL:</strong> Precios mostrados antes de IVA. Se agrega el 16% de Impuesto al Valor Agregado al final de la cotización.
    Las descripciones son traducidas bajo la NOM-050-SCFI-2004.</p>
    </div>
    """, unsafe_allow_html=True)
