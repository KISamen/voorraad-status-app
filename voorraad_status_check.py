import pandas as pd
import streamlit as st
from io import BytesIO
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
    
    # Strip kolomnamen om spaties te verwijderen en naar kleine letters converteren
    voorraad_df.columns = voorraad_df.columns.str.strip().str.lower()
    webshop_df.columns = webshop_df.columns.str.strip().str.lower()
    
    # Kolomnamen mappen inclusief varianten
    voorraad_df.rename(columns={"nr.": "Stiercode", "beschikbare voorraad": "Voorraad", "rasomschrijving": "Ras", "naam stier": "naam stier"}, inplace=True)
    webshop_df.rename(columns={"stiercode nl / ki code": "Stiercode", "rasomschrijving": "Ras", "status": "Status", "naam stier": "naam stier"}, inplace=True)
    
    # Samenvoegen op Stiercode
    merged_df = pd.merge(voorraad_df, webshop_df, on="Stiercode", how="outer")
    
    # Corrigeren van de Ras-kolom (Ras_x en Ras_y samenvoegen)
    if "Ras_y" in merged_df.columns:
        merged_df["Ras"] = merged_df["Ras_y"].combine_first(merged_df["Ras_x"])
    elif "Ras_x" in merged_df.columns:
        merged_df.rename(columns={"Ras_x": "Ras"}, inplace=True)
    
    # Vullen van missende waarden in de Ras-kolom
    merged_df["Ras"] = merged_df["Ras"].fillna("Onbekend")
    
    # Corrigeren van de Naam Stier-kolom (Correct toevoegen vóór verwijdering)
    merged_df["Naam Stier"] = merged_df.get("naam stier_y", "").combine_first(merged_df.get("naam stier_x", ""))
    
    # Drop overbodige kolommen
    merged_df.drop(columns=[col for col in ["Ras_x", "Ras_y", "naam stier_x", "naam stier_y"] if col in merged_df.columns], inplace=True)
    
    # Status en Voorraad normaliseren
    merged_df["Status"] = merged_df["Status"].astype(str).str.strip().str.upper()
    merged_df["Voorraad"] = merged_df["Voorraad"].fillna(0)
    
    # Stiercode als string weergeven zonder komma's
    merged_df["Stiercode"] = merged_df["Stiercode"].astype(str).str.strip()
    
    # Unieke rassen ophalen en sorteren
    unieke_rassen = sorted(merged_df["Ras"].dropna().unique())
    
    # Drempelwaarden per ras instellen
    for ras in unieke_rassen:
        if ras.lower().strip() in speciale_rassen:
            drempelwaarden[ras] = st.sidebar.number_input(f"Drempelwaarde voor {ras}", min_value=0, value=50)
        else:
            drempelwaarden[ras] = st.sidebar.number_input(f"Drempelwaarde voor {ras}", min_value=0, value=10)
    
    # Functie om te bepalen in welke lijst een stier hoort
    def bepaal_status(row):
        voorraad = row.get("Voorraad", 0)  # Alleen correcte voorraadkolom gebruiken
        status = row.get("Status", "").strip().upper()
        ras = row.get("Ras", "Onbekend").strip().lower()
        drempel = drempelwaarden.get(ras, default_drempel)
        
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
    
    # Overzicht aanpassingen
    st.subheader("Overzicht aanpassingen")
    overzicht_data = {
        "Aantal stieren met beperkte voorraad": (merged_df["Resultaat"] == "Stieren met beperkte voorraad").sum(),
        "Aantal stieren mag weer online": (merged_df["Resultaat"] == "Voorraad weer voldoende").sum(),
        "Aantal stieren toevoegen aan webshop": (merged_df["Resultaat"] == "Toevoegen aan Webshop").sum()
    }
    overzicht_df = pd.DataFrame([overzicht_data])
    st.dataframe(overzicht_df)
    
    # Opslaan van resultaten
    resultaten = {}
    for categorie, titel in zip(["Stieren met beperkte voorraad",
                                 "Voorraad weer voldoende",
                                 "Toevoegen aan Webshop",
                                 "Concept: Toevoegen aan Webshop",
                                 "Concept: Lage voorraad"],
                                ["Beperkte voorraad",
                                 "Mag weer online", "Toevoegen webshop",
                                 "Concept toevoegen", "Concept lage voorraad"]):
        subset = merged_df[merged_df["Resultaat"] == categorie].sort_values(by=["Ras"])
        if not subset.empty:
            st.subheader(titel)
            st.dataframe(subset[["Stiercode", "Naam Stier", "Ras", "Voorraad", "Status"]])
            resultaten[titel[:31]] = subset[["Stiercode", "Naam Stier", "Ras", "Voorraad", "Status"]]  # Sheetnaam max 31 tekens
