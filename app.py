import streamlit as st
import re
import requests
import io
import time
from pypdf import PdfReader, PdfWriter

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="ZPL a PDF - Conversor Seguro",
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
st.title("🏷️ Convertidor ZPL a PDF (Modo Seguro)")
st.write("Genera PDFs para imprimir (2x1 pulg / 51x25 mm). Procesamiento paso a paso para máxima fiabilidad.")

# Bloque para Anuncio Horizontal
st.components.v1.html("""
    <div style="text-align:center;">
        <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; height: 90px; display: flex; align-items: center; justify-content: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
            <p style="color: #999; font-family: sans-serif; font-size: 12px;">ESPACIO PARA ANUNCIO GOOGLE ADSENSE</p>
        </div>
    </div>
""", height=100)

# --- LÓGICA DE PROCESAMIENTO SEGURO ---

def process_labels_secure(zpl_blocks):
    # CONFIGURACIÓN CLAVE: Procesamos de 1 en 1 para evitar errores de tamaño.
    batch_size = 1 
    
    pdf_writer = PdfWriter()
    url = 'http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/'
    headers = {'Accept': 'application/pdf'}
    
    total_blocks = len(zpl_blocks)
    labels_procesadas_count = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Procesar en bucle (etiqueta por etiqueta)
    for i, zpl_block in enumerate(zpl_blocks):
        label_num = i + 1
        status_text.markdown(f"🔄 Procesando etiqueta *{label_num} de {total_blocks}*...")

        max_retries = 3
        retry_delay = 1
        success = False

        for attempt in range(max_retries):
            try:
                # Enviar la etiqueta individual
                response = requests.post(url, headers=headers, data=zpl_block.encode('utf-8'), timeout=30)
                
                if response.status_code == 200:
                    batch_pdf_bytes = io.BytesIO(response.content)
                    batch_reader = PdfReader(batch_pdf_bytes)
                    
                    # Si el ZPL tiene comando ^PQ (cantidad), Labelary devuelve varias páginas.
                    # Las añadimos todas al PDF final.
                    paginas_recibidas = len(batch_reader.pages)
                    for page in batch_reader.pages:
                        pdf_writer.add_page(page)
                    
                    labels_procesadas_count += paginas_recibidas
                    success = True
                    # Brevísima pausa para no bombardear la API
                    time.sleep(0.1) 
                    break 
                elif response.status_code == 429:
                     status_text.warning(f"⚠️ Límite de velocidad de API. Esperando un momento...")
                     time.sleep(4)
                elif response.status_code == 413:
                     # Esto no debería pasar en modo 1 a 1, pero por seguridad:
                     st.error(f"❌ Error fatal: La etiqueta {label_num} es demasiado grande incluso sola.")
                     return None, 0
                else:
                    status_text.warning(f"⚠️ Hubo un pequeño error en la etiqueta {label_num}. Reintentando...")
                    time.sleep(retry_delay)

            except requests.exceptions.RequestException:
                status_text.warning(f"⚠️ Error de conexión momentáneo. Reintentando...")
                time.sleep(retry_delay)
        
        if not success:
             st.error(f"❌ ERROR CRÍTICO: No se pudo procesar la etiqueta {label_num} después de varios intentos. El proceso se detuvo.")
             return None, 0

        percent = (i + 1) / total_blocks
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
    key="zpl_file_uploader_final"
)

if uploaded_file:
    try:
        raw_data = uploaded_file.read()
        try:
            content = raw_data.decode("utf-8")
        except UnicodeDecodeError:
             content = raw_data.decode("latin-1")

        # Regex para encontrar bloques completos
        zpl_blocks = re.findall(r'(\^XA.*?\^XZ)', content, re.DOTALL | re.MULTILINE)
        num_detected = len(zpl_blocks)

        if num_detected == 0:
            st.error("❌ No se detectaron etiquetas válidas (^XA...^XZ) en el archivo.")
        else:
            st.info(f"✅ Se han detectado *{num_detected}* diseños de etiquetas distintos.")
            
            if st.button("GENERAR PDF FINAL 🚀", type="primary"):
                with st.spinner("Procesando etiquetas de forma segura... Por favor espera."):
                    pdf_bytes, total_paginas = process_labels_secure(zpl_blocks)
                    
                    if pdf_bytes:
                        st.balloons()
                        if total_paginas > num_detected:
                             st.success(f"¡Éxito! Se generaron *{total_paginas}* etiquetas en total (algunos diseños incluían copias múltiples).")
                        else:
                             st.success(f"¡Éxito! Se generaron *{total_paginas}* etiquetas correctamente.")
                        
                        st.download_button(
                            label="📥 DESCARGAR PDF",
                            data=pdf_bytes,
                            file_name="etiquetas_final.pdf",
                            mime="application/pdf"
                        )
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

# --- PIE DE PÁGINA Y SEO ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📖 Instrucciones
    1. Sube tu archivo de etiquetas.
    2. El sistema las procesará una a una para asegurar que no haya errores.
    3. Espera a que la barra de progreso termine (puede tomar unos minutos para archivos grandes).
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
