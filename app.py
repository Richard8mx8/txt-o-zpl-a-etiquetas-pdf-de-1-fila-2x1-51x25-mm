import streamlit as st
import re
import requests
import io
import time
from pypdf import PdfReader, PdfWriter

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="ZPL Total - Sin Deduplicar",
    page_icon="🏭",
    layout="centered"
)

# --- CONFIGURACIÓN PARA GOOGLE ADSENSE ---
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
        background-color: #28a745; /* Verde para indicar éxito */
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- TÍTULO ---
st.title("🏭 Impresora Masiva ZPL (326/326)")
st.write("Este sistema procesa *TODAS* las etiquetas del archivo, incluyendo las repetidas. Ideal para inventarios.")

# --- LÓGICA DE EXTRACCIÓN ESTRICTA ---
def get_all_blocks_sequential(content):
    """
    Usa expresiones regulares para encontrar CADA ocurrencia de ^XA...^XZ.
    Al usar findall sin sets ni dicts, se mantiene el orden exacto y las repeticiones.
    """
    # El patrón busca desde ^XA hasta ^XZ, incluyendo saltos de línea (DOTALL)
    # y es "no codicioso" (*?) para no comerse varias etiquetas en una.
    raw_blocks = re.findall(r'(\^XA.*?\^XZ)', content, re.DOTALL | re.MULTILINE)
    return raw_blocks

# --- LÓGICA DE PROCESAMIENTO ROBUSTO ---
def process_labels_sequential(zpl_blocks):
    pdf_writer = PdfWriter()
    url = 'http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/'
    headers = {'Accept': 'application/pdf'}
    
    total_blocks = len(zpl_blocks)
    labels_procesadas_count = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Iteramos sobre la lista. Si hay 326 elementos, el bucle corre 326 veces.
    for i, zpl_block in enumerate(zpl_blocks):
        label_num = i + 1
        
        # Mensaje de estado
        status_text.markdown(f"🖨️ Procesando etiqueta *{label_num} de {total_blocks}*...")

        # Reintentos robustos (Copiado de la versión V6 exitosa)
        max_retries = 5
        base_delay = 2
        success = False

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=zpl_block.encode('utf-8'), timeout=30)
                
                if response.status_code == 200:
                    batch_pdf_bytes = io.BytesIO(response.content)
                    batch_reader = PdfReader(batch_pdf_bytes)
                    
                    # Añadimos las páginas al PDF final
                    paginas_recibidas = len(batch_reader.pages)
                    for page in batch_reader.pages:
                        pdf_writer.add_page(page)
                    
                    labels_procesadas_count += paginas_recibidas
                    success = True
                    time.sleep(0.1) # Pequeña pausa
                    break 

                elif response.status_code == 429:
                     status_text.warning(f"⚠️ API llena. Pausando 5s...")
                     time.sleep(5)
                elif response.status_code == 413:
                     st.error(f"❌ La etiqueta {label_num} es demasiado pesada.")
                     return None, 0
                else:
                    wait_time = base_delay + (attempt * 2)
                    time.sleep(wait_time)

            except requests.exceptions.RequestException:
                wait_time = base_delay + (attempt * 2)
                time.sleep(wait_time)
        
        if not success:
             st.error(f"❌ Falló la etiqueta {label_num}. Proceso detenido.")
             return None, 0

        progress_bar.progress((i + 1) / total_blocks)

    # Finalizar PDF
    output_stream = io.BytesIO()
    pdf_writer.write(output_stream)
    final_pdf_bytes = output_stream.getvalue()
    
    status_text.empty()
    progress_bar.empty()
    
    return final_pdf_bytes, labels_procesadas_count

# --- INTERFAZ ---

uploaded_file = st.file_uploader(
    "Sube tu archivo .txt o .zpl completo",
    type=["txt", "zpl", "prn"],
    key="zpl_file_uploader_v7"
)

if uploaded_file:
    try:
        raw_data = uploaded_file.read()
        try:
            content = raw_data.decode("utf-8")
        except UnicodeDecodeError:
             content = raw_data.decode("latin-1")

        # PASO 1: Obtener la lista BRUTA de bloques (incluyendo repetidos)
        zpl_blocks = get_all_blocks_sequential(content)
        total_encontrados = len(zpl_blocks)

        if total_encontrados == 0:
            st.error("❌ No se encontraron etiquetas.")
        else:
            # --- VERIFICACIÓN VISUAL IMPORTANTE ---
            st.info(f"✅ ANÁLISIS DEL ARCHIVO: Se encontraron *{total_encontrados}* bloques ZPL en total.")
            
            # Aquí le decimos al usuario lo que va a pasar
            st.markdown(f"""
            Esto significa que *se generarán {total_encontrados} etiquetas*.
            * Si tu archivo tiene 131 diseños pero algunos se repiten, el total debe ser la suma (ej. 326).
            * *Verifica:* ¿Es {total_encontrados} el número total de etiquetas físicas que necesitas?
            """)
            
            if st.button(f"IMPRIMIR LAS {total_encontrados} ETIQUETAS 🚀"):
                with st.spinner("Generando PDF masivo..."):
                    pdf_bytes, total_paginas = process_labels_sequential(zpl_blocks)
                    
                    if pdf_bytes:
                        st.balloons()
                        st.success(f"¡Listo! PDF generado con *{total_paginas}* páginas.")
                        st.download_button(
                            label="📥 DESCARGAR PDF (326 etiquetas)",
                            data=pdf_bytes,
                            file_name="etiquetas_completas_v7.pdf",
                            mime="application/pdf"
                        )
    except Exception as e:
        st.error(f"Error: {e}")

# --- FOOTER ---
st.markdown("---")
st.write("Sistema V7: Sin deduplicación. Imprime exactamente lo que contiene el archivo.")
