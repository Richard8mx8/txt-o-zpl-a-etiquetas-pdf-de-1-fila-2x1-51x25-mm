import streamlit as st
import requests
import io
import time
# Ya no necesitamos regex (re) para la extracción principal
from pypdf import PdfReader, PdfWriter

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="ZPL a PDF - Conversor Total V6",
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
st.title("🏷️ Convertidor ZPL Total (V6 - Incluye Repetidos)")
st.write("Garantiza el procesamiento de CADA bloque ZPL del archivo, incluyendo etiquetas repetidas, usando el modo ultra seguro paso a paso.")

# Bloque para Anuncio Horizontal
st.components.v1.html("""
    <div style="text-align:center;">
        <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; height: 90px; display: flex; align-items: center; justify-content: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
            <p style="color: #999; font-family: sans-serif; font-size: 12px;">ESPACIO PARA ANUNCIO GOOGLE ADSENSE</p>
        </div>
    </div>
""", height=100)

# --- FUNCIÓN DE EXTRACCIÓN MANUAL (NUEVO EN V6) ---
def extraer_bloques_zpl_total(content):
    """
    Extrae bloques ZPL dividiendo manualmente el texto.
    Garantiza que se capturan etiquetas idénticas repetidas.
    """
    blocks = []
    # Dividimos el contenido gigante usando el inicio de etiqueta como separador
    raw_chunks = content.split('^XA')

    # El primer fragmento (raw_chunks[0]) es lo que hay antes del primer ^XA, lo ignoramos.
    # Iteramos desde el segundo fragmento.
    for chunk in raw_chunks[1:]:
        # En cada fragmento, buscamos dónde está el primer cierre ^XZ
        xz_index = chunk.find('^XZ')
        
        if xz_index != -1:
            # Cortamos desde el principio hasta justo después del ^XZ (+3 caracteres)
            clean_content = chunk[:xz_index+3]
            # Reconstruimos el bloque añadiendo el ^XA que quitamos al hacer split
            full_block = '^XA' + clean_content
            # Añadimos a la lista. Esto NO elimina duplicados.
            blocks.append(full_block)
            
    return blocks

# --- LÓGICA DE PROCESAMIENTO ULTRA SEGURO (V5 MANTENIDA) ---

def process_labels_total_secure(zpl_blocks):
    # CONFIGURACIÓN: Procesamos de 1 en 1 para máxima seguridad.
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
        # Mostramos un mensaje claro de que estamos procesando instancias individuales
        status_text.markdown(f"🔄 Procesando instancia de etiqueta *{label_num} de {total_blocks}*...")

        # --- REINTENTOS Y ESPERA PROGRESIVA ---
        max_retries = 5
        base_delay = 2
        success = False

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=zpl_block.encode('utf-8'), timeout=30)
                
                if response.status_code == 200:
                    batch_pdf_bytes = io.BytesIO(response.content)
                    batch_reader = PdfReader(batch_pdf_bytes)
                    
                    paginas_recibidas = len(batch_reader.pages)
                    for page in batch_reader.pages:
                        pdf_writer.add_page(page)
                    
                    labels_procesadas_count += paginas_recibidas
                    success = True
                    time.sleep(0.1) 
                    break 

                elif response.status_code == 429:
                     status_text.warning(f"⚠️ API saturada (429). Pausando 5s antes de reintentar instancia {label_num}...")
                     time.sleep(5)

                elif response.status_code == 413:
                     st.error(f"❌ Error fatal: La instancia {label_num} es demasiado grande (413).")
                     return None, 0
                else:
                    wait_time = base_delay + (attempt * 2)
                    status_text.warning(f"⚠️ Error del servidor ({response.status_code}) en instancia {label_num}. Reintentando en {wait_time}s...")
                    time.sleep(wait_time)

            except requests.exceptions.RequestException as e:
                wait_time = base_delay + (attempt * 2)
                error_msg = str(e).split(':')[0] 
                status_text.warning(f"⚠️ Problema de conexión en instancia {label_num}: {error_msg}. Reintentando en {wait_time}s...")
                time.sleep(wait_time)
        
        if not success:
             st.error(f"❌ ERROR CRÍTICO: Se agotaron los 5 intentos para la instancia {label_num}. Proceso detenido.")
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
    "Sube tu archivo .txt o .zpl (con múltiples etiquetas, incluso repetidas)",
    type=["txt", "zpl", "prn"],
    key="zpl_file_uploader_v6"
)

if uploaded_file:
    try:
        raw_data = uploaded_file.read()
        try:
            content = raw_data.decode("utf-8")
        except UnicodeDecodeError:
             content = raw_data.decode("latin-1")

        # --- CAMBIO PRINCIPAL V6: Usamos la nueva función de extracción manual ---
        zpl_blocks = extraer_bloques_zpl_total(content)
        num_detected = len(zpl_blocks)

        if num_detected == 0:
            st.error("❌ No se detectaron bloques válidos (^XA...^XZ) en el archivo.")
        else:
            # Ahora el mensaje confirma que se detectaron todas las instancias
            st.info(f"✅ Se han detectado *{num_detected}* instancias de etiquetas en total (incluyendo repetidas).")
            st.write("El PDF final contendrá exactamente este número de etiquetas.")
            
            if st.button("GENERAR PDF TOTAL (Incluir Repetidos) 🚀", type="primary"):
                with st.spinner(f"Procesando las {num_detected} etiquetas una por una..."):
                    pdf_bytes, total_paginas = process_labels_total_secure(zpl_blocks)
                    
                    if pdf_bytes:
                        st.balloons()
                        st.success(f"¡Éxito absoluto! Se generó un PDF con *{total_paginas}* páginas.")
                        
                        st.download_button(
                            label="📥 DESCARGAR PDF COMPLETO",
                            data=pdf_bytes,
                            file_name="etiquetas_total_v6.pdf",
                            mime="application/pdf"
                        )
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

# --- PIE DE PÁGINA Y SEO ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📖 Instrucciones V6 (Total)
    1. Sube tu archivo. *Se procesarán todas las etiquetas, incluidas las repetidas.*
    2. Si tu archivo tiene 326 bloques, obtendrás 326 etiquetas.
    3. Se usa el modo ultra seguro (lento pero fiable).
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

