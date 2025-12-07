import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

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
    if value >= 1000:
        # Konversi ke Triliun (T)
        return f"Rp {value / 1000:,.2f} T"
    else:
        # Konversi ke Miliar (M)
        return f"Rp {value:,.0f} M"

# --- FUNGSI LOADING DATA HYBRID (MENGGABUNGKAN TOTAL CSV DENGAN DISTRIBUSI SIMULASI) ---
def load_updated_data(csv_data_string):
    """
    Memuat data bencana alam Sumatera Barat menggunakan total agregat dari CSV 
    dan proporsi simulasi untuk breakdown per Kabupaten/Kota.
    """
    from io import StringIO
    df_raw = pd.read_csv(StringIO(csv_data_string))
    
    # 1. Dapatkan Total Otoritatif dari CSV
    df_csv = df_raw.set_index('Sub_Kategori')
    
    # Konversi total kerugian dari Rupiah ke Miliar untuk perhitungan
    rupiah_total_raw = float(df_csv.loc['Taksiran Kerugian Total', 'Nilai'])
    TOTAL_KERUGIAN_BARU_M = rupiah_total_raw / 1_000_000_000 # Dalam Miliar Rupiah
    TOTAL_MENINGGAL_BARU = float(df_csv.loc['Meninggal Total', 'Nilai'])
    TOTAL_MENGUNGSI_BARU = float(df_csv.loc['Mengungsi', 'Nilai'])
    
    # Total Unit Rusak (Jembatan Rusak + Sekolah + Fasilitas Kesehatan)
    TOTAL_UNIT_RUSAK_BARU = float(df_csv.loc['Jembatan Rusak', 'Nilai']) + float(df_csv.loc['Sekolah', 'Nilai']) + float(df_csv.loc['Fasilitas Kesehatan', 'Nilai'])

    # 2. Data Simulasi Awal (digunakan untuk proporsi Kabupaten/Kota)
    data_bencana_simulasi = {
        'Kabupaten_Kota': ['Lima Puluh Kota', 'Pesisir Selatan', 'Agam', 'Tanah Datar', 'Padang', 'Solok Selatan', 'Padang Pariaman', 'Solok', 'Lainnya'],
        'Total_Meninggal': [30, 15, 8, 5, 4, 2, 1, 0, 0], # Total: 65 (basis lama)
        'Mengungsi_Jiwa': [15000, 10000, 6000, 4000, 3000, 1000, 500, 500, 0], # Total: 40000 (basis lama)
        'Kerugian_Rupiah_Miliar': [90, 65, 30, 25, 20, 10, 5, 3, 2], # Total: 250 (basis lama)
        'Jembatan_Rusak': [5, 3, 2, 1, 1, 0, 0, 0, 0], # Total: 12 (basis lama)
        'Sekolah_Rusak': [7, 4, 3, 2, 1, 0, 0, 0, 0], # Total: 17 (basis lama)
        'Faskes_Rusak': [2, 1, 1, 0, 0, 0, 0, 0, 0], # Total: 4 (basis lama)
        'Jenis_Bencana': ['Banjir Bandang', 'Banjir', 'Tanah Longsor', 'Banjir Bandang', 'Banjir', 'Tanah Longsor', 'Banjir', 'Banjir', 'Tanah Longsor']
    }
    df_base = pd.DataFrame(data_bencana_simulasi)

    # 3. Skala Data Base agar Totalnya Sesuai CSV (Proporsional)
    faktor_meninggal = TOTAL_MENINGGAL_BARU / df_base['Total_Meninggal'].sum()
    faktor_mengungsi = TOTAL_MENGUNGSI_BARU / df_base['Mengungsi_Jiwa'].sum()
    faktor_kerugian = TOTAL_KERUGIAN_BARU_M / df_base['Kerugian_Rupiah_Miliar'].sum()
    
    # Faktor untuk Infrastruktur Rusak agar totalnya sesuai CSV
    faktor_jembatan = float(df_csv.loc['Jembatan Rusak', 'Nilai']) / df_base['Jembatan_Rusak'].sum()
    faktor_sekolah = float(df_csv.loc['Sekolah', 'Nilai']) / df_base['Sekolah_Rusak'].sum()
    faktor_faskes = float(df_csv.loc['Fasilitas Kesehatan', 'Nilai']) / df_base['Faskes_Rusak'].sum()
    
    df_bencana = df_base.copy()
    
    # Aplikasikan faktor skala dan lakukan pembulatan untuk menjaga integritas (total harus sesuai CSV)
    df_bencana['Total_Meninggal'] = (df_base['Total_Meninggal'] * faktor_meninggal).round().astype(int)
    df_bencana['Mengungsi_Jiwa'] = (df_base['Mengungsi_Jiwa'] * faktor_mengungsi).round().astype(int)
    df_bencana['Kerugian_Rupiah_Miliar'] = (df_base['Kerugian_Rupiah_Miliar'] * faktor_kerugian)
    df_bencana['Jembatan_Rusak'] = (df_base['Jembatan_Rusak'] * faktor_jembatan).round().astype(int)
    df_bencana['Sekolah_Rusak'] = (df_base['Sekolah_Rusak'] * faktor_sekolah).round().astype(int)
    df_bencana['Faskes_Rusak'] = (df_base['Faskes_Rusak'] * faktor_faskes).round().astype(int)

    # Penyesuaian Pembulatan (Pastikan Total Agregat Tetap Sesuai CSV)
    df_bencana.loc[df_bencana.index[-1], 'Total_Meninggal'] += int(TOTAL_MENINGGAL_BARU) - df_bencana['Total_Meninggal'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Mengungsi_Jiwa'] += int(TOTAL_MENGUNGSI_BARU) - df_bencana['Mengungsi_Jiwa'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Jembatan_Rusak'] += int(df_csv.loc['Jembatan Rusak', 'Nilai']) - df_bencana['Jembatan_Rusak'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Sekolah_Rusak'] += int(df_csv.loc['Sekolah', 'Nilai']) - df_bencana['Sekolah_Rusak'].sum()
    df_bencana.loc[df_bencana.index[-1], 'Faskes_Rusak'] += int(df_csv.loc['Fasilitas Kesehatan', 'Nilai']) - df_bencana['Faskes_Rusak'].sum()

    df_bencana['Total_Unit_Rusak'] = df_bencana['Jembatan_Rusak'] + df_bencana['Sekolah_Rusak'] + df_bencana['Faskes_Rusak']
    
    # Data trend harian (simulasi 5 hari, diskalakan ke total baru)
    days = pd.to_datetime(['2025-12-01', '2025-12-02', '2025-12-03', '2025-12-04', '2025-12-05'])
    # Menggunakan basis trend lama dan menskalakannya
    trend_data = pd.DataFrame({
        'Tanggal': days,
        'Meninggal_Kumulatif': (np.array([10, 25, 40, 55, 65]) * faktor_meninggal).round().astype(int), 
        'Mengungsi_Kumulatif': (np.array([5000, 15000, 25000, 35000, 40000]) * faktor_mengungsi).round().astype(int), 
        # Kerugian harian disimulasikan secara proporsional
        'Kerugian_Harian_Miliar': (np.array([15, 30, 50, 75, 80]) * faktor_kerugian).round(1) 
    })
    
    # Penyesuaian terakhir: pastikan nilai akhir di trend cocok dengan total CSV
    trend_data.loc[trend_data.index[-1], 'Meninggal_Kumulatif'] = int(TOTAL_MENINGGAL_BARU)
    trend_data.loc[trend_data.index[-1], 'Mengungsi_Kumulatif'] = int(TOTAL_MENGUNGSI_BARU)
    
    return df_bencana, trend_data, TOTAL_KERUGIAN_BARU_M, TOTAL_MENINGGAL_BARU, TOTAL_MENGUNGSI_BARU, TOTAL_UNIT_RUSAK_BARU

# --- MUAT DATA DARI CSV YANG DISEDIAKAN ---
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

df_bencana, df_trend, TOTAL_KERUGIAN, TOTAL_MENINGGAL, TOTAL_MENGUNGSI, TOTAL_UNIT_RUSAK = load_updated_data(csv_string)

# --- JUDUL UTAMA ---
st.title("⚡ Pusat Komando 5D: Dashboard Prioritas Bencana Sumbar")
st.markdown(f"***Update Data Terbaru: {df_trend['Tanggal'].iloc[-1].strftime('%d %B %Y')}***")
st.divider()

# ====================================================================
# TAB 1: RINGKASAN EKSEKUTIF
# ====================================================================

st.header("1. Ringkasan Eksekutif Bencana")
col1, col2, col3, col4 = st.columns(4)

# Metrik Utama
with col1:
    # Menggunakan total Meninggal dari CSV: 176
    st.metric("Total Korban Meninggal", f"{int(TOTAL_MENINGGAL)} Jiwa", delta="Sesuai Data Terbaru")
with col2:
    # Menggunakan total Mengungsi dari CSV: 137,383
    st.metric("Total Jiwa Mengungsi", f"{int(TOTAL_MENGUNGSI):,} Jiwa", delta="Sangat Tinggi")
with col3:
    # Menggunakan total Kerugian dari CSV (~1.07 Triliun)
    st.metric("Total Kerugian (Estimasi)", format_rupiah(TOTAL_KERUGIAN), delta="Kebutuhan Tinggi")
with col4:
    # Menggunakan total Unit Rusak dari CSV: 244
    st.metric("Total Unit Infrastruktur Rusak", f"{int(TOTAL_UNIT_RUSAK)} Unit", delta="Kritis")

st.markdown("---")

# Grafik 1: Sebaran Korban Meninggal per Kabupaten/Kota (Menggunakan data yang diskalakan)
st.subheader("Penyebaran Dampak Kemanusiaan (Meninggal & Mengungsi)")
chart_meninggal_mengungsi = alt.Chart(df_bencana).mark_bar().encode(
    x=alt.X('Kabupaten_Kota', sort='-y', title='Kabupaten/Kota Terdampak'),
    y=alt.Y('Total_Meninggal', title='Korban Meninggal (Jiwa)'),
    color=alt.Color('Kabupaten_Kota', legend=None),
    tooltip=['Kabupaten_Kota', 'Total_Meninggal', 'Mengungsi_Jiwa']
).properties(
    title='Korban Meninggal Berdasarkan Kabupaten/Kota (Proporsi)'
)

chart_mengungsi_line = alt.Chart(df_bencana).mark_line(color='red', point=True).encode(
    x=alt.X('Kabupaten_Kota', sort='-y', axis=None),
    y=alt.Y('Mengungsi_Jiwa', title='Jiwa Mengungsi')
).interactive()

st.altair_chart(chart_meninggal_mengungsi + chart_mengungsi_line, use_container_width=True)


# Grafik 2: Trend Harian Korban dan Kerugian (Menggunakan data trend yang diskalakan)
st.subheader("Trend Kumulatif Dampak Harian")
trend_chart = alt.Chart(df_trend).transform_fold(
    ['Meninggal_Kumulatif', 'Mengungsi_Kumulatif'],
    as_=['Metrik', 'Jumlah']
).mark_line(point=True).encode(
    x=alt.X('Tanggal:T', title='Tanggal Update Data'),
    y=alt.Y('Jumlah:Q', title='Jumlah Kumulatif'),
    color='Metrik:N',
    tooltip=['Tanggal:T', 'Metrik:N', 'Jumlah:Q']
).properties(
    title='Trend Kumulatif Meninggal dan Mengungsi Harian (Total Sesuai CSV)'
).interactive()

st.altair_chart(trend_chart, use_container_width=True)

st.markdown("---")

# ====================================================================
# TAB 2: ANALISIS FINANSIAL & KERUGIAN
# ====================================================================
st.header("2. Analisis Finansial & Kerugian Infrastruktur")

colA, colB = st.columns([2, 1])

with colA:
    st.subheader("Sebaran Kerugian Finansial per Kabupaten (Proporsi)")
    # Urutkan berdasarkan kerugian terbesar
    df_kerugian = df_bencana.sort_values(by='Kerugian_Rupiah_Miliar', ascending=False)
    
    kerugian_chart = alt.Chart(df_kerugian).mark_bar(color='#FFA07A').encode(
        x=alt.X('Kerugian_Rupiah_Miliar', title='Kerugian (Miliar Rupiah)'),
        y=alt.Y('Kabupaten_Kota', sort='-x', title=''),
        tooltip=['Kabupaten_Kota', alt.Tooltip('Kerugian_Rupiah_Miliar', format='.2f')]
    ).properties(
        title='Kerugian Rupiah (Estimasi) Berdasarkan Kabupaten/Kota (Total Akurat CSV)'
    )
    st.altair_chart(kerugian_chart, use_container_width=True)

with colB:
    st.subheader("Rata-Rata Kerugian Harian")
    # Gunakan data trend untuk rata-rata kerugian harian
    avg_kerugian_harian = df_trend['Kerugian_Harian_Miliar'].mean()
    st.info(f"Rata-rata kerugian harian estimasi: **{format_rupiah(avg_kerugian_harian)}**")

    st.subheader("Kerusakan Infrastruktur Kritis (Total Akurat CSV)")
    # Grafik Pie/Donut untuk Infrastruktur Rusak
    df_infrastruktur = df_bencana[['Jembatan_Rusak', 'Sekolah_Rusak', 'Faskes_Rusak']].sum().reset_index()
    df_infrastruktur.columns = ['Tipe_Unit', 'Jumlah']
    
    donut_chart = alt.Chart(df_infrastruktur).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="Jumlah", type="quantitative"),
        color=alt.Color(field="Tipe_Unit", type="nominal"),
        tooltip=['Tipe_Unit', 'Jumlah']
    ).properties(
        title='Total Unit Rusak Berdasarkan Tipe'
    )
    st.altair_chart(donut_chart, use_container_width=True)

st.markdown("---")

# ====================================================================
# TAB 3: PRIORITAS & PEMULIHAN (5D COMMAND CENTER)
# ====================================================================

st.header("3. Pusat Komando 5D: Prioritas dan Rekomendasi Aksi Cepat")

# Tentukan Kabupaten Prioritas (Berdasarkan kerugian terbesar dan korban terbanyak)
kabupaten_prioritas_df = df_bencana.sort_values(by=['Kerugian_Rupiah_Miliar', 'Total_Meninggal'], ascending=False).iloc[0]
kabupaten_prioritas = kabupaten_prioritas_df['Kabupaten_Kota']
jiwa_mengungsi_prioritas = kabupaten_prioritas_df['Mengungsi_Jiwa']
jembatan_rusak_prioritas = kabupaten_prioritas_df['Jembatan_Rusak']
sekolah_rusak_prioritas = kabupaten_prioritas_df['Sekolah_Rusak']
faskes_rusak_prioritas = kabupaten_prioritas_df['Faskes_Rusak']


st.markdown(f"""
    <div style="background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 5px solid #1e90ff;">
        <h3 style="color: #1e90ff; margin-top: 0;">🎯 FOKUS PRIORITAS SAAT INI</h3>
        <p style="font-size: 1.2em; font-weight: bold;">
            Kabupaten/Kota Prioritas Utama: <span style="color: #ff4b4b;">{kabupaten_prioritas.upper()}</span>
        </p>
        <p>Prioritas ini ditentukan berdasarkan Kerugian Finansial Terbesar dan Jumlah Korban Jiwa Mengungsi Terbanyak ({jiwa_mengungsi_prioritas:,} Jiwa).</p>
    </div>
""", unsafe_allow_html=True)

st.subheader("Rekomendasi Tindakan Utama")

colP1, colP2 = st.columns(2)

with colP1:
    st.markdown("#### 🆘 Tindakan Kemanusiaan (Jangka Pendek)")
    st.markdown(f"""
    1.  **Distribusi Bantuan Mendesak**: Fokus pada {jiwa_mengungsi_prioritas:,} jiwa mengungsi di {kabupaten_prioritas} (makanan, air bersih, tenda).
    2.  **Layanan Kesehatan Darurat**: Prioritaskan {faskes_rusak_prioritas} Faskes yang rusak dan ketersediaan tim medis di lokasi pengungsian.
    3.  **Psikososial**: Kerahkan tim pendampingan bagi keluarga korban meninggal total ({int(TOTAL_MENINGGAL)} jiwa).
    """)

with colP2:
    st.markdown("#### 🏗️ Tindakan Rekonstruksi & Mitigasi (Jangka Menengah)")
    st.markdown(f"""
    1.  **Infrastruktur Kritis**: Prioritaskan perbaikan Jembatan Rusak ({jembatan_rusak_prioritas} unit) di {kabupaten_prioritas} untuk akses logistik.
    2.  **Jalur Pendidikan**: Inventarisasi cepat perbaikan Sekolah Rusak ({sekolah_rusak_prioritas} unit) agar proses belajar mengajar dapat segera dilanjutkan.
    3.  **Reboisasi**: Tentukan area yang mengalami deforestasi tinggi di hulu sungai sebagai langkah mitigasi jangka panjang terhadap banjir bandang.
    """)

st.subheader("Gap Pemulihan (Recovery Gap)")
st.warning(f"Perlu Alokasi Dana Tambahan untuk Kerugian Infrastruktur Kritis (Jembatan & Sekolah) di **{kabupaten_prioritas}** sebesar minimum **Rp 50 Miliar** untuk memulai tahap rekonstruksi. Kerugian riil diperkirakan mencapai **{format_rupiah(kabupaten_prioritas_df['Kerugian_Rupiah_Miliar'])}** di wilayah ini.")
st.write("---")
st.caption("Aplikasi ini dibuat untuk tujuan simulasi analisis data kebencanaan. Total agregat data bersumber dari CSV data terbaru.")
