import os
import numpy as np
import cv2
from PIL import Image
import streamlit as st
from ultralytics import YOLO
from paddleocr import PaddleOCR
import re
import uuid

from postproc import ekstrak_nutrisi, konversi_ke_100g, cek_kesehatan_bpom, auto_tidy_for_extraction
import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

@st.cache_resource
def load_model():
    return YOLO("tabledet_model/best.pt")

model_yolo = load_model()

@st.cache_resource
def load_ocr():
    return PaddleOCR(lang="en", rec_model_dir='infer_pp-ocrv3_rec',det_model_dir="infer_pp-ocrv3_det", use_angle_cls=False)

ocr = load_ocr()

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
st.subheader("📤 Upload atau Ambil Foto Label Nutrisi")

tab1, tab2 = st.tabs(["Upload File", "Kamera"])

with tab1:
    uploaded_file = st.file_uploader("Upload Gambar", type=["jpg", "jpeg", "png"], key="upload_gambar")
    if uploaded_file:
        unique_name = f"{uuid.uuid4()}_{uploaded_file.name}"
        st.session_state["uploaded_file_name"] = unique_name
        st.session_state["uploaded_file"] = uploaded_file

with tab2:
    camera_file = st.camera_input("Ambil Foto dengan Kamera", key="kamera_gambar")
    if camera_file:
        unique_name = f"{uuid.uuid4()}_camera.png"
        st.session_state["uploaded_file_name"] = unique_name
        st.session_state["uploaded_file"] = camera_file

if "uploaded_file" in st.session_state:
    with st.spinner("📤 Memproses gambar..."):
        image = Image.open(st.session_state["uploaded_file"]).convert("RGB")
        width, height = image.size
        if max(width, height) > 1080:
            scale = 1080 / max(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = image.resize((new_width, new_height))
        img_np = np.array(image) 
        st.image(image, caption="📷 Gambar Diupload", use_container_width=True)

    if st.button("🔍 Jalankan Proses"):
        with st.spinner("🚀 Inference YOLO berjalan..."):
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            results = model_yolo(img_bgr)

        if results and results[0].boxes is not None and len(results[0].boxes) > 0:
            box = max(results[0].boxes, key=lambda b: b.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            crop_bgr = img_np[y1:y2, x1:x2]
            temp_path = "paddle_tmp.png"
            Image.fromarray(crop_bgr).save(temp_path)

            with st.spinner("🔎 Menjalankan PaddleOCR..."):
                ocr_raw = ocr.ocr(crop_bgr)

            if ocr_raw and len(ocr_raw[0]) > 0:
                text_out = "\n".join([line[1][0] for line in ocr_raw[0]])
            else:
                text_out = "❌ OCR tidak menemukan teks."

            st.session_state["crop_image"] = Image.open(temp_path)
            st.session_state["ocr_raw"] = text_out
            cleaned_for_extraction = auto_tidy_for_extraction(text_out)
            st.session_state["nutrisi"] = ekstrak_nutrisi(cleaned_for_extraction)

            st.image(temp_path, caption="📋 Tabel Nutrisi Ter-crop", width=350)
            st.code(text_out)
            os.remove(temp_path)
        else:
            st.warning("❌ Tabel tidak ditemukan.")
                
if "crop_image" in st.session_state and "ocr_raw" in st.session_state:
    st.subheader("📋 Hasil Deteksi & OCR")
    st.image(st.session_state["crop_image"], caption="📋 Tabel Nutrisi Ter-crop", width=350)
    st.code(st.session_state["ocr_raw"])
    
if "nutrisi" in st.session_state:
    st.subheader("🧪 Koreksi & Evaluasi Nutrisi")

    kategori_pilihan = st.selectbox("📦 Pilih Kategori Produk", [
        "Minuman Siap Konsumsi", "Pasta & Mi Instan", "Susu Bubuk Plain", "Susu Bubuk Rasa",
        "Keju", "Yogurt Plain", "Yogurt Rasa", "Serbuk Minuman Sereal", "Oatmeal",
        "Sereal Siap Santap (Flake/Keping)", "Sereal Batang (Bar)", "Granola",
        "Biskuit Renyah", "Biskuit Marie, Kukis, dan Wafer", "Krekers",
        "Puding dan Nata/jeli Siap Santap", "Sambal", "Kecap Manis", "Makanan Ringan Siap Santap", "Olahan Kacang",
        "Bubuk Minuman Cokelat","Es Krim"
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
