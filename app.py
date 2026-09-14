import streamlit as st
import pandas as pd
import datetime
import io
import requests
import random
import string
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials

# Modul ReportLab untuk Generate PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ---------------------------------------------------------
# KONFIGURASI HALAMAN & INJEKSI CSS (HILANGKAN SIDEBAR & 200MB)
# ---------------------------------------------------------
st.set_page_config(page_title="Prakualifikasi Kontraktor CSMS", layout="wide", initial_sidebar_state="collapsed")

custom_css = """
<style>
    /* 1. Sembunyikan Sidebar Panel Admin secara Total */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        display: none !important;
        width: 0px !important;
    }
    
    /* 2. Sembunyikan Teks Keterangan Size Default Streamlit (200MB per file) */
    [data-testid="stFileUploaderDropzoneInstructions"] > div:nth-child(2),
    [data-testid="stFileUploaderDropzoneInstructions"] small,
    [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stFileUploader"] small,
    div[data-testid="stFileUploaderFileData"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        font-size: 0px !important;
        height: 0px !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

query_params = st.query_params
url_token = query_params.get("token", "").strip().upper()

st.title("📋 Form Prakualifikasi Kontraktor (CSMS)")
st.caption("Contractor Safety Management System - FM/QHE/0127 rev. 2")
st.divider()

# ---------------------------------------------------------
# FUNGSI INTEGRASI TELEGRAM BOT API
# ---------------------------------------------------------
def send_telegram_message(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.json()
    except Exception:
        return None

def send_telegram_document(bot_token, chat_id, file_bytes, filename, caption=""):
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    files = {"document": (filename, file_bytes)}
    data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data, files=files, timeout=30)
        return response.json()
    except Exception:
        return None

# ---------------------------------------------------------
# FUNGSI INTEGRASI GOOGLE SHEETS & VERIFIKASI TOKEN
# ---------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

@st.cache_resource
def get_gsheets():
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc

def verify_token_credentials(input_token):
    try:
        gc = get_gsheets()
        spreadsheet_id = st.secrets["google_drive"]["spreadsheet_id"]
        sh = gc.open_by_key(spreadsheet_id)
        
        try:
            t_sheet = sh.worksheet("Token_Akses")
            records = t_sheet.get_all_records()
        except Exception:
            records = []
        
        matched = None
        matched_row_idx = None
        for idx, row in enumerate(records, start=2):
            if str(row.get("Token")).strip().upper() == input_token:
                matched = row
                matched_row_idx = idx
                break
        
        if not matched:
            return False, "⛔ Kode Token tidak terdaftar atau Salah!", None, None
        
        status = matched.get("Status")
        exp_date_str = str(matched.get("Expired Date"))
        vendor_name_assigned = matched.get("Nama Vendor")
        
        today = datetime.date.today()
        exp_date = datetime.datetime.strptime(exp_date_str, "%Y-%m-%d").date() if exp_date_str else today
        
        if status != "Aktif":
            return False, "⛔ Kode Token ini sudah pernah digunakan (Hangus)!", None, None
        elif today > exp_date:
            return False, f"⛔ Kode Token ini sudah Kadaluarsa (Expired pada {exp_date_str})!", None, None
        else:
            return True, "Valid", matched_row_idx, vendor_name_assigned
    except Exception as e:
        return False, f"Gagal memverifikasi token: {e}", None, None

# ---------------------------------------------------------
# FUNGSI GENERATE PDF CSMS
# ---------------------------------------------------------
def generate_csms_pdf(nama_vendor, tgl_update, nama_pj, kontak_vendor, score_pct, total_poin, summary_list):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, leading=18, alignment=1, textColor=colors.HexColor('#1E3A8A'))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=9, leading=11, alignment=1, textColor=colors.gray)
    bold_body = ParagraphStyle('BoldBody', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10)
    normal_body = ParagraphStyle('NormalBody', parent=styles['Normal'], fontSize=8, leading=10)
    center_body = ParagraphStyle('CenterBody', parent=styles['Normal'], fontSize=8, leading=10, alignment=1)
    
    if score_pct >= 70.0:
        kesimpulan_text = "<font color='#166534'><b>Dapat diterima (Lulus CSMS)</b></font>"
    else:
        kesimpulan_text = "<font color='#DC2626'><b>Tidak dapat diterima (Tidak Lulus)</b></font>"

    elements = [
        Paragraph("HASIL EVALUASI PRAKUALIFIKASI KONTRAKTOR (CSMS)", title_style),
        Paragraph("Contractor Safety Management System - Form Ref: FM/QHE/0127 rev. 2", subtitle_style),
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=12)
    ]
    
    info_data = [
        [Paragraph("<b>Nama Vendor/Supplier</b>", normal_body), Paragraph(f": {nama_vendor}", normal_body),
         Paragraph("<b>Tanggal Pengisian</b>", normal_body), Paragraph(f": {tgl_update}", normal_body)],
        [Paragraph("<b>Penanggung Jawab K3</b>", normal_body), Paragraph(f": {nama_pj}", normal_body),
         Paragraph("<b>Kontak/Email</b>", normal_body), Paragraph(f": {kontak_vendor}", normal_body)],
        [Paragraph("<b>Total Poin Evaluasi</b>", normal_body), Paragraph(f": <b>{total_poin} / 50 Poin</b>", normal_body),
         Paragraph("<b>Skor Kepatuhan CSMS</b>", normal_body), Paragraph(f": <b>{score_pct:.1f}%</b>", normal_body)],
        [Paragraph("<b>Kesimpulan Hasil Evaluasi</b>", normal_body), Paragraph(f": {kesimpulan_text}", normal_body),
         Paragraph("", normal_body), Paragraph("", normal_body)]
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
    
    table_data = [[
        Paragraph("<b>No</b>", ParagraphStyle('HCenter', parent=bold_body, alignment=1)),
        Paragraph("<b>Pertanyaan Evaluasi CSMS</b>", bold_body),
        Paragraph("<b>Jawaban</b>", ParagraphStyle('HCenter2', parent=bold_body, alignment=1)),
        Paragraph("<b>Keterangan Lampiran</b>", bold_body)
    ]]
    
    for item in summary_list:
        table_data.append([
            Paragraph(str(item["No"]), center_body),
            Paragraph(f"<b>[{item['Kategori']}]</b><br/>{item['Pertanyaan']}", normal_body),
            Paragraph(item["Jawaban"], center_body),
            Paragraph(item["Lampiran"], normal_body)
        ])
        
    t_questions = Table(table_data, colWidths=[30, 320, 50, 120])
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
# MASTER DATA SOAL CSMS (REVISI 2 SEESUAI REVISI TERBARU)
# ---------------------------------------------------------
sections = [
    {
        "kat_id": "1",
        "kategori": "PERNYATAAN KEBIJAKAN",
        "questions": [
            {"id": "1a", "text": "Apakah perusahaan mempunyai Kebijakan tertulis tentang K3 dan Lingkungan ?", "has_file": True, "file_label": "Lampirkan copy Kebijakan K3 & Lingkungan"},
            {"id": "1b", "text": "Apakah manajemen perusahaan bertanggung jawab atas kinerja K3 dan Lingkungan ?", "has_file": False},
            {"id": "1c", "text": "Apakah kebijakan K3 & Lingkungan itu dikomunikasikan kepada pekerja di perusahaan ?", "has_file": False}
        ]
    },
    {
        "kat_id": "2",
        "kategori": "ORGANISASI KESELAMATAN KERJA",
        "questions": [
            {"id": "2a", "text": "Apakah di dalam struktur organisasi, perusahaan mempunyai HSE atau Petugas K3L ?", "has_file": False},
            {"id": "2b", "text": "Apakah perusahaan telah mempunyai job description HSE atau Petugas K3L ?", "has_file": True, "file_label": "Lampirkan copy job description dari HSE / Petugas K3L"},
            {"id": "2c", "text": "Apakah HSE atau Petugas K3L telah mempunyai program kerja ?", "has_file": True, "file_label": "Bila Ya, lampirkan copy program kerja HSE / Petugas K3L"}
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
            {"id": "4a", "text": "Adakah perusahaan memberikan pelatihan K3 kepada personil perusahaan ?", "has_file": True, "file_label": "Berikan data pelatihan (daftar hadir / sertifikat pelatihan)"},
            {"id": "4b", "text": "Apakah personil pada pekerjaan khusus (welder pada pipa bertekanan tinggi, operator crane, forklift, pemanjat tower dsb) telah menerima pelatihan dari PJK3 dan mempunyai sertifikat resmi ?", "has_file": True, "file_label": "Lampirkan copy sertifikat resmi"},
            {"id": "4c", "text": "Apakah pelatihan pekerja telah dijadwalkan termasuk pelatihan penyegaran ?", "has_file": False}
        ]
    },
    {
        "kat_id": "5",
        "kategori": "ALAT PELINDUNG DIRI",
        "questions": [
            {"id": "5a", "text": "Apakah pekerja perusahaan diberi Alat Pelindung Diri (PPE) yang tepat.", "has_file": True, "file_label": "Berikan daftar Matriks APD pekerja"},
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
            {"id": "6c", "text": "Apakah orientasi terencana dan dilakukan observasi dan evaluasi ?", "has_file": True, "file_label": "Lampirkan program orientasi pekerja perusahaan jika ada"}
        ]
    },
    {
        "kat_id": "7",
        "kategori": "PROGRAM HSE MEETING",
        "questions": [
            {"id": "7a", "text": "Apakah perusahaan menyelenggarakan sendiri HSE Meeting berkala?", "has_file": False},
            {"id": "7b", "text": "Apakah topik setiap HSE Meeting dibicarakan bergiliran ?", "has_file": False},
            {"id": "7c", "text": "Apakah HSE Meeting dihadiri oleh pimpinan Kontraktor ?", "has_file": False}
        ]
    },
    {
        "kat_id": "8",
        "kategori": "PROGRAM INSPEKSI KESELAMATAN, KESEHATAN KERJA, DAN LINGKUNGAN",
        "questions": [
            {"id": "8a", "text": "Apakah perusahaan telah mempunyai program inspeksi K3L tertulis dan melakukan pemeriksaan K3L ?", "has_file": False},
            {"id": "8b", "text": "Apakah hasil inspeksi K3L ditindak lanjuti dengan perbaikan-perbaikan ?", "has_file": False},
            {"id": "8c", "text": "Apakah rekomendasi temuan dan tindakan perbaikannya?", "has_file": True, "file_label": "Lampirkan program inspeksi K3L (bila ada)"}
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
            {"id": "10a", "text": "Apakah perusahaan mempunyai prosedur pelaporan dan penyelidikan kecelakaan antara lain tentang alur pelaporan sampai investigasi kerjadian dan komunikasi pelaporan kecelakaan ?", "has_file": True, "file_label": "Lampirkan copy prosedur pelaporan dan alur komunikasinya"}
        ]
    },
    {
        "kat_id": "11",
        "kategori": "PROSEDUR KERJA DAN TANGGAP DARURAT",
        "questions": [
            {"id": "11a", "text": "Apakah prosedur kerja tertulis dari pekerjaan-pekerjaan tertentu dan Tanggap Darurat telah ditetapkan ?", "has_file": True, "file_label": "Lampirkan copy Prosedur Kerja & Tanggap Darurat"},
            {"id": "11b", "text": "Apakah ada prosedur yang mewajibkan perusahaan menyediakan obat-obatan P3K ditempat kerja ?", "has_file": False},
            {"id": "11c", "text": "Apakah sudah ada pelatihan atau simulasi Tanggap Darurat ?", "has_file": True, "file_label": "Lampirkan bukti simulasi Tanggap Darurat"}
        ]
    },
    {
        "kat_id": "12",
        "kategori": "KESEHATAN KERJA",
        "questions": [
            {"id": "12a", "text": "Apakah perusahaan mempunyai peraturan tentang pemeliharaan kebersihan tempat kerja?", "has_file": False},
            {"id": "12b", "text": "Apakah peraturan tersebut disosialisasikan kepada pekerja ?", "has_file": True, "file_label": "Lampirkan bukti sosialisasi kebersihan tempat kerja"}
        ]
    },
    {
        "kat_id": "13",
        "kategori": "PENGELOLAAN LINGKUNGAN",
        "questions": [
            {"id": "13a", "text": "Apakah perusahaan telah mempunyai prosedur pembuangan sampah dan pengendalian bahan kimia berbahaya?", "has_file": False},
            {"id": "13b", "text": "Apakah dilakukan pengawasan memastikan prosedur pembuangan sampah dipatuhi, oli bekas dan bahan kimia berbahaya ditampung secara khusus serta tidak membakar sampah sembarangan ?", "has_file": False},
            {"id": "13c", "text": "Apakah perusahaan sudah berkerjasama dengan pihak ke 3 yang berizin untuk mengangkut dan mengelola limbah B3 yang dihasilkan perusahaan", "has_file": False}
        ]
    },
    {
        "kat_id": "14",
        "kategori": "DATA DAN STATISTIK",
        "questions": [
            {"id": "14a", "text": "Apakah perusahaan mencatat data kecelakaan kerja perusahaan seperti :\n- Fatal (Kematian)\n- LTI (Hilang Hari Kerja)\n- MTI (Berobat Jalan)\n- Nearmiss (Hampir Celaka)\n- dll ?", "has_file": False},
            {"id": "14b", "text": "Apakah data kecelakaan kerja telah dijadikan statistik sebagai acuan untuk pencegahan kecelakaan?", "has_file": False},
            {"id": "14c", "text": "Statistik Kecelakaan Kerja (1 Tahun Terakhir)", "has_file": True, "file_label": "Lampirkan statistik kecelakaan periode 1 tahun terakhir"}
        ]
    }
]

# ---------------------------------------------------------
# DETEKSI URL OTOMATIS APLIKASI
# ---------------------------------------------------------
def get_current_app_url():
    if hasattr(st, "context") and hasattr(st.context, "headers"):
        headers = st.context.headers
        host = headers.get("host", "")
        if host:
            return f"https://{host}"
    return "https://csms-contractor-app.streamlit.app"

# ---------------------------------------------------------
# AUTO-VERIFIKASI URL TOKEN JIKA DIKLIK VENDOR (AUTO-LOGIN)
# ---------------------------------------------------------
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated'] and url_token:
    is_valid, msg, row_idx, v_name = verify_token_credentials(url_token)
    if is_valid:
        st.session_state['authenticated'] = True
        st.session_state['active_token'] = url_token
        st.session_state['token_row_idx'] = row_idx
        st.session_state['assigned_vendor'] = v_name
        st.rerun()
    else:
        st.error(msg)

# ---------------------------------------------------------
# TAB REGISTRASI & VERIFIKASI MANUAL (JIKA TANPA TOKEN)
# ---------------------------------------------------------
if not st.session_state['authenticated']:
    st.subheader("🔑 Pendaftaran & Verifikasi Akses Vendor (CSMS)")
    
    tab_reg, tab_token = st.tabs(["📝 Registrasi Mandiri Vendor Baru", "🔑 Punya Kode Token / Link Unik"])
    
    with tab_reg:
        st.info("Bagi Vendor/Kontraktor baru, silakan daftarkan perusahaan Anda untuk mendapatkan Link Pengisian CSMS berdurasi 7 hari.")
        reg_vendor_name = st.text_input("Nama Perusahaan / Supplier / Vendor (Resmi)")
        reg_vendor_email = st.text_input("Email Resmi Perusahaan / PIC HSE")
        
        if st.button("🚀 Daftarkan & Dapatkan Link CSMS", type="primary"):
            if not reg_vendor_name or not reg_vendor_email:
                st.error("Harap isi Nama Perusahaan dan Email Resmi terlebih dahulu!")
            else:
                with st.spinner("Memproses registrasi & menerbitkan Token Akses CSMS..."):
                    try:
                        gc = get_gsheets()
                        spreadsheet_id = st.secrets["google_drive"]["spreadsheet_id"]
                        sh = gc.open_by_key(spreadsheet_id)
                        
                        try:
                            t_sheet = sh.worksheet("Token_Akses")
                        except Exception:
                            t_sheet = sh.add_worksheet(title="Token_Akses", rows="100", cols="4")
                            t_sheet.append_row(["Token", "Nama Vendor", "Expired Date", "Status"])
                        
                        rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                        new_token = f"K3-{rand_str}"
                        exp_date = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
                        
                        t_sheet.append_row([new_token, reg_vendor_name, exp_date, "Aktif"])
                        
                        base_url = get_current_app_url()
                        share_url = f"{base_url}/?token={new_token}"
                        
                        # Kirim Notifikasi & Link Unik ke Telegram Admin QHSE
                        if "telegram" in st.secrets and "bot_token" in st.secrets["telegram"]:
                            bot_token = st.secrets["telegram"]["bot_token"]
                            chat_id = st.secrets["telegram"]["chat_id"]
                            
                            notif_admin = (
                                f"🔔 <b>REGISTRASI MANDIRI VENDOR CSMS</b>\n\n"
                                f"🏢 <b>Vendor:</b> {reg_vendor_name}\n"
                                f"📧 <b>Email Vendor:</b> {reg_vendor_email}\n"
                                f"🔑 <b>Token Akses:</b> <code>{new_token}</code>\n"
                                f"📅 <b>Kadaluarsa:</b> {exp_date}\n\n"
                                f"📋 <b>Pesan Siap Kirim Ke Email/WA Vendor:</b>\n"
                                f"<code>Yth. {reg_vendor_name},\n\n"
                                f"Berikut adalah Link Pengisian Prakualifikasi CSMS Perusahaan Anda:\n"
                                f"{share_url}\n\n"
                                f"📌 Catatan: Link berlaku 7 hari (s.d {exp_date}) dan otomatis hangus setelah 1x submit.</code>"
                            )
                            send_telegram_message(bot_token, chat_id, notif_admin)
                            
                        st.success("✅ Registrasi Berhasil!")
                        st.markdown(f"**Link Pengisian CSMS Anda:**\n[{share_url}]({share_url})")
                        st.info("📌 Silakan klik link di atas untuk langsung mengisikan Formulir CSMS perusahaan Anda.")
                    except Exception as e:
                        st.error(f"Gagal melakukan registrasi: {e}")

    with tab_token:
        st.info("Jika Anda sudah menerima Kode Token atau mengeklik Link Unik dari Email, verifikasi di sini.")
        input_token = st.text_input("Masukkan Kode Token CSMS (Contoh: K3-X89A2)", value=url_token).strip().upper()
        
        if st.button("🔑 Buka Formulir CSMS"):
            if not input_token:
                st.error("Silakan masukkan Kode Token terlebih dahulu!")
            else:
                is_valid, msg, row_idx, v_name = verify_token_credentials(input_token)
                if is_valid:
                    st.session_state['authenticated'] = True
                    st.session_state['active_token'] = input_token
                    st.session_state['token_row_idx'] = row_idx
                    st.session_state['assigned_vendor'] = v_name
                    st.success("✅ Token Valid! Membuka Formulir CSMS...")
                    st.rerun()
                else:
                    st.error(msg)
    
    st.stop()

# ---------------------------------------------------------
# FORM CSMS (LAYAR VENDOR)
# ---------------------------------------------------------
st.info(f"🔑 **Token Akses Aktif:** `{st.session_state.get('active_token')}` — Perusahaan: **{st.session_state.get('assigned_vendor')}**")

st.subheader("1. Identitas Perusahaan")
col1, col2 = st.columns(2)
with col1:
    nama_vendor = st.text_input("Nama Perusahaan / Supplier / Vendor", value=st.session_state.get('assigned_vendor', ''))
    tgl_update = st.date_input("Tanggal Pengisian", datetime.date.today())
with col2:
    nama_pj = st.text_input("Penanggung Jawab K3 / HSE Leader")
    kontak_vendor = st.text_input("Nomor Telepon / Email Kontak")

st.divider()

st.subheader("2. Pertanyaan Evaluasi CSMS")

responses = {}
uploaded_files_dict = {}
file_status = {}
q_counter = 0
file_error_flag = False

for section in sections:
    st.markdown(f"### {section['kategori']}")
    
    for q in section['questions']:
        q_counter += 1
        q_id = q['id']
        
        st.markdown(f"**{q_counter}. {q['text']}**")
        col_ans, col_file = st.columns([1, 2])
        
        with col_ans:
            ans = st.radio(f"Jawaban ({q_counter})", ["Ya", "Tidak"], key=f"ans_{q_id}", horizontal=True)
            responses[q_id] = ans
            
        with col_file:
            if q.get('has_file'):
                if ans == "Ya":
                    up_file = st.file_uploader(f"📎 {q.get('file_label')} (Format PDF, Maks. 5MB)", type=["pdf"], key=f"file_{q_id}")
                    if up_file:
                        if up_file.size > 5 * 1024 * 1024:
                            st.error(f"⚠️ File **{up_file.name}** melebihi batas 5MB! Harap unggah file PDF yang lebih kecil.")
                            uploaded_files_dict[q_id] = None
                            file_status[q_id] = "File Melebihi Batas 5MB"
                            file_error_flag = True
                        else:
                            uploaded_files_dict[q_id] = up_file
                            file_status[q_id] = f"Ada ({up_file.name})"
                    else:
                        uploaded_files_dict[q_id] = None
                        file_status[q_id] = "Ada (Belum diunggah)"
                else:
                    uploaded_files_dict[q_id] = None
                    file_status[q_id] = "Tidak Ada (N/A)"
            else:
                uploaded_files_dict[q_id] = None
                file_status[q_id] = "-"
    st.markdown("---")

# ---------------------------------------------------------
# PROSES SUBMIT CSMS & PERHITUNGAN SKOR BESERTA DOKUMEN PDF
# ---------------------------------------------------------
if st.button("Submit Aplikasi CSMS", type="primary", use_container_width=True):
    if not nama_vendor:
        st.error("⚠️ Harap isi Nama Perusahaan terlebih dahulu!")
    elif file_error_flag:
        st.error("⚠️ Ada file lampiran yang melebihi batas ukuran 5MB. Harap periksa dan unggah kembali file yang sesuai.")
    else:
        with st.spinner("Menyimpan data CSMS & Mengubah Status Token menjadi Hangus..."):
            try:
                # HITUNG POIN RESMI BERDASARKAN FM/QHE/0127 REV. 2:
                # - Jawaban Ya = 1 Poin (Total 37 Soal)
                # - Lampiran PDF Ada = 1 Poin (Total 13 Lampiran)
                # - Total Poin Maksimal = 50 Poin
                # - Nilai CSMS (%) = Total Poin x 2
                
                total_ya = sum(1 for v in responses.values() if v == "Ya")
                total_files_uploaded = sum(1 for q_id, f_obj in uploaded_files_dict.items() if f_obj is not None)
                
                total_poin = total_ya + total_files_uploaded
                score_pct = total_poin * 2.0  # (total_poin / 50) * 100%

                if score_pct >= 70.0:
                    status_eval = "Dapat diterima (Lulus CSMS)"
                else:
                    status_eval = "Tidak dapat diterima (Tidak Lulus)"

                summary_list = []
                num_idx = 1
                for section in sections:
                    for q in section['questions']:
                        q_id = q['id']
                        summary_list.append({
                            "No": num_idx,
                            "Kategori": section['kategori'],
                            "Pertanyaan": q['text'],
                            "Jawaban": responses[q_id],
                            "Lampiran": file_status[q_id]
                        })
                        num_idx += 1

                clean_vendor_name = "".join(c for c in nama_vendor if c.isalnum() or c in (' ', '_', '-')).rstrip()
                pdf_bytes = generate_csms_pdf(nama_vendor, str(tgl_update), nama_pj, kontak_vendor, score_pct, total_poin, summary_list)
                pdf_filename = f"CSMS_Summary_{clean_vendor_name}.pdf"

                # 1. Simpan Rekapitulasi ke Google Sheets
                gc = get_gsheets()
                spreadsheet_id = st.secrets["google_drive"]["spreadsheet_id"]
                sh = gc.open_by_key(spreadsheet_id)
                worksheet = sh.sheet1
                
                headers = ["Timestamp", "Nama Vendor", "Tgl Pengisian", "Penanggung Jawab K3", "Kontak", "Total Poin", "Skor CSMS (%)", "Kesimpulan Hasil Evaluasi"]
                for sec in sections:
                    for q in sec['questions']:
                        headers.append(f"[{q['id']}] Jawaban")
                        if q.get('has_file'):
                            headers.append(f"[{q['id']}] Status Lampiran")

                all_values = worksheet.get_all_values()
                if len(all_values) == 0:
                    worksheet.append_row(headers)
                elif all_values[0][0] != "Timestamp":
                    worksheet.insert_row(headers, index=1)

                row_data = [
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    nama_vendor,
                    str(tgl_update),
                    nama_pj,
                    kontak_vendor,
                    f"{total_poin}/50",
                    f"{score_pct:.1f}%",
                    status_eval
                ]
                for sec in sections:
                    for q in sec['questions']:
                        q_id = q['id']
                        row_data.append(responses[q_id])
                        if q.get('has_file'):
                            row_data.append(file_status[q_id])

                worksheet.append_row(row_data)

                # 2. Update Status Token Menjadi 'Sudah Dipakai' (Hangus)
                if 'token_row_idx' in st.session_state:
                    t_sheet = sh.worksheet("Token_Akses")
                    t_sheet.update_cell(st.session_state['token_row_idx'], 4, "Sudah Dipakai")

                # 3. Kirim Telegram Notifikasi Rapi Hasil CSMS ke Admin
                if "telegram" in st.secrets and "bot_token" in st.secrets["telegram"]:
                    bot_token = st.secrets["telegram"]["bot_token"]
                    chat_id = st.secrets["telegram"]["chat_id"]

                    status_emoji = "✅" if score_pct >= 70.0 else "❌"
                    notif_text = (
                        f"🚨 <b>PENGAJUAN CSMS BARU (FM/QHE/0127 rev. 2)</b>\n\n"
                        f"🏢 <b>Vendor:</b> {nama_vendor}\n"
                        f"📅 <b>Tgl Pengisian:</b> {tgl_update}\n"
                        f"👤 <b>Penanggung Jawab K3:</b> {nama_pj}\n"
                        f"📞 <b>Kontak:</b> {kontak_vendor}\n\n"
                        f"📊 <b>Skor CSMS:</b> <code>{score_pct:.1f}%</code> ({total_poin} dari 50 Poin)\n"
                        f"├ 📝 <b>Jawaban 'Ya':</b> {total_ya} dari 37 Soal\n"
                        f"└ 📎 <b>Lampiran PDF:</b> {total_files_uploaded} dari 13 Dokumen\n\n"
                        f"📌 <b>Hasil Evaluasi:</b> {status_emoji} <b>{status_eval}</b>"
                    )
                    send_telegram_message(bot_token, chat_id, notif_text)

                    for q_id, f_obj in uploaded_files_dict.items():
                        if f_obj is not None:
                            file_b = f_obj.getvalue()
                            dest_fn = f"{q_id}_{clean_vendor_name}_{f_obj.name}"
                            cap = f"📎 <b>Lampiran [{q_id}]</b> - {nama_vendor}"
                            send_telegram_document(bot_token, chat_id, file_b, dest_fn, cap)

                    pdf_cap = f"📄 <b>PDF RINGKASAN CSMS (rev. 2)</b> - {nama_vendor}"
                    send_telegram_document(bot_token, chat_id, pdf_bytes, pdf_filename, pdf_cap)

                st.session_state['authenticated'] = False
                st.session_state.pop('active_token', None)

                st.success(f"✅ Pengajuan CSMS untuk **{nama_vendor}** berhasil tersimpan!")
                st.balloons()
                
                # TAMPILAN DETIL METRIK SKOR UNTUK VENDOR
                st.markdown("### 📊 Hasil Evaluasi Prakualifikasi CSMS")
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric(label="Skor Kepatuhan CSMS", value=f"{score_pct:.1f}%", delta=f"{total_poin}/50 Poin Terkumpul")
                with col_m2:
                    st.metric(label="Status Hasil Evaluasi", value=status_eval)
                with col_m3:
                    st.download_button(
                        label="📄 Unduh Laporan PDF CSMS",
                        data=pdf_bytes,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"Terjadi kesalahan saat memproses data: {e}")
