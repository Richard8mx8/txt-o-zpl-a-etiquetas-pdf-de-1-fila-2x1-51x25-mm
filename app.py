import streamlit as st
import re
import requests
import io
import time
from pypdf import PdfReader, PdfWriter

# --- 1. CONFIGURACIÓN DE LA PÁGINA Y ADS.TXT ---
st.set_page_config(
    page_title="Convertidor ZPL y TXT a Etiquetas PDF 2x1",
    page_icon="🏷️",
    layout="centered"
)

# Lógica para servir el contenido de ads.txt virtualmente
# Para que Google verifique tu sitio, debes ir a tudominio.com/?ads.txt
query_params = st.query_params
if "ads.txt" in query_params:
    st.text("google.com, pub-8311228733708760, DIRECT, f08c47fec0942fa0")
    st.stop()

# --- 2. INYECCIÓN DEL SCRIPT DE ADSENSE (GLOBAL) ---
st.components.v1.html("""
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8311228733708760"
     crossorigin="anonymous"></script>
""", height=0, scrolling=False)

# --- 3. ESTILOS CSS PERSONALIZADOS (MEJORA VISUAL) ---
st.markdown("""
    <style>
    /* Fondo general limpio */
    .stApp {
        background-color: #f8f9fa;
    }
    /* Título principal centrado y estilizado */
    h1 {
        color: #2c3e50;
        text-align: center;
        font-family: 'Helvetica', sans-serif;
        font-weight: 700;
        padding-bottom: 20px;
    }
    /* Estilo del botón de acción */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        color: #005c3e;
        border: none;
        font-weight: bold;
        font-size: 18px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 8px rgba(0,0,0,0.15);
    }
    /* Cajas de información */
    .stAlert {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Contenedor de publicidad */
    .ad-container {
        display: flex;
        justify-content: center;
        margin: 20px 0;
        padding: 10px;
        background-color: white;
        border: 1px solid #e9ecef;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. TÍTULO ---
st.title("Convertidor ZPL y TXT a Etiquetas PDF 2x1")
st.markdown("<p style='text-align: center; color: #666;'>Herramienta profesional para transformar códigos Zebra en archivos de impresión masiva.</p>", unsafe_allow_html=True)

# --- 5. ESPACIO PUBLICITARIO SUPERIOR (Banner) ---
st.markdown("---")
st.caption("Publicidad")
# Nota: Streamlit ejecuta esto en un iframe. Si tu dominio está aprobado, el anuncio saldrá aquí.
st.components.v1.html("""
    <div style="text-align: center;">
        <ins class="adsbygoogle"
             style="display:block"
             data-ad-client="ca-pub-8311228733708760"
             data-ad-slot="auto"
             data-ad-format="auto"
             data-full-width-responsive="true"></ins>
        <script>
             (adsbygoogle = window.adsbygoogle || []).push({});
        </script>
    </div>
""", height=120)
st.markdown("---")

# --- 6. LÓGICA DEL MOTOR "V8" (EL QUE FUNCIONA) ---

def obtener_cantidad_zpl(zpl_code):
    """Busca ^PQ para saber cuántas copias hacer."""
    match = re.search(r'\^PQ(\d+)', zpl_code)
    if match:
        return int(match.group(1))
    return 1

def process_labels_final(zpl_blocks):
    pdf_writer = PdfWriter()
    # Configuración 2x1 pulgadas (51x25mm)
    url = 'http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/'
    headers = {'Accept': 'application/pdf'}
    
    total_blocks = len(zpl_blocks)
    total_etiquetas_finales = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, zpl_block in enumerate(zpl_blocks):
        cantidad_copias = obtener_cantidad_zpl(zpl_block)
        label_num = i + 1
        
        status_text.markdown(f"⚙️ Procesando diseño *{label_num}/{total_blocks}* (Generando *{cantidad_copias}* copias)...")

        # Lógica de reintentos robusta
        max_retries = 5
        base_delay = 2
        success = False
        pdf_pagina_modelo = None 

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=zpl_block.encode('utf-8'), timeout=30)
                
                if response.status_code == 200:
                    batch_pdf_bytes = io.BytesIO(response.content)
                    batch_reader = PdfReader(batch_pdf_bytes)
                    if len(batch_reader.pages) > 0:
                        pdf_pagina_modelo = batch_reader.pages[0]
                        success = True
                        time.sleep(0.1) 
                        break 
                elif response.status_code == 429:
                     time.sleep(5)
                elif response.status_code == 413:
                     st.error(f"❌ Error: El diseño {label_num} es demasiado pesado.")
                     return None, 0
                else:
                    time.sleep(base_delay + (attempt * 2))
            except requests.exceptions.RequestException:
                time.sleep(base_delay + (attempt * 2))
        
        if not success or pdf_pagina_modelo is None:
             st.error(f"❌ No se pudo conectar con el servidor para el diseño {label_num}. Intenta más tarde.")
             return None, 0
        
        # Multiplicación interna
        for _ in range(cantidad_copias):
            pdf_writer.add_page(pdf_pagina_modelo)
            total_etiquetas_finales += 1

        progress_bar.progress((i + 1) / total_blocks)

    output_stream = io.BytesIO()
    pdf_writer.write(output_stream)
    final_pdf_bytes = output_stream.getvalue()
    
    status_text.empty()
    progress_bar.empty()
    
    return final_pdf_bytes, total_etiquetas_finales

# --- 7. INTERFAZ DE USUARIO ---

uploaded_file = st.file_uploader(
    "📂 Sube tu archivo .txt, .zpl o .prn",
    type=["txt", "zpl", "prn"],
    help="El archivo debe contener el código ZPL. El sistema detectará automáticamente las cantidades (^PQ)."
)

if uploaded_file:
    try:
        raw_data = uploaded_file.read()
        try:
            content = raw_data.decode("utf-8")
        except UnicodeDecodeError:
             content = raw_data.decode("latin-1")

        zpl_blocks = re.findall(r'(\^XA.*?\^XZ)', content, re.DOTALL | re.MULTILINE)
        diseños_unicos = len(zpl_blocks)

        if diseños_unicos == 0:
            st.error("⚠️ No se encontraron códigos ZPL válidos en el archivo.")
        else:
            # Cálculo previo
            total_esperado = sum(obtener_cantidad_zpl(b) for b in zpl_blocks)
            
            st.info(f"""
            *Análisis del Archivo:*
            * Diseños únicos detectados: *{diseños_unicos}*
            * Total de etiquetas a imprimir (leyendo ^PQ): *{total_esperado}*
            """)
            
            if st.button(f"GENERAR PDF ({total_esperado} ETIQUETAS) 🚀"):
                with st.spinner("Procesando etiquetas... Esto puede tomar unos momentos."):
                    pdf_bytes, total_generado = process_labels_final(zpl_blocks)
                    
                    if pdf_bytes:
                        st.balloons()
                        st.success(f"✅ ¡Proceso completado! Se generaron *{total_generado}* etiquetas.")
                        
                        st.download_button(
                            label="📥 DESCARGAR PDF FINAL",
                            data=pdf_bytes,
                            file_name="etiquetas_impresion_2x1.pdf",
                            mime="application/pdf"
                        )
    except Exception as e:
        st.error(f"Ocurrió un error al leer el archivo: {e}")

# --- 8. ESPACIO PUBLICITARIO INFERIOR (Rectángulo Grande) ---
st.markdown("---")
st.caption("Publicidad")
st.components.v1.html("""
    <div style="text-align: center;">
        <ins class="adsbygoogle"
             style="display:block"
             data-ad-client="ca-pub-8311228733708760"
             data-ad-slot="auto"
             data-ad-format="rectangle"
             data-full-width-responsive="true"></ins>
        <script>
             (adsbygoogle = window.adsbygoogle || []).push({});
        </script>
    </div>
""", height=300)

# --- 9. PIE DE PÁGINA ---
st.markdown("""
<div style="text-align: center; margin-top: 50px; color: #888; font-size: 12px;">
    <p>© 2024 Convertidor de Etiquetas. Todos los derechos reservados.</p>
    <p><a href="/?page=privacy" style="color: #888;">Política de Privacidad</a> | <a href="#" style="color: #888;">Contacto</a></p>
</div>
""", unsafe_allow_html=True)
