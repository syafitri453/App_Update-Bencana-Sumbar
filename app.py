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

def highlight_priority(val):
    """Fungsi untuk highlight sel di DataFrame berdasarkan nilai."""
    if val > 50:
        color = '#ffe0e0' # Merah Muda untuk nilai tinggi
    elif val > 10:
        color = '#fffbe0' # Kuning Muda untuk nilai sedang
    else:
        color = ''
    return f'background-color: {color}'

# --- DATA AKURAT (DARI CSV - TOTAL OTORITATIF) ---
csv_string = """Kategori,Sub_Kategori,Satuan,Nilai
Korbang Jiwa,Meninggal Total,Jiwa,176
Korbang Jiwa,Meninggal Teridentifikasi,Jiwa,140
Korbang Jiwa,Hilang,Jiwa,117
Korbang Jiwa,Luka-Luka,Jiwa,112
Korbang Jiwa,Mengungsi,Jiwa,137383
Kerusakan Rumah,Rusak Ringan,Unit,1827
Kerusakan Rumah,Rusak Sedang,Unit,660
Kerusakan Rumah,Rusak Berat,Unit,1092
Fasilitas Publik,Rumah Ibadah,Unit,86
Fasilitas Publik,Fasilitas Kesehatan,Unit,13
Fasilitas Publik,Kantor,Unit,16
Fasilitas Publik,Sekolah,Unit,110
Prasarana Vital,Jalan Rusak,Unit,7
Prasarana Vital,Jembatan Rusak,Unit,121
Dampak Ekonomi,Sawah,Ha,3473
Kerugian Finansial,Taksiran Kerugian Total,Rupiah,1072779241505
"""

# --- FUNGSI LOADING DATA HYBRID DENGAN WILAYAH LENGKAP ---
@st.cache_data
def load_updated_data(csv_data_string):
    """
    Memuat data bencana alam Sumatera Barat dengan daftar wilayah yang lebih lengkap 
    dan total yang disesuaikan dengan data otoritatif.
    """
    df_raw = pd.read_csv(StringIO(csv_data_string)).set_index('Sub_Kategori')
    
    # Dapatkan Total Otoritatif dari CSV
    rupiah_total_raw = float(df_raw.loc['Taksiran Kerugian Total', 'Nilai'])
    TOTAL_KERUGIAN_BARU_M = rupiah_total_raw / 1_000_000_000 # Dalam Miliar Rupiah (~1072.7 M)
    TOTAL_MENINGGAL_BARU = float(df_raw.loc['Meninggal Total', 'Nilai'])
    TOTAL_MENGUNGSI_BARU = float(df_raw.loc['Mengungsi', 'Nilai'])
    TOTAL_JEMBATAN_RUSAK_BARU = float(df_raw.loc['Jembatan Rusak', 'Nilai'])
    TOTAL_SEKOLAH_RUSAK_BARU = float(df_raw.loc['Sekolah', 'Nilai'])
    TOTAL_FASKES_RUSAK_BARU = float(df_raw.loc['Fasilitas Kesehatan', 'Nilai'])
    TOTAL_UNIT_RUSAK_BARU = TOTAL_JEMBATAN_RUSAK_BARU + TOTAL_SEKOLAH_RUSAK_BARU + TOTAL_FASKES_RUSAK_BARU
    
    # Daftar 15 Kab/Kota di Sumatera Barat
    kab_kota_list = [
        'Agam', 'Lima Puluh Kota', 'Pesisir Selatan', 'Tanah Datar', 'Padang Pariaman', 
        'Solok Selatan', 'Pasaman Barat', 'Pasaman', 'Sijunjung', 'Dharmasraya', 
        'Kota Padang', 'Kota Solok', 'Kota Bukittinggi', 'Kota Pariaman', 'Kota Sawahlunto'
    ]
    
    # Data Basis Simulasi Awal (Weighted Scores - Lebih tinggi = dampak lebih parah)
    # Total score harus 100 untuk memudahkan proporsionalitas awal
    base_scores = {
        'Agam': 15, 'Lima Puluh Kota': 20, 'Pesisir Selatan': 18, 'Tanah Datar': 12, 
        'Padang Pariaman': 8, 'Solok Selatan': 5, 'Pasaman Barat': 4, 'Pasaman': 3, 
        'Sijunjung': 3, 'Dharmasraya': 2, 'Kota Padang': 5, 'Kota Solok': 2, 
        'Kota Bukittinggi': 1, 'Kota Pariaman': 1, 'Kota Sawahlunto': 1
    }

    # Distribusi jenis bencana (simulasi)
    jenis_bencana = [
        'Tanah Longsor', 'Banjir Bandang', 'Banjir', 'Tanah Longsor', 'Banjir', 
        'Tanah Longsor', 'Banjir', 'Banjir', 'Tanah Longsor', 'Banjir', 
        'Banjir', 'Tanah Longsor', 'Banjir', 'Banjir', 'Tanah Longsor'
    ]
    
    # Buat DataFrame Basis
    df_base = pd.DataFrame({'Kabupaten_Kota': kab_kota_list})
    df_base['Base_Score'] = df_base['Kabupaten_Kota'].map(base_scores)
    df_base['Jenis_Bencana'] = jenis_bencana
    
    # Hitung faktor skala (total score adalah 100)
    score_factor = df_base['Base_Score'] / 100
    
    # Aplikasikan faktor skala ke total otoritatif
    df_bencana = df_base.copy()
    
    # Korbang Jiwa
    df_bencana['Total_Meninggal'] = (score_factor * TOTAL_MENINGGAL_BARU).round().astype(int)
    df_bencana['Mengungsi_Jiwa'] = (score_factor * TOTAL_MENGUNGSI_BARU).round().astype(int)
    
    # Finansial & Infrastruktur (Skala yang berbeda untuk variasi visual)
    df_bencana['Kerugian_Rupiah_Miliar'] = score_factor * TOTAL_KERUGIAN_BARU_M
    df_bencana['Jembatan_Rusak'] = (score_factor * TOTAL_JEMBATAN_RUSAK_BARU).round().astype(int)
    df_bencana['Sekolah_Rusak'] = (score_factor * TOTAL_SEKOLAH_RUSAK_BARU).round().astype(int)
    df_bencana['Faskes_Rusak'] = (score_factor * TOTAL_FASKES_RUSAK_BARU).round().astype(int)

    # Penyesuaian Pembulatan Terakhir (Untuk memastikan total akhir SAMA PERSIS)
    df_bencana.loc[df_bencana.index[-1], 'Total_Meninggal'] += int(TOTAL_MENINGGAL_BARU) - df_bencana['Total_Meninggal'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Mengungsi_Jiwa'] += int(TOTAL_MENGUNGSI_BARU) - df_bencana['Mengungsi_Jiwa'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Jembatan_Rusak'] += int(TOTAL_JEMBATAN_RUSAK_BARU) - df_bencana['Jembatan_Rusak'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Sekolah_Rusak'] += int(TOTAL_SEKOLAH_RUSAK_BARU) - df_bencana['Sekolah_Rusak'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Faskes_Rusak'] += int(TOTAL_FASKES_RUSAK_BARU) - df_bencana['Faskes_Rusak'].sum()
    
    df_bencana['Total_Unit_Rusak'] = df_bencana['Jembatan_Rusak'] + df_bencana['Sekolah_Rusak'] + df_bencana['Faskes_Rusak']
    df_bencana = df_bencana.drop(columns=['Base_Score'])
    
    # Data Trend Harian (Simulasi 7 hari)
    start_date = datetime.date(2025, 12, 1)
    days = pd.date_range(start_date, periods=7, freq='D')
    
    # Basis lama trend (untuk scaling)
    trend_base_meninggal = [10, 25, 40, 55, 65, 80, 100]
    trend_base_mengungsi = [5000, 15000, 25000, 35000, 40000, 60000, 80000]
    trend_base_kerugian = [50, 150, 250, 400, 600, 800, 1000] # Dalam Miliar
    
    trend_data = pd.DataFrame({
        'Tanggal': days,
        # Skala trend
        'Meninggal_Kumulatif': (np.array(trend_base_meninggal) * (TOTAL_MENINGGAL_BARU / trend_base_meninggal[-1])).round().astype(int), 
        'Mengungsi_Kumulatif': (np.array(trend_base_mengungsi) * (TOTAL_MENGUNGSI_BARU / trend_base_mengungsi[-1])).round().astype(int), 
        'Kerugian_Kumulatif_Miliar': (np.array(trend_base_kerugian) * (TOTAL_KERUGIAN_BARU_M / trend_base_kerugian[-1])),
    })
    
    # Penyesuaian nilai akhir trend agar sama persis dengan total CSV
    trend_data.loc[trend_data.index[-1], 'Meninggal_Kumulatif'] = int(TOTAL_MENINGGAL_BARU)
    trend_data.loc[trend_data.index[-1], 'Mengungsi_Kumulatif'] = int(TOTAL_MENGUNGSI_BARU)
    trend_data.loc[trend_data.index[-1], 'Kerugian_Kumulatif_Miliar'] = TOTAL_KERUGIAN_BARU_M
    
    return df_bencana, trend_data, TOTAL_KERUGIAN_BARU_M, TOTAL_MENINGGAL_BARU, TOTAL_MENGUNGSI_BARU, TOTAL_UNIT_RUSAK_BARU

df_bencana, df_trend, TOTAL_KERUGIAN, TOTAL_MENINGGAL, TOTAL_MENGUNGSI, TOTAL_UNIT_RUSAK = load_updated_data(csv_string)

# --- JUDUL UTAMA ---
st.title("⚡ Pusat Komando 5D: Dashboard Prioritas Bencana Sumbar")
st.markdown(f"***Data Agregat Akurat (Total Akhir): {df_trend['Tanggal'].iloc[-1].strftime('%d %B %Y')}***")
st.divider()

# ====================================================================
# SIDEBAR UNTUK FILTER
# ====================================================================

st.sidebar.header("Filter Data Analisis")

# Filter 1: Hari/Tanggal (dengan opsi Semua Hari)
date_options = ['Semua Hari'] + df_trend['Tanggal'].dt.date.astype(str).tolist()
selected_date_str = st.sidebar.selectbox(
    'Pilih Tanggal Data Kumulatif',
    options=date_options,
    index=len(date_options) - 1 # Default ke tanggal terakhir
)

# Terapkan filter tanggal
if selected_date_str == 'Semua Hari':
    df_trend_filtered = df_trend
    current_date_display = 'Semua Hari'
else:
    selected_date = datetime.date.fromisoformat(selected_date_str)
    date_index = df_trend[df_trend['Tanggal'].dt.date == selected_date].index[0]
    df_trend_filtered = df_trend.iloc[:date_index + 1]
    current_date_display = selected_date.strftime('%d %B %Y')


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
current_meninggal = df_trend_filtered['Meninggal_Kumulatif'].iloc[-1]
current_mengungsi = df_trend_filtered['Mengungsi_Kumulatif'].iloc[-1]
current_kerugian_kumulatif = df_trend_filtered['Kerugian_Kumulatif_Miliar'].iloc[-1] 
# Kerusakan Infrastruktur TIDAK dihitung kumulatif harian karena tidak ada data detail, 
# menggunakan total dari filter wilayah/jenis bencana
current_unit_rusak = df_filtered['Total_Unit_Rusak'].sum()

# Metrik Utama (Di luar tab agar selalu terlihat)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Korban Meninggal", f"{int(current_meninggal)} Jiwa")
with col2:
    st.metric("Jiwa Mengungsi", f"{int(current_mengungsi):,} Jiwa")
with col3:
    st.metric("Kerugian Finansial", format_rupiah(current_kerugian_kumulatif))
with col4:
    st.metric(f"Infrastruktur Rusak ({'Terfilter' if selected_wilayah != ['Semua Wilayah'] or selected_jenis != 'Semua Jenis' else 'Total'})", f"{int(current_unit_rusak)} Unit")

st.divider()

# ====================================================================
# TABBED DASHBOARD
# ====================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Ringkasan Eksekutif & Trend", 
    "💰 Analisis Finansial & Infrastruktur", 
    "📍 Prioritas Aksi Cepat",
    "✅ Rekomendasi Tindakan Detail"
])

# ====================================================================
# TAB 1: RINGKASAN EKSEKUTIF & TREND
# ====================================================================
with tab1:
    st.subheader(f"Visual 1.1: Trend Kumulatif Dampak Kemanusiaan ({current_date_display})")
    
    trend_chart = alt.Chart(df_trend_filtered).transform_fold(
        ['Meninggal_Kumulatif', 'Mengungsi_Jiwa'],
        as_=['Metrik', 'Jumlah']
    ).mark_line(point=True).encode(
        x=alt.X('Tanggal:T', title='Tanggal Update Data'),
        y=alt.Y('Jumlah:Q', title='Jumlah Kumulatif'),
        color='Metrik:N',
        tooltip=['Tanggal:T', 'Metrik:N', alt.Tooltip('Jumlah:Q', format=',')]
    ).properties(
        title=f'Trend Dampak Kemanusiaan Hingga {df_trend_filtered["Tanggal"].iloc[-1].strftime("%d %B %Y")}'
    ).interactive()
    
    st.altair_chart(trend_chart, use_container_width=True)
    
    st.markdown("""
    #### Analisis Visual 1.1: Trend Kumulatif
    Visual ini menunjukkan **laju perkembangan krisis**. Peningkatan tajam menandakan situasi memburuk atau adanya penemuan korban baru.
    * **Tindakan Cepat:** Identifikasi tanggal dengan kenaikan paling curam untuk mengalokasikan sumber daya investigasi (SAR) dan memastikan respon pada hari itu sudah optimal.
    """)
    st.markdown("---")

    st.subheader("Visual 1.2: Peta Sebaran Korban Meninggal per Kab/Kota (Terfilter)")
    
    df_sorted_korban = df_filtered.sort_values(by='Total_Meninggal', ascending=False).head(10)
    
    chart_meninggal_mengungsi = alt.Chart(df_sorted_korban).mark_bar().encode(
        x=alt.X('Kabupaten_Kota', sort='-y', title='Kabupaten/Kota Terdampak'),
        y=alt.Y('Total_Meninggal', title='Korban Meninggal (Jiwa)', scale=alt.Scale(domain=[0, df_bencana['Total_Meninggal'].max() * 1.1])),
        color=alt.Color('Total_Meninggal', scale=alt.Scale(range=['#fdd0d0', '#ff0000']), legend=None),
        tooltip=['Kabupaten_Kota', 'Total_Meninggal', 'Mengungsi_Jiwa', 'Jenis_Bencana']
    ).properties(
        title=f'Top 10 Sebaran Korban Meninggal ({selected_jenis})'
    )
    
    st.altair_chart(chart_meninggal_mengungsi, use_container_width=True)

    st.markdown("""
    #### Analisis Visual 1.2: Hotspot Kemanusiaan
    Grafik ini adalah alat utama untuk menentukan **prioritas SAR dan Evakuasi**. Wilayah dengan batang tertinggi adalah titik fokus utama.
    * **Tindakan Cepat:** Segera kerahkan tim tambahan ke 3 kabupaten teratas untuk pencarian dan penyelamatan serta memastikan layanan kesehatan tersedia di sana.
    """)

# ====================================================================
# TAB 2: ANALISIS FINANSIAL & INFRASTRUKTUR
# ====================================================================
with tab2:
    st.subheader("Visual 2.1: Estimasi Kerugian Finansial per Kabupaten (Terfilter)")
    
    df_kerugian_filtered = df_filtered.sort_values(by='Kerugian_Rupiah_Miliar', ascending=False).head(10)
    
    kerugian_chart = alt.Chart(df_kerugian_filtered).mark_bar(color='#2A9D8F').encode(
        x=alt.X('Kerugian_Rupiah_Miliar', title='Kerugian (Miliar Rupiah)'),
        y=alt.Y('Kabupaten_Kota', sort='-x', title=''),
        tooltip=['Kabupaten_Kota', alt.Tooltip('Kerugian_Rupiah_Miliar', format='.2f')]
    ).properties(
        title='Kerugian Rupiah (Estimasi) Berdasarkan Kabupaten/Kota'
    )
    st.altair_chart(kerugian_chart, use_container_width=True)

    st.markdown("""
    #### Analisis Visual 2.1: Prioritas Anggaran
    Visual ini memandu **alokasi dana rekonstruksi**. Wilayah dengan kerugian tertinggi membutuhkan audit kerusakan dan perencanaan anggaran pemulihan segera.
    * **Tindakan Cepat:** Bentuk tim pemulihan ekonomi di kabupaten teratas untuk memulai pendataan aset dan infrastruktur yang rusak demi mempercepat klaim anggaran.
    """)
    st.markdown("---")

    st.subheader("Visual 2.2: Komposisi Kerusakan Infrastruktur Kritis (Terfilter)")
    
    # Agregasi infrastruktur
    df_infrastruktur = df_filtered[['Jembatan_Rusak', 'Sekolah_Rusak', 'Faskes_Rusak']].sum().reset_index()
    df_infrastruktur.columns = ['Tipe_Unit', 'Jumlah']
    
    donut_chart = alt.Chart(df_infrastruktur).mark_arc(innerRadius=80).encode(
        theta=alt.Theta(field="Jumlah", type="quantitative"),
        color=alt.Color(field="Tipe_Unit", type="nominal", scale=alt.Scale(range=['#E9C46A', '#F4A261', '#E76F51'])),
        order=alt.Order(field="Jumlah", sort="descending"),
        tooltip=['Tipe_Unit', alt.Tooltip('Jumlah', format=',')]
    ).properties(
        title='Total Unit Rusak Berdasarkan Tipe'
    )
    
    text = alt.Chart(df_infrastruktur).mark_text(align='center', baseline='middle').encode(
        text=alt.Text("Jumlah:Q", format=","),
        order=alt.Order(field="Jumlah", sort="descending"),
        color=alt.value("black") 
    )
    
    st.altair_chart(donut_chart, use_container_width=True)
    
    st.markdown("""
    #### Analisis Visual 2.2: Fokus Rekonstruksi
    Diagram ini menentukan **jenis tim teknis** yang paling dibutuhkan.
    * **Jika Jembatan dominan:** Perlu tim teknik sipil spesialis jembatan untuk membuka akses logistik.
    * **Jika Sekolah dominan:** Perlu koordinasi cepat dengan Kemendikbud untuk sekolah darurat.
    * **Tindakan Cepat:** Bentuk gugus tugas khusus perbaikan Jembatan (untuk akses) dan Sekolah/Faskes (untuk layanan publik).
    """)

# ====================================================================
# TAB 3: PRIORITAS AKSI CEPAT
# ====================================================================
with tab3:
    st.header("Ringkasan Prioritas (Berdasarkan Data Terfilter)")
    
    if not df_filtered.empty:
        # Menghitung Total Skor Prioritas (gabungan korban, kerugian, dan kerusakan)
        df_prioritas = df_filtered.copy()
        
        # Normalisasi untuk skor gabungan
        df_prioritas['Skor_Meninggal'] = df_prioritas['Total_Meninggal'] / df_prioritas['Total_Meninggal'].max()
        df_prioritas['Skor_Mengungsi'] = df_prioritas['Mengungsi_Jiwa'] / df_prioritas['Mengungsi_Jiwa'].max()
        df_prioritas['Skor_Kerugian'] = df_prioritas['Kerugian_Rupiah_Miliar'] / df_prioritas['Kerugian_Rupiah_Miliar'].max()
        df_prioritas['Skor_Infrastruktur'] = df_prioritas['Total_Unit_Rusak'] / df_prioritas['Total_Unit_Rusak'].max()
        
        # Skor akhir (bobot: Kemanusiaan 40%, Finansial 30%, Infrastruktur 30%)
        df_prioritas['Skor_Prioritas_Gabungan'] = (
            (df_prioritas['Skor_Meninggal'] + df_prioritas['Skor_Mengungsi']) * 0.20 +
            (df_prioritas['Skor_Kerugian'] * 0.30) +
            (df_prioritas['Skor_Infrastruktur'] * 0.30)
        ) * 100
        
        df_top_prioritas = df_prioritas.sort_values(by='Skor_Prioritas_Gabungan', ascending=False).head(5)
        
        # Menampilkan tabel prioritas
        st.subheader("Top 5 Wilayah Berdasarkan Skor Prioritas Gabungan")
        
        df_display = df_top_prioritas[[
            'Kabupaten_Kota', 
            'Total_Meninggal', 
            'Mengungsi_Jiwa', 
            'Kerugian_Rupiah_Miliar',
            'Total_Unit_Rusak',
            'Skor_Prioritas_Gabungan'
        ]].rename(columns={
            'Total_Meninggal': 'Meninggal', 
            'Mengungsi_Jiwa': 'Mengungsi', 
            'Kerugian_Rupiah_Miliar': 'Kerugian (M)',
            'Total_Unit_Rusak': 'Rusak (Unit)',
            'Skor_Prioritas_Gabungan': 'Skor (%)'
        })
        
        df_display['Skor (%)'] = df_display['Skor (%)'].round(1)
        df_display['Kerugian (M)'] = df_display['Kerugian (M)'].round(1)

        # Highlight skor tertinggi
        st.dataframe(
            df_display.style.applymap(highlight_priority, subset=['Skor (%)']),
            use_container_width=True
        )

        st.markdown("---")
        
        # Prioritas Eksekutif Berdasarkan Peringkat 1
        top_kab = df_top_prioritas.iloc[0]['Kabupaten_Kota']
        
        st.markdown(f"""
            <div style="background-color: #ffcccc; padding: 25px; border-radius: 12px; border-left: 8px solid #cc0000; margin-top: 20px;">
                <h2 style="color: #cc0000; margin-top: 0; font-weight: 700;">🚨 FOKUS AKSI UTAMA (Peringkat 1)</h2>
                <p style="font-size: 1.6em; font-weight: bold;">
                    Prioritas Tunggal: <span style="color: #990000;">{top_kab.upper()}</span>
                </p>
                <p>Semua sumber daya cepat (SAR, Medis, Logistik 48 Jam) harus diarahkan ke wilayah ini terlebih dahulu.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Pilih setidaknya satu wilayah atau jenis bencana untuk melihat rekomendasi prioritas.")

# ====================================================================
# TAB 4: REKOMENDASI TINDAKAN DETAIL
# ====================================================================
with tab4:
    st.header("Rencana Aksi Prioritas 5D (Detail)")
    
    if not df_filtered.empty:
        # Ambil data top 3 dari hasil skor gabungan
        df_prioritas_aksi = df_prioritas.sort_values(by='Skor_Prioritas_Gabungan', ascending=False).head(3)
        
        if len(df_prioritas_aksi) > 0:
            P1 = df_prioritas_aksi.iloc[0]
            P2 = df_prioritas_aksi.iloc[1] if len(df_prioritas_aksi) > 1 else None
            P3 = df_prioritas_aksi.iloc[2] if len(df_prioritas_aksi) > 2 else None
        
        st.subheader("1. Kemanusiaan & SAR (Prioritas Waktu 0-72 Jam)")
        st.markdown("""
        Fokus: Menyelamatkan jiwa, mengevakuasi, dan memastikan kebutuhan dasar terpenuhi.
        """)
        
        st.info(f"""
        **PRIORITAS TERTINGGI ({P1['Kabupaten_Kota']}):**
        - **SAR:** Kerahkan 75% tim SAR tersisa ke lokasi Bencana {P1['Jenis_Bencana']} untuk pencarian **{int(P1['Total_Meninggal'])} korban** dan **{int(P1['Mengungsi_Jiwa']):,} jiwa mengungsi**.
        - **Logistik:** Distribusikan 100% bantuan darurat (makanan siap saji, selimut, obat-obatan) untuk 72 jam pertama ke pusat evakuasi terbesar.
        - **Medis:** Siapkan posko darurat dan tim medis trauma untuk korban luka-luka.
        """)

        if P2 is not None:
            st.warning(f"""
            **PRIORITAS SEKUNDER ({P2['Kabupaten_Kota']}):**
            - **SAR:** Kerahkan 25% tim SAR untuk menyisir lokasi-lokasi terpencil yang terisolasi di area {P2['Jenis_Bencana']}.
            - **Kesehatan:** Kirim tim psikososial untuk membantu trauma korban mengungsi.
            """)
        
        st.markdown("---")
        
        st.subheader("2. Pemulihan Akses & Infrastruktur (Prioritas Waktu 72 Jam +)")
        st.markdown("""
        Fokus: Membuka jalur vital, memfungsikan fasilitas publik.
        """)
        
        # Ambil total infrastruktur dari top 3
        total_jembatan = df_prioritas_aksi['Jembatan_Rusak'].sum()
        total_sekolah = df_prioritas_aksi['Sekolah_Rusak'].sum()
        total_faskes = df_prioritas_aksi['Faskes_Rusak'].sum()

        st.error(f"""
        **Aksi Infrastruktur Total Top 3:**
        - **Jembatan ({total_jembatan} Unit Rusak):** Segera bangun jembatan darurat (Bailey) untuk minimal 3 jembatan yang paling vital di **{P1['Kabupaten_Kota']}** dalam 7 hari ke depan.
        - **Sekolah ({total_sekolah} Unit Rusak):** Identifikasi bangunan publik terdekat (Kantor Desa/Balai Pertemuan) untuk dijadikan Sekolah Darurat.
        - **Faskes ({total_faskes} Unit Rusak):** Prioritaskan perbaikan **1 Faskes** terpenting di **{P1['Kabupaten_Kota']}** agar layanan bersalin dan darurat berjalan.
        """)

        st.markdown("---")

        st.subheader("3. Pemulihan Ekonomi & Keuangan (Prioritas Jangka Panjang)")
        st.markdown("""
        Fokus: Mempersiapkan anggaran, dan pemulihan mata pencaharian.
        """)
        
        st.success(f"""
        **Aksi Finansial:**
        - **Anggaran:** Siapkan dokumen klaim untuk anggaran pemulihan sebesar **{format_rupiah(df_prioritas_aksi['Kerugian_Rupiah_Miliar'].sum())}** yang terakumulasi di Top 3 Wilayah.
        - **Mata Pencaharian:** Mulai pendataan kerusakan lahan (Sawah/Kebun) di wilayah dengan kerugian terbesar untuk program bantuan benih dan modal kerja.
        """)
        
    else:
        st.info("Pilih setidaknya satu wilayah atau jenis bencana untuk melihat rekomendasi tindakan detail.")

    st.caption("Dashboard ini menyediakan analisis cepat berdasarkan data agregat bencana. Gunakan ini sebagai panduan awal dalam pengambilan keputusan.")
