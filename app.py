import streamlit as st
import re
import requests
import io
import time
from pypdf import PdfReader, PdfWriter

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="ZPL Diagnóstico y Conversión",
    page_icon="🕵️‍♂️",
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
st.title("🕵️‍♂️ Convertidor ZPL: Modo Diagnóstico")
st.write("Procesamiento 1 a 1 para detectar etiquetas corruptas o 'pesadas'.")

# Bloque para Anuncio Horizontal
st.components.v1.html("""
    <div style="text-align:center;">
        <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; height: 90px; display: flex; align-items: center; justify-content: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
            <p style="color: #999; font-family: sans-serif; font-size: 12px;">ESPACIO PARA ANUNCIO GOOGLE ADSENSE</p>
        </div>
    </div>
""", height=100)

# --- LÓGICA DE PROCESAMIENTO ROBUSTO CON DIAGNÓSTICO ---

# --- CAMBIO CLAVE: batch_size=1 por defecto para aislar el problema ---
def process_labels_diagnostico(zpl_blocks, batch_size=1):
    pdf_writer = PdfWriter()
    url = 'http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/'
    headers = {'Accept': 'application/pdf'}
    
    total_blocks = len(zpl_blocks)
    labels_procesadas_count = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    error_container = st.container() # Contenedor para reportar errores específicos

    # Procesar en bucle por lotes (ahora lotes de 1)
    for i in range(0, total_blocks, batch_size):
        current_batch = zpl_blocks[i : i + batch_size]
        
        # Índices para mostrar al usuario (base 1)
        start_idx = i + 1
        end_idx = min(i + batch_size, total_blocks)
        batch_label = f"etiqueta {start_idx}" if batch_size == 1 else f"etiquetas {start_idx}-{end_idx}"

        batch_zpl_string = "\n".join(current_batch)
        
        # --- DIAGNÓSTICO DE PESO ---
        batch_bytes = batch_zpl_string.encode('utf-8')
        payload_size_kb = len(batch_bytes) / 1024
        
        status_text.markdown(f"⚖️ Procesando *{batch_label}*. Tamaño del envío: *{payload_size_kb:.2f} KB*...")

        max_retries = 2 # Menos reintentos en modo diagnóstico
        retry_delay = 1
        batch_success = False

        for attempt in range(max_retries):
            try:
                # Usamos batch_bytes directamente que ya lo calculamos
                response = requests.post(url, headers=headers, data=batch_bytes, timeout=30)
                
                if response.status_code == 200:
                    batch_pdf_bytes = io.BytesIO(response.content)
                    batch_reader = PdfReader(batch_pdf_bytes)
                    for page in batch_reader.pages:
                        pdf_writer.add_page(page)
                    
                    labels_procesadas_count += len(batch_reader.pages)
                    batch_success = True
                    # Pausa muy breve para no saturar demasiado
                    time.sleep(0.2) 
                    break 
                elif response.status_code == 429:
                     status_text.warning(f"⚠️ Límite de velocidad de API. Esperando 3s...")
                     time.sleep(3)
                elif response.status_code == 413:
                     # --- REPORTE DETALLADO DEL ERROR 413 ---
                     error_msg = f"❌ *ERROR 413 FATAL en {batch_label}*."
                     error_msg += f" Esta etiqueta individual pesa *{payload_size_kb:.2f} KB*, lo cual es demasiado para el servidor."
                     error_msg += " Revisa el código ZPL de esta etiqueta específica en tu archivo original, probablemente contiene datos corruptos o imágenes enormes ocultas."
                     error_container.error(error_msg)
                     status_text.error("Proceso detenido por etiqueta corrupta.")
                     break # Romper el bucle de reintentos
                else:
                    # Otros errores
                    time.sleep(retry_delay)

            except requests.exceptions.RequestException as e:
                time.sleep(retry_delay)
        
        if not batch_success:
             # Si falló y no fue por 413 (que ya se reportó arriba), reportamos aquí
             if response is None or response.status_code != 413:
                 error_container.error(f"❌ No se pudo procesar {batch_label} tras reintentos. Posible error de red o API caída momentáneamente.")
             
             st.error("⚠️ El proceso se detuvo incompleto debido a errores. Descarga lo que se pudo generar.")
             # Devolvemos lo que tengamos hasta ahora
             break

        percent = min(end_idx / total_blocks, 1.0)
        progress_bar.progress(percent)

    output_stream = io.BytesIO()
    pdf_writer.write(output_stream)
    final_pdf_bytes = output_stream.getvalue()

    status_text.empty()
    progress_bar.empty()
    
    return final_pdf_bytes, labels_procesadas_count, total_blocks

# --- INTERFAZ DE USUARIO ---

uploaded_file = st.file_uploader(
    "Sube tu archivo .txt o .zpl",
    type=["txt", "zpl", "prn"],
    key="zpl_file_uploader_diag"
)

if uploaded_file:
    try:
        raw_data = uploaded_file.read()
        try:
            content = raw_data.decode("utf-8")
        except UnicodeDecodeError:
             content = raw_data.decode("latin-1")

        zpl_blocks = re.findall(r'(\^XA.*?\^XZ)', content, re.DOTALL | re.MULTILINE)
        num_detected = len(zpl_blocks)

        if num_detected == 0:
            st.error("❌ No se detectaron etiquetas válidas (^XA...^XZ).")
        else:
            st.info(f"✅ Se detectaron *{num_detected}* etiquetas.")
            st.warning("ℹ️ MODO DIAGNÓSTICO: Se procesarán UNA POR UNA para encontrar la causa del 'Error 413'. Esto tomará unos minutos. Por favor ten paciencia y observa los mensajes de estado.")
            
            # Usamos un key diferente para forzar el renderizado del botón
            if st.button("INICIAR PROCESO 1 A 1 🕵️‍♂️", type="primary", key="btn_diag_start"):
                with st.spinner("Procesando etiquetas individualmente y verificando peso..."):
                    # --- LLAMADA CON batch_size=1 IMPLÍCITO ---
                    pdf_bytes, total_paginas, total_intentadas = process_labels_diagnostico(zpl_blocks)
                    
                    if pdf_bytes and total_paginas > 0:
                        if total_paginas == total_intentadas:
                             st.balloons()
                             st.success(f"✅ ¡Éxito total! Se procesaron las {total_paginas} etiquetas sin errores 413.")
                        else:
                             st.warning(f"⚠️ Proceso finalizado parcialmente. Se generaron *{total_paginas} de {total_intentadas}* etiquetas. Revisa los errores rojos arriba para ver cuál falló.")

                        st.download_button(
                            label="📥 DESCARGAR PDF GENERADO",
                            data=pdf_bytes,
                            file_name="etiquetas_diagnostico.pdf",
                            mime="application/pdf"
                        )
    except Exception as e:
        st.error(f"Error de lectura: {e}")

# --- PIE DE PÁGINA ---
st.markdown("---")
st.write("Modo de diagnóstico para identificar errores de 'Payload Too Large'.")
