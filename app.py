import streamlit as st
import pandas as pd

# Konfigurasi Tampilan
st.set_page_config(page_title="Prakualifikasi Kontraktor CSMS", layout="wide")

st.title("📋 Form Prakualifikasi Kontraktor (CSMS)")
st.caption("Contractor Safety Management System - FM/QHE/0127 rev. 1")

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

# Master Data Pertanyaan Lengkap (Kategori 1 s/d 14)
sections = [
    {
        "kat_id": "1",
        "kategori": "PERNYATAAN KEBIJAKAN",
        "questions": [
            {"id": "1a", "text": "Apakah perusahaan mempunyai Kebijakan tertulis tentang K3 dan Lingkungan ?", "has_file": True, "file_label": "Lampirkan copy Kebijakan K3 & Lingkungan"},
            {"id": "1b", "text": "Apakah manajemen perusahaan bertanggung jawab atas kinerja K3 dan Lingkungan ?", "has_file": False},
            {"id": "1c", "text": "Apakah kebijakan K3 & Lingkungan itu dikomunikasikan dengan pekerja perusahaan ?", "has_file": False}
        ]
    },
    {
        "kat_id": "2",
        "kategori": "ORGANISASI KESELAMATAN KERJA",
        "questions": [
            {"id": "2a", "text": "Apakah didalam struktur organisasi, perusahaan mempunyai HSE Officer dan/atau HSE Leader ?", "has_file": False},
            {"id": "2b", "text": "Apakah perusahaan telah mempunyai job description HSE Officer dan/atau HSE Leader ?", "has_file": True, "file_label": "Lampirkan copy job description (tugas dan tanggung jawab) HSE Officer/Leader"},
            {"id": "2c", "text": "Apakah HSE Officer dan/atau HSE Leader telah mempunyai program kerja ?", "has_file": True, "file_label": "Bila Ya, lampirkan copy program kerja HSE Officer/Leader"}
        ]
    },
    {
        "kat_id": "3",
        "kategori": "PERATURAN DASAR KESELAMATAN KERJA",
        "questions": [
            {"id": "3a", "text": "Apakah perusahaan telah mempunyai Pedoman / Peraturan Dasar Keselamatan Kerja tertulis antara lain memberikan pedoman tentang tangga, perancah (scafolding), angkutan, alat berat, bahan kimia atau pekerjaan berbahaya lainnya ?", "has_file": True, "file_label": "Lampirkan copy Pedoman / Peraturan Dasar K3"},
            {"id": "3b", "text": "Apakah Peraturan Dasar K3 dijadikan pedoman dan disosialisasikan kepada pekerja ?", "has_file": False}
        ]
    },
    {
        "kat_id": "4",
        "kategori": "PROGRAM PELATIHAN KESELAMATAN KERJA",
        "questions": [
            {"id": "4a", "text": "Adakah perusahaan memberikan pelatihan K3 kepada personil perusahaan ?", "has_file": True, "file_label": "Berikan data-datanya bila pernah mendapat pelatihan (daftar hadir / sertifikat pelatihan)"},
            {"id": "4b", "text": "Apakah personil pada pekerjaan khusus (welder pada pipa bertekanan tinggi, operator crane, forklift, pemanjat tower dsb) telah mempunyai sertifikat resmi ?", "has_file": True, "file_label": "Lampirkan copy sertifikat resmi"},
            {"id": "4c", "text": "Apakah pelatihan pekerja telah dijadwalkan termasuk pelatihan penyegaran ?", "has_file": False}
        ]
    },
    {
        "kat_id": "5",
        "kategori": "ALAT PELINDUNG DIRI",
        "questions": [
            {"id": "5a", "text": "Apakah pekerja perusahaan diberi Alat Pelindung Diri (PPE) yang tepat ?", "has_file": True, "file_label": "Berikan daftar Alat Pelindung Diri (PPE) pekerja untuk lingkup pekerjaan ini (Matriks APD)"},
            {"id": "5b", "text": "Apakah perusahaan melakukan pengawasan memastikan APD (PPE) dipakai dan dipelihara ?", "has_file": False},
            {"id": "5c", "text": "Apakah perusahaan memberikan pelatihan penggunaan APD (PPE) bagi pekerja perusahaan ?", "has_file": False}
        ]
    },
    {
        "kat_id": "6",
        "kategori": "PROGRAM ORIENTASI PEKERJA",
        "questions": [
            {"id": "6a", "text": "Apakah ada orientasi kerja bagi pekerja baru atau pekerja yang baru dialih tugaskan atau yang memangku jabatan baru ?", "has_file": False},
            {"id": "6b", "text": "Apakah program orientasi tersebut dilakukan bimbingan dengan instruksi tertulis ?", "has_file": False},
            {"id": "6c", "text": "Apakah orientasi terencana dan dilakukan observasi dan evaluasi ?", "has_file": True, "file_label": "Lampirkan program orientasi pekerja perusahaan bila ada"}
        ]
    },
    {
        "kat_id": "7",
        "kategori": "PROGRAM HSE MEETING",
        "questions": [
            {"id": "7a", "text": "Apakah perusahaan menyelenggarakan sendiri HSE Meeting berkala ?", "has_file": False},
            {"id": "7b", "text": "Apakah topik setiap HSE Meeting dibicarakan bergiliran ?", "has_file": False},
            {"id": "7c", "text": "Apakah HSE Meeting dihadiri oleh pimpinan Kontraktor ?", "has_file": False}
        ]
    },
    {
        "kat_id": "8",
        "kategori": "PROGRAM INSPEKSI KESELAMATAN, KESEHATAN KERJA, DAN LINGKUNGAN",
        "questions": [
            {"id": "8a", "text": "Apakah perusahaan telah mempunyai program inspeksi K3LH tertulis dan melakukan pemeriksaan K3LH ?", "has_file": False},
            {"id": "8b", "text": "Apakah hasil inspeksi K3LH ditindak lanjuti dengan perbaikan-perbaikan ?", "has_file": False},
            {"id": "8c", "text": "Apakah rekomendasi temuan dan tindakan perbaikannya ?", "has_file": True, "file_label": "Lampirkan program inspeksi K3LH (bila ada)"}
        ]
    },
    {
        "kat_id": "9",
        "kategori": "MANAJEMEN PERALATAN DAN MATERIAL",
        "questions": [
            {"id": "9a", "text": "Apakah perusahaan mempunyai program pemeriksaan peralatan dan material yang digunakan perusahaan seperti mesin las, mobil angkutan pekerja dan barang, alat pemadam api, forklift, dsb ?", "has_file": False},
            {"id": "9b", "text": "Apakah semua hasil pemeriksaan dan tindak lanjut didokumentasikan ?", "has_file": False}
        ]
    },
    {
        "kat_id": "10",
        "kategori": "PROSEDUR PELAPORAN & PENYELIDIKAN KECELAKAAN",
        "questions": [
            {"id": "10a", "text": "Apakah perusahaan mempunyai prosedur pelaporan dan penyelidikan kecelakaan antara lain tentang alur pelaporan sampai investigasi kejadian dan komunikasi pelaporan kecelakaan ?", "has_file": True, "file_label": "Lampirkan copy prosedur pelaporan dan alur komunikasinya"}
        ]
    },
    {
        "kat_id": "11",
        "kategori": "PROSEDUR KERJA DAN TANGGAP DARURAT",
        "questions": [
            {"id": "11a", "text": "Apakah prosedur kerja tertulis dari pekerjaan-pekerjaan tertentu dan Tanggap Darurat telah ditetapkan ?", "has_file": True, "file_label": "Kalau 'YA', sebutkan dan lampirkan copynya"},
            {"id": "11b", "text": "Apakah ada prosedur yang mewajibkan perusahaan menyediakan obat-obatan P3K ditempat kerja ? Apakah semua prosedur telah dibakukan / disetujui pimpinan tertinggi perusahaan ?", "has_file": False},
            {"id": "11c", "text": "Apakah sudah ada pelatihan atau simulasi Tanggap Darurat dipatuhi ?", "has_file": True, "file_label": "Lampirkan bukti pelatihan/simulasi Tanggap Darurat"}
        ]
    },
    {
        "kat_id": "12",
        "kategori": "KESEHATAN KERJA",
        "questions": [
            {"id": "12a", "text": "Apakah perusahaan mempunyai peraturan tentang pemeliharaan kebersihan tempat kerja ?", "has_file": False},
            {"id": "12b", "text": "Apakah peraturan tersebut disosialisasikan kepada pekerja ?", "has_file": True, "file_label": "Bila YA, bagaimana peraturan tersebut disosialisasikan kepada pekerja? (Lampirkan bukti)"}
        ]
    },
    {
        "kat_id": "13",
        "kategori": "PENGELOLAAN LINGKUNGAN",
        "questions": [
            {"id": "13a", "text": "Apakah perusahaan telah mempunyai prosedur pembuangan sampah dan pengendalian bahan kimia berbahaya ?", "has_file": False},
            {"id": "13b", "text": "Apakah dilakukan pengawasan memastikan prosedur pembuangan sampah dipatuhi, oli bekas dan bahan kimia berbahaya ditampung secara khusus serta tidak membakar sampah sembarangan ?", "has_file": False},
            {"id": "13c", "text": "Apakah perusahaan sudah bekerjasama dengan pihak ke 3 yang berizin untuk mengangkut dan mengelola limbah B3 yang dihasilkan perusahaan ?", "has_file": False}
        ]
    },
    {
        "kat_id": "14",
        "kategori": "DATA DAN STATISTIK",
        "questions": [
            {"id": "14a", "text": "Apakah perusahaan mencatat data kecelakaan kerja perusahaan (Fatal, LTI, MTI, Nearmiss, dll) ?", "has_file": False},
            {"id": "14b", "text": "Apakah data kecelakaan kerja telah dijadikan statistik sebagai acuan untuk pencegahan kecelakaan ?", "has_file": False},
            {"id": "14c", "text": "Statistik Kecelakaan Kerja", "has_file": True, "file_label": "Lampirkan statistik kecelakaan perusahaan selama periode 1 tahun terakhir"}
        ]
    }
]

responses = {}
uploads = {}
total_questions_count = 0

# Loop untuk menampilkan seluruh kategori & pertanyaan
for section in sections:
    st.markdown(f"#### {section['kat_id']}. {section['kategori']}")
    
    for q in section['questions']:
        total_questions_count += 1
        st.markdown(f"**[{q['id']}] {q['text']}**")
        
        col_ans, col_file = st.columns([1, 2])
        
        with col_ans:
            ans = st.radio(
                f"Jawaban ({q['id']})", 
                ["Ya", "Tidak"], 
                key=f"ans_{q['id']}", 
                horizontal=True
            )
            responses[q['id']] = ans
            
        with col_file:
            if q.get('has_file'):
                label = q.get('file_label', 'Lampirkan Bukti Dokumen')
                if ans == "Ya":
                    uploaded_file = st.file_uploader(
                        f"📎 {label}", 
                        type=["pdf", "png", "jpg", "doc", "docx", "xls", "xlsx"], 
                        key=f"file_{q['id']}"
                    )
                    uploads[q['id']] = uploaded_file.name if uploaded_file else "Belum diunggah"
                else:
                    uploads[q['id']] = "N/A (Jawaban Tidak)"
            else:
                uploads[q['id']] = "-"
                
        st.caption("")
    st.markdown("---")

# Tombol Kirim Form
if st.button("Submit Aplikasi CSMS", type="primary", use_container_width=True):
    if not nama_vendor:
        st.error("⚠️ Harap isi Nama Perusahaan / Supplier / Vendor terlebih dahulu!")
    else:
        # Kalkulasi Skor Sederhana
        total_ya = sum(1 for v in responses.values() if v == "Ya")
        score_pct = (total_ya / total_questions_count) * 100
        
        st.success(f"Form CSMS untuk **{nama_vendor}** berhasil dikirim!")
        st.metric(label="Skor Kepatuhan Sementara", value=f"{score_pct:.1f}%", delta=f"{total_ya} dari {total_questions_count} Ya")
        
        # Tampilkan Ringkasan Hasil
        st.subheader("Ringkasan Pengajuan Vendor")
        
        summary_list = []
        for section in sections:
            for q in section['questions']:
                summary_list.append({
                    "Kategori": section['kategori'],
                    "No": q['id'],
                    "Pertanyaan": q['text'],
                    "Jawaban": responses[q['id']],
                    "Lampiran": uploads[q['id']]
                })
                
        summary_df = pd.DataFrame(summary_list)
        st.dataframe(summary_df, use_container_width=True)
