import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os

# 🔐 Firebase setup
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 📄 PDF-analyse functie
def analyze_pdf(pdf_file):
    items = []
    datum = None

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split("\n")

            # Zoek datum
            if not datum:
                for l in lines:
                    if "2025" in l and ":" in l:
                        try:
                            parts = l.split()
                            datum = datetime.strptime(parts[1], "%d/%m/%Y")
                            break
                        except:
                            pass

            # Parse regels
            for l in lines:
                parts = l.split()
                if len(parts) < 5:
                    continue

                if parts[0] in ["A", "C"]:
                    artikelnummer = parts[1]
                    if "kg" in parts[-3]:
                        naam = " ".join(parts[2:-3])
                        gewicht = float(parts[-3].replace("kg", "").replace(",", "."))
                        prijs_per_kg = float(parts[-2].replace(",", "."))
                        totaal = float(parts[-1].replace(",", "."))
                        items.append([datum, artikelnummer, naam, gewicht, prijs_per_kg, totaal])
                    else:
                        naam = " ".join(parts[2:-3])
                        aantal = float(parts[-3].replace(",", "."))
                        prijs_per_stuk = float(parts[-2].replace(",", "."))
                        totaal = float(parts[-1].replace(",", "."))
                        items.append([datum, artikelnummer, naam, aantal, prijs_per_stuk, totaal])

    df = pd.DataFrame(items, columns=["Datum", "Art.Nr", "Artikel", "Aantal/gewicht", "Prijs", "Totaal"])
    return df, datum

# ☁️ Upload naar Firestore met bestandsnaam als ID
def upload_to_firestore(df, pdf_file):
    doc_id = os.path.splitext(os.path.basename(pdf_file))[0]
    doc_ref = db.collection("kastickets_raw").document(doc_id)

    if doc_ref.get().exists:
        print(f"⚠️ Kasticket '{doc_id}' bestaat al in Firestore. Upload wordt overgeslagen.")
        return

    for _, row in df.iterrows():
        item = {
            "datum": row["Datum"].strftime("%Y-%m-%d"),
            "artikelnummer": row["Art.Nr"],
            "artikel": row["Artikel"],
            "aantal_of_gewicht": row["Aantal/gewicht"],
            "prijs": row["Prijs"],
            "totaal": row["Totaal"]
        }
        doc_ref.collection("items").add(item)

    print(f"✅ Kasticket '{doc_id}' succesvol geüpload.")

# 📊 Analyse en visualisatie
def visualize_data(df):
    print("\n📋 Geëxtraheerde items:")
    print(df.head(10))

    df["Maand"] = pd.to_datetime(df["Datum"]).dt.to_period("M")
    maand_totalen = df.groupby("Maand")["Totaal"].sum()

    print("\n💰 Totale uitgaven per maand:")
    print(maand_totalen)

    plt.figure(figsize=(8,5))
    maand_totalen.plot(kind="bar", color="#4CAF50")
    plt.title("Totale uitgaven per maand")
    plt.xlabel("Maand")
    plt.ylabel("€")
    plt.tight_layout()
    plt.show()

# 🚀 Main flow
if __name__ == "__main__":
    pdf_file = "kasticket_9551_13-08-2025 19-24.pdf"
    df, datum = analyze_pdf(pdf_file)
    upload_to_firestore(df, pdf_file)
    visualize_data(df)
