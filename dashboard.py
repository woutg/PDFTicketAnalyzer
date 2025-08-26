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
    # 📅 Maandkolom
    df = df.assign(Maand=df["Datum"].dt.to_period("M"))
    df["Maand"] = df["Maand"].dt.to_timestamp()

    # 💸 Bruto uitgaven per maand
    bruto = df.groupby("Maand")["Totaal"].sum()

    # 💚 Kortingen per maand
    kortingen = df.groupby("Maand")["korting"].sum()

    # 🧮 Netto uitgaven = bruto - korting
    netto = bruto + kortingen

    # 📊 Combineer in één DataFrame
    labels = bruto.index.strftime("%b %Y")
    grafiek_df = pd.DataFrame({
        "Maand": labels,
        "Netto uitgaven": netto.values,
        "Korting": kortingen.values
    })

    # 🔄 Herstructureer voor Altair
    grafiek_melted = grafiek_df.melt("Maand", var_name="Type", value_name="Bedrag")

    # 🎨 Altair stacked bar chart
    chart = alt.Chart(grafiek_melted).mark_bar().encode(
        x=alt.X("Maand:N", title="Maand", sort=grafiek_df["Maand"].tolist()),
        y=alt.Y("Bedrag:Q", title="Bedrag (€)"),
        color=alt.Color("Type:N", scale=alt.Scale(domain=["Netto uitgaven", "Korting"], range=["#1f77b4", "#2ca02c"])),
        tooltip=["Maand", "Type", "Bedrag"]
    ).properties(
        title="💰 Effectieve uitgaven per maand (inclusief kortingen)",
        width=700,
        height=400
    )

    st.altair_chart(chart, use_container_width=True)

    # 📦 Prijs per artikel per maand
    artikel = st.selectbox("📦 Kies een artikel", sorted(df["Artikel"].unique()))
    artikel_df = df.query("Artikel == @artikel").copy()
    prijs_per_datum = artikel_df.groupby("Datum")["Prijs"].mean().reset_index()

    chart = alt.Chart(prijs_per_datum).mark_line(point=True).encode(
        x=alt.X("Datum:T", title="Day"),
        y=alt.Y("Prijs:Q", title="Bedrag (€)"),
        tooltip=["Datum", "Prijs"]
    ).properties(
        title=f"📈 Prijsontwikkeling voor: {artikel}",
        width=700,
        height=400
    )

    st.altair_chart(chart, use_container_width=True

    # 📋 Optioneel: ruwe data tonen
    with st.expander("📋 Toon ruwe data"):
        st.dataframe(df.sort_values("Datum", ascending=False))
