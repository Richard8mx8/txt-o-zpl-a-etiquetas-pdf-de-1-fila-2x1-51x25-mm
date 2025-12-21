import streamlit as st
import re
import requests
import io
import time
from fpdf import FPDF

# Configuración de la página para la Web App
st.set_page_config(
    page_title="ZPL & TXT to PDF Converter", 
    page_icon="🏷️",
    layout="centered"
)

# --- ESTILO PERSONALIZADO ---
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA Y MONETIZACIÓN ---
st.title("🏷️ Convertidor Universal de Etiquetas ZPL/TXT")
st.write("Transforma tus códigos Zebra en un PDF listo para imprimir (Tamaño 2x1 pulg / 51x25 mm).")

# Bloque para Google AdSense (Superior)
st.components.v1.html("""
    <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; height: 90px; display: flex; align-items: center; justify-content: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
        <p style="color: #999; font-family: sans-serif; font-size: 12px;">ANUNCIO DE GOOGLE ADSENSE (Banner Horizontal)</p>
    </div>
""", height=100)

# --- LÓGICA DE PROCESAMIENTO ---

def get_quantity(zpl_text):
    """Busca el comando ^PQ para determinar la cantidad de copias."""
    match = re.search(r'\^PQ(\d+)', zpl_text)
    return int(match.group(1)) if match else 1

def process_labels(zpl_blocks):
    """Renderiza las etiquetas y genera los bytes del PDF de forma segura."""
    # Tamaño 51x25 mm
    pdf = FPDF(unit="mm", format=[51, 25])
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_labels = 0
    
    for i, zpl in enumerate(zpl_blocks):
        cantidad = get_quantity(zpl)
        # API de Labelary (8 dpmm = 203 dpi)
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/'
        
        try:
            response = requests.post(url, data=zpl.encode('utf-8'))
            if response.status_code == 200:
                img_data = io.BytesIO(response.content)
                for _ in range(cantidad):
                    pdf.add_page()
                    pdf.image(img_data, 0, 0, 51, 25)
                    total_labels += 1
                # Pausa para respetar la API gratuita y evitar error 429
                time.sleep(0.6)
            
            # Actualización de la interfaz
            percent = (i + 1) / len(zpl_blocks)
            progress_bar.progress(percent)
            status_text.text(f"Procesando diseño {i+1} de {len(zpl_blocks)}...")
            
        except Exception as e:
            st.error(f"Error en bloque {i+1}: {e}")
            continue

    # --- CORRECCIÓN CRÍTICA PARA STREAMLIT ---
    # Obtenemos la salida del PDF
    pdf_output = pdf.output(dest='S')
    
    # Aseguramos que el formato sea 'bytes' (inmutable) y no 'bytearray'
    if isinstance(pdf_output, str):
        # Si es string (versiones antiguas fpdf), codificar a latin-1
        final_pdf_bytes = bytes(pdf_output, 'latin-1')
    else:
        # Forzar bytearray a bytes
        final_pdf_bytes = bytes(pdf_output)

    return final_pdf_bytes, total_labels

# --- INTERFAZ DE USUARIO ---

uploaded_file = st.file_uploader(
    "Sube tu archivo .txt o .zpl", 
    type=["txt", "zpl"],
    help="El archivo debe contener comandos Zebra (^XA ... ^XZ)"
)

if uploaded_file:
    # Leer datos del archivo subido
    raw_data = uploaded_file.read()
    content = raw_data.decode("utf-8", errors="ignore")
    
    # Extraer todos los bloques ZPL
    zpl_blocks = re.findall(r'\^XA.*?\^XZ', content, re.DOTALL)
    
    if not zpl_blocks:
        st.error("No se detectaron etiquetas válidas (^XA...^XZ) en el archivo.")
    else:
        st.success(f"Se detectaron {len(zpl_blocks)} diseños únicos.")
        
        if st.button("CONVERTIR A PDF PARA IMPRIMIR 🚀"):
            with st.spinner("Conectando con el motor de renderizado..."):
                pdf_bytes, total = process_labels(zpl_blocks)
                
                st.balloons()
                st.success(f"¡Éxito! Se generó un PDF con {total} etiquetas.")
                
                # Botón de descarga con los bytes corregidos
                st.download_button(
                    label="📥 DESCARGAR PDF FINAL",
                    data=pdf_bytes,
                    file_name="etiquetas_2x1_generadas.pdf",
                    mime="application/pdf"
                )

# --- PIE DE PÁGINA Y SEO ---
st.markdown("---")
st.markdown("""
### ¿Cómo usar esta herramienta?
1. Sube tu archivo generado por tu sistema de ventas o almacén.
2. Haz clic en convertir.
3. Abre el PDF resultante e imprime en tu impresora térmica Zebra, Munbyn o Rollo. 
4. *Configuración de impresión:* Asegúrate de seleccionar el tamaño de papel *51x25mm* y escala *"Tamaño Real"*.
""")

# Bloque para Google AdSense (Inferior)
st.components.v1.html("""
    <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; height: 250px; display: flex; align-items: center; justify-content: center; margin-top: 20px;">
        <p style="color: #999; font-family: sans-serif; font-size: 14px;">ANUNCIO DE GOOGLE ADSENSE (Cuadrado)</p>
    </div>
""", height=260)
