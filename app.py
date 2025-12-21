import streamlit as st
import re
import requests
import io
import time
from fpdf import FPDF

# --- CONFIGURACIÓN PARA GOOGLE ADSENSE (ads.txt) ---
# Reemplaza esta línea con tu ID real de AdSense cuando lo tengas
ADS_TXT_CONTENT = "google.com, pub-0000000000000000, DIRECT, f08c47fec0942fa0"

# Lógica para servir ads.txt (Esencial para la validación de Google)
query_params = st.query_params
if "ads.txt" in query_params or ("page" in query_params and query_params["page"] == "ads.txt"):
    st.text(ADS_TXT_CONTENT)
    st.stop()

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="ZPL & TXT to PDF Converter", 
    page_icon="🏷️",
    layout="centered"
)

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
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA Y MONETIZACIÓN SUPERIOR ---
st.title("🏷️ Convertidor Universal de Etiquetas ZPL/TXT")
st.write("Transforma tus códigos Zebra en un PDF listo para imprimir (2x1 pulg / 51x25 mm 1 Fila).")

# Bloque para Anuncio Horizontal
st.components.v1.html("""
    <div style="text-align:center;">
        <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; height: 90px; display: flex; align-items: center; justify-content: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
            <p style="color: #999; font-family: sans-serif; font-size: 12px;">ESPACIO PARA ANUNCIO GOOGLE ADSENSE</p>
        </div>
    </div>
""", height=100)

# --- LÓGICA DE PROCESAMIENTO ---

def get_quantity(zpl_text):
    match = re.search(r'\^PQ(\d+)', zpl_text)
    return int(match.group(1)) if match else 1

def process_labels(zpl_blocks):
    pdf = FPDF(unit="mm", format=[51, 25])
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_labels = 0
    
    for i, zpl in enumerate(zpl_blocks):
        cantidad = get_quantity(zpl)
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/2x1/0/'
        
        try:
            response = requests.post(url, data=zpl.encode('utf-8'))
            if response.status_code == 200:
                img_data = io.BytesIO(response.content)
                for _ in range(cantidad):
                    pdf.add_page()
                    pdf.image(img_data, 0, 0, 51, 25)
                    total_labels += 1
                time.sleep(0.6) # Delay para API
            
            percent = (i + 1) / len(zpl_blocks)
            progress_bar.progress(percent)
            status_text.text(f"Procesando diseño {i+1} de {len(zpl_blocks)}...")
            
        except Exception as e:
            st.error(f"Error en bloque {i+1}: {e}")
            continue

    pdf_output = pdf.output(dest='S')
    final_pdf_bytes = bytes(pdf_output) if not isinstance(pdf_output, str) else bytes(pdf_output, 'latin-1')
    return final_pdf_bytes, total_labels

# --- INTERFAZ DE USUARIO ---

uploaded_file = st.file_uploader(
    "Sube tu archivo .txt o .zpl", 
    type=["txt", "zpl"],
    help="El archivo debe contener comandos Zebra (^XA ... ^XZ)",
    key="zpl_file_uploader_main"
)

if uploaded_file:
    raw_data = uploaded_file.read()
    content = raw_data.decode("utf-8", errors="ignore")
    zpl_blocks = re.findall(r'\^XA.*?\^XZ', content, re.DOTALL)
    
    if not zpl_blocks:
        st.error("No se detectaron etiquetas válidas (^XA...^XZ) en el archivo.")
    else:
        st.success(f"Se detectaron {len(zpl_blocks)} diseños únicos.")
        
        if st.button("CONVERTIR A PDF PARA IMPRIMIR 🚀"):
            with st.spinner("Generando archivo PDF..."):
                pdf_bytes, total = process_labels(zpl_blocks)
                st.balloons()
                st.success(f"¡Éxito! Se generaron {total} etiquetas.")
                
                st.download_button(
                    label="📥 DESCARGAR PDF FINAL",
                    data=pdf_bytes,
                    file_name="etiquetas_2x1.pdf",
                    mime="application/pdf"
                )

# --- PIE DE PÁGINA Y SEO ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📖 Instrucciones
    1. Sube tu archivo *.txt* o *.zpl*.
    2. Haz clic en el botón azul de convertir.
    3. Imprime el PDF en tamaño real (51x25mm).
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

