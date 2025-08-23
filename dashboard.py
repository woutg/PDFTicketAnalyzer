import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
 
# 🔐 Firebase setup
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 📥 Data ophalen uit Firestore
@st.cache_data
def fetch_data():
    docs = db.collection("kastickets").stream()
    data = []
    for doc in docs:
        d = doc.to_dict()
        try:
            data.append({
                "Datum": pd.to_datetime(d["datum"]),
                "Art.Nr": d["artikelnummer"],
                "Artikel": d["artikel"],
                "Aantal/gewicht": float(d["aantal_of_gewicht"]),
                "Prijs": float(d["prijs"]),
                "Totaal": float(d["totaal"])
            })
        except:
            continue
    return pd.DataFrame(data)

# 📊 Streamlit layout
st.set_page_config(page_title="Kasticket Dashboard", layout="wide")
st.title("🧾 Uitgavenanalyse kastickets")

df = fetch_data()

if df.empty:
    st.warning("Geen data gevonden in Firestore.")
else:
    df["Maand"] = df["Datum"].dt.to_period("M")

    # 💰 Totale uitgaven per maand
    maand_totalen = df.groupby("Maand")["Totaal"].sum()
    st.subheader("💰 Totale uitgaven per maand")
    st.bar_chart(maand_totalen)

    # 📦 Prijs per artikel per maand
    artikel = st.selectbox("📦 Kies een artikel", sorted(df["Artikel"].unique()))
    artikel_df = df[df["Artikel"] == artikel]
    artikel_df["Maand"] = artikel_df["Datum"].dt.to_period("M")
    prijs_per_maand = artikel_df.groupby("Maand")["Prijs"].mean()

    st.subheader(f"📈 Gemiddelde prijs per maand voor: {artikel}")
    st.line_chart(prijs_per_maand)

    # 📋 Optioneel: tabel tonen
    with st.expander("📋 Toon ruwe data"):
        st.dataframe(df.sort_values("Datum", ascending=False))
