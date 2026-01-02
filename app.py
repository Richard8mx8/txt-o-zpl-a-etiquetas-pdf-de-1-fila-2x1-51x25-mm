import streamlit as st
import re
import requests
import io
import time
from pypdf import PdfReader, PdfWriter

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="ZPL con Cantidades (^PQ)",
    page_icon="🔢",
    layout="centered"
)

# --- CONFIGURACIÓN ADSENSE ---
query_params = st.query_params
if "ads.txt" in query_params:
    st.text("google.com, pub-8311228733708760, DIRECT, f08c47fec0942fa0")
    st.stop()

st.components.v1.html("""
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8311228733708760"
     crossorigin="anonymous"></script>
""", height=0)

# --- ESTILOS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #6f42c1; /* Color morado para diferenciar esta versión */
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- TÍTULO ---
st.title("🔢 Generador ZPL con Multiplicador (^PQ)")
st.write("Detecta automáticamente el comando ^PQ (Print Quantity) para repetir las etiquetas las veces necesarias.")

# --- FUNCIÓN PARA DETECTAR CANTIDAD ---
def obtener_cantidad_zpl(zpl_code):
    """
    Busca el comando ^PQ (Print Quantity) y extrae el número.
    Ejemplo: ^PQ5 -> Retorna 5
    Si no encuentra nada, asume que es 1.
    """
    # Regex busca ^PQ seguido de dígitos
    match = re.search(r'\^PQ(\d+)', zpl_code)
    if match:
        return int(match.group(1))
    return 1

# --- PROCESAMIENTO INTELIGENTE ---
def process_labels_with_quantity(zpl_blocks):
    pdf_writer = PdfWriter()
    url = 'http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/'
    headers = {'Accept': 'application/pdf'}
    
    total_blocks = len(zpl_blocks)
    total_etiquetas_finales = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, zpl_block in enumerate(zpl_blocks):
        # 1. Detectar cuántas copias necesita esta etiqueta
        cantidad_copias = obtener_cantidad_zpl(zpl_block)
        
        label_num = i + 1
        status_text.markdown(f"🔄 Procesando diseño *{label_num}/{total_blocks}* (Se repetirá *{cantidad_copias}* veces)...")

        # 2. Obtener la imagen de la API (Solo pedimos 1 copia a la API para no saturarla)
        #    Nota: Aunque el ZPL tenga ^PQ5, la API nos devolverá lo que tenga, 
        #    pero nosotros controlaremos la repetición en el PDF.
        
        max_retries = 5
        base_delay = 2
        success = False
        pdf_pagina_modelo = None # Aquí guardaremos la página "molde"

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=zpl_block.encode('utf-8'), timeout=30)
                
                if response.status_code == 200:
                    batch_pdf_bytes = io.BytesIO(response.content)
                    batch_reader = PdfReader(batch_pdf_bytes)
                    
                    # Tomamos la primera página que nos devuelve la API como "modelo"
                    if len(batch_reader.pages) > 0:
                        pdf_pagina_modelo = batch_reader.pages[0]
                        success = True
                        time.sleep(0.1) 
                        break 
                elif response.status_code == 429:
                     status_text.warning(f"⚠️ API llena. Pausando 5s...")
                     time.sleep(5)
                elif response.status_code == 413:
                     st.error(f"❌ La etiqueta {label_num} es demasiado pesada.")
                     return None, 0
                else:
                    time.sleep(base_delay + (attempt * 2))

            except requests.exceptions.RequestException:
                time.sleep(base_delay + (attempt * 2))
        
        if not success or pdf_pagina_modelo is None:
             st.error(f"❌ No se pudo generar el diseño {label_num}. Proceso detenido.")
             return None, 0
        
        # 3. MULTIPLICACIÓN MANUAL
        # Ahora que tenemos el "molde" (pdf_pagina_modelo), lo agregamos al PDF final
        # tantas veces como diga la variable 'cantidad_copias'
        for _ in range(cantidad_copias):
            pdf_writer.add_page(pdf_pagina_modelo)
            total_etiquetas_finales += 1

        progress_bar.progress((i + 1) / total_blocks)

    # Generar PDF Final
    output_stream = io.BytesIO()
    pdf_writer.write(output_stream)
    final_pdf_bytes = output_stream.getvalue()
    
    status_text.empty()
    progress_bar.empty()
    
    return final_pdf_bytes, total_etiquetas_finales, total_blocks

# --- INTERFAZ ---

uploaded_file = st.file_uploader(
    "Sube tu archivo .txt o .zpl con códigos ^PQ",
    type=["txt", "zpl", "prn"],
    key="zpl_file_uploader_v8"
)

if uploaded_file:
    try:
        raw_data = uploaded_file.read()
        try:
            content = raw_data.decode("utf-8")
        except UnicodeDecodeError:
             content = raw_data.decode("latin-1")

        # Extraemos los bloques de diseño únicos
        zpl_blocks = re.findall(r'(\^XA.*?\^XZ)', content, re.DOTALL | re.MULTILINE)
        diseños_unicos = len(zpl_blocks)

        if diseños_unicos == 0:
            st.error("❌ No se encontraron bloques ZPL.")
        else:
            # Pre-cálculo de cantidad total para informar al usuario
            total_esperado = sum(obtener_cantidad_zpl(block) for block in zpl_blocks)
            
            st.info(f"✅ ANÁLISIS: Se detectaron *{diseños_unicos}* diseños únicos.")
            st.success(f"📊 Según los comandos ^PQ internos, se generarán *{total_esperado}* etiquetas en total.")
            
            if st.button(f"GENERAR LAS {total_esperado} ETIQUETAS 🚀"):
                with st.spinner("Generando y multiplicando etiquetas..."):
                    pdf_bytes, total_generado, _ = process_labels_with_quantity(zpl_blocks)
                    
                    if pdf_bytes:
                        st.balloons()
                        st.write(f"### Resumen Final:")
                        st.write(f"- Diseños procesados: {diseños_unicos}")
                        st.write(f"- Etiquetas generadas (con copias): *{total_generado}*")
                        
                        st.download_button(
                            label=f"📥 DESCARGAR PDF ({total_generado} ETIQUETAS)",
                            data=pdf_bytes,
                            file_name="etiquetas_con_cantidades_v8.pdf",
                            mime="application/pdf"
                        )
    except Exception as e:
        st.error(f"Error: {e}")

# --- FOOTER ---
st.markdown("---")
st.write("Sistema V8: Detecta ^PQ y multiplica las páginas automáticamente.")

