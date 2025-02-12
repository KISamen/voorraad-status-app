import pandas as pd
import streamlit as st
import re

# Streamlit app configureren
st.title("Stieren Voorraadbeheer")

# Drempelwaarden per ras beheren
st.sidebar.header("Instellingen")
drempelwaarden = {}
default_drempel = 10  # Standaard op 10, tenzij specifiek aangepast

# Rassen waarvoor de drempelwaarde 50 moet zijn
speciale_rassen = {"red holstein", "holstein zwartbont", "jersey", "belgisch witblauw"}

# Upload bestanden
st.sidebar.subheader("Upload Bestanden")
webshop_file = st.sidebar.file_uploader("Upload Status Webshop (Excel)", type=["xlsx"])
voorraad_file = st.sidebar.file_uploader("Upload Beschikbare Voorraad Lablocaties (Excel)", type=["xlsx"])

if webshop_file and voorraad_file:
    # Inladen van de bestanden
    webshop_xls = pd.ExcelFile(webshop_file)
    voorraad_df = pd.read_excel(voorraad_file, sheet_name=0)  # Eerste sheet
    webshop_df = pd.read_excel(webshop_xls, sheet_name="Stieren")
    variaties_df = pd.read_excel(webshop_xls, sheet_name="Artikelvariaties")

    # Strip kolomnamen en converteren naar kleine letters
    voorraad_df.columns = voorraad_df.columns.str.strip().str.lower()
    webshop_df.columns = webshop_df.columns.str.strip().str.lower()
    variaties_df.columns = variaties_df.columns.str.strip().str.lower()

    # Kolommen hernoemen voor eenduidigheid
    voorraad_df.rename(columns={"nr.": "stiercode", "beschikbare voorraad": "voorraad", "rasomschrijving": "ras"}, inplace=True)
    webshop_df.rename(columns={"stiercode nl / ki code": "stiercode", "rasomschrijving": "ras", "status": "status"}, inplace=True)
    variaties_df.rename(columns={"stiercode": "stiercode", "nederland": "artikelvariaties_nl", "voorraad": "voorraad_variatie"}, inplace=True)

    # Samenvoegen van de voorraad en webshop data
    merged_df = pd.merge(voorraad_df, webshop_df, on="stiercode", how="outer")

    # Ras en naam samenvoegen als ze dubbel voorkomen
    if "ras_y" in merged_df.columns:
        merged_df["ras"] = merged_df["ras_y"].combine_first(merged_df["ras_x"])
        merged_df.drop(columns=["ras_x", "ras_y"], inplace=True)

    # Missende raswaarden invullen
    merged_df["ras"] = merged_df["ras"].fillna("Onbekend")

    # Voorraad normaliseren en numeriek maken
    merged_df["voorraad"] = pd.to_numeric(merged_df["voorraad"], errors='coerce').fillna(0)
    variaties_df["voorraad_variatie"] = pd.to_numeric(variaties_df["voorraad_variatie"], errors='coerce').fillna(0)

    # Unieke rassen ophalen en drempelwaarden instellen
    unieke_rassen = sorted(merged_df["ras"].dropna().unique())
    for ras in unieke_rassen:
        if ras.lower().strip() in speciale_rassen:
            drempelwaarden[ras] = st.sidebar.number_input(f"Drempelwaarde voor {ras}", min_value=0, value=50)
        else:
            drempelwaarden[ras] = st.sidebar.number_input(f"Drempelwaarde voor {ras}", min_value=0, value=10)

    # Functie om de status van een stier te bepalen
    def bepaal_status(row):
        stiercode = row["stiercode"]
        voorraad = row["voorraad"]
        status = row["status"]
        ras = row["ras"].strip().lower()
        drempel = drempelwaarden.get(ras, default_drempel)

        # Check of er een variatie bestaat (-m of -s)
        if re.search(r"-[ms]$", stiercode):
            variatie_info = variaties_df[variaties_df["stiercode"] == stiercode]

            if not variatie_info.empty:
                artikelvariatie_nl = variatie_info["artikelvariaties_nl"].values[0]
                voorraad_variatie = variatie_info["voorraad_variatie"].values[0]

                if voorraad_variatie < drempel and artikelvariatie_nl == "Ja":
                    return "Beperkte voorraad gesekst sperma"
                elif voorraad_variatie > drempel and artikelvariatie_nl == "Nee":
                    return "Mag weer online gesekst sperma"

        # Reguliere voorraadcontrole
        if status == "CONCEPT":
            return "Concept: Toevoegen aan Webshop" if voorraad > drempel else "Concept: Lage voorraad"

        if status not in ["ACTIVE", "ARCHIVE"]:
            return "Toevoegen aan Webshop" if voorraad > drempel else None

        if voorraad < drempel and status == "ACTIVE":
            return "Stieren met beperkte voorraad"
        elif voorraad > drempel and status == "ARCHIVE":
            return "Voorraad weer voldoende"

        return None

    # Status bepalen
    merged_df["Resultaat"] = merged_df.apply(bepaal_status, axis=1)

    # Overzicht van aanpassingen tonen
    st.subheader("Overzicht aanpassingen")
    overzicht_data = {
        "Aantal stieren met beperkte voorraad": (merged_df["Resultaat"] == "Stieren met beperkte voorraad").sum(),
        "Aantal stieren mag weer online": (merged_df["Resultaat"] == "Voorraad weer voldoende").sum(),
        "Aantal stieren toevoegen aan webshop": (merged_df["Resultaat"] == "Toevoegen aan Webshop").sum()
    }
    overzicht_df = pd.DataFrame([overzicht_data])
    st.dataframe(overzicht_df)

    # Resultaten tonen per categorie
    resultaten = {
        "Beperkte voorraad gesekst sperma": "Stieren met beperkte voorraad",
        "Mag weer online gesekst sperma": "Mag weer online gesekst sperma",
        "Toevoegen aan Webshop": "Toevoegen aan Webshop",
        "Concept: Toevoegen aan Webshop": "Concept: Toevoegen aan Webshop",
        "Concept: Lage voorraad": "Concept: Lage voorraad"
    }

    for titel, categorie in resultaten.items():
        subset = merged_df[merged_df["Resultaat"] == categorie].sort_values(by=["ras"])
        if not subset.empty:
            st.subheader(titel)
            st.dataframe(subset[["stiercode", "ras", "voorraad", "status"]])

    # Exportknop toevoegen
    if st.button("Download resultaten als Excel"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            for titel, categorie in resultaten.items():
                subset = merged_df[merged_df["Resultaat"] == categorie]
                if not subset.empty:
                    subset.to_excel(writer, sheet_name=titel[:31], index=False)
        output.seek(0)
        st.download_button("Klik hier om te downloaden", output, file_name="Voorraadbeheer_resultaten.xlsx")

