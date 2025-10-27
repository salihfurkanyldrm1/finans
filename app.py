import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db, auth
import json

# =============================
# 🔧 Firebase Bağlantısı (sadece bir kez initialize)
# =============================
if not firebase_admin._apps:
    cred_dict = json.loads(st.secrets["FIREBASE"]["FIREBASE_KEY"])
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        "databaseURL": st.secrets["FIREBASE"]["DATABASE_URL"]
    })

# =============================
# 🧑‍💻 Kullanıcı Girişi (Firebase Auth)
# =============================
st.title("💸 Kişisel Finans Takip Uygulaması")
st.write("Her kullanıcı kendi verilerini görür, tüm kayıtlar bulutta saklanır ☁️")

# Eğer daha önce giriş yapıldıysa session_state kullan
if 'uid' not in st.session_state:
    email = st.text_input("Email girin:")
    sifre = st.text_input("Şifre girin:", type="password")

    if st.button("Giriş Yap"):
        try:
            # Firebase Admin SDK email doğrulama
            user = auth.get_user_by_email(email)
            st.success(f"Giriş başarılı! Hoşgeldiniz {user.email}")
            st.session_state['uid'] = user.uid
        except auth.UserNotFoundError:
            st.error("Kullanıcı bulunamadı. Emailinizi kontrol edin.")
        except Exception as e:
            st.error(f"Hata: {e}")

# Giriş yapılmadan devam etme
if 'uid' not in st.session_state:
    st.stop()

# UID tabanlı kullanıcı referansı
user_ref = db.reference(f"kullanicilar/{st.session_state['uid']}")

# =============================
# 📊 Veri Yükleme
# =============================
veri = user_ref.get()
df = pd.DataFrame(veri) if veri else pd.DataFrame(columns=["Tarih", "Tür", "Kategori", "Tutar", "Gider Türü"])

# =============================
# 📝 Yeni Kayıt Ekleme
# =============================
st.header("📝 Yeni Kayıt Ekle")

tur = st.radio("Tür seçin:", ["Gelir", "Gider"], horizontal=True)

if tur == "Gelir":
    kategori = st.selectbox("Kategori seçin:", ["Maaş", "Ek Gelir", "Yatırım", "Diğer"])
    gider_turu = "-"
else:
    kategori = st.selectbox("Kategori seçin:", ["Market", "Fatura", "Kişisel Bakım", "Ulaşım", "Eğitim", "Sağlık", "Cafe/Restaurant", "Diğer"])
    gider_turu = st.radio("Gider türü seçin:", ["Zorunlu", "Keyfi"])

tutar = st.number_input("Tutar (₺)", min_value=0.0, step=10.0)

if st.button("💾 Kaydı Ekle"):
    yeni_kayit = {
        "Tarih": datetime.now().strftime("%Y-%m-%d"),
        "Tür": tur,
        "Kategori": kategori,
        "Tutar": tutar,
        "Gider Türü": gider_turu
    }
    kayitlar = df.to_dict(orient="records") if not df.empty else []
    kayitlar.append(yeni_kayit)
    user_ref.set(kayitlar)
    st.success("✅ Kayıt başarıyla eklendi!")
    st.experimental_rerun()

# =============================
# 📋 Kayıtları Göster
# =============================
st.header("📊 Kayıtlar")
if not df.empty:
    st.dataframe(df)
else:
    st.info("Henüz kayıt yok.")

# =============================
# 🗑️ Kayıt Silme
# =============================
st.subheader("🗑️ Kayıt Sil")
if not df.empty:
    secilen_index = st.selectbox("Silmek istediğiniz kayıt numarasını seçin:", df.index)
    if st.button("❌ Kaydı Sil"):
        df = df.drop(secilen_index).reset_index(drop=True)
        user_ref.set(df.to_dict(orient="records"))
        st.success("🧹 Kayıt başarıyla silindi!")
        st.experimental_rerun()

# =============================
# 📈 Anlık Analiz
# =============================
st.header("📈 Anlık Finans Analizi")
if not df.empty:
    df["Tutar"] = pd.to_numeric(df["Tutar"], errors="coerce").fillna(0)
    toplam_gelir = df[df["Tür"]=="Gelir"]["Tutar"].sum()
    toplam_gider = df[df["Tür"]=="Gider"]["Tutar"].sum()
    bakiye = toplam_gelir - toplam_gider

    zorunlu_gider = df[(df["Tür"]=="Gider") & (df["Gider Türü"]=="Zorunlu")]["Tutar"].sum()
    keyfi_gider = df[(df["Tür"]=="Gider") & (df["Gider Türü"]=="Keyfi")]["Tutar"].sum()

    st.metric("Toplam Gelir", f"{toplam_gelir:.2f} ₺")
    st.metric("Toplam Gider", f"{toplam_gider:.2f} ₺")
    st.metric("Kalan Bakiye", f"{bakiye:.2f} ₺")

    st.write("Zorunlu ve Keyfi Gider Dağılımı:")
    gider_turleri = {"Zorunlu": zorunlu_gider, "Keyfi": keyfi_gider}
    plt.figure(figsize=(5,5))
    plt.pie(gider_turleri.values(), labels=gider_turleri.keys(), autopct="%1.1f%%")
    st.pyplot(plt)

    # Son 30 günlük gelir/gider grafiği
    df["Tarih"] = pd.to_datetime(df["Tarih"])
    son_30gun = datetime.now() - timedelta(days=30)
    son_kayitlar = df[df["Tarih"] >= son_30gun]
    gunluk_toplam = son_kayitlar.groupby(["Tarih","Tür"])["Tutar"].sum().unstack().fillna(0)
    st.write("Son 30 Günlük Gelir/Gider Grafiği:")
    st.line_chart(gunluk_toplam)
else:
    st.info("Analiz için yeterli veri bulunamadı.")

