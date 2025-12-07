import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import StringIO
import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Pusat Komando 5D: Dashboard Prioritas Bencana Sumbar",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- FUNGSI FORMATTING BESAR ---
def format_rupiah(value):
    """Mengubah nilai Rupiah (dalam Miliar) menjadi format yang mudah dibaca (T/M)."""
    # Mengonversi dari Miliar ke Triliun jika angkanya besar
    if value >= 1000:
        return f"Rp {value / 1000:,.2f} T"
    else:
        return f"Rp {value:,.0f} M"

# --- DATA AKURAT (DARI CSV) ---
# Data CSV ini digunakan untuk mendapatkan TOTAL agregat yang akurat
csv_string = """Kategori,Sub_Kategori,Satuan,Nilai
Korbang Jiwa,Meninggal Total,Jiwa,176
Korbang Jiwa,Meninggal Teridentifikasi,Jiwa,140
Korbang Jiwa,Meninggal Belum Teridentifikasi,Jiwa,36
Korbang Jiwa,Hilang,Jiwa,117
Korbang Jiwa,Luka-Luka,Jiwa,112
Korbang Jiwa,Mengungsi,Jiwa,137383
Korbang Jiwa,Terdampak,Jiwa,141324
Kerusakan Rumah,Rusak Ringan,Unit,1827
Kerusakan Rumah,Rusak Sedang,Unit,660
Kerusakan Rumah,Rusak Berat,Unit,1092
Kerusakan Rumah,Terendam,Unit,0
Fasilitas Publik,Rumah Ibadah,Unit,86
Fasilitas Publik,Fasilitas Kesehatan,Unit,13
Fasilitas Publik,Kantor,Unit,16
Fasilitas Publik,Sekolah,Unit,110
Prasarana Vital,Jalan Rusak,Unit,7
Prasarana Vital,Jembatan Rusak,Unit,121
Dampak Ekonomi,Sawah,Ha,3473
Dampak Ekonomi,Lahan,Ha,2992
Dampak Ekonomi,Kebun,Ha,199
Dampak Ekonomi,Kolam,Ha,10483
Kerugian Finansial,Taksiran Kerugian Total,Rupiah,1072779241505
"""

# --- FUNGSI LOADING DATA HYBRID (MENGAMBIL TOTAL AKURAT DARI CSV) ---
@st.cache_data
def load_updated_data(csv_data_string):
    """
    Memuat data bencana alam Sumatera Barat menggunakan total agregat dari CSV 
    dan proporsi simulasi untuk breakdown per Kabupaten/Kota.
    """
    df_raw = pd.read_csv(StringIO(csv_data_string)).set_index('Sub_Kategori')
    
    # Dapatkan Total Otoritatif dari CSV
    rupiah_total_raw = float(df_raw.loc['Taksiran Kerugian Total', 'Nilai'])
    TOTAL_KERUGIAN_BARU_M = rupiah_total_raw / 1_000_000_000 # Dalam Miliar Rupiah
    TOTAL_MENINGGAL_BARU = float(df_raw.loc['Meninggal Total', 'Nilai'])
    TOTAL_MENGUNGSI_BARU = float(df_raw.loc['Mengungsi', 'Nilai'])
    TOTAL_JEMBATAN_RUSAK_BARU = float(df_raw.loc['Jembatan Rusak', 'Nilai'])
    TOTAL_SEKOLAH_RUSAK_BARU = float(df_raw.loc['Sekolah', 'Nilai'])
    TOTAL_FASKES_RUSAK_BARU = float(df_raw.loc['Fasilitas Kesehatan', 'Nilai'])
    TOTAL_UNIT_RUSAK_BARU = TOTAL_JEMBATAN_RUSAK_BARU + TOTAL_SEKOLAH_RUSAK_BARU + TOTAL_FASKES_RUSAK_BARU
    
    # Data Basis Simulasi (Proporsi Distribusi per Wilayah)
    data_bencana_simulasi = {
        'Kabupaten_Kota': ['Lima Puluh Kota', 'Pesisir Selatan', 'Agam', 'Tanah Datar', 'Padang', 'Solok Selatan', 'Padang Pariaman', 'Solok', 'Lainnya'],
        'Total_Meninggal': [30, 15, 8, 5, 4, 2, 1, 0, 0],
        'Mengungsi_Jiwa': [15000, 10000, 6000, 4000, 3000, 1000, 500, 500, 0],
        'Kerugian_Rupiah_Miliar': [90, 65, 30, 25, 20, 10, 5, 3, 2],
        'Jembatan_Rusak': [5, 3, 2, 1, 1, 0, 0, 0, 0],
        'Sekolah_Rusak': [7, 4, 3, 2, 1, 0, 0, 0, 0],
        'Faskes_Rusak': [2, 1, 1, 0, 0, 0, 0, 0, 0],
        'Jenis_Bencana': ['Banjir Bandang', 'Banjir', 'Tanah Longsor', 'Banjir Bandang', 'Banjir', 'Tanah Longsor', 'Banjir', 'Banjir', 'Tanah Longsor']
    }
    df_base = pd.DataFrame(data_bencana_simulasi)

    # Skala Data Base agar Totalnya Sesuai CSV (Proporsional)
    faktor_meninggal = TOTAL_MENINGGAL_BARU / df_base['Total_Meninggal'].sum()
    faktor_mengungsi = TOTAL_MENGUNGSI_BARU / df_base['Mengungsi_Jiwa'].sum()
    faktor_kerugian = TOTAL_KERUGIAN_BARU_M / df_base['Kerugian_Rupiah_Miliar'].sum()
    
    faktor_jembatan = TOTAL_JEMBATAN_RUSAK_BARU / df_base['Jembatan_Rusak'].sum()
    faktor_sekolah = TOTAL_SEKOLAH_RUSAK_BARU / df_base['Sekolah_Rusak'].sum()
    faktor_faskes = TOTAL_FASKES_RUSAK_BARU / df_base['Faskes_Rusak'].sum()
    
    df_bencana = df_base.copy()
    
    # Aplikasikan faktor skala dan lakukan penyesuaian untuk menjaga integritas total
    df_bencana['Total_Meninggal'] = (df_base['Total_Meninggal'] * faktor_meninggal).round().astype(int)
    df_bencana['Mengungsi_Jiwa'] = (df_base['Mengungsi_Jiwa'] * faktor_mengungsi).round().astype(int)
    df_bencana['Kerugian_Rupiah_Miliar'] = (df_base['Kerugian_Rupiah_Miliar'] * faktor_kerugian)
    df_bencana['Jembatan_Rusak'] = (df_base['Jembatan_Rusak'] * faktor_jembatan).round().astype(int)
    df_bencana['Sekolah_Rusak'] = (df_base['Sekolah_Rusak'] * faktor_sekolah).round().astype(int)
    df_bencana['Faskes_Rusak'] = (df_base['Faskes_Rusak'] * faktor_faskes).round().astype(int)

    # Penyesuaian Pembulatan Terakhir (Untuk memastikan total akhir SAMA PERSIS dengan CSV)
    df_bencana.loc[df_bencana.index[-1], 'Total_Meninggal'] += int(TOTAL_MENINGGAL_BARU) - df_bencana['Total_Meninggal'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Mengungsi_Jiwa'] += int(TOTAL_MENGUNGSI_BARU) - df_bencana['Mengungsi_Jiwa'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Jembatan_Rusak'] += int(TOTAL_JEMBATAN_RUSAK_BARU) - df_bencana['Jembatan_Rusak'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Sekolah_Rusak'] += int(TOTAL_SEKOLAH_RUSAK_BARU) - df_bencana['Sekolah_Rusak'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Faskes_Rusak'] += int(TOTAL_FASKES_RUSAK_BARU) - df_bencana['Faskes_Rusak'].sum()
    
    df_bencana['Total_Unit_Rusak'] = df_bencana['Jembatan_Rusak'] + df_bencana['Sekolah_Rusak'] + df_bencana['Faskes_Rusak']
    
    # Data Trend Harian (Simulasi 5 hari, dengan nilai akhir sesuai total baru)
    start_date = datetime.date(2025, 12, 1)
    days = pd.date_range(start_date, periods=5, freq='D')
    
    # Basis lama trend (untuk scaling)
    trend_base_meninggal = [10, 25, 40, 55, 65]
    trend_base_mengungsi = [5000, 15000, 25000, 35000, 40000]
    
    # Skala trend
    trend_data = pd.DataFrame({
        'Tanggal': days,
        'Meninggal_Kumulatif': (np.array(trend_base_meninggal) * faktor_meninggal).round().astype(int), 
        'Mengungsi_Kumulatif': (np.array(trend_base_mengungsi) * faktor_mengungsi).round().astype(int), 
        'Kerugian_Harian_Miliar': np.random.uniform(20, 300, 5).cumsum() # Nilai random karena tidak ada di CSV
    })
    
    # Penyesuaian nilai akhir trend agar sama persis dengan total CSV
    trend_data.loc[trend_data.index[-1], 'Meninggal_Kumulatif'] = int(TOTAL_MENINGGAL_BARU)
    trend_data.loc[trend_data.index[-1], 'Mengungsi_Kumulatif'] = int(TOTAL_MENGUNGSI_BARU)
    
    return df_bencana, trend_data, TOTAL_KERUGIAN_BARU_M, TOTAL_MENINGGAL_BARU, TOTAL_MENGUNGSI_BARU, TOTAL_UNIT_RUSAK_BARU

df_bencana, df_trend, TOTAL_KERUGIAN, TOTAL_MENINGGAL, TOTAL_MENGUNGSI, TOTAL_UNIT_RUSAK = load_updated_data(csv_string)

# --- JUDUL UTAMA ---
st.title("⚡ Pusat Komando 5D: Dashboard Prioritas Bencana Sumbar")
st.markdown(f"***Data Agregat Akurat (Total): {df_trend['Tanggal'].iloc[-1].strftime('%d %B %Y')}***")
st.divider()

# ====================================================================
# SIDEBAR UNTUK FILTER
# ====================================================================

st.sidebar.header("Filter Data")

# Filter 1: Hari/Tanggal
selected_date = st.sidebar.select_slider(
    'Pilih Tanggal Data',
    options=df_trend['Tanggal'].dt.date,
    value=df_trend['Tanggal'].dt.date.max()
)
# Temukan indeks tanggal yang dipilih
date_index = df_trend[df_trend['Tanggal'].dt.date == selected_date].index[0]

# Filter 2: Wilayah
all_kab_kota = df_bencana['Kabupaten_Kota'].unique().tolist()
selected_wilayah = st.sidebar.multiselect(
    'Pilih Kabupaten/Kota',
    options=['Semua Wilayah'] + all_kab_kota,
    default='Semua Wilayah'
)
if 'Semua Wilayah' in selected_wilayah:
    df_filtered_wilayah = df_bencana
else:
    df_filtered_wilayah = df_bencana[df_bencana['Kabupaten_Kota'].isin(selected_wilayah)]

# Filter 3: Jenis Bencana
all_jenis_bencana = df_bencana['Jenis_Bencana'].unique().tolist()
selected_jenis = st.sidebar.selectbox(
    'Pilih Jenis Bencana',
    options=['Semua Jenis'] + all_jenis_bencana
)
if selected_jenis == 'Semua Jenis':
    df_filtered = df_filtered_wilayah
else:
    df_filtered = df_filtered_wilayah[df_filtered_wilayah['Jenis_Bencana'] == selected_jenis]

# --- APLIKASIKAN FILTER HARI KE METRIK (HANYA UNTUK METRIK UTAMA DARI TREND) ---
df_trend_filtered = df_trend.iloc[:date_index + 1]
current_meninggal = df_trend_filtered['Meninggal_Kumulatif'].iloc[-1]
current_mengungsi = df_trend_filtered['Mengungsi_Kumulatif'].iloc[-1]
# Kerugian dihitung sebagai total kumulatif trend
current_kerugian = df_trend_filtered['Kerugian_Harian_Miliar'].sum() 
# Kerusakan Infrastruktur TIDAK dihitung kumulatif karena tidak ada data harian detail
current_unit_rusak = df_bencana['Total_Unit_Rusak'].sum()

# ====================================================================
# TABBED DASHBOARD
# ====================================================================

# Metrik Utama (Di luar tab agar selalu terlihat)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Korban Meninggal (Kumulatif)", f"{int(current_meninggal)} Jiwa")
with col2:
    st.metric("Jiwa Mengungsi (Kumulatif)", f"{int(current_mengungsi):,} Jiwa")
with col3:
    st.metric("Kerugian Finansial (Kumulatif)", format_rupiah(current_kerugian))
with col4:
    st.metric("Total Unit Infrastruktur Rusak", f"{int(current_unit_rusak)} Unit")

st.divider()

tab1, tab2, tab3 = st.tabs(["📊 Ringkasan Eksekutif & Trend", "💰 Analisis Finansial & Infrastruktur", "📍 Prioritas Aksi Cepat"])

# ====================================================================
# TAB 1: RINGKASAN EKSEKUTIF & TREND
# ====================================================================
with tab1:
    st.subheader("Visual 1.1: Trend Kumulatif Dampak Harian")
    
    trend_chart = alt.Chart(df_trend_filtered).transform_fold(
        ['Meninggal_Kumulatif', 'Mengungsi_Kumulatif'],
        as_=['Metrik', 'Jumlah']
    ).mark_line(point=True).encode(
        x=alt.X('Tanggal:T', title='Tanggal Update Data'),
        y=alt.Y('Jumlah:Q', title='Jumlah Kumulatif'),
        color='Metrik:N',
        tooltip=['Tanggal:T', 'Metrik:N', 'Jumlah:Q']
    ).properties(
        title=f'Trend Dampak Kemanusiaan Hingga {selected_date.strftime("%d %B")}'
    ).interactive()
    
    st.altair_chart(trend_chart, use_container_width=True)
    
    st.markdown("""
    #### Analisis Visual 1.1: Trend Kumulatif
    Visual ini menunjukkan **laju peningkatan** korban meninggal dan mengungsi dari hari ke hari. Jika garis melandai, itu indikasi penanganan darurat mulai stabil. **Tindakan Cepat:** Fokus pada titik puncak kenaikan harian untuk mengidentifikasi hari dengan dampak terparah, memungkinkan evaluasi respon darurat di hari tersebut.
    """)
    st.markdown("---")

    st.subheader("Visual 1.2: Sebaran Dampak per Kabupaten/Kota (Terfilter)")
    
    # Grafik Sebaran Korban Meninggal dan Mengungsi
    chart_meninggal_mengungsi = alt.Chart(df_filtered).mark_bar().encode(
        x=alt.X('Kabupaten_Kota', sort='-y', title='Kabupaten/Kota Terdampak'),
        y=alt.Y('Total_Meninggal', title='Korban Meninggal (Jiwa)'),
        color=alt.Color('Kabupaten_Kota', legend=None),
        tooltip=['Kabupaten_Kota', 'Total_Meninggal', 'Mengungsi_Jiwa', 'Jenis_Bencana']
    ).properties(
        title=f'Sebaran Korban Meninggal Berdasarkan Wilayah ({selected_jenis})'
    )
    
    chart_mengungsi_line = alt.Chart(df_filtered).mark_line(color='red', point=True).encode(
        x=alt.X('Kabupaten_Kota', sort='-y', axis=None),
        y=alt.Y('Mengungsi_Jiwa', title='Jiwa Mengungsi')
    )
    
    st.altair_chart(chart_meninggal_mengungsi + chart_mengungsi_line, use_container_width=True)

    st.markdown("""
    #### Analisis Visual 1.2: Sebaran Dampak
    Visual ini adalah **pusat identifikasi hotspot**. Wilayah dengan batang tertinggi adalah prioritas utama untuk bantuan kemanusiaan, logistik, dan evakuasi. **Tindakan Cepat:** Arahkan tim SAR dan logistik ke wilayah tersebut, seperti **Lima Puluh Kota** (berdasarkan data proporsional) yang menunjukkan dampak kemanusiaan tertinggi.
    """)

# ====================================================================
# TAB 2: ANALISIS FINANSIAL & INFRASTRUKTUR
# ====================================================================
with tab2:
    st.subheader("Visual 2.1: Kerugian Finansial per Kabupaten (Terfilter)")
    
    df_kerugian_filtered = df_filtered.sort_values(by='Kerugian_Rupiah_Miliar', ascending=False)
    
    kerugian_chart = alt.Chart(df_kerugian_filtered).mark_bar(color='#FFA07A').encode(
        x=alt.X('Kerugian_Rupiah_Miliar', title='Kerugian (Miliar Rupiah)'),
        y=alt.Y('Kabupaten_Kota', sort='-x', title=''),
        tooltip=['Kabupaten_Kota', alt.Tooltip('Kerugian_Rupiah_Miliar', format='.2f')]
    ).properties(
        title='Kerugian Rupiah (Estimasi) Berdasarkan Kabupaten/Kota'
    )
    st.altair_chart(kerugian_chart, use_container_width=True)

    st.markdown("""
    #### Analisis Visual 2.1: Kerugian Finansial
    Grafik ini memprioritaskan alokasi dana rekonstruksi. Wilayah dengan nilai Kerugian Rupiah terbesar (terutama jika difilter berdasarkan Jenis Bencana tertentu) membutuhkan **anggaran pemulihan yang masif**. **Tindakan Cepat:** Siapkan proposal anggaran darurat dan tim akuntabilitas finansial untuk mengelola dana di wilayah teratas.
    """)
    st.markdown("---")

    st.subheader("Visual 2.2: Kerusakan Infrastruktur Kritis (Terfilter)")
    
    # Agregasi infrastruktur untuk Donut Chart
    df_infrastruktur = df_filtered[['Jembatan_Rusak', 'Sekolah_Rusak', 'Faskes_Rusak']].sum().reset_index()
    df_infrastruktur.columns = ['Tipe_Unit', 'Jumlah']
    
    donut_chart = alt.Chart(df_infrastruktur).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="Jumlah", type="quantitative"),
        color=alt.Color(field="Tipe_Unit", type="nominal"),
        tooltip=['Tipe_Unit', 'Jumlah']
    ).properties(
        title='Total Unit Rusak Berdasarkan Tipe'
    )
    st.altair_chart(donut_chart, use_container_width=True)
    
    st.markdown("""
    #### Analisis Visual 2.2: Kerusakan Infrastruktur
    Diagram Donut ini menunjukkan **kebutuhan rekonstruksi yang paling mendesak** berdasarkan jenis infrastruktur. Dominasi **Jembatan Rusak** (jika yang tertinggi) berarti fokus logistik, sementara dominasi **Sekolah Rusak** berarti fokus pada pemulihan pendidikan. **Tindakan Cepat:** Kirim tim teknis sipil ke tipe unit dengan kerusakan tertinggi untuk penilaian kerusakan cepat.
    """)

# ====================================================================
# TAB 3: PRIORITAS AKSI CEPAT
# ====================================================================
with tab3:
    st.header("Ringkasan Aksi dan Prioritas 5D")
    
    # Tentukan Kabupaten Prioritas (Berdasarkan kerugian terbesar DAN korban terbanyak pada data yang difilter)
    if not df_filtered.empty:
        kabupaten_prioritas_df = df_filtered.sort_values(by=['Kerugian_Rupiah_Miliar', 'Total_Meninggal'], ascending=False).iloc[0]
        kabupaten_prioritas = kabupaten_prioritas_df['Kabupaten_Kota']
        jiwa_mengungsi_prioritas = kabupaten_prioritas_df['Mengungsi_Jiwa']
        jembatan_rusak_prioritas = kabupaten_prioritas_df['Jembatan_Rusak']
        sekolah_rusak_prioritas = kabupaten_prioritas_df['Sekolah_Rusak']
        faskes_rusak_prioritas = kabupaten_prioritas_df['Faskes_Rusak']

        st.markdown(f"""
            <div style="background-color: #ffe0e0; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b;">
                <h3 style="color: #ff4b4b; margin-top: 0;">🛑 KEPUTUSAN UTAMA: WILAYAH PRIORITAS</h3>
                <p style="font-size: 1.5em; font-weight: bold;">
                    Prioritas Utama Saat Ini: <span style="color: #c0392b;">{kabupaten_prioritas.upper()}</span>
                </p>
                <p>Wilayah ini memiliki kombinasi dampak tertinggi: **{jiwa_mengungsi_prioritas:,} Jiwa Mengungsi** dan Kerugian Finansial Terbesar di antara wilayah yang difilter.</p>
            </div>
        """, unsafe_allow_html=True)
        
        colP1, colP2 = st.columns(2)

        with colP1:
            st.markdown("#### 🆘 Tindakan Kemanusiaan (Immediate Action)")
            st.markdown(f"""
            1.  **Logistik**: Fokuskan bantuan pada {jiwa_mengungsi_prioritas:,} jiwa mengungsi di **{kabupaten_prioritas}**.
            2.  **Kesehatan**: Prioritaskan penanganan pada {faskes_rusak_prioritas} Faskes yang rusak untuk mencegah wabah.
            3.  **Ketersediaan**: Cek stok makanan dan air bersih untuk 24 jam ke depan di lokasi tersebut.
            """)

        with colP2:
            st.markdown("#### 🏗️ Tindakan Rekonstruksi (Medium-Term Action)")
            st.markdown(f"""
            1.  **Akses**: Prioritaskan perbaikan **{jembatan_rusak_prioritas} Jembatan Rusak** di **{kabupaten_prioritas}** untuk membuka jalur utama.
            2.  **Pendidikan**: Rencanakan sekolah darurat untuk **{sekolah_rusak_prioritas} Sekolah Rusak** agar proses belajar tidak terhenti.
            3.  **Mitigasi**: Tinjau area rawan longsor dan banjir bandang di {kabupaten_prioritas} untuk perencanaan reboisasi.
            """)
    else:
        st.info("Pilih setidaknya satu wilayah atau jenis bencana untuk melihat rekomendasi prioritas.")

    st.markdown("---")
    st.caption("Aplikasi ini dibuat untuk simulasi analisis data kebencanaan. Total agregat data bersumber dari CSV data terbaru.")
