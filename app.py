import streamlit as st
import pandas as pd
import json
import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import gspread

# Modul ReportLab untuk Generate PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ---------------------------------------------------------
# KONFIGURASI HALAMAN
# ---------------------------------------------------------
st.set_page_config(page_title="Prakualifikasi Kontraktor CSMS", layout="wide")
st.title("📋 Form Prakualifikasi Kontraktor (CSMS)")
st.caption("Contractor Safety Management System - FM/QHE/0127 rev. 1")
st.divider()

# ---------------------------------------------------------
# FUNGSI INTEGRASI GOOGLE DRIVE & SHEETS
# ---------------------------------------------------------
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

@st.cache_resource
def get_gservices():
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    gc = gspread.authorize(creds)
    return drive_service, gc

def create_subfolder(drive_service, parent_id, folder_name):
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    file = drive_service.files().create(
        body=file_metadata, 
        fields='id',
        supportsAllDrives=True
    ).execute()
    return file.get('id')

def upload_file_to_drive(drive_service, parent_id, file_name, file_bytes, mime_type):
    file_metadata = {
        'name': file_name,
        'parents': [parent_id]
    }
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
    uploaded = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink',
        supportsAllDrives=True
    ).execute()
    return uploaded.get('webViewLink')

# ---------------------------------------------------------
# FUNGSI GENERATE PDF CSMS
# ---------------------------------------------------------
def generate_csms_pdf(nama_vendor, tgl_update, nama_pj, kontak_vendor, score_pct, summary_list):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.HexColor('#1E3A8A')
    )
    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=1,
        textColor=colors.gray
    )
    bold_body = ParagraphStyle('BoldBody', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10)
    normal_body = ParagraphStyle('NormalBody', parent=styles['Normal'], fontSize=8, leading=10)
    
    elements = []
    
    # Header Dokumen
    elements.append(Paragraph("HASIL EVALUASI PRAKUALIFIKASI KONTRAKTOR (CSMS)", title_style))
    elements.append(Paragraph("Contractor Safety Management System - Form Ref: FM/QHE/0127 rev. 1", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=12))
    
    # Tabel Informasi Vendor
    info_data = [
        [Paragraph("<b>Nama Vendor/Supplier</b>", normal_body), Paragraph(f": {nama_vendor}", normal_body),
         Paragraph("<b>Tanggal Pengisian</b>", normal_body), Paragraph(f": {tgl_update}", normal_body)],
        [Paragraph("<b>Penanggung Jawab K3</b>", normal_body), Paragraph(f": {nama_pj}", normal_body),
         Paragraph("<b>Kontak/Email</b>", normal_body), Paragraph(f": {kontak_vendor}", normal_body)],
        [Paragraph("<b>Skor Kepatuhan CSMS</b>", normal_body), Paragraph(f": <b>{score_pct:.1f}%</b>", normal_body),
         Paragraph("<b>Status Pengajuan</b>", normal_body), Paragraph(": TERSIMPAN", normal_body)]
    ]
    
    t_info = Table(info_data, colWidths=[120, 150, 110, 140])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB'))
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 12))
    
    # Tabel Jawaban CSMS
    table_data = [
        [Paragraph("<b>No</b>", bold_body), Paragraph("<b>Pertanyaan Evaluasi CSMS</b>", bold_body), Paragraph("<b>Jawaban</b>", bold_body), Paragraph("<b>Status Lampiran</b>", bold_body)]
    ]
    
    for item in summary_list:
        status_lampiran = "Ada Dokumen" if item["Lampiran"] != "N/A" and item["Lampiran"] != "-" else item["Lampiran"]
        table_data.append([
            Paragraph(item["No"], normal_body),
            Paragraph(f"<b>[{item['Kategori']}]</b><br/>{item['Pertanyaan']}", normal_body),
            Paragraph(item["Jawaban"], normal_body),
            Paragraph(status_lampiran, normal_body)
        ])
        
    t_questions = Table(table_data, colWidths=[30, 320, 60, 110])
    t_questions.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#9CA3AF')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9FAFB')])
    ]))
    
    elements.append(t_questions)
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# ---------------------------------------------------------
# INPUT IDENTITAS VENDOR
# ---------------------------------------------------------
st.subheader("1. Identitas Perusahaan")
col1, col2 = st.columns(2)
with col1:
    nama_vendor = st.text_input("Nama Perusahaan / Supplier / Vendor")
    tgl_update = st.date_input("Tanggal Pengisian", datetime.date.today())
with col2:
    nama_pj = st.text_input("Penanggung Jawab K3 / HSE Leader")
    kontak_vendor = st.text_input("Nomor Telepon / Email Kontak")

st.divider()

# ---------------------------------------------------------
# MASTER DATA SOAL CSMS (14 KATEGORI)
# ---------------------------------------------------------
st.subheader("2. Pertanyaan Evaluasi CSMS")

sections = [
    {"kat_id": "1", "kategori": "PERNYATAAN KEBIJAKAN", "questions": [
        {"id": "1a", "text": "Apakah perusahaan mempunyai Kebijakan tertulis tentang K3 dan Lingkungan ?", "has_file": True, "file_label": "Lampirkan copy Kebijakan K3 & Lingkungan"},
        {"id": "1b", "text": "Apakah manajemen perusahaan bertanggung jawab atas kinerja K3 dan Lingkungan ?", "has_file": False},
        {"id": "1c", "text": "Apakah kebijakan K3 & Lingkungan itu dikomunikasikan dengan pekerja perusahaan ?", "has_file": False}
    ]},
    {"kat_id": "2", "kategori": "ORGANISASI KESELAMATAN KERJA", "questions": [
        {"id": "2a", "text": "Apakah didalam struktur organisasi, perusahaan mempunyai HSE Officer dan/atau HSE Leader ?", "has_file": False},
        {"id": "2b", "text": "Apakah perusahaan telah mempunyai job description HSE Officer dan/atau HSE Leader ?", "has_file": True, "file_label": "Lampirkan copy job description HSE Officer/Leader"},
        {"id": "2c", "text": "Apakah HSE Officer dan/atau HSE Leader telah mempunyai program kerja ?", "has_file": True, "file_label": "Bila Ya, lampirkan copy program kerja HSE Officer/Leader"}
    ]},
    {"kat_id": "3", "kategori": "PERATURAN DASAR KESELAMATAN KERJA", "questions": [
        {"id": "3a", "text": "Apakah perusahaan telah mempunyai Pedoman / Peraturan Dasar Keselamatan Kerja tertulis ?", "has_file": True, "file_label": "Lampirkan copy Pedoman / Peraturan Dasar K3"},
        {"id": "3b", "text": "Apakah Peraturan Dasar K3 dijadikan pedoman dan disosialisasikan kepada pekerja ?", "has_file": False}
    ]},
    {"kat_id": "4", "kategori": "PROGRAM PELATIHAN KESELAMATAN KERJA", "questions": [
        {"id": "4a", "text": "Adakah perusahaan memberikan pelatihan K3 kepada personil perusahaan ?", "has_file": True, "file_label": "Berikan data pelatihan (daftar hadir / sertifikat)"},
        {"id": "4b", "text": "Apakah personil pada pekerjaan khusus telah mempunyai sertifikat resmi ?", "has_file": True, "file_label": "Lampirkan copy sertifikat resmi"},
        {"id": "4c", "text": "Apakah pelatihan pekerja telah dijadwalkan termasuk pelatihan penyegaran ?", "has_file": False}
    ]},
    {"kat_id": "5", "kategori": "ALAT PELINDUNG DIRI", "questions": [
        {"id": "5a", "text": "Apakah pekerja perusahaan diberi Alat Pelindung Diri (PPE) yang tepat ?", "has_file": True, "file_label": "Berikan daftar Matriks APD"},
        {"id": "5b", "text": "Apakah perusahaan melakukan pengawasan memastikan APD (PPE) dipakai dan dipelihara ?", "has_file": False},
        {"id": "5c", "text": "Apakah perusahaan memberikan pelatihan penggunaan APD (PPE) ?", "has_file": False}
    ]},
    {"kat_id": "6", "kategori": "PROGRAM ORIENTASI PEKERJA", "questions": [
        {"id": "6a", "text": "Apakah ada orientasi kerja bagi pekerja baru ?", "has_file": False},
        {"id": "6b", "text": "Apakah program orientasi tersebut dilakukan bimbingan dengan instruksi tertulis ?", "has_file": False},
        {"id": "6c", "text": "Apakah orientasi terencana dan dilakukan observasi dan evaluasi ?", "has_file": True, "file_label": "Lampirkan program orientasi pekerja"}
    ]},
    {"kat_id": "7", "kategori": "PROGRAM HSE MEETING", "questions": [
        {"id": "7a", "text": "Apakah perusahaan menyelenggarakan sendiri HSE Meeting berkala ?", "has_file": False},
        {"id": "7b", "text": "Apakah topik setiap HSE Meeting dibicarakan bergiliran ?", "has_file": False},
        {"id": "7c", "text": "Apakah HSE Meeting dihadiri oleh pimpinan Kontraktor ?", "has_file": False}
    ]},
    {"kat_id": "8", "kategori": "PROGRAM INSPEKSI K3LH", "questions": [
        {"id": "8a", "text": "Apakah perusahaan telah mempunyai program inspeksi K3LH tertulis ?", "has_file": False},
        {"id": "8b", "text": "Apakah hasil inspeksi K3LH ditindak lanjuti dengan perbaikan-perbaikan ?", "has_file": False},
        {"id": "8c", "text": "Apakah rekomendasi temuan dan tindakan perbaikannya ?", "has_file": True, "file_label": "Lampirkan program inspeksi K3LH"}
    ]},
    {"kat_id": "9", "kategori": "MANAJEMEN PERALATAN DAN MATERIAL", "questions": [
        {"id": "9a", "text": "Apakah perusahaan mempunyai program pemeriksaan peralatan dan material ?", "has_file": False},
        {"id": "9b", "text": "Apakah semua hasil pemeriksaan dan tindak lanjut didokumentasikan ?", "has_file": False}
    ]},
    {"kat_id": "10", "kategori": "PROSEDUR PELAPORAN KECELAKAAN", "questions": [
        {"id": "10a", "text": "Apakah perusahaan mempunyai prosedur pelaporan dan penyelidikan kecelakaan ?", "has_file": True, "file_label": "Lampirkan copy prosedur pelaporan dan alur komunikasi"}
    ]},
    {"kat_id": "11", "kategori": "PROSEDUR KERJA DAN TANGGAP DARURAT", "questions": [
        {"id": "11a", "text": "Apakah prosedur kerja tertulis dan Tanggap Darurat telah ditetapkan ?", "has_file": True, "file_label": "Lampirkan copy Prosedur Kerja & Tanggap Darurat"},
        {"id": "11b", "text": "Apakah ada prosedur yang mewajibkan penyediaan obat-obatan P3K ?", "has_file": False},
        {"id": "11c", "text": "Apakah sudah ada pelatihan atau simulasi Tanggap Darurat ?", "has_file": True, "file_label": "Lampirkan bukti simulasi Tanggap Darurat"}
    ]},
    {"kat_id": "12", "kategori": "KESEHATAN KERJA", "questions": [
        {"id": "12a", "text": "Apakah perusahaan mempunyai peraturan tentang kebersihan tempat kerja ?", "has_file": False},
        {"id": "12b", "text": "Apakah peraturan tersebut disosialisasikan kepada pekerja ?", "has_file": True, "file_label": "Lampirkan bukti sosialisasi kebersihan tempat kerja"}
    ]},
    {"kat_id": "13", "kategori": "PENGELOLAAN LINGKUNGAN", "questions": [
        {"id": "13a", "text": "Apakah perusahaan telah mempunyai prosedur pembuangan sampah & limbah ?", "has_file": False},
        {"id": "13b", "text": "Apakah dilakukan pengawasan penampungan oli bekas / bahan kimia ?", "has_file": False},
        {"id": "13c", "text": "Apakah bekerjasama dengan pihak ke-3 berizin untuk pengangkutan limbah B3 ?", "has_file": False}
    ]},
    {"kat_id": "14", "kategori": "DATA DAN STATISTIK", "questions": [
        {"id": "14a", "text": "Apakah perusahaan mencatat data kecelakaan kerja (Fatal, LTI, MTI, Nearmiss, dll) ?", "has_file": False},
        {"id": "14b", "text": "Apakah data kecelakaan kerja telah dijadikan statistik acuan pencegahan ?", "has_file": False},
        {"id": "14c", "text": "Statistik Kecelakaan Kerja", "has_file": True, "file_label": "Lampirkan statistik kecelakaan periode 1 tahun terakhir"}
    ]}
]

responses = {}
file_objects = {}
total_questions = 0

for section in sections:
    st.markdown(f"#### {section['kat_id']}. {section['kategori']}")
    for q in section['questions']:
        total_questions += 1
        st.markdown(f"**[{q['id']}] {q['text']}**")
        col_ans, col_file = st.columns([1, 2])
        
        with col_ans:
            ans = st.radio(f"Jawaban ({q['id']})", ["Ya", "Tidak"], key=f"ans_{q['id']}", horizontal=True)
            responses[q['id']] = ans
            
        with col_file:
            if q.get('has_file'):
                if ans == "Ya":
                    up_file = st.file_uploader(f"📎 {q.get('file_label')}", key=f"file_{q['id']}")
                    file_objects[q['id']] = up_file
                else:
                    file_objects[q['id']] = None
            else:
                file_objects[q['id']] = None
    st.markdown("---")

# ---------------------------------------------------------
# PROSES SUBMIT FORM
# ---------------------------------------------------------
if st.button("Submit Aplikasi CSMS", type="primary", use_container_width=True):
    if not nama_vendor:
        st.error("⚠️ Harap isi Nama Perusahaan terlebih dahulu!")
    else:
        with st.spinner("Mengunggah dokumen, menghasilkan PDF ringkasan, dan menyimpan data..."):
            try:
                drive_service, gc = get_gservices()
                upload_parent_id = st.secrets["google_drive"]["folder_upload_id"]
                spreadsheet_id = st.secrets["google_drive"]["spreadsheet_id"]

                # 1. Buat Subfolder Khusus Vendor di Drive
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                clean_vendor_name = "".join(c for c in nama_vendor if c.isalnum() or c in (' ', '_', '-')).rstrip()
                vendor_folder_name = f"{clean_vendor_name}_{timestamp}"
                vendor_folder_id = create_subfolder(drive_service, upload_parent_id, vendor_folder_name)

                # 2. Upload Lampiran Vendor
                attachment_links = {}
                summary_list = []
                
                for section in sections:
                    for q in section['questions']:
                        q_id = q['id']
                        f_obj = file_objects.get(q_id)
                        
                        if f_obj is not None:
                            file_ext = f_obj.name.split('.')[-1]
                            dest_filename = f"{q_id}_{clean_vendor_name}.{file_ext}"
                            link = upload_file_to_drive(
                                drive_service,
                                vendor_folder_id,
                                dest_filename,
                                f_obj.getvalue(),
                                f_obj.type
                            )
                            attachment_links[q_id] = link
                        else:
                            attachment_links[q_id] = "N/A"
                            
                        summary_list.append({
                            "Kategori": section['kategori'],
                            "No": q_id,
                            "Pertanyaan": q['text'],
                            "Jawaban": responses[q_id],
                            "Lampiran": attachment_links[q_id]
                        })

                # 3. Hitung Skor CSMS
                total_ya = sum(1 for v in responses.values() if v == "Ya")
                score_pct = (total_ya / total_questions) * 100

                # 4. Generate & Upload PDF Ringkasan
                pdf_bytes = generate_csms_pdf(
                    nama_vendor, str(tgl_update), nama_pj, kontak_vendor, score_pct, summary_list
                )
                
                pdf_filename = f"CSMS_Summary_{clean_vendor_name}.pdf"
                pdf_drive_link = upload_file_to_drive(
                    drive_service,
                    vendor_folder_id,
                    pdf_filename,
                    pdf_bytes,
                    "application/pdf"
                )

                # 5. Simpan Rekapitulasi ke Google Sheets
                sh = gc.open_by_key(spreadsheet_id)
                worksheet = sh.sheet1
                
                if len(worksheet.get_all_values()) == 0:
                    headers = ["Timestamp", "Nama Vendor", "Tgl Pengisian", "Penanggung Jawab", "Kontak", "Skor (%)", "Link PDF Ringkasan"]
                    for sec in sections:
                        for q in sec['questions']:
                            headers.append(f"[{q['id']}] Jawaban")
                            if q.get('has_file'):
                                headers.append(f"[{q['id']}] Link Lampiran")
                    worksheet.append_row(headers)

                row_data = [
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    nama_vendor,
                    str(tgl_update),
                    nama_pj,
                    kontak_vendor,
                    f"{score_pct:.1f}%",
                    pdf_drive_link
                ]
                
                for sec in sections:
                    for q in sec['questions']:
                        q_id = q['id']
                        row_data.append(responses[q_id])
                        if q.get('has_file'):
                            row_data.append(attachment_links[q_id])

                worksheet.append_row(row_data)

                # 6. Tampilkan Konfirmasi & Tombol Unduh PDF
                st.success(f"✅ Formulir CSMS **{nama_vendor}** berhasil dikirim & disimpan!")
                st.balloons()
                
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric(label="Skor Kepatuhan CSMS", value=f"{score_pct:.1f}%")
                with col_m2:
                    st.download_button(
                        label="📄 Unduh Ringkasan PDF CSMS",
                        data=pdf_bytes,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        type="primary"
                    )

            except Exception as e:
                st.error(f"Terjadi kesalahan saat menyimpan data: {e}")
