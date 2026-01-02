import streamlit as st
import re
import requests
import io
import time
from pypdf import PdfReader, PdfWriter

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="ZPL a PDF - Conversor Ultra Seguro V5",
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
st.title("🏷️ Convertidor ZPL a PDF (Ultra Seguro V5)")
st.write("Procesamiento paso a paso con reintentos avanzados para máxima fiabilidad ante inestabilidad de red.")

# Bloque para Anuncio Horizontal
st.components.v1.html("""
    <div style="text-align:center;">
        <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; height: 90px; display: flex; align-items: center; justify-content: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
            <p style="color: #999; font-family: sans-serif; font-size: 12px;">ESPACIO PARA ANUNCIO GOOGLE ADSENSE</p>
        </div>
    </div>
""", height=100)

# --- LÓGICA DE PROCESAMIENTO ULTRA SEGURO ---

def process_labels_ultra_secure(zpl_blocks):
    # CONFIGURACIÓN: Procesamos de 1 en 1.
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

        # --- MEJORA V5: MÁS REINTENTOS Y ESPERA PROGRESIVA ---
        max_retries = 5  # Aumentado de 3 a 5
        base_delay = 2   # Espera base de 2 segundos

        success = False

        for attempt in range(max_retries):
            try:
                # Timeout de 30s es suficiente para una sola etiqueta
                response = requests.post(url, headers=headers, data=zpl_block.encode('utf-8'), timeout=30)
                
                if response.status_code == 200:
                    batch_pdf_bytes = io.BytesIO(response.content)
                    batch_reader = PdfReader(batch_pdf_bytes)
                    
                    paginas_recibidas = len(batch_reader.pages)
                    for page in batch_reader.pages:
                        pdf_writer.add_page(page)
                    
                    labels_procesadas_count += paginas_recibidas
                    success = True
                    # Brevísima pausa de cortesía si todo va bien
                    time.sleep(0.1) 
                    break 

                elif response.status_code == 429:
                     # Si nos dice que paremos, paramos 5 segundos fijos.
                     status_text.warning(f"⚠️ API saturada (429). Pausando 5s antes de reintentar etiqueta {label_num}...")
                     time.sleep(5)

                elif response.status_code == 413:
                     # Esto no debería pasar en modo 1 a 1 tras el diagnóstico.
                     st.error(f"❌ Error fatal: La etiqueta {label_num} es demasiado grande (413).")
                     return None, 0
                else:
                    # Otros errores del servidor (ej. 500, 503)
                    # Espera progresiva: 2s, 4s, 6s, 8s, 10s
                    wait_time = base_delay + (attempt * 2)
                    status_text.warning(f"⚠️ Error del servidor ({response.status_code}) en etiqueta {label_num}. Reintentando en {wait_time}s (Intento {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)

            except requests.exceptions.RequestException as e:
                # Errores de conexión (internet caído momentáneamente, DNS, etc)
                wait_time = base_delay + (attempt * 2)
                # Simplificamos el mensaje de error para que no sea tan largo en pantalla
                error_msg = str(e).split(':')[0] 
                status_text.warning(f"⚠️ Problema de conexión en etiqueta {label_num}: {error_msg}. Reintentando en {wait_time}s (Intento {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
        
        if not success:
             st.error(f"❌ ERROR CRÍTICO: Se agotaron los 5 intentos para la etiqueta {label_num}. La API de Labelary no responde para esta etiqueta en este momento. Intenta más tarde.")
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
    key="zpl_file_uploader_v5"
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
            
            if st.button("GENERAR PDF FINAL (ULTRA SEGURO) 🚀", type="primary"):
                with st.spinner("Procesando etiquetas con alta tolerancia a fallos de red..."):
                    pdf_bytes, total_paginas = process_labels_ultra_secure(zpl_blocks)
                    
                    if pdf_bytes:
                        st.balloons()
                        msg = f"¡Éxito! Se generaron *{total_paginas}* etiquetas correctamente."
                        if total_paginas > num_detected:
                             msg += " (Algunos diseños incluían copias múltiples)."
                        st.success(msg)
                        
                        st.download_button(
                            label="📥 DESCARGAR PDF",
                            data=pdf_bytes,
                            file_name="etiquetas_final_v5.pdf",
                            mime="application/pdf"
                        )
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

# --- PIE DE PÁGINA Y SEO ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📖 Instrucciones V5
    1. Sube tu archivo de etiquetas.
    2. El sistema procesará una a una, con *múltiples reintentos y esperas* si la API falla.
    3. Ten paciencia, este método prioriza terminar bien sobre la velocidad.
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

