import streamlit as st
import re
import requests
import io
import time
from pypdf import PdfReader, PdfWriter

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="ZPL & TXT to PDF Converter Robusto v2",
    page_icon="🏷️",
    layout="centered"
)

# --- CONFIGURACIÓN PARA GOOGLE ADSENSE (ads.txt) ---
query_params = st.query_params
if "ads.txt" in query_params:
    st.text("google.com, pub-8311228733708760, DIRECT, f08c47fec0942fa0")
    st.stop()

st.components.v1.html("""
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8311228733708760"
     crossorigin="anonymous"></script>
""", height=0)

# --- ESTILO PERSONALIZADO ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
        font-weight: bold;
    }
    .stAlert { border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA Y MONETIZACIÓN SUPERIOR ---
st.title("🏷️ Convertidor Robusto ZPL a PDF (v2)")
st.write("Transforma tus códigos Zebra en un PDF listo para imprimir (2x1 pulg / 51x25 mm).")

# Bloque para Anuncio Horizontal
st.components.v1.html("""
    <div style="text-align:center;">
        <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; height: 90px; display: flex; align-items: center; justify-content: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
            <p style="color: #999; font-family: sans-serif; font-size: 12px;">ESPACIO PARA ANUNCIO GOOGLE ADSENSE</p>
        </div>
    </div>
""", height=100)

# --- LÓGICA DE PROCESAMIENTO ROBUSTO ---

# --- CAMBIO AQUÍ: Reducimos el tamaño del lote por defecto a 10 ---
def process_labels_robusto(zpl_blocks, batch_size=10):
    """
    Procesa una lista de bloques ZPL en lotes pequeños para evitar errores 413.
    Une los resultados en un solo PDF usando pypdf.
    """
    pdf_writer = PdfWriter()
    
    # URL para etiquetas de 2x1 pulgadas a 8dpmm (203dpi)
    url = 'http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/'
    headers = {'Accept': 'application/pdf'}
    
    total_blocks = len(zpl_blocks)
    labels_procesadas_count = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Procesar en bucle por lotes
    for i in range(0, total_blocks, batch_size):
        current_batch = zpl_blocks[i : i + batch_size]
        batch_number = (i // batch_size) + 1
        total_batches = (total_blocks + batch_size - 1) // batch_size
        
        status_text.markdown(f"🔄 Procesando lote *{batch_number}/{total_batches}* (Etiquetas {i+1} a {min(i + batch_size, total_blocks)})...")

        batch_zpl_string = "\n".join(current_batch)

        max_retries = 3
        retry_delay = 2
        batch_success = False

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=batch_zpl_string.encode('utf-8'), timeout=60)
                
                if response.status_code == 200:
                    batch_pdf_bytes = io.BytesIO(response.content)
                    batch_reader = PdfReader(batch_pdf_bytes)
                    
                    paginas_en_lote = len(batch_reader.pages)
                    for page in batch_reader.pages:
                        pdf_writer.add_page(page)
                    
                    labels_procesadas_count += paginas_en_lote
                    batch_success = True
                    time.sleep(0.5) 
                    break 
                elif response.status_code == 429:
                     status_text.warning(f"⚠️ Límite de velocidad de API. Esperando 5s...")
                     time.sleep(5)
                # --- CAMBIO AQUÍ: Manejo específico del error 413 ---
                elif response.status_code == 413:
                     status_text.error(f"❌ Error 413 en lote {batch_number}: El lote es muy pesado. Intenta reducir más el 'batch_size' en el código.")
                     # Si es 413, no tiene sentido reintentar el mismo lote pesado, fallará igual. Salimos del loop de intentos.
                     break 
                else:
                    status_text.warning(f"⚠️ Error API lote {batch_number} (Intento {attempt+1}): Código {response.status_code}. Reintentando...")
                    time.sleep(retry_delay)

            except requests.exceptions.RequestException as e:
                status_text.warning(f"⚠️ Error conexión lote {batch_number} (Intento {attempt+1}): {e}. Reintentando...")
                time.sleep(retry_delay)
        
        if not batch_success:
             st.error(f"❌ ERROR CRÍTICO: No se pudo procesar el lote {batch_number}. El PDF final estará incompleto o vacío.")
             # Importante: Si un lote falla por 413, detenemos todo para que el usuario ajuste.
             return None, 0

        percent = min((i + batch_size) / total_blocks, 1.0)
        progress_bar.progress(percent)

    output_stream = io.BytesIO()
    pdf_writer.write(output_stream)
    final_pdf_bytes = output_stream.getvalue()

    status_text.empty()
    progress_bar.empty()
    
    return final_pdf_bytes, labels_procesadas_count

# --- INTERFAZ DE USUARIO ---

uploaded_file = st.file_uploader(
    "Sube tu archivo .txt o .zpl (con múltiples etiquetas)",
    type=["txt", "zpl", "prn"],
    help="El archivo debe contener bloques ZPL que empiecen con ^XA y terminen con ^XZ",
    key="zpl_file_uploader_main"
)

if uploaded_file:
    try:
        raw_data = uploaded_file.read()
        try:
            content = raw_data.decode("utf-8")
        except UnicodeDecodeError:
             content = raw_data.decode("latin-1")

        # Regex robusto para encontrar bloques
        zpl_blocks = re.findall(r'(\^XA.*?\^XZ)', content, re.DOTALL | re.MULTILINE)
        
        num_detected = len(zpl_blocks)

        if num_detected == 0:
            st.error("❌ No se detectaron etiquetas válidas en el archivo. Asegúrate de que cada etiqueta empiece con ^XA y termine con ^XZ.")
        else:
            st.info(f"✅ Se han detectado *{num_detected}* bloques de etiquetas en el archivo.")
            st.info("ℹ️ Se procesarán en lotes de 10 para evitar errores de tamaño.")
            
            if st.button("GENERAR PDF ROBUSTO (Lotes de 10) 🚀", type="primary"):
                with st.spinner("Procesando por lotes pequeños..."):
                    # --- CAMBIO AQUÍ: Llamamos con batch_size=10 ---
                    pdf_bytes, total_paginas = process_labels_robusto(zpl_blocks, batch_size=10)
                    
                    if pdf_bytes:
                        st.balloons()
                        st.success(f"¡Éxito! Se generó un PDF con un total de *{total_paginas}* etiquetas.")
                        
                        st.download_button(
                            label="📥 DESCARGAR PDF FINAL",
                            data=pdf_bytes,
                            file_name="etiquetas_robustas_2x1.pdf",
                            mime="application/pdf"
                        )
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

# --- PIE DE PÁGINA Y SEO ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📖 Instrucciones V2
    1. Sube tu archivo con múltiples etiquetas.
    2. El sistema las procesará en *lotes seguros de 10*.
    3. Espera a que la barra de progreso termine.
    4. Descarga tu PDF completo.
    """)

with col2:
    st.markdown("""
    ### ⚖️ Legal
    - [Política de Privacidad](/?page=privacy)
    - [Contacto](mailto:tuemail@dominio.com)
    """)

# Bloque para Anuncio Cuadrado (Inferior)
st.components.v1.html("""
    <div style="text-align:center; margin-top: 20px;">
        <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; height: 250px; display: flex; align-items: center; justify-content: center;">
            <p style="color: #999; font-family: sans-serif; font-size: 14px;">ANUNCIO DE GOOGLE ADSENSE</p>
        </div>
    </div>
""", height=260)


