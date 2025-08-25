import streamlit as st
import pandas as pd
from firebase_admin import credentials, firestore
import firebase_admin
from datetime import datetime

# 🔐 Firebase via Streamlit Secrets
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 📥 Data ophalen uit Firestore
@st.cache_data(ttl=600)
def fetch_data():
    data = []
    kastickets = db.collection("kastickets_raw").stream()

    for ticket_doc in kastickets:
        items = ticket_doc.reference.collection("items").stream()
        for item in items:
            d = item.to_dict()
            try:
                data.append({
                    "Datum": pd.to_datetime(d["datum"], format="%Y-%m-%d"),
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
    st.warning("⚠️ Geen data gevonden in Firestore.")
else:
    # 📅 Maandkolom toevoegen
    df = df.assign(Maand=df["Datum"].dt.to_period("M"))

    # 💰 Totale uitgaven per maand
    df = df.assign(Maand=df["Datum"].dt.to_period("M"))
    uitgaven = df.groupby("Maand")["Totaal"].sum()

    # 💚 Totale korting per maand
    if "korting" in df.columns:
        kortingen = df.groupby("Maand")["korting"].sum()
    else:
        kortingen = pd.Series(0, index=uitgaven.index)

    # 📅 Format index
    uitgaven.index = uitgaven.index.to_timestamp()
    kortingen.index = kortingen.index.to_timestamp()
    labels = uitgaven.index.strftime("%b %Y")

    # 📊 Combineer in één DataFrame
    grafiek_df = pd.DataFrame({
        "Uitgaven": uitgaven.values,
        "Korting": -kortingen.values  # negatief voor visuele impact
    }, index=labels)

    st.subheader("💰 Totale uitgaven per maand (inclusief kortingen)")
    st.bar_chart(grafiek_df)

    # 📦 Prijs per artikel per maand
    artikel = st.selectbox("📦 Kies een artikel", sorted(df["Artikel"].unique()))
    artikel_df = df.query("Artikel == @artikel").copy()
    artikel_df = artikel_df.assign(Maand=artikel_df["Datum"].dt.to_period("M"))
    prijs_per_maand = artikel_df.groupby("Maand")["Prijs"].mean()
    prijs_per_maand.index = prijs_per_maand.index.to_timestamp()
    prijs_per_maand.index = prijs_per_maand.index.strftime("%b %Y")

    st.subheader(f"📈 Gemiddelde prijs per maand voor: {artikel}")
    st.line_chart(prijs_per_maand)

    # 📋 Optioneel: ruwe data tonen
    with st.expander("📋 Toon ruwe data"):
        st.dataframe(df.sort_values("Datum", ascending=False))
