import streamlit as st
import pandas as pd

# Konfigurasi Tampilan
st.set_page_config(page_title="Prakualifikasi Kontraktor CSMS", layout="wide")

st.title("📋 Form Prakualifikasi Kontraktor (CSMS)")
st.caption("Prakualifikasi Kontraktor / Contractor Safety Management System")

st.divider()

# Form Identitas Vendor
st.subheader("1. Identitas Perusahaan")
col1, col2 = st.columns(2)
with col1:
    nama_vendor = st.text_input("Nama Perusahaan / Supplier / Vendor")
    tgl_update = st.date_input("Tanggal Pengisian")
with col2:
    nama_pj = st.text_input("Penanggung Jawab K3 / HSE Leader")
    kontak_vendor = st.text_input("Nomor Telepon / Email Kontak")

st.divider()

# Form Pertanyaan CSMS
st.subheader("2. Pertanyaan Evaluasi CSMS")

# Struktur Pertanyaan berdasarkan FM 0127
questions = [
    {"id": "1a", "kategori": "Pernyataan Kebijakan", "text": "Apakah perusahaan mempunyai Kebijakan tertulis tentang K3 dan Lingkungan?"},
    {"id": "1b", "kategori": "Pernyataan Kebijakan", "text": "Apakah manajemen perusahaan bertanggung jawab atas kinerja K3 dan Lingkungan?"},
    {"id": "1c", "kategori": "Pernyataan Kebijakan", "text": "Apakah kebijakan K3 & Lingkungan dikomunikasikan dengan pekerja perusahaan?"},
    {"id": "2a", "kategori": "Organisasi K3", "text": "Apakah di dalam struktur organisasi, perusahaan mempunyai HSE Officer / HSE Leader?"},
    {"id": "2b", "kategori": "Organisasi K3", "text": "Apakah perusahaan telah mempunyai Job Description HSE Officer / HSE Leader?"},
]

responses = {}
uploads = {}

for q in questions:
    st.markdown(f"**[{q['id']}] {q['text']}**")
    col_ans, col_file = st.columns([1, 2])
    
    with col_ans:
        ans = st.radio(f"Jawaban ({q['id']})", ["Ya", "Tidak"], key=f"ans_{q['id']}", horizontal=True)
        responses[q['id']] = ans
        
    with col_file:
        if ans == "Ya":
            uploaded_file = st.file_uploader(f"Unggah Lampiran Bukti Dokumen ({q['id']})", type=["pdf", "png", "jpg", "doc", "docx"], key=f"file_{q['id']}")
            uploads[q['id']] = uploaded_file.name if uploaded_file else "Belum diunggah"
        else:
            uploads[q['id']] = "N/A"
    st.markdown("---")

# Tombol Submit Form
if st.button("Submit Aplikasi CSMS", type="primary"):
    if not nama_vendor:
        st.error("Harap isi Nama Perusahaan terlebih dahulu.")
    else:
        # Hitung Skor Sederhana
        total_ya = sum(1 for v in responses.values() if v == "Ya")
        total_q = len(questions)
        score_pct = (total_ya / total_q) * 100
        
        st.success(f"Form CSMS untuk **{nama_vendor}** berhasil dikirim!")
        st.metric(label="Skor Evaluasi Sementara", value=f"{score_pct:.1f}%")
        
        # Tampilkan Summary Data
        st.subheader("Ringkasan Pengajuan")
        summary_df = pd.DataFrame([
            {"No": q['id'], "Pertanyaan": q['text'], "Jawaban": responses[q['id']], "Lampiran": uploads[q['id']]}
            for q in questions
        ])
        st.dataframe(summary_df, use_container_width=True)
