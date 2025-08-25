import streamlit as st
import pandas as pd
import altair as alt
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
                    "Totaal": float(d["totaal"]),
                    "korting": float(d.get("korting", 0.0))
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
    df["Maand"] = df["Maand"].dt.to_timestamp()

    # 💸 Uitgaven en 💚 Kortingen per maand
    uitgaven = df.groupby("Maand")["Totaal"].sum()
    kortingen = df.groupby("Maand")["korting"].sum() * -1  # negatief voor visuele impact

    # 📊 Combineer in één DataFrame
    grafiek_df = pd.DataFrame({
        "Maand": uitgaven.index,
        "Uitgaven": uitgaven.values,
        "Korting": kortingen.values
    })

    # 🔄 Herstructureer voor Altair
    grafiek_melted = grafiek_df.melt("Maand", var_name="Type", value_name="Bedrag")

    # 🎨 Altair stacked bar chart
    chart = alt.Chart(grafiek_melted).mark_bar().encode(
        x=alt.X("Maand:T", title="Maand"),
        y=alt.Y("Bedrag:Q", title="Bedrag (€)"),
        color=alt.Color("Type:N", scale=alt.Scale(domain=["Uitgaven", "Korting"], range=["#1f77b4", "#2ca02c"])),
        tooltip=["Maand", "Type", "Bedrag"]
    ).properties(
        title="💰 Totale uitgaven per maand (inclusief kortingen)",
        width=700,
        height=400
    )

    st.altair_chart(chart, use_container_width=True)

    # 📦 Prijs per artikel per maand
    artikel = st.selectbox("📦 Kies een artikel", sorted(df["Artikel"].unique()))
    artikel_df = df.query("Artikel == @artikel").copy()
    artikel_df = artikel_df.assign(Maand=artikel_df["Datum"].dt.to_period("M"))
    artikel_df["Maand"] = artikel_df["Maand"].dt.to_timestamp()
    prijs_per_maand = artikel_df.groupby("Maand")["Prijs"].mean()

    st.subheader(f"📈 Gemiddelde prijs per maand voor: {artikel}")
    st.line_chart(prijs_per_maand)

    # 📋 Optioneel: ruwe data tonen
    with st.expander("📋 Toon ruwe data"):
        st.dataframe(df.sort_values("Datum", ascending=False))
