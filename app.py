import streamlit as st
import re
import requests
import io
import time
from fpdf import FPDF

# Configuración de la página
st.set_page_config(page_title="ZPL to PDF Converter", layout="centered")

# Título y Publicidad Superior
st.title("🖨️ Convertidor ZPL a PDF (2x1 pulg)")
st.components.v1.html("""
    <div style="text-align:center; background-color:#f0f2f6; padding:10px; border-radius:10px;">
        <p style="color:#555;">Espacio para Banner de Google AdSense</p>
        </div>
""", height=100)

def get_quantity(zpl_text):
    match = re.search(r'\^PQ(\d+)', zpl_text)
    return int(match.group(1)) if match else 1

def convert_zpl_to_pdf(zpl_blocks):
    pdf = FPDF(unit="mm", format=[51, 25])
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_labels = 0
    for i, zpl in enumerate(zpl_blocks):
        cantidad = get_quantity(zpl)
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/'
        
        try:
            res = requests.post(url, data=zpl)
            if res.status_code == 200:
                img_data = io.BytesIO(res.content)
                for _ in range(cantidad):
                    pdf.add_page()
                    pdf.image(img_data, 0, 0, 51, 25)
                    total_labels += 1
                time.sleep(0.6) # Evitar bloqueo API
            
            # Actualizar barra de progreso
            progress = (i + 1) / len(zpl_blocks)
            progress_bar.progress(progress)
            status_text.text(f"Procesando diseño {i+1} de {len(zpl_blocks)}...")
            
        except Exception as e:
            st.error(f"Error en etiqueta {i+1}: {e}")

    return pdf.output(dest='S'), total_labels

# Interfaz de subida
uploaded_file = st.file_uploader("Sube tu archivo .txt o .zpl", type=["txt", "zpl"])

if uploaded_file is not None:
    content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
    zpl_blocks = re.findall(r'\^XA.*?\^XZ', content, re.DOTALL)
    
    if st.button("🚀 Iniciar Conversión"):
        if zpl_blocks:
            pdf_bytes, total = convert_zpl_to_pdf(zpl_blocks)
            st.success(f"¡Listo! Se generaron {total} etiquetas.")
            
            # Botón de descarga
            st.download_button(
                label="📥 Descargar PDF Final",
                data=pdf_bytes,
                file_name="etiquetas_2x1.pdf",
                mime="application/pdf"
            )
        else:
            st.error("No se detectaron comandos ZPL (^XA...^XZ) en el archivo.")

# Publicidad Lateral o Inferior
st.write("---")
st.info("Nota: Este servicio es gratuito. Considera hacer clic en nuestros anuncios para apoyarnos.")