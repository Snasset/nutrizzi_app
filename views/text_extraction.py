import os
import numpy as np
import cv2
from PIL import Image
import streamlit as st
from ultralytics import YOLO
from paddleocr import PaddleOCR
import re

from postproc import ekstrak_nutrisi, konversi_ke_100g, cek_kesehatan_bpom, postproc_paddle

# === LOAD MODEL ===
@st.cache_resource
def load_model():
    return YOLO("path/to/best.pt")

model_yolo = load_model()

@st.cache_resource
def load_ocr():
    return PaddleOCR(use_angle_cls=False, lang="en", show_log=False)

ocr = load_ocr()

# === STREAMLIT UI ===

st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #61FF61; 
        color: white;
        transition: background-color 0.3s ease;
    }

    div.stButton > button:first-child:hover {
        background-color: #ffffff;  
        color: #61FF61;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Ekstraksi dan Evaluasi Informasi Nilai Gizi")
st.subheader("📤 Upload Gambar Label Nutrisi")
uploaded_file = st.file_uploader("Upload Gambar", type=["jpg", "jpeg", "png"], key="upload_gambar")

if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    img_np = np.array(image) 
    st.image(image, caption="📷 Gambar Diupload", use_column_width=True)
    if st.button("🔍 Jalankan Proses"):
                resized_for_yolo = cv2.resize(img_np, (640, 640))
                img_bgr = cv2.cvtColor(resized_for_yolo, cv2.COLOR_RGB2BGR)
                results = model_yolo(img_bgr)

                if results and results[0].boxes is not None:
                    box = max(results[0].boxes, key=lambda b: b.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    crop = img_np[y1:y2, x1:x2]
                    crop_bgr = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)
                    temp_path = "paddle_tmp.png"
                    Image.fromarray(crop_bgr).save(temp_path)

                    with st.spinner("🔎 Menjalankan PaddleOCR..."):
                        ocr_raw = ocr.ocr(crop_bgr, cls=False)
                    ocr_cleaned = postproc_paddle(ocr_raw)
                    text_out = ocr_cleaned
                    st.session_state["crop_image"] = Image.open(temp_path)
                    st.session_state["ocr_raw"] = text_out
                    st.session_state["nutrisi"] = ekstrak_nutrisi(text_out)
                    st.image(temp_path, caption="📋 Tabel Nutrisi Ter-crop", width=350)
                    st.code(text_out)
                    os.remove(temp_path)
                else:
                    st.warning("❌ Tabel tidak ditemukan.")



# === EVALUASI ===
if "nutrisi" in st.session_state:
    st.subheader("🧪 Koreksi & Evaluasi Nutrisi")

    kategori_pilihan = st.selectbox("📦 Pilih Kategori Produk", [
        "Minuman Siap Konsumsi", "Pasta & Mi Instan", "Susu Bubuk Plain", "Susu Bubuk Rasa",
        "Keju", "Yogurt Plain", "Yogurt Rasa", "Serbuk Minuman Sereal", "Oatmeal",
        "Sereal Siap Santap (Flake/Keping)", "Sereal Batang (Bar)", "Granola",
        "Biskuit dan Kukis", "Roti dan Produk Roti", "Kue (Kue Kering dan Lembut)",
        "Puding Siap Santap", "Sambal", "Kecap Manis", "Makanan Ringan Siap Santap"
    ])


    label_nutrisi_fix = [
        "Takaran Saji", "Energi", "Lemak", "Gula", "Serat",
        "Garam", "Protein", "Karbohidrat", "Kalsium"
    ]
    nutrisi_input = {}

    with st.form("form_koreksi"):
        for label in label_nutrisi_fix:
            val = st.session_state["nutrisi"].get(label, "-")
            nutrisi_input[label] = st.text_input(f"{label}", value=val, key=f"input_{label}")
        submitted = st.form_submit_button("✅ Evaluasi")

    if submitted:
        try:
            takaran_str = nutrisi_input["Takaran Saji"]
            angka = re.findall(r"[\d.]+", takaran_str)
            takaran = float(angka[0]) if angka else None

            if takaran is None:
                raise ValueError

        except:
            st.error("❌ Takaran Saji harus berupa angka.")
            st.stop()

        nutrisi_norm = konversi_ke_100g(nutrisi_input, takaran)
        hasil = cek_kesehatan_bpom(kategori_pilihan, nutrisi_norm)

        st.subheader("📊 Evaluasi Berdasarkan Aturan BPOM")
        for line in hasil:
            if "⚠️" in line:
                st.warning(line)
            elif "✅" in line:
                st.success(line)
            else:
                st.info(line)
