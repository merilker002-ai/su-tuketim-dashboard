import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ======================================================================
# 🚀 STREAMLIT UYGULAMASI
# ======================================================================

st.set_page_config(
    page_title="Su Tüketim Davranış Analiz Dashboard",
    page_icon="💧",
    layout="wide"
)

# ======================================================================
# 📊 VERİ İŞLEME FONKSİYONLARI
# ======================================================================

@st.cache_data
def load_and_analyze_data():
    """Veriyi yükler ve analiz eder"""
    try:
        df = pd.read_excel('yavuz.xlsx')
        st.success(f"✅ Veri başarıyla yüklendi: {len(df)} kayıt")
    except Exception as e:
        st.error(f"❌ Dosya yükleme hatası: {e}")
        return None, None, None

    # Tarih formatını düzelt
    df['ILK_OKUMA_TARIHI'] = pd.to_datetime(df['ILK_OKUMA_TARIHI'], format='%Y%m%d', errors='coerce')
    df['OKUMA_TARIHI'] = pd.to_datetime(df['OKUMA_TARIHI'], format='%Y%m%d', errors='coerce')
    
    # Tesisat numarası olan kayıtları filtrele
    df = df[df['TESISAT_NO'].notnull()]
    
    # Davranış analizi fonksiyonları
    def perform_behavior_analysis(df):
        son_okumalar = df.sort_values('OKUMA_TARIHI').groupby('TESISAT_NO').last().reset_index()
        son_okumalar['OKUMA_PERIYODU_GUN'] = (son_okumalar['OKUMA_TARIHI'] - son_okumalar['ILK_OKUMA_TARIHI']).dt.days
        son_okumalar['OKUMA_PERIYODU_GUN'] = son_okumalar['OKUMA_PERIYODU_GUN'].clip(lower=1, upper=365)
        son_okumalar['GUNLUK_ORT_TUKETIM_m3'] = son_okumalar['AKTIF_m3'] / son_okumalar['OKUMA_PERIYODU_GUN']
        son_okumalar['GUNLUK_ORT_TUKETIM_m3'] = son_okumalar['GUNLUK_ORT_TUKETIM_m3'].clip(lower=0.001, upper=100)
        return son_okumalar

    son_okumalar = perform_behavior_analysis(df)
    
    # Zone analizi
    zone_analizi = None
    if 'KARNE_NO' in df.columns:
        ekim_2024_df = df[(df['OKUMA_TARIHI'].dt.month == 10) & (df['OKUMA_TARIHI'].dt.year == 2024)]
        if len(ekim_2024_df) == 0:
            ekim_2024_df = df.copy()
        
        zone_analizi = ekim_2024_df.groupby('KARNE_NO').agg({
            'TESISAT_NO': 'count',
            'AKTIF_m3': 'sum',
            'TOPLAM_TUTAR': 'sum'
        }).reset_index()
        zone_analizi.columns = ['KARNE_NO', 'TESISAT_SAYISI', 'TOPLAM_TUKETIM', 'TOPLAM_GELIR']

    return df, son_okumalar, zone_analizi

# ======================================================================
# 🎨 STREAMLIT ARAYÜZ
# ======================================================================

# Başlık
st.title("💧 Su Tüketim Davranış Analiz Dashboard")

# Veriyi yükle
df, son_okumalar, zone_analizi = load_and_analyze_data()

# Genel Metrikler
if son_okumalar is not None:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Toplam Tesisat",
            value=f"{len(son_okumalar):,}"
        )
    
    with col2:
        st.metric(
            label="💧 Toplam Tüketim",
            value=f"{son_okumalar['AKTIF_m3'].sum():,.0f} m³"
        )
    
    with col3:
        st.metric(
            label="💰 Toplam Gelir",
            value=f"{son_okumalar['TOPLAM_TUTAR'].sum():,.0f} TL"
        )
    
    with col4:
        st.metric(
            label="📈 Ortalama Tüketim",
            value=f"{son_okumalar['AKTIF_m3'].mean():.1f} m³"
        )

# Tab Menü
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Genel Görünüm", 
    "🗺️ Zone Analizi", 
    "🔍 Detaylı Analiz", 
    "📊 İleri Analiz"
])

with tab1:
    if son_okumalar is not None:
        col1, col2 = st.columns(2)
        
        with col1:
            # Tüketim Dağılım Grafiği
            fig1 = px.histogram(son_okumalar, x='GUNLUK_ORT_TUKETIM_m3', 
                              title='Günlük Tüketim Dağılımı',
                              labels={'GUNLUK_ORT_TUKETIM_m3': 'Günlük Tüketim (m³)'},
                              color_discrete_sequence=['#3498DB'])
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Tüketim-Tutar İlişkisi
            fig2 = px.scatter(son_okumalar, x='AKTIF_m3', y='TOPLAM_TUTAR',
                            title='Tüketim-Tutar İlişkisi',
                            labels={'AKTIF_m3': 'Tüketim (m³)', 'TOPLAM_TUTAR': 'Toplam Tutar (TL)'},
                            color_discrete_sequence=['#2ECC71'])
            st.plotly_chart(fig2, use_container_width=True)
        
        # Zaman Serisi Grafiği
        if df is not None:
            df_aylik = df.groupby(df['OKUMA_TARIHI'].dt.to_period('M')).agg({
                'AKTIF_m3': 'sum',
                'TOPLAM_TUTAR': 'sum'
            }).reset_index()
            df_aylik['OKUMA_TARIHI'] = df_aylik['OKUMA_TARIHI'].dt.to_timestamp()

            fig3 = make_subplots(specs=[[{"secondary_y": True}]])
            fig3.add_trace(
                go.Scatter(x=df_aylik['OKUMA_TARIHI'], y=df_aylik['AKTIF_m3'], 
                          name="Tüketim (m³)", line=dict(color='blue')),
                secondary_y=False,
            )
            fig3.add_trace(
                go.Scatter(x=df_aylik['OKUMA_TARIHI'], y=df_aylik['TOPLAM_TUTAR'], 
                          name="Gelir (TL)", line=dict(color='green')),
                secondary_y=True,
            )
            fig3.update_layout(title_text="Aylık Tüketim ve Gelir Trendi")
            fig3.update_xaxes(title_text="Tarih")
            fig3.update_yaxes(title_text="Tüketim (m³)", secondary_y=False)
            fig3.update_yaxes(title_text="Gelir (TL)", secondary_y=True)
            st.plotly_chart(fig3, use_container_width=True)

with tab2:
    if zone_analizi is not None:
        col1, col2 = st.columns(2)
        
        with col1:
            # Zone Tüketim Dağılımı
            fig4 = px.pie(zone_analizi, values='TOPLAM_TUKETIM', names='KARNE_NO',
                        title='Zone Bazlı Tüketim Dağılımı')
            st.plotly_chart(fig4, use_container_width=True)
        
        with col2:
            # Zone Tesisat Sayısı
            fig5 = px.bar(zone_analizi, x='KARNE_NO', y='TESISAT_SAYISI',
                        title='Zone Bazlı Tesisat Sayısı',
                        labels={'KARNE_NO': 'Zone', 'TESISAT_SAYISI': 'Tesisat Sayısı'},
                        color_discrete_sequence=['#E74C3C'])
            st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("Zone verisi bulunamadı")

with tab3:
    if son_okumalar is not None:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Filtreleme Seçenekleri")
            
            # Tüketim Slider
            tuketim_range = st.slider(
                "Tüketim Aralığı (m³)",
                min_value=0,
                max_value=100,
                value=[0, 100],
                help="Tüketim değerine göre filtreleme yapın"
            )
            
            # Sıralama Seçeneği
            siralama = st.selectbox(
                "Sıralama Türü",
                options=['En Yüksek Tüketim', 'En Düşük Tüketim'],
                index=0
            )
        
        with col2:
            st.subheader("Tesisat Tablosu")
            
            # Filtreleme
            min_tuketim, max_tuketim = tuketim_range
            filtreli_veri = son_okumalar[
                (son_okumalar['AKTIF_m3'] >= min_tuketim) & 
                (son_okumalar['AKTIF_m3'] <= max_tuketim)
            ]
            
            # Sıralama
            if siralama == 'En Yüksek Tüketim':
                gosterilecek_veri = filtreli_veri.nlargest(10, 'AKTIF_m3')
            else:
                gosterilecek_veri = filtreli_veri.nsmallest(10, 'AKTIF_m3')
            
            # Tablo gösterimi
            st.dataframe(
                gosterilecek_veri[['TESISAT_NO', 'AKTIF_m3', 'TOPLAM_TUTAR', 'GUNLUK_ORT_TUKETIM_m3']].round(3),
                use_container_width=True
            )

with tab4:
    if son_okumalar is not None:
        col1, col2 = st.columns(2)
        
        with col1:
            # Kategori Dağılımı
            kategoriler = pd.cut(son_okumalar['AKTIF_m3'], 
                                bins=[0, 10, 50, 100, 500, float('inf')],
                                labels=['Çok Düşük (0-10)', 'Düşük (10-50)', 'Orta (50-100)', 
                                       'Yüksek (100-500)', 'Çok Yüksek (500+)'])
            kategori_dagilim = kategoriler.value_counts().sort_index()
            
            fig6 = px.bar(x=kategori_dagilim.index.astype(str), y=kategori_dagilim.values,
                        title='Tüketim Kategori Dağılımı',
                        labels={'x': 'Tüketim Kategorisi', 'y': 'Tesisat Sayısı'},
                        color_discrete_sequence=['#9B59B6'])
            st.plotly_chart(fig6, use_container_width=True)
        
        with col2:
            # Korelasyon Matrisi
            numeric_cols = son_okumalar.select_dtypes(include=[np.number]).columns
            corr_matrix = son_okumalar[numeric_cols].corr()
            
            fig7 = px.imshow(corr_matrix, 
                           title='Korelasyon Matrisi',
                           color_continuous_scale='RdBu_r',
                           aspect="auto")
            st.plotly_chart(fig7, use_container_width=True)
        
        # Aykırı Değer Analizi
        fig8 = px.box(son_okumalar, y='AKTIF_m3', 
                     title='Tüketim Dağılımı - Aykırı Değer Analizi',
                     color_discrete_sequence=['#F39C12'])
        st.plotly_chart(fig8, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("💧 Su Tüketim Analiz Sistemi | Streamlit Dashboard")
